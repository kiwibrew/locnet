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
  area_sqkm: 100,
  battery_age_derating: 0.5,
  battery_cost_watt_hour: 0.42,
  charger_inverter_base: 50,
  charger_inverter_variable: 0.35,
  iso_3: 'PER',
  labour_cost: 25,
  locations: [
    {
      location_name: 'Location 1',
      tower_cost: 1000,
      network_type: ['ISM Wi-Fi 2.4 GHz', 'ISM FWA 5.8 GHz'],
      sectors: [2, 2],
      network_links: ['ISM FWA 500'],
      backhaul_links: [],
      backhaul_cost_base: [],
      backhaul_cost_mbps: [],
      power_type: 'power_mains_rel',
    },
    {
      location_name: 'Location 2',
      tower_cost: 2000,
      network_type: ['ISM Wi-Fi 2.4 GHz', 'ISM FWA 5.8 GHz'],
      sectors: [2, 2],
      network_links: ['ISM FWA 500', 'ISM FWA 500'],
      backhaul_links: ['LEO Satellite'],
      backhaul_cost_base: [100],
      backhaul_cost_mbps: [5],
      power_type: 'power_mains_int',
    },
    {
      location_name: 'Location 3',
      tower_cost: 6000,
      network_type: ['ISM Wi-Fi 2.4 GHz', 'ISM FWA 5.8 GHz'],
      sectors: [3, 1],
      network_links: ['ISM FWA 500'],
      backhaul_links: ['Fibre 1G', 'HTS VSAT'],
      backhaul_cost_base: [200, 50],
      backhaul_cost_mbps: [0.5, 20],
      power_type: 'power_solar',
    },
  ],
  mains_power_cost_kwh: 0.65,
  mains_power_installation_cost: 2000,
  solar_cost_watt: 0.6,
  solar_derating: 0.1,
  solar_efficiency: 20,
  system_life: 10,
  terrain_type: 'None',
  total_potential_users: 500,
  traffic_growth: 30,
  users_per_household: 4,
  vegetation_type: 'None',
  year_1_traffic: 10,
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
        'nodes.2.children.0.children.7.children.0';
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
          case 'terrain_type':
          case 'total_potential_users':
          case 'traffic_growth':
          case 'users_per_household':
          case 'vegetation_type':
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