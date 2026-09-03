import unittest
from unittest.mock import AsyncMock, Mock, patch

import requests
from fastapi import HTTPException

from app.services.power import NASA_POWER_ERROR_DETAIL, get_solar_statistics


MONTHS = (
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def nasa_payload(annual_temperature=10.88):
    temperatures = dict(zip(MONTHS, (16.41, 16.31, 14.39, 11.43, 8.9, 6.53,
                                     5.64, 6.66, 8.19, 9.85, 12.07, 14.47)))
    temperatures["ANN"] = annual_temperature
    irradiance = dict(zip(MONTHS, (5.2, 5.1, 4.9, 4.4, 3.6, 3.1,
                                   3.2, 3.9, 4.6, 5.1, 5.5, 5.4)))
    irradiance["ANN"] = 4.5
    no_sun_days = dict(zip(MONTHS, (2.57, 2.34, 3.13, 3.57, 4.09, 3.45,
                                    2.98, 3.43, 3.33, 3.14, 3.32, 3.11)))
    no_sun_days["ANN"] = -999.0
    return {
        "properties": {
            "parameter": {
                "T2M": temperatures,
                "SI_TILTED_AVG_LATITUDE": irradiance,
                "EQUIV_NO_SUN_CONSEC_07": no_sun_days,
            }
        }
    }


class SolarCacheTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def repository(cache_records):
        repository = Mock()
        repository.fetch_all = AsyncMock(return_value=cache_records)
        repository.store_solar_cache = AsyncMock()
        return repository

    async def test_complete_cache_record_is_used_without_nasa_request(self):
        cache_record = {
            "min_sun": 3.1,
            "max_no_sun_days": 4.09,
            "annual_no_sun_days": 165.38,
            "avg_temp": 10.88,
            "min_temp": 5.64,
            "max_temp": 16.41,
        }

        repository = self.repository([cache_record])
        with patch("app.services.power.requests.get") as nasa_get:
            solar_stats = await get_solar_statistics(
                repository, -36.854, 174.764
            )

        self.assertEqual(solar_stats, cache_record)
        self.assertIn("FROM Solar_cache", repository.fetch_all.call_args.args[0])
        self.assertEqual(
            repository.fetch_all.call_args.args[1],
            {"latitude": -36.85, "longitude": 174.76},
        )
        nasa_get.assert_not_called()

    async def test_cache_miss_fetches_nasa_and_stores_rounded_coordinates(self):
        repository = self.repository([])
        with patch(
            "app.services.power.requests.get", return_value=FakeResponse(nasa_payload())
        ) as nasa_get:
            solar_stats = await get_solar_statistics(
                repository, -36.854, 174.764
            )

        self.assertEqual(solar_stats["annual_no_sun_days"], 165.38)
        self.assertEqual(solar_stats["avg_temp"], 10.88)
        self.assertEqual(solar_stats["min_temp"], 5.64)
        self.assertEqual(solar_stats["max_temp"], 16.41)
        self.assertIn("longitude=174.76&latitude=-36.85", nasa_get.call_args.args[0])

        latitude, longitude, stored_fields = repository.store_solar_cache.call_args.args
        self.assertEqual(latitude, -36.85)
        self.assertEqual(longitude, 174.76)
        self.assertEqual(stored_fields["annual_no_sun_days"], 165.38)

    async def test_incomplete_cache_record_is_replaced_with_nasa_data(self):
        incomplete_cache_record = {
            "min_sun": 3.1,
            "max_no_sun_days": 4.09,
            "annual_no_sun_days": 165.38,
            "avg_temp": 10.88,
            "min_temp": 5.64,
        }
        repository = self.repository([incomplete_cache_record])
        with patch(
            "app.services.power.requests.get", return_value=FakeResponse(nasa_payload())
        ) as nasa_get:
            solar_stats = await get_solar_statistics(repository, -36.85, 174.76)

        self.assertEqual(solar_stats["max_temp"], 16.41)
        nasa_get.assert_called_once()

    async def test_missing_annual_temperature_uses_ten_valid_months(self):
        payload = nasa_payload(annual_temperature=-999.0)
        temperatures = payload["properties"]["parameter"]["T2M"]
        temperatures["NOV"] = -999.0
        temperatures["DEC"] = -999.0
        repository = self.repository([])
        with patch("app.services.power.requests.get", return_value=FakeResponse(payload)):
            solar_stats = await get_solar_statistics(repository, -36.85, 174.76)

        self.assertAlmostEqual(solar_stats["avg_temp"], 10.431)
        self.assertEqual(solar_stats["min_temp"], 5.64)
        self.assertEqual(solar_stats["max_temp"], 16.41)

    async def test_nasa_request_failure_is_returned_as_the_expected_502(self):
        repository = self.repository([])
        with patch(
            "app.services.power.requests.get",
            side_effect=requests.Timeout("timed out"),
        ):
            with self.assertRaises(HTTPException) as raised:
                await get_solar_statistics(repository, -36.85, 174.76)

        self.assertEqual(raised.exception.status_code, 502)
        self.assertEqual(raised.exception.detail, NASA_POWER_ERROR_DETAIL)

    async def test_incomplete_nasa_payload_is_returned_as_the_expected_502(self):
        repository = self.repository([])
        with patch(
            "app.services.power.requests.get",
            return_value=FakeResponse({"properties": None}),
        ):
            with self.assertRaises(HTTPException) as raised:
                await get_solar_statistics(repository, -36.85, 174.76)

        self.assertEqual(raised.exception.status_code, 502)
        self.assertEqual(raised.exception.detail, NASA_POWER_ERROR_DETAIL)


if __name__ == "__main__":
    unittest.main()
