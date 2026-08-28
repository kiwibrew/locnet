import { z } from 'zod';
import { getDomJson } from '../domJson';
import {
  type BackhaulLink,
  type MidhaulLink,
  type NetworkElement,
  type NetworkType,
} from './NetworkElements';
import { removeSoftDeletes } from '../softDeletes';
import { getLang } from '../Intl.utils';
import { generateRandomKey } from '../key';

const SAFETY_EXIT_AFTER_LOOPS = 1000;

export const newLocationName = (networkElements: NetworkElement[]): string => {
  const getName = (index: number) => {
    const lang = getLang();
    if (lang !== 'en') {
      // TODO
      console.error(
        `Location name for language `,
        lang,
        ' not found. Using English.',
      );
    }
    return `Location ${index}`;
  };

  const nonDeletedNetworkElements = removeSoftDeletes(networkElements);

  for (
    let i = nonDeletedNetworkElements.length + 1;
    i < SAFETY_EXIT_AFTER_LOOPS;
    i++
  ) {
    const potentialName = getName(i);
    if (
      !nonDeletedNetworkElements.some(
        (networkElement) => networkElement.location_name === potentialName,
      )
    ) {
      return potentialName;
    }
  }

  return 'Location';
};

export const newBlankLocation = (
  index: number,
  defaults: Partial<NetworkElement>,
): NetworkElement => {
  return {
    type: 'NetworkElement',
    isSoftDeleted: false,
    index,
    number: index + 1,
    location_name: `Location ${index + 1}`,
    latitude: 0,
    longitude: 0,
    radius: 2,
    use_model_households: true,
    households: '',
    networkTypes: [],
    towerType: {
      name: towerTypesDataFromDOM[0]?.variable ?? '',
      cost_USD: towerTypesDataFromDOM[0]?.value.toString() ?? '',
      opex_USD: towerDetailsDataFromDOM
        .find((detail) => detail.variable === 'tower_opex')
        ?.value.toString() ?? '',
      height_m: towerDetailsDataFromDOM
        .find((detail) => detail.variable === 'tower_height')
        ?.value.toString() ?? '',
    },
    midhaulLink: [],
    backhaulLinks: [],
    power_type: null,
    ...defaults,
  };
};

export const newBlankNetworkType = (index: number): NetworkType => {
  if (networkTypesDataFromDOM.length === 0) {
    throw Error("Can't create network type without valid type options");
  }
  return {
    key: generateRandomKey(),
    isSoftDeleted: false,
    index,
    type: networkTypesDataFromDOM[0].network_type,
    unitCount: '1',
  };
};

export const newBlankMidhaulLink = (index: number): MidhaulLink => {
  return {
    key: generateRandomKey(),
    index,
    isSoftDeleted: false,
    type: '',
    name: '',
  };
};

export const newBlankBackhaulLink = (
  index: number,
  defaults?: Partial<BackhaulLink>,
): BackhaulLink => {
  return {
    key: generateRandomKey(),
    isSoftDeleted: false,
    index,
    type: '',
    name: '',
    monthlyCharge: '',
    trafficCost_USD: '',
    ...defaults,
  };
};

const networkTypesDataSchema = z
  .object({
    frequency: z.number(),
    network_type: z.string(),
    technology: z.string(),
  })
  .array();

const getNetworkTypesData = () => {
  const maybeNetworkTypesData = getDomJson('network_types');
  if (!maybeNetworkTypesData) return [];
  return networkTypesDataSchema.parse(maybeNetworkTypesData);
};

export const networkTypesDataFromDOM = getNetworkTypesData();

const powerTypesDataSchema = z
  .object({
    element: z.string(),
    description: z.string(),
  })
  .array();

const getPowerTypesData = () => {
  const maybePowerTypesData = getDomJson('power_types');
  if (!maybePowerTypesData) return [];
  return powerTypesDataSchema.parse(maybePowerTypesData);
};

export const powerTypesFromDOM = getPowerTypesData();

const towerTypesDataSchema = z
  .object({
    element: z.string(),
    max: z.number(),
    min: z.number(),
    step: z.number(),
    value: z.number(),
    variable: z.string(),
  })
  .array();

