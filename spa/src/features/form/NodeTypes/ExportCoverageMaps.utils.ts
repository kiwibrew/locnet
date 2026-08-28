import type { GeoJSON, Geometry, Position } from 'geojson';

type Bounds = [[number, number], [number, number]];

const normalizeLongitude = (longitude: number, centerLongitude: number) => {
  let normalizedLongitude = longitude;
  while (normalizedLongitude - centerLongitude > 180) {
    normalizedLongitude -= 360;
  }
  while (normalizedLongitude - centerLongitude < -180) {
    normalizedLongitude += 360;
  }
  return normalizedLongitude;
};

export const getGeoJsonBounds = (
  geojson: GeoJSON,
  centerLongitude: number,
): Bounds | undefined => {
  let west = Number.POSITIVE_INFINITY;
  let south = Number.POSITIVE_INFINITY;
  let east = Number.NEGATIVE_INFINITY;
  let north = Number.NEGATIVE_INFINITY;

  const visitPosition = (position: Position) => {
    const [rawLongitude, latitude] = position;
    if (!Number.isFinite(rawLongitude) || !Number.isFinite(latitude)) return;
    const longitude = normalizeLongitude(rawLongitude, centerLongitude);
    west = Math.min(west, longitude);
    south = Math.min(south, latitude);
    east = Math.max(east, longitude);
    north = Math.max(north, latitude);
  };

  const visitCoordinates = (coordinates: unknown) => {
    if (!Array.isArray(coordinates)) return;
    if (
      coordinates.length >= 2 &&
      typeof coordinates[0] === 'number' &&
      typeof coordinates[1] === 'number'
    ) {
      visitPosition(coordinates as Position);
      return;
    }
    coordinates.forEach(visitCoordinates);
  };

  const visitGeometry = (geometry: Geometry | null) => {
    if (!geometry) return;
    if (geometry.type === 'GeometryCollection') {
      geometry.geometries.forEach(visitGeometry);
      return;
    }
    visitCoordinates(geometry.coordinates);
  };

  if (geojson.type === 'FeatureCollection') {
    geojson.features.forEach((feature) => visitGeometry(feature.geometry));
  } else if (geojson.type === 'Feature') {
    visitGeometry(geojson.geometry);
  } else {
    visitGeometry(geojson);
  }

  if (![west, south, east, north].every(Number.isFinite)) return undefined;
  return [
    [west, south],
    [east, north],
  ];
};
