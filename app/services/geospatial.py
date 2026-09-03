import asyncio
import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

import httpx

from app.config import (
    ESAWC_API_TOKEN,
    ESAWC_API_URL,
    GEOJSON_CACHE_DIRECTORY,
    GEOSPATIAL_API_TIMEOUT_SECONDS,
    GLO30_API_TOKEN,
    GLO30_API_URL,
    WPOP_API_TOKEN,
    WPOP_API_URL,
)
from app.schemas.modeling import LocationData
from app.services.geojson_cache import GeoJSONCache


GEOSPATIAL_API_ERROR_DETAIL = (
    "The model could not be processed because an API doesn't have data on the location"
)


class GeospatialServiceError(RuntimeError):
    pass


class GeospatialConfigurationError(GeospatialServiceError):
    pass


class CoverageService(Protocol):
    async def viewshed(
        self,
        *,
        longitude: float,
        latitude: float,
        radius_m: float,
        observer_height_agl_m: float,
        target_height_agl_m: float,
    ) -> dict[str, Any]: ...

    async def land_cover_fractions(
        self, geojson: Mapping[str, Any]
    ) -> dict[str, float]: ...

    async def population(
        self, iso_3: str, geojson: Mapping[str, Any]
    ) -> float: ...


class GeospatialClient:
    """Authenticated client for the GLO-30, WorldCover, and WorldPop APIs."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        *,
        glo30_url: str,
        glo30_token: str,
        esawc_url: str,
        esawc_token: str,
        wpop_url: str,
        wpop_token: str,
        viewshed_cache: GeoJSONCache | None = None,
    ):
        self.http_client = http_client
        self.glo30_url = glo30_url.rstrip("/")
        self.glo30_token = glo30_token
        self.esawc_url = esawc_url.rstrip("/")
        self.esawc_token = esawc_token
        self.wpop_url = wpop_url.rstrip("/")
        self.wpop_token = wpop_token
        self.viewshed_cache = viewshed_cache

    @classmethod
    def from_config(cls) -> "GeospatialClient":
        return cls(
            httpx.AsyncClient(
                timeout=GEOSPATIAL_API_TIMEOUT_SECONDS,
                follow_redirects=True,
            ),
            glo30_url=GLO30_API_URL,
            glo30_token=GLO30_API_TOKEN,
            esawc_url=ESAWC_API_URL,
            esawc_token=ESAWC_API_TOKEN,
            wpop_url=WPOP_API_URL,
            wpop_token=WPOP_API_TOKEN,
            viewshed_cache=GeoJSONCache(GEOJSON_CACHE_DIRECTORY),
        )

    async def __aenter__(self) -> "GeospatialClient":
        return self

    async def __aexit__(self, *_args) -> None:
        await self.http_client.aclose()

    @staticmethod
    def _headers(service: str, base_url: str, token: str) -> dict[str, str]:
        if not base_url or not token:
            raise GeospatialConfigurationError(
                f"{service} API URL and bearer token must be configured"
            )
        return {"Authorization": f"Bearer {token}"}

    @staticmethod
    def _response_object(service: str, response: httpx.Response) -> dict[str, Any]:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            try:
                detail = response.json().get("detail")
            except (ValueError, AttributeError):
                detail = None
            suffix = f": {detail}" if detail else ""
            raise GeospatialServiceError(
                f"{service} API returned HTTP {response.status_code}{suffix}"
            ) from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise GeospatialServiceError(
                f"{service} API returned invalid JSON"
            ) from exc
        if not isinstance(body, dict):
            raise GeospatialServiceError(
                f"{service} API returned a non-object response"
            )
        return body

    async def viewshed(
        self,
        *,
        longitude: float,
        latitude: float,
        radius_m: float,
        observer_height_agl_m: float,
        target_height_agl_m: float,
    ) -> dict[str, Any]:
        headers = self._headers("GLO-30", self.glo30_url, self.glo30_token)
        request_body = {
            "observer_coordinates": [float(longitude), float(latitude)],
            "observer_height_agl_m": float(observer_height_agl_m),
            "target_height_agl_m": float(target_height_agl_m),
            "radius_m": float(radius_m),
        }
        cache_key = self._viewshed_cache_key(request_body)
        if self.viewshed_cache is not None:
            cached = await asyncio.to_thread(self.viewshed_cache.get, cache_key)
            if cached is not None and self._is_valid_viewshed(cached):
                return cached
            if cached is not None:
                await asyncio.to_thread(self.viewshed_cache.delete, cache_key)

        try:
            response = await self.http_client.post(
                f"{self.glo30_url}/api/v1/viewsheds",
                headers=headers,
                json=request_body,
            )
        except httpx.HTTPError as exc:
            raise GeospatialServiceError("GLO-30 API request failed") from exc

        body = self._response_object("GLO-30", response)
        if not self._is_valid_viewshed(body):
            raise GeospatialServiceError("GLO-30 API returned invalid GeoJSON")
        if self.viewshed_cache is not None:
            await asyncio.to_thread(self.viewshed_cache.set, cache_key, body)
        return body

    def _viewshed_cache_key(self, request_body: Mapping[str, Any]) -> str:
        key_data = json.dumps(
            {
                "service_url": self.glo30_url,
                "request": request_body,
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(key_data).hexdigest()

    @staticmethod
    def _is_valid_viewshed(body: Mapping[str, Any]) -> bool:
        properties = body.get("properties")
        return (
            body.get("type") == "Feature"
            and isinstance(properties, dict)
            and isinstance(body.get("geometry"), dict)
            and isinstance(properties.get("visible_area_sq_km"), (int, float))
        )

    async def land_cover_fractions(
        self, geojson: Mapping[str, Any]
    ) -> dict[str, float]:
        headers = self._headers("ESA WorldCover", self.esawc_url, self.esawc_token)
        try:
            response = await self.http_client.post(
                f"{self.esawc_url}/api/land-cover-geojson",
                headers=headers,
                files={
                    "geojson_file": (
                        "coverage.geojson",
                        json.dumps(geojson).encode("utf-8"),
                        "application/geo+json",
                    )
                },
            )
        except httpx.HTTPError as exc:
            raise GeospatialServiceError(
                "ESA WorldCover API request failed"
            ) from exc

        body = self._response_object("ESA WorldCover", response)
        try:
            return {str(key): float(value) for key, value in body.items()}
        except (TypeError, ValueError) as exc:
            raise GeospatialServiceError(
                "ESA WorldCover API returned invalid land-cover fractions"
            ) from exc

    async def population(
        self, iso_3: str, geojson: Mapping[str, Any]
    ) -> float:
        headers = self._headers("WorldPop", self.wpop_url, self.wpop_token)
        try:
            response = await self.http_client.post(
                f"{self.wpop_url}/api/pop-shape",
                params={"iso3": iso_3},
                headers=headers,
                files={
                    "geojson_file": (
                        "coverage.geojson",
                        json.dumps(geojson).encode("utf-8"),
                        "application/geo+json",
                    )
                },
            )
        except httpx.HTTPError as exc:
            raise GeospatialServiceError("WorldPop API request failed") from exc

        body = self._response_object("WorldPop", response)
        pop = body.get("pop")
        if not isinstance(pop, (int, float)) or pop < 0:
            raise GeospatialServiceError(
                "WorldPop API returned an invalid population"
            )
        return float(pop)


@dataclass(frozen=True)
class CoveragePopulationResult:
    cell_radius_km: float
    sector_coverage_sqkm: float
    vegetation_factor: float
    vegetation_loss: float
    population_covered: float
    geojson: dict[str, Any]


def free_space_cell_radius_km(
    max_path_loss: float,
    nominal_freq_mhz: float,
    vegetation_loss: float = 0,
) -> float:
    if nominal_freq_mhz <= 0:
        raise ValueError("nominal frequency must be greater than zero")
    return 10 ** (
        (
            max_path_loss
            - vegetation_loss
            - 32.44
            - (20 * math.log10(nominal_freq_mhz))
        )
        / 20
    )


def circle_geojson(
    longitude: float,
    latitude: float,
    radius_km: float,
    point_count: int = 64,
) -> dict[str, Any]:
    earth_radius_km = 6371.0088
    angular_distance = radius_km / earth_radius_km
    latitude_radians = math.radians(latitude)
    longitude_radians = math.radians(longitude)
    coordinates: list[list[float]] = []

    for index in range(point_count):
        bearing = index * 2 * math.pi / point_count
        point_latitude = math.asin(
            math.sin(latitude_radians) * math.cos(angular_distance)
            + math.cos(latitude_radians)
            * math.sin(angular_distance)
            * math.cos(bearing)
        )
        point_longitude = longitude_radians + math.atan2(
            math.sin(bearing)
            * math.sin(angular_distance)
            * math.cos(latitude_radians),
            math.cos(angular_distance)
            - math.sin(latitude_radians) * math.sin(point_latitude),
        )
        longitude_degrees = (math.degrees(point_longitude) + 540) % 360 - 180
        coordinates.append([longitude_degrees, math.degrees(point_latitude)])

    coordinates.append(coordinates[0])
    return {
        "type": "Feature",
        "properties": {"radius_m": radius_km * 1000},
        "geometry": {"type": "Polygon", "coordinates": [coordinates]},
    }


async def calculate_coverage_population(
    *,
    location: LocationData,
    technology: Mapping[str, Any],
    iso_3: str,
    household_size: float,
    service: CoverageService,
) -> CoveragePopulationResult:
    technology_family = technology["technology"]
    vegetation_factor = 0.0
    vegetation_loss = 0.0

    if technology_family in {"GPON", "PAF"}:
        cell_radius_km = location.radius
        sector_coverage_sqkm = math.pi * cell_radius_km ** 2
        geojson = circle_geojson(
            location.longitude,
            location.latitude,
            cell_radius_km,
        )
    elif technology_family in {"Mobile", "FWA"}:
        if location.tower_height is None:
            raise ValueError(
                f"Tower height is required for radio coverage at {location.location_name}"
            )

        free_space_radius_km = free_space_cell_radius_km(
            float(technology["max_path_loss"]),
            float(technology["nominal_freq"]),
        )
        requested_radius_km = min(location.radius, free_space_radius_km)
        target_height_agl_m = 2 if technology_family == "Mobile" else 6
        geojson = await service.viewshed(
            longitude=location.longitude,
            latitude=location.latitude,
            radius_m=requested_radius_km * 1000,
            observer_height_agl_m=location.tower_height,
            target_height_agl_m=target_height_agl_m,
        )

        fractions = await service.land_cover_fractions(geojson)
        vegetation_factor = fractions.get("10", 0) + fractions.get("95", 0)
        if not 0 <= vegetation_factor <= 1:
            raise GeospatialServiceError(
                "ESA WorldCover tree and mangrove fractions must total between 0 and 1"
            )

        vegetation_loss = float(technology["veg_loss_meter"]) * vegetation_factor
        vegetation_radius_km = free_space_cell_radius_km(
            float(technology["max_path_loss"]),
            float(technology["nominal_freq"]),
            vegetation_loss,
        )
        cell_radius_km = min(requested_radius_km, vegetation_radius_km)

        if cell_radius_km < requested_radius_km:
            geojson = await service.viewshed(
                longitude=location.longitude,
                latitude=location.latitude,
                radius_m=cell_radius_km * 1000,
                observer_height_agl_m=location.tower_height,
                target_height_agl_m=target_height_agl_m,
            )

        sector_coverage_sqkm = float(
            geojson["properties"]["visible_area_sq_km"]
        )
    else:
        raise ValueError(f"Unsupported technology family: {technology_family}")

    if location.households is not None:
        population_covered = float(location.households) * household_size
    else:
        population_covered = await service.population(iso_3, geojson)

    return CoveragePopulationResult(
        cell_radius_km=cell_radius_km,
        sector_coverage_sqkm=sector_coverage_sqkm,
        vegetation_factor=vegetation_factor,
        vegetation_loss=vegetation_loss,
        population_covered=population_covered,
        geojson=geojson,
    )
