import unittest

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.repositories import DataRepository
from app.services.reference_data import get_countries


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
                        max_temp NUMERIC,
                        sun_jan REAL,
                        sun_feb REAL,
                        sun_mar REAL,
                        sun_apr REAL,
                        sun_may REAL,
                        sun_jun REAL,
                        sun_jul REAL,
                        sun_aug REAL,
                        sun_sep REAL,
                        sun_oct REAL,
                        sun_nov REAL,
                        sun_dec REAL
                    )
                    """
                )
            )
            await connection.execute(
                text(
                    "INSERT INTO Countries (name, iso_3) VALUES ('New Zealand', 'NZL')"
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

    async def test_inserts_solar_cache_in_the_request_transaction(self) -> None:
        await self.repository.upsert_solar_cache(
            -41.29,
            174.78,
            {
                "min_sun": 2.5,
                "max_no_sun_days": 3.0,
                "annual_no_sun_days": 25.0,
                "avg_temp": 13.0,
                "min_temp": 5.0,
                "max_temp": 22.0,
                "sun_jan": 4.1,
                "sun_feb": 4.2,
                "sun_mar": 4.3,
                "sun_apr": 4.4,
                "sun_may": 4.5,
                "sun_jun": 4.6,
                "sun_jul": 4.7,
                "sun_aug": 4.8,
                "sun_sep": 4.9,
                "sun_oct": 5.0,
                "sun_nov": 5.1,
                "sun_dec": 5.2,
            },
        )

        rows = await self.repository.fetch_all(
            "SELECT latitude, longitude FROM Solar_cache"
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(float(rows[0]["latitude"]), -41.29)
        self.assertEqual(float(rows[0]["longitude"]), 174.78)

    async def test_updates_existing_solar_cache_records(self) -> None:
        solar_stats = {
            "min_sun": 2.5,
            "max_no_sun_days": 3.0,
            "annual_no_sun_days": 25.0,
            "avg_temp": 13.0,
            "min_temp": 5.0,
            "max_temp": 22.0,
            "sun_jan": 4.1,
            "sun_feb": 4.2,
            "sun_mar": 4.3,
            "sun_apr": 4.4,
            "sun_may": 4.5,
            "sun_jun": 4.6,
            "sun_jul": 4.7,
            "sun_aug": 4.8,
            "sun_sep": 4.9,
            "sun_oct": 5.0,
            "sun_nov": 5.1,
            "sun_dec": 5.2,
        }
        await self.repository.upsert_solar_cache(-41.29, 174.78, solar_stats)
        updated_stats = {**solar_stats, "sun_dec": 0.0}
        await self.repository.upsert_solar_cache(-41.29, 174.78, updated_stats)

        rows = await self.repository.get_solar_cache_records(-41.29, 174.78)

        self.assertEqual(len(rows), 1)
        self.assertEqual(float(rows[0]["sun_dec"]), 0.0)


if __name__ == "__main__":
    unittest.main()
