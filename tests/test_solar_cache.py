import unittest
from unittest.mock import AsyncMock, Mock, patch

import requests
from fastapi import HTTPException

from app.schemas.modeling import LocationData, PowerModelInput
from app.services.power import (
    MONTHLY_SUN_CACHE_COLUMNS,
    NASA_POWER_ERROR_DETAIL,
    UNSUPPORTED_SOLAR_SYSTEM_DETAIL,
    _parse_hybrid_nasa_solar_stats,
    get_hybrid_solar_statistics,
    get_mains_solar_statistics,
    get_solar_statistics,
    power_model,
)

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
MONTHLY_SUN = (5.2, 5.1, 4.9, 4.4, 3.6, 3.1, 3.2, 3.9, 4.6, 5.1, 5.5, 5.4)
NO_SUN_DAYS = (2.57, 2.34, 3.13, 3.57, 4.09, 3.45, 2.98, 3.43, 3.33, 3.14, 3.32, 3.11)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def nasa_payload(
    irradiance_values=MONTHLY_SUN,
    no_sun_values=NO_SUN_DAYS,
    annual_temperature=10.88,
):
    temperatures = dict(
        zip(
            MONTHS,
            (
                16.41,
                16.31,
                14.39,
                11.43,
                8.9,
                6.53,
                5.64,
                6.66,
                8.19,
                9.85,
                12.07,
                14.47,
            ),
        )
    )
    temperatures["ANN"] = annual_temperature
    irradiance = dict(zip(MONTHS, irradiance_values))
    irradiance["ANN"] = sum(irradiance_values) / len(irradiance_values)
    no_sun_days = dict(zip(MONTHS, no_sun_values))
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


def solar_stats(monthly_sun=None, no_sun_available=True):
    stats = {
        "min_sun": 3.1,
        "max_no_sun_days": 4.09 if no_sun_available else -999.0,
        "annual_no_sun_days": 165.38 if no_sun_available else -999.0,
        "avg_temp": 10.88,
        "min_temp": 5.64,
        "max_temp": 16.41,
    }
    if monthly_sun is not None:
        stats.update(dict(zip(MONTHLY_SUN_CACHE_COLUMNS, monthly_sun)))
    return stats


def power_input(system_type="power_hybrid", system_life=1, solar_derating=0.0):
    location = LocationData(
        location_name="Test site",
        latitude=-36.85,
        longitude=174.76,
        network_type=[],
        sectors=[],
        network_links=[],
        backhaul_links=[],
        backhaul_cost_base=[],
        backhaul_cost_mbps=[],
        power_type=system_type,
    )
    return PowerModelInput(
        location=location,
        latitude=-36.85,
        longitude=174.76,
        power_required=100.0,
        system_life=system_life,
        solar_cost_watt=0.6,
        solar_derating=solar_derating,
        solar_efficiency=20,
        battery_age_derating=0.0,
        battery_cost_watt_hour=0.5,
        battery_dod=80.0,
        charger_inverter_base=10.0,
        charger_inverter_variable=0.1,
        mains_power_cost_kwh=1.0,
        mains_power_installation_cost=1000.0,
        power_hybrid_hours=12.0,
        power_intermittent_hours=24.0,
        power_reliable_hours=4.0,
        system_type=system_type,
    )


class SolarCacheTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def repository(cache_records):
        repository = Mock()
        repository.get_solar_cache_records = AsyncMock(return_value=cache_records)
        repository.upsert_solar_cache = AsyncMock()
        return repository

    async def test_complete_standard_cache_record_is_used_without_nasa_request(self):
        cache_record = solar_stats()
        repository = self.repository([cache_record])

        with patch("app.services.power.requests.get") as nasa_get:
            result = await get_solar_statistics(repository, -36.854, 174.764)

        self.assertEqual(result, cache_record)
        repository.get_solar_cache_records.assert_awaited_once_with(-36.85, 174.76)
        nasa_get.assert_not_called()

    async def test_standard_cache_miss_fetches_nasa_and_upserts_rounded_coordinates(
        self,
    ):
        repository = self.repository([])
        with patch(
            "app.services.power.requests.get", return_value=FakeResponse(nasa_payload())
        ) as nasa_get:
            result = await get_solar_statistics(repository, -36.854, 174.764)

        self.assertEqual(result["annual_no_sun_days"], 165.38)
        self.assertIn("longitude=174.76&latitude=-36.85", nasa_get.call_args.args[0])
        repository.upsert_solar_cache.assert_awaited_once_with(-36.85, 174.76, result)

    async def test_complete_hybrid_cache_record_is_used_without_nasa_request(self):
        cache_record = solar_stats(MONTHLY_SUN)
        repository = self.repository([cache_record])

        with patch("app.services.power.requests.get") as nasa_get:
            result = await get_hybrid_solar_statistics(repository, -36.854, 174.764)

        self.assertEqual(result, cache_record)
        nasa_get.assert_not_called()

    async def test_legacy_hybrid_cache_record_refreshes_from_nasa(self):
        repository = self.repository([solar_stats()])
        with patch(
            "app.services.power.requests.get", return_value=FakeResponse(nasa_payload())
        ):
            result = await get_hybrid_solar_statistics(repository, -36.85, 174.76)

        self.assertEqual(result["sun_jan"], 5.2)
        self.assertEqual(result["sun_dec"], 5.4)
        repository.upsert_solar_cache.assert_awaited_once_with(-36.85, 174.76, result)

    async def test_hybrid_allows_missing_no_sun_data_when_sunlight_exists(self):
        polar_sun = (
            0.0338,
            1.2223,
            3.9358,
            6.7248,
            6.6547,
            5.7036,
            4.8694,
            3.3588,
            1.9862,
            0.989,
            0.1219,
            0.0,
        )
        repository = self.repository([])
        with patch(
            "app.services.power.requests.get",
            return_value=FakeResponse(nasa_payload(polar_sun, (-999.0,) * len(MONTHS))),
        ):
            result = await get_hybrid_solar_statistics(repository, -36.85, 174.76)

        self.assertEqual(result["sun_dec"], 0.0)
        self.assertEqual(result["max_no_sun_days"], -999.0)
        self.assertEqual(result["annual_no_sun_days"], -999.0)
        repository.upsert_solar_cache.assert_awaited_once_with(-36.85, 174.76, result)

    def test_hybrid_parser_rejects_invalid_monthly_irradiance(self):
        invalid_sun = (*MONTHLY_SUN[:-1], -999.0)

        with self.assertRaises(HTTPException) as raised:
            _parse_hybrid_nasa_solar_stats(nasa_payload(invalid_sun))

        self.assertEqual(raised.exception.status_code, 502)
        self.assertEqual(raised.exception.detail, NASA_POWER_ERROR_DETAIL)

    async def test_hybrid_model_rejects_an_all_zero_irradiance_year(self):
        repository = self.repository([])
        with (
            self.assertRaises(HTTPException) as raised,
            patch(
                "app.services.power.get_hybrid_solar_statistics",
                new=AsyncMock(
                    return_value=solar_stats(
                        (0.0,) * len(MONTHS), no_sun_available=False
                    )
                ),
            ),
        ):
            await power_model(repository, power_input())

        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(
            raised.exception.detail,
            UNSUPPORTED_SOLAR_SYSTEM_DETAIL.format(system_name="Hybrid power"),
        )

    async def test_hybrid_model_uses_month_lengths_caps_solar_and_includes_panel_cost(
        self,
    ):
        monthly_sun = (100.0,) + (1.0,) * (len(MONTHS) - 1)
        repository = self.repository([])
        with patch(
            "app.services.power.get_hybrid_solar_statistics",
            new=AsyncMock(return_value=solar_stats(monthly_sun)),
        ):
            result = await power_model(repository, power_input())

        self.assertEqual(result.power_opex, 400.8)
        self.assertEqual(result.power_capex, 2654.92)
        self.assertEqual(
            result.power_capex,
            round(
                result.power_row.battery_cost
                + result.power_row.charger_cost
                + result.power_row.solar_cost
                + 1000.0,
                2,
            ),
        )

    async def test_hybrid_model_applies_yearly_solar_derating(self):
        repository = self.repository([])
        with patch(
            "app.services.power.get_hybrid_solar_statistics",
            new=AsyncMock(return_value=solar_stats((1.0,) * len(MONTHS))),
        ):
            result = await power_model(
                repository, power_input(system_life=2, solar_derating=10.0)
            )

        self.assertEqual(result.power_opex, 827.33)

    async def test_mains_models_use_the_mains_statistics_path(self):
        repository = self.repository([])
        for system_type in ("power_mains_rel", "power_mains_int"):
            with (
                self.subTest(system_type=system_type),
                patch(
                    "app.services.power.get_mains_solar_statistics",
                    new=AsyncMock(return_value=solar_stats()),
                ) as get_mains_statistics,
            ):
                await power_model(repository, power_input(system_type=system_type))

            get_mains_statistics.assert_awaited_once_with(repository, -36.85, 174.76)

    async def test_mains_power_allows_unavailable_solar_and_no_sun_data(self):
        repository = self.repository([])
        unavailable_solar = (-999.0,) * len(MONTHS)
        with patch(
            "app.services.power.requests.get",
            return_value=FakeResponse(
                nasa_payload(unavailable_solar, unavailable_solar)
            ),
        ):
            result = await get_mains_solar_statistics(repository, -36.85, 174.76)

        self.assertEqual(result["min_sun"], -999.0)
        self.assertEqual(result["max_no_sun_days"], -999.0)
        self.assertEqual(result["annual_no_sun_days"], -999.0)

    async def test_solar_returns_a_location_specific_nasa_error(self):
        unavailable_no_sun = (-999.0,) * len(MONTHS)
        repository = self.repository([])
        with (
            patch(
                "app.services.power.requests.get",
                return_value=FakeResponse(
                    nasa_payload(MONTHLY_SUN, unavailable_no_sun)
                ),
            ),
            self.assertRaises(HTTPException) as raised,
        ):
            await get_solar_statistics(repository, -36.85, 174.76)

        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(
            raised.exception.detail,
            UNSUPPORTED_SOLAR_SYSTEM_DETAIL.format(system_name="Solar power"),
        )

    async def test_mains_nasa_request_failure_returns_the_expected_502(self):
        repository = self.repository([])
        with (
            patch(
                "app.services.power.requests.get",
                side_effect=requests.Timeout("timed out"),
            ),
            self.assertRaises(HTTPException) as raised,
        ):
            await get_mains_solar_statistics(repository, -36.85, 174.76)

        self.assertEqual(raised.exception.status_code, 502)
        self.assertEqual(raised.exception.detail, NASA_POWER_ERROR_DETAIL)


if __name__ == "__main__":
    unittest.main()
