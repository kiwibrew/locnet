import type { Option } from './RadioToggleButtons';

export const getOrganisationTypesData = (): {
  name: string;
  options: Option[];
  defaultValue: string;
} => {
  return {
    name: 'provider_type',
    options: [
      { value: 'provider_community', intlId: 'provider_community' },
      { value: 'provider_commercial', intlId: 'provider_commercial' },
    ],
    defaultValue: 'provider_community',
  };
};
