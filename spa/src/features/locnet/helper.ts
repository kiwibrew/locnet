import { get } from 'lodash-es';
import { useCallback } from 'react';
import { assertNever } from '../../utils/typescript';
import { type BuilderInput } from './api-generated-client';
import { locnetStaticFormValue, type LocNetFormPath } from './formData';
import { type LocNetModel } from './model';
import { locnetBuilderInputToModel } from './submit';
import { useStaticFormTsContext } from '../form/FormProvider';

// Sample data value from API docs
export const sampleData: BuilderInput = {
  model_version: 2,
  iso_3: 'PER',
  area_sqkm: 100,
  households_total: 100,
  users_per_household: 3.19,
  total_potential_users: 319,
  pop_growth_rate: 1.1,
  hh_income_week: 245.9,
  paf_usd_hour: 0.6,
  capex_subsidy: 10000,
  businesses: 1,
  business_users: 2,
  service_providers: 1,
  service_provider_users: 2,
  paf_deterred_use: 13,
  paf_sub_use: 4,
  paf_non_sub_use: 9,
  paf_facilities_charge: 0.25,
  provider_type: 'provider_community',
  oc_margin: 15,
  other_opex: 7.5,
  corp_tax: 0,
  wacc: 6,
  finance_cost: 5,
  staff_opex_fixed: 1.2,
  staff_opex_variable: 0.3,
  power_reliable_hours: 4,
  power_intermittent_hours: 24,
  power_offgrid_hours: 48,
  power_hybrid_hours: 12,
  labour_cost: 4.6,
  maintenance_opex: 2,
  opex_subsidy: 0,
  ue_subsidy: 0,
  ue_cost: 100,
  debt_proportion: 50,
  inflation: 2.01,
  spectrum_licence_fee: 0,
  community_capex_discount: 0,
  system_life: 10,
  year_1_traffic: 10,
  traffic_growth: 25,
  hh_size: 3.5,
  existing_ue_above_med: 50,
  existing_ue_below_med: 30,
  mains_power_installation_cost: 2000,
  mains_power_cost_kwh: 0.65,
  solar_cost_watt: 0.6,
  battery_cost_watt_hour: 0.3,
  battery_dod: 80,
  charger_inverter_base: 50,
  charger_inverter_variable: 0.35,
  solar_efficiency: 21,
  solar_derating: 0.5,
  battery_age_derating: 0.5,
  locations: [
    {
      location_name: 'Location 1',
      latitude: 0,
      longitude: 0,
      radius: 2,
      households: null,
      power_type: 'power_mains_rel',
      tower_cost: 1000,
      tower_opex: 0,
      tower_height: 6,
      network_type: ['ISM FWA 5.8 GHz', 'ISM Wi-Fi 2.4 GHz'],
      sectors: [1, 1],
      network_links: ['ISM FWA 500'],
      backhaul_links: [],
      backhaul_cost_base: [],
      backhaul_cost_mbps: [],
    },
    {
      location_name: 'Location 2',
      latitude: 0,
      longitude: 0,
      radius: 2,
      households: null,
      power_type: 'power_mains_rel',
      tower_cost: 1000,
      tower_opex: 0,
      tower_height: 6,
      network_type: ['ISM FWA 5.8 GHz', 'ISM Wi-Fi 2.4 GHz'],
      sectors: [1, 1],
      network_links: ['ISM FWA 500', 'ISM FWA 500'],
      backhaul_links: ['LEO Satellite'],
      backhaul_cost_base: [100],
      backhaul_cost_mbps: [5],
    },
    {
      location_name: 'Location 3',
      latitude: 0,
      longitude: 0,
      radius: 2,
      households: null,
      power_type: 'power_solar',
      tower_cost: 1000,
      tower_opex: 0,
      tower_height: 6,
      network_type: ['ISM FWA 5.8 GHz', 'ISM Wi-Fi 2.4 GHz'],
      sectors: [1, 1],
      network_links: ['ISM FWA 500'],
      backhaul_links: ['Fibre 1G', 'HTS VSAT'],
      backhaul_cost_base: [200, 50],
      backhaul_cost_mbps: [0.5, 20],
    },
  ],
};