const getTowerTypesData = () => {
  const maybeTowerTypesData = getDomJson('tower_data');
  if (!maybeTowerTypesData) return [];
  return towerTypesDataSchema.parse(maybeTowerTypesData);
};

export const towerTypesDataFromDOM = getTowerTypesData();

const towerDetailsDataSchema = z
  .object({
    variable: z.string(),
    value: z.number(),
    min: z.number(),
    max: z.number(),
    step: z.number(),
    unit: z.string(),
    element: z.string(),
    category: z.string(),
    seq: z.number(),
    alt: z.number(),
  })
  .array();

const getTowerDetailsData = () => {
  const maybeTowerDetailsData = getDomJson('tower_details');
  if (!maybeTowerDetailsData) return [];
  return towerDetailsDataSchema.parse(maybeTowerDetailsData);
};

export const towerDetailsDataFromDOM = getTowerDetailsData();

export const calculateLocationsAreaSqKm = (
  locations: readonly NetworkElement[],
): number =>
  Number(
    locations
      .filter((location) => !location.isSoftDeleted)
      .reduce((total, location) => total + Math.PI * location.radius ** 2, 0)
      .toFixed(2),
  );

export const calculateOverrideHouseholds = (
  locations: readonly NetworkElement[],
): number =>
  locations
    .filter((location) => !location.isSoftDeleted)
    .reduce((total, location) => {
      if (location.use_model_households) return total;
      const households = Number(location.households);
      return Number.isFinite(households) ? total + households : total;
    }, 0);

const midhaulDataSchema = z
  .object({
    capital_cost_usd: z.number(),
    element: z.string(),
    name: z.string(),
    power_watts: z.number(),
    speed_mbps: z.number(),
  })
  .array();

const getMidhaulData = () => {
  const maybeMidhaulData = getDomJson('midhaul_data');
  if (!maybeMidhaulData) return [];
  return midhaulDataSchema
    .parse(maybeMidhaulData)
    .sort((a, b) => a.element.localeCompare(b.element))
    .filter(
      // UI doesn't show this option
      (item) => item.name !== 'None',
    );
};

export const midhaulDataFromDOM = getMidhaulData();

const backhaulDataSchema = z
  .object({
    capital_cost_usd: z.number(),
    cost_base: z.number(),
    cost_mbps: z.number(),
    element: z.string(),
    name: z.string(),
    power_watts: z.number(),
    speed_mbps: z.number(),
    type: z.string().optional(),
  })
  .array();

const getBackhaulData = () => {
  const maybeBackhaulData = getDomJson('backhaul_data');
  if (!maybeBackhaulData) return [];
  return backhaulDataSchema
    .parse(maybeBackhaulData)
    .sort((a, b) => a.name.localeCompare(b.name))
    .filter(
      // UI doesn't show this option
      (item) => item.name !== 'None',
    );
};

export const backhaulDataFromDOM = getBackhaulData();

const techDataSchema = z
  .object({
    bts_gain: z.number(),
    cost_per_sector: z.number(),
    cpe_cost: z.number(),
    efficiency_bits_hz: z.number(),
    element: z.string(),
    frequency: z.number(),
    frequency_name: z.string(),
    id: z.number(),
    lifespan: z.number().nullable(),
    manualSort: z.number(),
    max: z.number(),
    max_path_loss: z.number(),
    max_radius: z.number(),
    min: z.number(),
    network_type: z.string(),
    nominal_freq: z.number(),
    power_consumption: z.number(),
    required_signal: z.number(),
    spectrum_mhz: z.number(),
    technology: z.string(),
    technology_name: z.string(),
    ue_cost: z.number(),
    ue_gain: z.number(),
    ue_per_sector: z.number(),
    ue_tx_power: z.number(),
    unit: z.string(),
    veg_loss_meter: z.number(),
    wavelength: z.number(),
  })
  .array();

const getTechData = () => {
  const maybeTechData = getDomJson('tech_data');
  if (!maybeTechData) return [];
  return techDataSchema
    .parse(maybeTechData)
    .sort((a, b) => a.id - b.id)
};

export const techDataFromDOM = getTechData();
