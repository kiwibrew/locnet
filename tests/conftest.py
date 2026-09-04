import asyncio
import shutil
from pathlib import Path

import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_database_session
from app.main import create_app


def upgrade_test_database(database_url: str) -> None:
    original_database_url = settings.database_url
    settings.database_url = database_url
    try:
        alembic_config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
        command.upgrade(alembic_config, "head")
    finally:
        settings.database_url = original_database_url


@pytest_asyncio.fixture
async def database_session(tmp_path):
    database_path = tmp_path / "test.db"
    shutil.copyfile(settings.seed_database_path, database_path)
    database_url = f"sqlite+aiosqlite:///{database_path}"
    await asyncio.to_thread(upgrade_test_database, database_url)
    engine = create_async_engine(database_url)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        transaction = await session.begin()
        yield session
        await transaction.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def application(database_session: AsyncSession):
    application = create_app()

    async def override_database_session():
        yield database_session

    application.dependency_overrides[get_database_session] = override_database_session
    yield application
    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(application):
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
        follow_redirects=False,
    ) as test_client:
        yield test_client
