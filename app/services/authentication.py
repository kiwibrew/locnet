from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher


class PasswordHasher:
    def __init__(self) -> None:
        self._password_hash = PasswordHash((Argon2Hasher(), BcryptHasher()))

    def hash(self, password: str) -> str:
        return self._password_hash.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        return self._password_hash.verify(password, password_hash)


class InvalidSessionToken(Exception):
    pass


class SessionTokenService:
    def __init__(
        self,
        secret: str,
        *,
        algorithm: str = "HS256",
        lifetime: timedelta = timedelta(hours=8),
    ) -> None:
        if not secret:
            raise ValueError("A JWT secret is required")
        self.secret = secret
        self.algorithm = algorithm
        self.lifetime = lifetime

    def create(self, email: str, *, now: datetime | None = None) -> str:
        issued_at = now or datetime.now(UTC)
        return jwt.encode(
            {
                "sub": email,
                "exp": issued_at + self.lifetime,
                "credential_type": "session",
            },
            self.secret,
            algorithm=self.algorithm,
        )

    def subject(self, token: str) -> str:
        try:
            claims = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
            )
        except JWTError as error:
            raise InvalidSessionToken from error

        subject = claims.get("sub")
        if claims.get("credential_type") != "session" or not isinstance(subject, str):
            raise InvalidSessionToken
        return subject
