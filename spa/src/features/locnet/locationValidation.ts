import type { NetworkElement } from '../form/NodeTypes/NetworkElements';

const hasTextValue = (value: string | null | undefined): boolean =>
  Boolean(value?.trim());

const hasTowerCost = (towerCost: string): boolean =>
  hasTextValue(towerCost) && Number.isFinite(Number(towerCost));

const hasNumericValue = (value: string): boolean =>
  hasTextValue(value) && Number.isFinite(Number(value));

export const hasConfiguredLocation = (
  locations: readonly NetworkElement[] | undefined,
): boolean => {
  return (
    locations?.some(
      (location) =>
        !location.isSoftDeleted &&
        hasTextValue(location.location_name) &&
        hasTextValue(location.power_type) &&
        hasTowerCost(location.towerType.cost_USD) &&
        hasNumericValue(location.towerType.opex_USD) &&
        hasNumericValue(location.towerType.height_m) &&
        (location.use_model_households ||
          hasNumericValue(location.households)) &&
        location.networkTypes.some(
          (networkType) =>
            !networkType.isSoftDeleted && hasTextValue(networkType.type),
        ) &&
        [...location.midhaulLink, ...location.backhaulLinks].some(
          (link) => !link.isSoftDeleted && hasTextValue(link.type),
        ),
    ) ?? false
  );
};
