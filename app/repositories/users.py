from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_bearer_token_hash(self, token_hash: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.bearer_token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def get_by_reset_token_hash(self, token_hash: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.reset_token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def list_users(self) -> list[User]:
        result = await self.session.execute(select(User).order_by(User.email))
        return list(result.scalars())

    async def count_active_admins(self) -> int:
        result = await self.session.execute(
            select(func.count(User.id)).where(
                User.is_admin.is_(True),
                User.is_active.is_(True),
            )
        )
        return int(result.scalar_one())

    async def delete(self, user: User) -> None:
        await self.session.delete(user)
        await self.session.flush()
