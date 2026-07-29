import { expect, test } from 'vitest';
import type { NetworkElement } from '../form/NodeTypes/NetworkElements';
import { hasConfiguredLocation } from './locationValidation';

const configuredLocation = (): NetworkElement => ({
  type: 'NetworkElement',
  isSoftDeleted: false,
  index: 0,
  number: 1,
  location_name: 'Location 1',
  latitude: 41.145639143,
  longitude: 20.0064944925175,
  radius: 2,
  power_type: 'power_mains_rel',
  towerType: {
    name: '',
    cost_USD: '1000',
  },
  networkTypes: [
    {
      key: 'network-type-1',
      isSoftDeleted: false,
      index: 0,
      type: 'ISM FWA 5.8 GHz',
      unitCount: '1',
    },
  ],
  midhaulLink: [],
  backhaulLinks: [
    {
      key: 'backhaul-link-1',
      isSoftDeleted: false,
      index: 0,
      type: 'Microwave',
      name: 'Backhaul link 1',
      monthlyCharge: '500',
      trafficCost_USD: '0.5',
    },
  ],
});

test('requires a location with every required configuration value', () => {
  const completeLocation = configuredLocation();

  expect(hasConfiguredLocation([completeLocation])).toBe(true);
  expect(
    hasConfiguredLocation([{ ...completeLocation, location_name: ' ' }]),
  ).toBe(false);
  expect(
    hasConfiguredLocation([{ ...completeLocation, power_type: null }]),
  ).toBe(false);
  expect(
    hasConfiguredLocation([
      {
        ...completeLocation,
        towerType: { ...completeLocation.towerType, cost_USD: '' },
      },
    ]),
  ).toBe(false);
  expect(
    hasConfiguredLocation([{ ...completeLocation, networkTypes: [] }]),
  ).toBe(false);
  expect(
    hasConfiguredLocation([
      { ...completeLocation, midhaulLink: [], backhaulLinks: [] },
    ]),
  ).toBe(false);
  expect(
    hasConfiguredLocation([
      { ...completeLocation, power_type: null },
      completeLocation,
    ]),
  ).toBe(true);
});

test('accepts a network link and ignores soft-deleted configuration', () => {
  const completeLocation = configuredLocation();
  const networkLinkLocation: NetworkElement = {
    ...completeLocation,
    midhaulLink: [
      {
        key: 'network-link-1',
        isSoftDeleted: false,
        index: 0,
        type: 'Fibre',
        name: 'Network link 1',
      },
    ],
    backhaulLinks: [],
  };

  expect(hasConfiguredLocation([networkLinkLocation])).toBe(true);
  expect(
    hasConfiguredLocation([
      {
        ...completeLocation,
        networkTypes: [
          { ...completeLocation.networkTypes[0], isSoftDeleted: true },
        ],
      },
    ]),
  ).toBe(false);
  expect(
    hasConfiguredLocation([
      {
        ...completeLocation,
        backhaulLinks: [
          { ...completeLocation.backhaulLinks[0], isSoftDeleted: true },
        ],
      },
    ]),
  ).toBe(false);
});
