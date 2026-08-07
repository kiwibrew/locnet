import { afterEach, expect, test, vi } from 'vitest';
import type { NetworkElement } from '../form/NodeTypes/NetworkElements';
import type { LocNetModel } from './model';
import type { BuilderInput } from './api-generated-client';
import { locnetModelToBuilderInput, submitModel } from './submit';

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

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
  radius: 3,
  use_model_households: false,
  households: '14',
  networkTypes: [
    {
      key: 'fwa',
      isSoftDeleted: false,
      index: 0,
      type: 'Example FWA',
      unitCount: '2',
    },
  ],
  towerType: {
    name: 'tower',
    cost_USD: '1000',
    opex_USD: '25',
    height_m: '18',
  },
  midhaulLink: [],
  backhaulLinks: [],
  power_type: 'power_mains_rel',
  ...overrides,
});

test('builds version 2 location-derived input without legacy profiles', () => {
  const legacyModel: Partial<LocNetModel> & {
    terrain_type: string;
    vegetation_type: string;
  } = {
    area_sqkm: 999,
    households_total: 999,
    total_potential_users: 999,
    terrain_type: 'High Variation',
    vegetation_type: 'High',
    locations: [location()],
  };

  const input = locnetModelToBuilderInput(legacyModel);

  expect(input.model_version).toBe(2);
  expect(input.area_sqkm).toBe(Number((Math.PI * 3 ** 2).toFixed(2)));
  expect(input.households_total).toBe(14);
  expect(input.total_potential_users).toBeUndefined();
  expect(input).not.toHaveProperty('terrain_type');
  expect(input).not.toHaveProperty('vegetation_type');
  expect(input.locations?.[0]).toMatchObject({
    radius: 3,
    households: 14,
    tower_cost: 1000,
    tower_opex: 25,
    tower_height: 18,
  });
});

test('sends a null household override when modelled population is selected', () => {
  const input = locnetModelToBuilderInput({
    locations: [location({ use_model_households: true, households: '' })],
  });

  expect(input.locations?.[0]?.households).toBeNull();
  expect(input.households_total).toBe(0);
});

test('shows the server error and completes a failed model submission', async () => {
  const message =
    "The model could not be processed because an API doesn't have data on the location";
  const alert = vi.fn();
  vi.stubGlobal('alert', alert);
  vi.stubGlobal('location', { origin: 'https://locnet.test' });
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ detail: message }),
    }),
  );
  vi.spyOn(console, 'error').mockImplementation(() => undefined);

  const result = await submitModel({} as BuilderInput);

  expect(alert).toHaveBeenCalledOnce();
  expect(alert).toHaveBeenCalledWith(message);
  expect(result).toEqual({ type: 'error', message });
});