export const useLoadBuilderInput = () => {
  const { useFormStore, setModelAndFormByModelRoot, waitForFormChange } =
    useStaticFormTsContext();

  return useCallback(
    async (builderInput: BuilderInput) => {
      
      const locnetModel = locnetBuilderInputToModel(builderInput);

      setModelAndFormByModelRoot('iso_3', locnetModel.iso_3);

      // Wait for new characteristics to load
      const newCharacteristics = await waitForFormChange(
        'api.characteristics',
        locnetStaticFormValue.api.characteristics,
      );
      if (!newCharacteristics) {
        throw Error('Should have loaded API characteristics');
      }

      // wait for form to render updates
      await sleepPromise(50)

      type Params = Parameters<typeof setModelAndFormByModelRoot>;
      type Param2 = NonNullable<Params[2]>;
      type FormPath = Param2[string];

      const formPathForTechnologies: LocNetFormPath =
        'nodes.2.children.0.children.1.children.0';
      const technologies = get(useFormStore.getState(), formPathForTechnologies);
      if (!technologies || technologies.type !== 'Technologies') {
        throw Error('Unable to find technologies node');
      }
      technologies.children?.forEach((technologyToggleButton, index) => {
        if (technologyToggleButton.type !== 'ToggleButton') {
          console.log({ technologyToggleButton });
          throw Error("Couldn't find technology toggle button");
        }
        // Set every technology option as available so that NetworkElements has <select> options of all technologies
        const technologyOptionFormPath = `${formPathForTechnologies}.children.${index}.checked`;
        useFormStore.getState().set(technologyOptionFormPath, true);
      });

      // wait for form to render updates
      await sleepPromise(1000)

      const formPathForNetworkElements: LocNetFormPath =
        'nodes.2.children.0.children.6.children.0';
      const networkElements = get(useFormStore.getState(), formPathForNetworkElements);
      if (!networkElements || networkElements.type !== 'NetworkElements') {
        console.error(
          "Network elements isn't at ",
          formPathForNetworkElements,
          networkElements,
        );
        throw Error("Couldn't find NetworkElements");
      }

      // Set stub data structures for locations so that we can fill them

      const mappings = {
        locations: `${formPathForNetworkElements}.locations` as LocNetFormPath,
        ...locnetModel.locations.reduce((acc, _location, index) => {
          const modelRootPath = `locations.${index}.location_name`;
          acc[modelRootPath] =
            `${formPathForNetworkElements}.${modelRootPath}` as FormPath;
          return acc;
        }, {} as Param2),
      } as Param2;

      setModelAndFormByModelRoot('locations', locnetModel.locations, mappings);
      
      Object.entries(locnetModel).forEach(([_key, newValue]) => {
        const key = _key as keyof LocNetModel;

        switch (key) {
          case 'locations':
          case 'iso_3':
            // already set these, above
            // although this 'case' code does nothing we're putting the key
            // in the switch/case to allow assertNever() below to work
            // and assert that we've handled all keys
            break;
          case 'model_version':
          case 'area_sqkm':
          case 'battery_age_derating':
          case 'battery_cost_watt_hour':
          case 'battery_dod':
          case 'charger_inverter_base':
          case 'charger_inverter_variable':
          case 'labour_cost':
          case 'lang':
          case 'mains_power_cost_kwh':
          case 'mains_power_installation_cost':
          case 'power_hybrid_hours':
          case 'power_intermittent_hours':
          case 'power_reliable_hours':
          case 'solar_cost_watt':
          case 'solar_derating':
          case 'solar_efficiency':
          case 'system_life':
          case 'total_potential_users':
          case 'traffic_growth':
          case 'users_per_household':
          case 'year_1_traffic':
          case 'households_total':
          case 'hh_size':
          case 'pop_growth_rate':
          case 'hh_income_week':
          case 'businesses':
          case 'business_users':
          case 'service_providers':
          case 'service_provider_users':
          case 'staff_opex_fixed':
          case 'staff_opex_variable':
          case 'maintenance_opex':
          case 'capex_subsidy':
          case 'opex_subsidy':
          case 'ue_subsidy':
          case 'finance_cost':
          case 'debt_proportion':
          case 'wacc':
          case 'corp_tax':
          case 'spectrum_licence_fee':
          case 'other_opex':
          case 'oc_margin':
          case 'community_capex_discount':
          case 'paf_deterred_use':
          case 'paf_sub_use':
          case 'paf_non_sub_use':
          case 'paf_gb_hour':
          case 'paf_facilities_charge':
          case 'paf_usd_hour':
          case 'ue_cost':
          case 'inflation':
          case 'power_offgrid_hours':
          case 'provider_type':
          case 'existing_ue_above_med':
          case 'existing_ue_below_med':
            setModelAndFormByModelRoot(key, newValue);
            break;
          default:
            assertNever(key);
        }
      });
    },
    [setModelAndFormByModelRoot, useFormStore, waitForFormChange],
  );
};

const sleepPromise = (delayMs: number) => new Promise((resolve) => setTimeout(resolve, delayMs))
