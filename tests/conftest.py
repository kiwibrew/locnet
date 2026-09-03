import shutil

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_database_session
from app.main import create_app
from app.models import Base


@pytest_asyncio.fixture
async def database_session(tmp_path):
    database_path = tmp_path / "test.db"
    shutil.copyfile(settings.seed_database_path, database_path)
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

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
