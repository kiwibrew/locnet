import asyncio
import os

from app.database import async_session_factory, engine
from app.repositories import UserRepository
from app.services.users import UserService


async def ensure_user(
    service: UserService,
    repository: UserRepository,
    *,
    email: str,
    password: str,
    is_admin: bool,
    api_access_enabled: bool,
) -> None:
    user = await repository.get_by_email(service.normalize_email(email))
    if user is None:
        user = await service.create_user(email, password, is_admin=is_admin)
    if api_access_enabled and not user.api_access_enabled:
        await service.enable_api_access(user.id)


async def seed() -> None:
    async with async_session_factory() as session:
        async with session.begin():
            repository = UserRepository(session)
            service = UserService(repository)
            await ensure_user(
                service,
                repository,
                email=os.environ["E2E_ADMIN_EMAIL"],
                password=os.environ["E2E_ADMIN_PASSWORD"],
                is_admin=True,
                api_access_enabled=False,
            )
            await ensure_user(
                service,
                repository,
                email=os.environ["E2E_USER_EMAIL"],
                password=os.environ["E2E_USER_PASSWORD"],
                is_admin=False,
                api_access_enabled=True,
            )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
