from collections.abc import Mapping
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


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

    async def store_solar_cache(
        self,
        latitude: float,
        longitude: float,
        solar_stats: Mapping[str, float],
    ) -> None:
        async with self.session.begin_nested():
            await self.session.execute(
                text(
                    """
                    INSERT INTO Solar_cache (
                        latitude,
                        longitude,
                        min_sun,
                        max_no_sun_days,
                        annual_no_sun_days,
                        avg_temp,
                        min_temp,
                        max_temp
                    ) VALUES (
                        :latitude,
                        :longitude,
                        :min_sun,
                        :max_no_sun_days,
                        :annual_no_sun_days,
                        :avg_temp,
                        :min_temp,
                        :max_temp
                    )
                    """
                ),
                {"latitude": latitude, "longitude": longitude, **solar_stats},
            )
