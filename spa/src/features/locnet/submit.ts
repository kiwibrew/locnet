import { ApiClient, type BuilderInput } from './api-generated-client';
import type { SubmitHandler } from '../form/useStaticFormTs';
import type { EditableLocNetForm } from './formData';
import {
  type EditableLocNetModel,
  type LocNetModel,
  type LocNetModelOmitLocations,
} from './model';
import { useCallback } from 'react';
import { builderInputSchema } from './api-generated-zod';
import { removeSoftDeletes } from '../form/softDeletes';
import {
  newBlankBackhaulLink,
  newBlankLocation,
  newBlankNetworkType,
  calculateLocationsAreaSqKm,
  calculateOverrideHouseholds,
  towerTypesDataFromDOM,
} from '../form/NodeTypes/NetworkElements.utils';
import type { NetworkElement } from '../form/NodeTypes/NetworkElements';
import { generateRandomKey } from '../form/key';

declare global {
  interface Window {
    locnetBuilderInputToModel: (input: BuilderInput) => LocNetModel;
  }
}

export const GEOSPATIAL_API_ERROR_MESSAGE =
  "The model could not be processed because an API doesn't have data on the location";

export const useLocNetServerSubmit = () => {
  const handleSubmit: SubmitHandler<EditableLocNetForm, EditableLocNetModel> =
    useCallback((props) => {
      const { model, immerForm, queueFormSideEffect } = props;
      const maybeBuilderInput = locnetModelToBuilderInput(model.root);
      const { data: builderInput, error } =
        builderInputSchema.safeParse(maybeBuilderInput);
      if (error) {
        console.error(
          "Builder input validation error. Can't submit",
          maybeBuilderInput,
          error,
        );
        return;
      }

      immerForm.nodes[2].children[0].isButtonVisible = true;
      immerForm.nodes[2].children[0].isOpen = false;
      immerForm.nodes[3].isLoading = true;
      immerForm.nodes[4].isOpen = false;
      immerForm.api.modelerAPIOutput = undefined;
      queueFormSideEffect('api.modelerAPIOutput', submitModel(builderInput));
      window.scrollTo(0, 0);
    }, []);
  return handleSubmit;
};

export const submitModel = async (
  builderInput: BuilderInput,
): Promise<EditableLocNetForm['api']['modelerAPIOutput']> => {
  const api = new ApiClient();
  try {
    const modelResult =
      await api.apiPOSTEndpoints.modelerApiApiModelerPost(builderInput);
    return modelResult;
  } catch (e) {
    let message = String(e);
    if (e instanceof Response) {
      console.error('Non-JSON server response', e);
      message =
        e.status === 502
          ? GEOSPATIAL_API_ERROR_MESSAGE
          : `The server returned HTTP ${e.status}${e.statusText ? ` ${e.statusText}` : ''}.`;
    } else if (e && typeof e === 'object' && 'detail' in e) {
      console.error('Server response', e);
      message = String(e.detail);
    } else {
      console.error(e);
    }
    return { type: 'error', message };
  }
};

export const locnetModelToBuilderInput = (
  locNetModel?: Partial<LocNetModel>,
): Partial<BuilderInput> => {
  if (!locNetModel) {
    return {};
  }

  const model = removeSoftDeletes(locNetModel);
  const modelWithoutLegacyProfiles = { ...model };
  delete (modelWithoutLegacyProfiles as Record<string, unknown>).terrain_type;
  delete (modelWithoutLegacyProfiles as Record<string, unknown>).vegetation_type;

  return {
    ...modelWithoutLegacyProfiles,
    model_version: 2,
    area_sqkm: calculateLocationsAreaSqKm(model.locations ?? []),
    households_total: calculateOverrideHouseholds(model.locations ?? []),
    total_potential_users: undefined,
    locations: model.locations?.map(networkElementToLocationData) ?? [],
  };
};

