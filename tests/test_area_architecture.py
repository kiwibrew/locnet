import math
import unittest

from library.app_logic import calculate_access_users_supported
from library.classes import BuilderInput


def builder_payload():
    return {
        "area_sqkm": 9999,
        "households_total": 9999,
        "terrain_type": "Very High Variation",
        "vegetation_type": "Very High",
        "battery_age_derating": 0.5,
        "battery_cost_watt_hour": 0.3,
        "battery_dod": 80,
        "charger_inverter_base": 50,
        "charger_inverter_variable": 0.35,
        "iso_3": "NZL",
        "labour_cost": 4.6,
        "locations": [
            {
                "location_name": "Modelled population",
                "latitude": -36.85,
                "longitude": 174.76,
                "radius": 2,
                "households": None,
                "network_type": ["Example FWA"],
                "sectors": [2],
                "network_links": [],
                "backhaul_links": [],
                "backhaul_cost_base": [],
                "backhaul_cost_mbps": [],
                "power_type": "power_mains_rel",
            },
            {
                "location_name": "Household override",
                "latitude": -41.29,
                "longitude": 174.78,
                "radius": 3,
                "households": 17,
                "network_type": ["Example GPON"],
                "sectors": [1],
                "network_links": [],
                "backhaul_links": [],
                "backhaul_cost_base": [],
                "backhaul_cost_mbps": [],
                "power_type": "power_mains_rel",
            },
        ],
        "mains_power_cost_kwh": 0.65,
        "mains_power_installation_cost": 2000,
        "power_hybrid_hours": 12,
        "power_intermittent_hours": 24,
        "power_reliable_hours": 4,
        "solar_cost_watt": 0.6,
        "solar_derating": 0.5,
        "solar_efficiency": 21,
        "system_life": 10,
        "traffic_growth": 25,
        "users_per_household": 3.19,
        "year_1_traffic": 10,
        "hh_income_week": 245.9,
        "staff_opex_fixed": 1.2,
        "staff_opex_variable": 0.3,
        "wacc": 6,
        "spectrum_licence_fee": 0,
        "community_capex_discount": 0,
        "inflation": 2.01,
    }


class BuilderInputAreaArchitectureTests(unittest.TestCase):
    def test_legacy_aggregates_and_profiles_are_ignored(self):
        model = BuilderInput.model_validate(builder_payload())

        self.assertEqual(model.area_sqkm, round(math.pi * (2**2 + 3**2), 2))
        self.assertEqual(model.households_total, 17)
        self.assertIsNone(model.total_potential_users)
        self.assertFalse(hasattr(model, "terrain_type"))
        self.assertFalse(hasattr(model, "vegetation_type"))

    def test_location_radius_defaults_for_an_old_saved_model(self):
        payload = builder_payload()
        payload["model_version"] = 1
        del payload["locations"][0]["radius"]

        model = BuilderInput.model_validate(payload)

        self.assertEqual(model.model_version, 1)
        self.assertEqual(model.locations[0].radius, 2)


class AccessCapacityTests(unittest.TestCase):
    def test_mobile_equipment_capacity_counts_one_user_per_ue(self):
        supported = calculate_access_users_supported(
            technology_family="Mobile",
            population_covered=1000,
            ue_per_sector=30,
            sectors=3,
            household_size=4,
            sector_mbps=100,
            user_final_year_peak_mbps=1,
        )

        self.assertEqual(supported, 90)

    def test_fwa_and_gpon_equipment_capacity_counts_household_members(self):
        for technology_family in ("FWA", "GPON"):
            with self.subTest(technology_family=technology_family):
                supported = calculate_access_users_supported(
                    technology_family=technology_family,
                    population_covered=1000,
                    ue_per_sector=30,
                    sectors=3,
                    household_size=4,
                    sector_mbps=100,
                    user_final_year_peak_mbps=1,
                )

                self.assertEqual(supported, 300)

    def test_throughput_and_population_limits_still_apply(self):
        throughput_limited = calculate_access_users_supported(
            technology_family="FWA",
            population_covered=1000,
            ue_per_sector=1000,
            sectors=2,
            household_size=4,
            sector_mbps=25,
            user_final_year_peak_mbps=2,
        )
        population_limited = calculate_access_users_supported(
            technology_family="Mobile",
            population_covered=12,
            ue_per_sector=1000,
            sectors=2,
            household_size=4,
            sector_mbps=1000,
            user_final_year_peak_mbps=1,
        )

        self.assertEqual(throughput_limited, 25)
        self.assertEqual(population_limited, 12)


if __name__ == "__main__":
    unittest.main()
