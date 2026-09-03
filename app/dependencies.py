from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_database_session
from app.models import User
from app.repositories import DataRepository, UserRepository
from app.services import SessionTokenService, UserService
from app.services.email import (
    DisabledPasswordResetSender,
    PasswordResetSender,
    SmtpPasswordResetSender,
)
from app.services.users import InvalidCredentials


DatabaseSession = Annotated[AsyncSession, Depends(get_database_session)]
bearer_scheme = HTTPBearer(auto_error=False)


def get_data_repository(session: DatabaseSession) -> DataRepository:
    return DataRepository(session)


DataRepositoryDependency = Annotated[DataRepository, Depends(get_data_repository)]


def get_user_repository(session: DatabaseSession) -> UserRepository:
    return UserRepository(session)


UserRepositoryDependency = Annotated[UserRepository, Depends(get_user_repository)]


def get_user_service(repository: UserRepositoryDependency) -> UserService:
    return UserService(repository)


UserServiceDependency = Annotated[UserService, Depends(get_user_service)]


def build_session_token_service() -> SessionTokenService:
    secret = settings.jwt_secret.get_secret_value()
    if not secret:
        raise RuntimeError("JWT_SECRET must be configured")
    return SessionTokenService(
        secret,
        algorithm=settings.jwt_algorithm,
    )


def get_password_reset_sender() -> PasswordResetSender:
    if not settings.smtp_enabled:
        return DisabledPasswordResetSender()
    return SmtpPasswordResetSender(
        host=settings.smtp_host,
        port=settings.smtp_port,
        sender=settings.smtp_sender,
        username=settings.smtp_username,
        password=settings.smtp_password.get_secret_value(),
        starttls=settings.smtp_starttls,
    )


PasswordResetSenderDependency = Annotated[
    PasswordResetSender,
    Depends(get_password_reset_sender),
]


async def get_current_session_user(
    request: Request,
    service: UserServiceDependency,
) -> User | None:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        return None
    try:
        return await service.authenticate_session(token, build_session_token_service())
    except InvalidCredentials:
        return None


CurrentSessionUser = Annotated[User | None, Depends(get_current_session_user)]


async def get_current_active_session_user(
    user: CurrentSessionUser,
) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user


ActiveSessionUser = Annotated[User, Depends(get_current_active_session_user)]


async def get_current_api_principal(
    request: Request,
    service: UserServiceDependency,
    session_user: CurrentSessionUser,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> User:
    authorization = request.headers.get("authorization")
    if authorization is not None:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise _api_unauthorized()
        try:
            return await service.authenticate_api_token(credentials.credentials)
        except InvalidCredentials as error:
            raise _api_unauthorized() from error

    if session_user is None:
        raise _api_unauthorized()
    return session_user


ApiPrincipal = Annotated[User, Depends(get_current_api_principal)]


async def get_current_api_enabled_session_user(
    user: ActiveSessionUser,
) -> User:
    if user.is_admin or not user.api_access_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return user


ApiEnabledSessionUser = Annotated[
    User,
    Depends(get_current_api_enabled_session_user),
]


async def get_current_admin_user(user: ActiveSessionUser) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return user


CurrentAdminUser = Annotated[User, Depends(get_current_admin_user)]


def _api_unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        headers={"WWW-Authenticate": "Bearer"},
    )
