import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from pydantic import EmailStr, TypeAdapter
from sqlalchemy.exc import IntegrityError

from app.models import User
from app.repositories import UserRepository
from app.services.authentication import (
    InvalidSessionToken,
    PasswordHasher,
    SessionTokenService,
)
from app.services.email import PasswordResetSender


class UserServiceError(Exception):
    pass


class UserNotFound(UserServiceError):
    pass


class EmailAlreadyExists(UserServiceError):
    pass


class InvalidCredentials(UserServiceError):
    pass


class ApiAccessProhibited(UserServiceError):
    pass


class ApiAccessAlreadyEnabled(UserServiceError):
    pass


class ApiAccessNotEnabled(UserServiceError):
    pass


class LifecycleOperationProhibited(UserServiceError):
    pass


class InvalidResetCode(UserServiceError):
    pass


@dataclass(frozen=True)
class IssuedApiToken:
    user: User
    token: str


class UserService:
    def __init__(
        self,
        repository: UserRepository,
        password_hasher: PasswordHasher | None = None,
    ) -> None:
        self.repository = repository
        self.password_hasher = password_hasher or PasswordHasher()

    @staticmethod
    def normalize_email(email: str) -> str:
        return str(TypeAdapter(EmailStr).validate_python(email)).lower()

    @staticmethod
    def validate_password(password: str) -> None:
        if not 8 <= len(password) <= 128:
            raise ValueError("Password length must be from 8 through 128 characters")

    @staticmethod
    def token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    async def create_user(
        self,
        email: str,
        password: str,
        *,
        is_admin: bool = False,
    ) -> User:
        normalized_email = self.normalize_email(email)
        self.validate_password(password)
        if await self.repository.get_by_email(normalized_email) is not None:
            raise EmailAlreadyExists

        user = User(
            email=normalized_email,
            password_hash=self.password_hasher.hash(password),
            is_admin=is_admin,
            api_access_enabled=False,
            bearer_token_hash=None,
        )
        try:
            return await self.repository.add(user)
        except IntegrityError as error:
            raise EmailAlreadyExists from error

    async def visible_users(self, current_user: User) -> list[User]:
        if current_user.is_admin:
            return await self.repository.list_users()
        return [current_user]

    async def get_user(self, user_id: int) -> User:
        return await self._get_user(user_id)

    async def authenticate_password(self, email: str, password: str) -> User:
        normalized_email = self.normalize_email(email)
        user = await self.repository.get_by_email(normalized_email)
        if (
            user is None
            or not user.is_active
            or not self.password_hasher.verify(password, user.password_hash)
        ):
            raise InvalidCredentials

        user.last_login_at = datetime.now(UTC)
        await self.repository.session.flush()
        return user

    async def authenticate_session(
        self,
        token: str,
        token_service: SessionTokenService,
    ) -> User:
        try:
            email = token_service.subject(token)
        except InvalidSessionToken as error:
            raise InvalidCredentials from error
        user = await self.repository.get_by_email(email)
        if user is None or not user.is_active:
            raise InvalidCredentials
        return user

    async def authenticate_api_token(self, token: str) -> User:
        user = await self.repository.get_by_bearer_token_hash(self.token_hash(token))
        if (
            user is None
            or not user.is_active
            or user.is_admin
            or not user.api_access_enabled
        ):
            raise InvalidCredentials
        return user

    async def request_password_reset(
        self,
        email: str,
        sender: PasswordResetSender,
    ) -> None:
        normalized_email = self.normalize_email(email)
        user = await self.repository.get_by_email(normalized_email)
        if user is None or not user.is_active:
            return

        code = secrets.token_urlsafe(48)
        user.reset_token_hash = self.token_hash(code)
        user.reset_token_expires_at = datetime.now(UTC) + timedelta(minutes=30)
        await self.repository.session.flush()

        try:
            await sender.send_password_reset(user.email, code)
        except Exception:
            user.reset_token_hash = None
            user.reset_token_expires_at = None
            await self.repository.session.flush()
            logging.exception("Password-reset delivery failed")

    async def reset_password(self, code: str, new_password: str) -> User:
        self.validate_password(new_password)
        user = await self.repository.get_by_reset_token_hash(self.token_hash(code))
        if user is None or not user.is_active or user.reset_token_expires_at is None:
            raise InvalidResetCode

        expires_at = user.reset_token_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= datetime.now(UTC):
            raise InvalidResetCode

        user.password_hash = self.password_hasher.hash(new_password)
        user.reset_token_hash = None
        user.reset_token_expires_at = None
        await self.repository.session.flush()
        return user

    async def enable_api_access(self, user_id: int) -> IssuedApiToken:
        user = await self._get_user(user_id)
        if user.is_admin:
            raise ApiAccessProhibited
        if user.api_access_enabled:
            raise ApiAccessAlreadyEnabled
        return await self._issue_api_token(user)

    async def regenerate_api_token(self, user_id: int) -> IssuedApiToken:
        user = await self._get_user(user_id)
        if user.is_admin:
            raise ApiAccessProhibited
        if not user.api_access_enabled:
            raise ApiAccessNotEnabled
        return await self._issue_api_token(user)

    async def disable_api_access(self, user_id: int) -> User:
        user = await self._get_user(user_id)
        user.api_access_enabled = False
        user.bearer_token_hash = None
        await self.repository.session.flush()
        return user

    async def set_active(
        self,
        user_id: int,
        is_active: bool,
        *,
        actor_user_id: int,
    ) -> User:
        user = await self._get_user(user_id)
        if user.id == actor_user_id and not is_active:
            raise LifecycleOperationProhibited
        if user.is_admin and user.is_active and not is_active:
            await self._protect_last_active_admin()
        user.is_active = is_active
        await self.repository.session.flush()
        return user

    async def set_admin(
        self,
        user_id: int,
        is_admin: bool,
        *,
        actor_user_id: int,
    ) -> User:
        user = await self._get_user(user_id)
        if user.id == actor_user_id:
            raise LifecycleOperationProhibited
        if user.is_admin and not is_admin and user.is_active:
            await self._protect_last_active_admin()
        user.is_admin = is_admin
        user.api_access_enabled = False
        user.bearer_token_hash = None
        await self.repository.session.flush()
        return user

    async def delete_user(self, user_id: int, *, actor_user_id: int) -> None:
        user = await self._get_user(user_id)
        if user.id == actor_user_id:
            raise LifecycleOperationProhibited
        if user.is_admin and user.is_active:
            await self._protect_last_active_admin()
        await self.repository.delete(user)

    async def delete_user_for_operations(self, email: str) -> None:
        user = await self.repository.get_by_email(self.normalize_email(email))
        if user is None:
            raise UserNotFound
        if user.is_admin and user.is_active:
            await self._protect_last_active_admin()
        await self.repository.delete(user)

    async def _get_user(self, user_id: int) -> User:
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise UserNotFound
        return user

    async def _issue_api_token(self, user: User) -> IssuedApiToken:
        token = secrets.token_urlsafe(32)
        user.api_access_enabled = True
        user.bearer_token_hash = self.token_hash(token)
        await self.repository.session.flush()
        return IssuedApiToken(user=user, token=token)

    async def _protect_last_active_admin(self) -> None:
        if await self.repository.count_active_admins() <= 1:
            raise LifecycleOperationProhibited
