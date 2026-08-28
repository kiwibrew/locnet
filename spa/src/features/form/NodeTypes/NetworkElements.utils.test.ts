import { expect, test } from 'vitest';
import type { NetworkElement } from './NetworkElements';
import {
  calculateLocationsAreaSqKm,
  calculateOverrideHouseholds,
} from './NetworkElements.utils';

const location = (
  overrides: Partial<NetworkElement> = {},
): NetworkElement => ({
  type: 'NetworkElement',
  isSoftDeleted: false,
  index: 0,
  number: 1,
  location_name: 'Location 1',
  latitude: -36.85,
  longitude: 174.76,
  radius: 2,
  use_model_households: true,
  households: '',
  networkTypes: [],
  towerType: {
    name: 'tower',
    cost_USD: '1000',
    opex_USD: '0',
    height_m: '6',
  },
  midhaulLink: [],
  backhaulLinks: [],
  power_type: 'power_mains_rel',
  ...overrides,
});

test('sums circular location areas and ignores soft-deleted locations', () => {
  const locations = [
    location({ radius: 2 }),
    location({ index: 1, radius: 3 }),
    location({ index: 2, radius: 50, isSoftDeleted: true }),
  ];

  expect(calculateLocationsAreaSqKm(locations)).toBe(
    Number((Math.PI * (2 ** 2 + 3 ** 2)).toFixed(2)),
  );
});

test('sums only explicit household overrides', () => {
  const locations = [
    location({ use_model_households: true, households: '999' }),
    location({ index: 1, use_model_households: false, households: '12' }),
    location({
      index: 2,
      use_model_households: false,
      households: '20',
      isSoftDeleted: true,
    }),
  ];

  expect(calculateOverrideHouseholds(locations)).toBe(12);
});
