import unittest

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.repositories import DataRepository
from library.helpers import get_countries


class DatabaseRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    CREATE TABLE Countries (
                        id INTEGER PRIMARY KEY,
                        name TEXT,
                        iso_3 TEXT
                    )
                    """
                )
            )
            await connection.execute(
                text(
                    """
                    CREATE TABLE Solar_cache (
                        id INTEGER PRIMARY KEY,
                        latitude NUMERIC,
                        longitude NUMERIC,
                        min_sun NUMERIC,
                        max_no_sun_days NUMERIC,
                        annual_no_sun_days NUMERIC,
                        avg_temp NUMERIC,
                        min_temp NUMERIC,
                        max_temp NUMERIC
                    )
                    """
                )
            )
            await connection.execute(
                text(
                    "INSERT INTO Countries (name, iso_3) "
                    "VALUES ('New Zealand', 'NZL')"
                )
            )

        self.session = AsyncSession(self.engine, expire_on_commit=False)
        self.transaction = await self.session.begin()
        self.repository = DataRepository(self.session)

    async def asyncTearDown(self) -> None:
        await self.transaction.rollback()
        await self.session.close()
        await self.engine.dispose()

    async def test_reads_rows_as_dictionaries(self) -> None:
        countries = await get_countries(self.repository)

        self.assertEqual(countries, {"New Zealand": "NZL"})

    async def test_writes_solar_cache_in_the_request_transaction(self) -> None:
        await self.repository.store_solar_cache(
            -41.29,
            174.78,
            {
                "min_sun": 2.5,
                "max_no_sun_days": 3.0,
                "annual_no_sun_days": 25.0,
                "avg_temp": 13.0,
                "min_temp": 5.0,
                "max_temp": 22.0,
            },
        )

        rows = await self.repository.fetch_all(
            "SELECT latitude, longitude FROM Solar_cache"
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(float(rows[0]["latitude"]), -41.29)
        self.assertEqual(float(rows[0]["longitude"]), 174.78)


if __name__ == "__main__":
    unittest.main()
