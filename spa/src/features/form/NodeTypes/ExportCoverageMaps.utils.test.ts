import { describe, expect, test } from 'vitest';
import type { FeatureCollection, Polygon } from 'geojson';
import { getGeoJsonBounds } from './ExportCoverageMaps.utils';

describe('getGeoJsonBounds', () => {
  test('combines the bounds of all features', () => {
    const geojson: FeatureCollection<Polygon> = {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: {},
          geometry: {
            type: 'Polygon',
            coordinates: [
              [
                [170, -45],
                [172, -45],
                [172, -43],
                [170, -45],
              ],
            ],
          },
        },
        {
          type: 'Feature',
          properties: {},
          geometry: {
            type: 'Polygon',
            coordinates: [
              [
                [173, -42],
                [175, -42],
                [175, -40],
                [173, -42],
              ],
            ],
          },
        },
      ],
    };

    expect(getGeoJsonBounds(geojson, 172)).toEqual([
      [170, -45],
      [175, -40],
    ]);
  });

  test('unwraps antimeridian coordinates around the location', () => {
    const geojson: Polygon = {
      type: 'Polygon',
      coordinates: [
        [
          [179, -18],
          [-179, -18],
          [-179, -16],
          [179, -18],
        ],
      ],
    };

    expect(getGeoJsonBounds(geojson, 180)).toEqual([
      [179, -18],
      [181, -16],
    ]);
  });

  test('returns undefined for an empty feature collection', () => {
    expect(
      getGeoJsonBounds({ type: 'FeatureCollection', features: [] }, 0),
    ).toBeUndefined();
  });
});
