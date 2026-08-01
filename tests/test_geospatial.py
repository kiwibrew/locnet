import json
import math
import unittest

import httpx

from library.classes import LocationData
from library.geospatial import (
    GeospatialClient,
    calculate_coverage_population,
)


def geojson(visible_area_sq_km):
    return {
        "type": "Feature",
        "properties": {"visible_area_sq_km": visible_area_sq_km},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[174.7, -36.9], [174.8, -36.9], [174.7, -36.9]]],
        },
    }


def location(**overrides):
    values = {
        "location_name": "Test location",
        "latitude": -36.85,
        "longitude": 174.76,
        "radius": 8,
        "households": None,
        "tower_cost": 1000,
        "tower_opex": 20,
        "tower_height": 30,
        "network_type": ["Test network"],
        "sectors": [2],
        "network_links": [],
        "backhaul_links": [],
        "backhaul_cost_base": [],
        "backhaul_cost_mbps": [],
        "power_type": "power_mains_rel",
    }
    values.update(overrides)
    return LocationData.model_validate(values)


def technology(family, *, vegetation_loss_per_metre=20):
    # At 1 GHz, this path-loss budget produces a 10 km free-space radius.
    return {
        "technology": family,
        "max_path_loss": 112.44,
        "nominal_freq": 1000,
        "veg_loss_meter": vegetation_loss_per_metre,
    }


class RecordingCoverageService:
    def __init__(
        self,
        *,
        viewsheds=None,
        fractions=None,
        population=123,
    ):
        self.viewsheds = list(viewsheds or [])
        self.fractions = fractions or {}
        self.population_result = population
        self.viewshed_calls = []
        self.land_cover_calls = []
        self.population_calls = []

    async def viewshed(self, **kwargs):
        self.viewshed_calls.append(kwargs)
        return self.viewsheds.pop(0)

    async def land_cover_fractions(self, submitted_geojson):
        self.land_cover_calls.append(submitted_geojson)
        return self.fractions

    async def population(self, iso_3, submitted_geojson):
        self.population_calls.append((iso_3, submitted_geojson))
        return self.population_result


class CoveragePopulationWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_mobile_repeats_viewshed_after_vegetation_reduces_radius(self):
        first_viewshed = geojson(50)
        reduced_viewshed = geojson(12)
        service = RecordingCoverageService(
            viewsheds=[first_viewshed, reduced_viewshed],
            fractions={"10": 0.4, "95": 0.1},
            population=321,
        )

        result = await calculate_coverage_population(
            location=location(),
            technology=technology("Mobile"),
            iso_3="NZL",
            household_size=3.5,
            service=service,
        )

        self.assertEqual(len(service.viewshed_calls), 2)
        self.assertEqual(service.viewshed_calls[0]["radius_m"], 8000)
        self.assertAlmostEqual(
            service.viewshed_calls[1]["radius_m"],
            10 ** ((112.44 - 10 - 32.44 - 60) / 20) * 1000,
        )
        self.assertEqual(service.viewshed_calls[0]["target_height_agl_m"], 2)
        self.assertEqual(service.viewshed_calls[0]["observer_height_agl_m"], 30)
        self.assertEqual(service.land_cover_calls, [first_viewshed])
        self.assertEqual(service.population_calls, [("NZL", reduced_viewshed)])
        self.assertEqual(result.sector_coverage_sqkm, 12)
        self.assertEqual(result.population_covered, 321)
        self.assertEqual(result.vegetation_factor, 0.5)
        self.assertEqual(result.vegetation_loss, 10)

    async def test_fwa_keeps_first_viewshed_when_radius_is_not_reduced(self):
        first_viewshed = geojson(40)
        service = RecordingCoverageService(
            viewsheds=[first_viewshed],
            fractions={"10": 0, "95": 0},
        )

        result = await calculate_coverage_population(
            location=location(households=10),
            technology=technology("FWA"),
            iso_3="NZL",
            household_size=3.5,
            service=service,
        )

        self.assertEqual(len(service.viewshed_calls), 1)
        self.assertEqual(service.viewshed_calls[0]["target_height_agl_m"], 6)
        self.assertEqual(service.population_calls, [])
        self.assertEqual(result.cell_radius_km, 8)
        self.assertEqual(result.population_covered, 35)

    async def test_gpon_uses_location_radius_and_worldpop(self):
        service = RecordingCoverageService(population=88)

        result = await calculate_coverage_population(
            location=location(radius=3),
            technology=technology("GPON"),
            iso_3="NZL",
            household_size=3.5,
            service=service,
        )

        self.assertEqual(service.viewshed_calls, [])
        self.assertEqual(service.land_cover_calls, [])
        self.assertEqual(len(service.population_calls), 1)
        self.assertEqual(result.cell_radius_km, 3)
        self.assertAlmostEqual(result.sector_coverage_sqkm, math.pi * 9)
        polygon = result.geojson["geometry"]["coordinates"][0]
        self.assertEqual(polygon[0], polygon[-1])


class GeospatialClientContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_service_request_contracts(self):
        requests = []

        async def handler(request):
            body = await request.aread()
            requests.append((request, body))
            if request.url.path == "/api/v1/viewsheds":
                return httpx.Response(200, json=geojson(7.5))
            if request.url.path == "/api/land-cover-geojson":
                return httpx.Response(200, json={"10": 0.2, "95": 0.05})
            if request.url.path == "/api/pop-shape":
                return httpx.Response(200, json={"pop": 456.5})
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as http_client:
            client = GeospatialClient(
                http_client,
                glo30_url="https://glo30.example",
                glo30_token="glo-token",
                esawc_url="https://esawc.example",
                esawc_token="esa-token",
                wpop_url="https://wpop.example",
                wpop_token="pop-token",
            )
            viewshed = await client.viewshed(
                longitude=174.76,
                latitude=-36.85,
                radius_m=2500,
                observer_height_agl_m=30,
                target_height_agl_m=2,
            )
            fractions = await client.land_cover_fractions(viewshed)
            population = await client.population("NZL", viewshed)

        self.assertEqual(fractions, {"10": 0.2, "95": 0.05})
        self.assertEqual(population, 456.5)

        viewshed_request, viewshed_body = requests[0]
        self.assertEqual(
            viewshed_request.headers["Authorization"], "Bearer glo-token"
        )
        self.assertEqual(
            json.loads(viewshed_body),
            {
                "observer_coordinates": [174.76, -36.85],
                "observer_height_agl_m": 30,
                "target_height_agl_m": 2,
                "radius_m": 2500,
            },
        )

        land_cover_request, land_cover_body = requests[1]
        self.assertEqual(
            land_cover_request.headers["Authorization"], "Bearer esa-token"
        )
        self.assertIn(b'name="geojson_file"', land_cover_body)
        self.assertIn(b"coverage.geojson", land_cover_body)

        population_request, population_body = requests[2]
        self.assertEqual(
            population_request.headers["Authorization"], "Bearer pop-token"
        )
        self.assertEqual(population_request.url.params["iso3"], "NZL")
        self.assertIn(b'name="geojson_file"', population_body)


if __name__ == "__main__":
    unittest.main()