export const locnetBuilderInputToModel = (
  locNetBuilderInput: BuilderInput,
): LocNetModel => {
  return {
    ...(locNetBuilderInput satisfies LocNetModelOmitLocations),
    locations: locNetBuilderInput.locations.map(
      (location, index): LocNetModel['locations'][number] => {
        const networkElement = locationDataToNetworkElement(location, index);
        const locnetLocation = newBlankLocation(index, networkElement);
        if (location.tower_cost) {
          locnetLocation.towerType.cost_USD = location.tower_cost?.toString();
        }
        locnetLocation.power_type = location.power_type;
        locnetLocation.networkTypes = location.network_type.map(
          (networkType, networkTypeIndex) => {
            const locnetNetworkLocation = newBlankNetworkType(networkTypeIndex);
            locnetNetworkLocation.type = networkType;
            locnetNetworkLocation.unitCount =
              location.sectors[networkTypeIndex].toString();
            return locnetNetworkLocation;
          },
        );
        locnetLocation.backhaulLinks = location.backhaul_links.map(
          (backhaul_link, backhaul_link_index) => {
            const backhaulLink = newBlankBackhaulLink(backhaul_link_index, {
              name: `Backhaul link ${backhaul_link_index} `,
              type: backhaul_link,
              monthlyCharge:
                location.backhaul_cost_base?.[backhaul_link_index].toString(),
              trafficCost_USD:
                location.backhaul_cost_mbps?.[backhaul_link_index].toString(),
            });
            return backhaulLink;
          },
        );
        return locnetLocation;
      },
    ),
  };
};

if (typeof window !== 'undefined') {
  (window as Window).locnetBuilderInputToModel = locnetBuilderInputToModel;
}

const networkElementToLocationData = (
  networkElement: NetworkElement,
): BuilderInput['locations'][number] => ({
  location_name: networkElement.location_name,
  latitude: networkElement.latitude,
  longitude: networkElement.longitude,
  radius: networkElement.radius,
  households: networkElement.use_model_households
    ? null
    : parseInt(networkElement.households, 10),
  power_type: networkElement.power_type ?? null,
  tower_cost: parseFloat(networkElement.towerType.cost_USD),
  tower_opex: parseFloat(networkElement.towerType.opex_USD),
  tower_height: parseFloat(networkElement.towerType.height_m),
  network_type: networkElement.networkTypes.map(
    (networkType) => networkType.type,
  ),
  sectors: networkElement.networkTypes
    .map((networkType) => parseFloat(networkType.unitCount))
    .filter((num) => !Number.isNaN(num)),
  network_links: networkElement.midhaulLink.map(
    (midhaulLink) => midhaulLink.type,
  ),
  backhaul_links: networkElement.backhaulLinks
    .map((backhaulLink) => backhaulLink.type)
    .filter((val) => !!val),
  backhaul_cost_base: networkElement.backhaulLinks
    .map((backhaulLink) => parseFloat(backhaulLink.monthlyCharge))
    .filter((num) => !Number.isNaN(num)),
  backhaul_cost_mbps: networkElement.backhaulLinks
    .map((backhaulLink) => parseFloat(backhaulLink.trafficCost_USD))
    .filter((num) => !Number.isNaN(num)),
});

const locationDataToNetworkElement = (
  locationData: BuilderInput['locations'][number],
  index: number,
): NetworkElement => ({
  type: 'NetworkElement',
  isSoftDeleted: false,
  index,
  number: index,
  location_name: locationData.location_name,
  latitude: locationData.latitude,
  longitude: locationData.longitude,
  radius: locationData.radius ?? 2,
  use_model_households: locationData.households == null,
  households: locationData.households?.toString() ?? '',
  power_type: locationData.power_type,
  networkTypes: locationData.network_type.map(
    (network_type_item, index): NetworkElement['networkTypes'][number] => {
      const sector = locationData.sectors[index];
      if (typeof sector !== 'number') {
        throw Error(`Expected 'sector' to be number but was ${typeof sector}`);
      }
      return {
        key: generateRandomKey(),
        isSoftDeleted: false,
        index: index,
        type: network_type_item,
        unitCount: sector.toString(),
      };
    },
  ),
  towerType: {
    name: towerTypesDataFromDOM[0]?.variable ?? '',
    cost_USD: locationData.tower_cost?.toString() ?? '',
    opex_USD: locationData.tower_opex?.toString() ?? '',
    height_m: locationData.tower_height?.toString() ?? '',
  },
  midhaulLink: locationData.network_links.map(
    (network_link_item, index): NetworkElement['midhaulLink'][number] => {
      return {
        key: generateRandomKey(),
        index,
        isSoftDeleted: false,
        type: network_link_item,
        name: '',
      };
    },
  ),
  backhaulLinks: locationData.backhaul_links.map(
    (backhaul_link, index): NetworkElement['backhaulLinks'][number] => {
      return {
        key: generateRandomKey(),
        isSoftDeleted: false,
        index,
        type: backhaul_link,
        name: '',
        monthlyCharge: locationData.backhaul_cost_base?.toString() ?? '',
        trafficCost_USD: locationData.backhaul_cost_mbps?.toString() ?? '',
      };
    },
  ),
  labelIntlId: undefined,
  labelText: undefined,
  descriptionIntlId: undefined,
  descriptionText: undefined,
  location_name_error: undefined,
});
