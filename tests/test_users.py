import unittest

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models import Base
from app.repositories import UserRepository
from app.services.authentication import SessionTokenService
from app.services.users import (
    ApiAccessProhibited,
    EmailAlreadyExists,
    InvalidCredentials,
    LifecycleOperationProhibited,
    UserService,
)


class UserServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        self.session = AsyncSession(self.engine, expire_on_commit=False)
        self.transaction = await self.session.begin()
        self.repository = UserRepository(self.session)
        self.service = UserService(self.repository)

    async def asyncTearDown(self) -> None:
        await self.transaction.rollback()
        await self.session.close()
        await self.engine.dispose()

    async def test_creates_a_normalized_user_without_api_access(self) -> None:
        user = await self.service.create_user(
            "Person@Example.COM",
            "correct horse battery staple",
        )

        self.assertEqual(user.email, "person@example.com")
        self.assertFalse(user.api_access_enabled)
        self.assertIsNone(user.bearer_token_hash)
        self.assertNotEqual(user.password_hash, "correct horse battery staple")

        with self.assertRaises(EmailAlreadyExists):
            await self.service.create_user(
                "person@example.com",
                "another good password",
            )

    async def test_authenticates_password_and_browser_session(self) -> None:
        user = await self.service.create_user(
            "person@example.com",
            "correct horse battery staple",
        )

        authenticated = await self.service.authenticate_password(
            "PERSON@example.com",
            "correct horse battery staple",
        )
        self.assertEqual(authenticated.id, user.id)
        self.assertIsNotNone(authenticated.last_login_at)

        with self.assertRaises(InvalidCredentials):
            await self.service.authenticate_password(
                "person@example.com",
                "incorrect password",
            )

        tokens = SessionTokenService("test-secret")
        session_token = tokens.create(user.email)
        session_user = await self.service.authenticate_session(session_token, tokens)
        self.assertEqual(session_user.id, user.id)

        with self.assertRaises(InvalidCredentials):
            await self.service.authenticate_session("not-a-jwt", tokens)

    async def test_api_access_is_opt_in_revocable_and_stores_only_a_digest(self) -> None:
        user = await self.service.create_user(
            "api@example.com",
            "correct horse battery staple",
        )

        first_issue = await self.service.enable_api_access(user.id)
        self.assertTrue(user.api_access_enabled)
        self.assertNotEqual(user.bearer_token_hash, first_issue.token)
        self.assertEqual(
            user.bearer_token_hash,
            self.service.token_hash(first_issue.token),
        )
        self.assertEqual(
            (await self.service.authenticate_api_token(first_issue.token)).id,
            user.id,
        )

        replacement = await self.service.regenerate_api_token(user.id)
        with self.assertRaises(InvalidCredentials):
            await self.service.authenticate_api_token(first_issue.token)
        self.assertEqual(
            (await self.service.authenticate_api_token(replacement.token)).id,
            user.id,
        )

        await self.service.disable_api_access(user.id)
        with self.assertRaises(InvalidCredentials):
            await self.service.authenticate_api_token(replacement.token)

    async def test_administrator_cannot_receive_an_api_token(self) -> None:
        administrator = await self.service.create_user(
            "admin@example.com",
            "correct horse battery staple",
            is_admin=True,
        )

        with self.assertRaises(ApiAccessProhibited):
            await self.service.enable_api_access(administrator.id)

    async def test_protects_the_last_active_administrator(self) -> None:
        administrator = await self.service.create_user(
            "admin@example.com",
            "correct horse battery staple",
            is_admin=True,
        )
        actor = await self.service.create_user(
            "other-admin@example.com",
            "correct horse battery staple",
            is_admin=True,
        )

        await self.service.set_active(
            administrator.id,
            False,
            actor_user_id=actor.id,
        )
        with self.assertRaises(LifecycleOperationProhibited):
            await self.service.set_active(
                actor.id,
                False,
                actor_user_id=administrator.id,
            )


if __name__ == "__main__":
    unittest.main()
