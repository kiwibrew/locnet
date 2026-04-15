import { countBy } from 'lodash-es';
import type { Resolver } from '../form/useStaticFormTs';
import type { EditableLocNetForm } from './formData';
import {
  isApiCharacteristicsDefaultsDetailArray,
  type EditableLocNetModel,
  type LocNetModel,
} from './model';
import { getCharacteristics } from './api';

type LocNetFormValueResolver = Resolver<
  EditableLocNetForm,
  EditableLocNetModel
>;

export const locNetFormResolver: LocNetFormValueResolver = ({
  formPath,
  modelRootPath,
  previousValue,
  newValue,
  immerForm,
  immerModel,
  setErrorByModelRootPath,
  setFormAndModelValueByModelRootPath,
  getFormNodeByType,
  queueFormSideEffect,
  immerMeta,
}) => {
  // Reveal the rest of the form after choosing a country
  if (modelRootPath === 'iso_3' && Boolean(newValue)) {
    if (newValue !== previousValue) {
      console.log('Loading new country defaults data ', newValue);
      // reset the value
      immerForm.api.characteristics = undefined;
      queueFormSideEffect(
        'api.characteristics',
        getCharacteristics({ iso_3: newValue }),
      );
      immerForm.nodes[3].isLoading = true;
      immerForm.nodes[0].isOpen = false;
      immerForm.nodes[0].isButtonVisible = true;
    } else {
      // pass
    }
  }

  // when these fields change recalculate other values
  switch (modelRootPath) {
    case 'households_total':
    case 'hh_size':
    case 'paf_non_sub_use': {
      const households = getNumberOrUndefined(immerModel.root.households_total);
      const size = getNumberOrUndefined(immerModel.root.hh_size);
      const nonUsers = getNumberOrUndefined(immerModel.root.paf_non_sub_use);

      // Calculate users per household: hh_size * (1-(non_users_pct/100))
      const usersPerHH = size * (1 - nonUsers / 100);

      // Calculate total potential users: households_total * users_per_household
      const totalUsers = households * usersPerHH;

      // Update the read-only fields with formatted values
      setFormAndModelValueByModelRootPath(
        'users_per_household',
        parseFloat(usersPerHH.toFixed(2)), // 2 decimal places, converted back to number
      );
      setFormAndModelValueByModelRootPath(
        'total_potential_users',
        Math.round(totalUsers), // Rounded to whole number
      );
      break;
    }
    case 'hh_income_week':
    case 'paf_facilities_charge': {
      const incomeWeek = getNumberOrUndefined(immerModel.root.hh_income_week);
      const facilitiesCharge = getNumberOrUndefined(immerModel.root.paf_facilities_charge);

      // Calculate paf_usd_hour: hh_income_week * (paf_facilities_charge/100)
      const pafHourValue = incomeWeek * (facilitiesCharge / 100);

      // Update the read-only field with formatted value
      setFormAndModelValueByModelRootPath(
        'paf_usd_hour',
        parseFloat(pafHourValue.toFixed(2)), // 2 decimal places, converted back to number
      );
      break;
    }
  }

  if (formPath === 'api.characteristics') {
    // Reveal form
    console.log('formPath was ', formPath);
    immerForm.nodes[3].isLoading = false; // hide loading
    immerForm.nodes[2].isInert = false; // show inert

    immerForm.nodes[2].children[0].isOpen = true; // show disclosure
  }

  if (formPath === 'api.modelerAPIOutput' && !!newValue) {
    immerForm.nodes[3].isLoading = false;
    immerMeta.value.isSubmitting = false;
    const { modelerAPIOutput } = immerForm.api;
    if (
      modelerAPIOutput &&
      'type' in modelerAPIOutput &&
      modelerAPIOutput.type === 'error'
    ) {
      // do nothing. There should have been an alert() shown to the user
    } else {
      immerForm.nodes[4].isOpen = true;
    }
  }

  const technologies = getFormNodeByType('Technologies');
  if (technologies && technologies.children) {
    // Only show frequencies if they chose wireless technology
    const shouldShowFrequenciesSelector = technologies.children.some(
      (node) =>
        node.type === 'ToggleButton' &&
        ['FWA', 'Mobile'].includes(node.value ?? '') &&
        node.checked,
    );
    immerForm.nodes[2].children[0].children[2].isInert =
      !shouldShowFrequenciesSelector;

    // Only show Public Access Facilities if they selected it
    const shouldShowPublicAccessFacilitiesSelector = technologies.children.some(
      (node) =>
        node.type === 'ToggleButton' && node.value === 'PAF' && node.checked,
    );
    immerForm.nodes[2].children[0].children[3].isInert =
      !shouldShowPublicAccessFacilitiesSelector;
  }

  // Show errors if locations have the same name
  const locationNameCounts = countBy(
    immerModel.root?.locations,
    (location) => location.location_name,
  );
  immerModel.root?.locations?.forEach((location, index) => {
    const hasDuplicates = locationNameCounts[location.location_name] > 1;
    setErrorByModelRootPath(
      `locations.${index}.location_name`,
      hasDuplicates ? 'Has duplicates' : undefined,
    );
  });

  const selectedFrequencies =
    immerForm.nodes[2].children[0].children[2].children[0].children[0].children
      ?.map((node) => {
        if (node.type !== 'ToggleButton') {
          return undefined;
        }
        if (!node.checked) {
          return undefined;
        }
        return node.labelText;
      })
      .filter((maybeLabel) => Boolean(maybeLabel));

  if (selectedFrequencies && selectedFrequencies.length === 0) {
    // No frequencies are selected, so set initial spectrum fee to 0
    setFormAndModelValueByModelRootPath('spectrum_licence_fee', '0');
  }

  // When organisation type changes update the values
  if (modelRootPath === 'provider_type') {
    const elementsToSwap = [
      'oc_margin',
      'other_opex',
      'corp_tax',
      'wacc',
      'finance_cost',
      'staff_opex_fixed',
      'staff_opex_variable',
      'power_reliable_hours',
      'power_intermittent_hours',
      'power_offgrid_hours',
      'power_hybrid_hours',
    ] satisfies (keyof LocNetModel)[];

    if (
      !immerForm.api.characteristics ||
      (immerForm.api.characteristics &&
        !isApiCharacteristicsDefaultsDetailArray(immerForm.api.characteristics))
    ) {
      console.warn(
        "API characteristics (defaults detail) isn't available yet. The data may still be loading.",
        {
          characteristics: structuredClone(immerForm.api.characteristics),
          modelRootPath,
        },
      );
      return;
    }

    elementsToSwap.forEach((elementToSwap) => {
      if (
        !immerForm.api.characteristics ||
        (immerForm.api.characteristics &&
          !isApiCharacteristicsDefaultsDetailArray(
            immerForm.api.characteristics,
          ))
      ) {
        return;
      }
      const elementDefaultData = immerForm.api.characteristics.find(
        (obj) => obj.element === elementToSwap,
      );
      if (elementDefaultData) {
        setFormAndModelValueByModelRootPath(
          elementToSwap,
          newValue === 'provider_community'
            ? elementDefaultData.value
            : elementDefaultData.alt,
        );
      }
    });
  }
};

const getNumberOrUndefined = (
  val: number | string | null | undefined,
): number => {
  return val ? parseFloat(String(val)) : 0;
};
