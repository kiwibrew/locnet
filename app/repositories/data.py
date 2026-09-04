from collections.abc import Mapping
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

SOLAR_CACHE_COLUMNS = (
    "min_sun",
    "max_no_sun_days",
    "annual_no_sun_days",
    "avg_temp",
    "min_temp",
    "max_temp",
    "sun_jan",
    "sun_feb",
    "sun_mar",
    "sun_apr",
    "sun_may",
    "sun_jun",
    "sun_jul",
    "sun_aug",
    "sun_sep",
    "sun_oct",
    "sun_nov",
    "sun_dec",
)


class DataRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def fetch_all(
        self,
        sql_query: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(text(sql_query), parameters or {})
        return [dict(row) for row in result.mappings().all()]

    async def get_solar_cache_records(
        self,
        latitude: float,
        longitude: float,
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                """
                SELECT min_sun, max_no_sun_days, annual_no_sun_days, avg_temp,
                       min_temp, max_temp, sun_jan, sun_feb, sun_mar, sun_apr,
                       sun_may, sun_jun, sun_jul, sun_aug, sun_sep, sun_oct,
                       sun_nov, sun_dec
                FROM Solar_cache
                WHERE latitude = :latitude AND longitude = :longitude
                """
            ),
            {"latitude": latitude, "longitude": longitude},
        )
        return [dict(row) for row in result.mappings().all()]

    async def upsert_solar_cache(
        self,
        latitude: float,
        longitude: float,
        solar_stats: Mapping[str, float | None],
    ) -> None:
        values = {
            "latitude": latitude,
            "longitude": longitude,
            **{column: solar_stats.get(column) for column in SOLAR_CACHE_COLUMNS},
        }
        async with self.session.begin_nested():
            updated = cast(
                CursorResult[Any],
                await self.session.execute(
                    text(
                        """
                        UPDATE Solar_cache
                        SET min_sun = :min_sun,
                            max_no_sun_days = :max_no_sun_days,
                            annual_no_sun_days = :annual_no_sun_days,
                            avg_temp = :avg_temp,
                            min_temp = :min_temp,
                            max_temp = :max_temp,
                            sun_jan = COALESCE(:sun_jan, sun_jan),
                            sun_feb = COALESCE(:sun_feb, sun_feb),
                            sun_mar = COALESCE(:sun_mar, sun_mar),
                            sun_apr = COALESCE(:sun_apr, sun_apr),
                            sun_may = COALESCE(:sun_may, sun_may),
                            sun_jun = COALESCE(:sun_jun, sun_jun),
                            sun_jul = COALESCE(:sun_jul, sun_jul),
                            sun_aug = COALESCE(:sun_aug, sun_aug),
                            sun_sep = COALESCE(:sun_sep, sun_sep),
                            sun_oct = COALESCE(:sun_oct, sun_oct),
                            sun_nov = COALESCE(:sun_nov, sun_nov),
                            sun_dec = COALESCE(:sun_dec, sun_dec)
                        WHERE latitude = :latitude AND longitude = :longitude
                        """
                    ),
                    values,
                ),
            )
            if updated.rowcount:
                return

            columns = ", ".join(("latitude", "longitude", *SOLAR_CACHE_COLUMNS))
            parameters = ", ".join(
                (
                    ":latitude",
                    ":longitude",
                    *(f":{column}" for column in SOLAR_CACHE_COLUMNS),
                )
            )
            await self.session.execute(
                text(f"INSERT INTO Solar_cache ({columns}) VALUES ({parameters})"),
                values,
            )
