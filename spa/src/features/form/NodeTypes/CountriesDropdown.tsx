import { z } from 'zod';
import { formPathJoin } from '../path';
import { FormNodeSchema } from '../base';
import { type NodeProps } from '../node';
import { useCallback, type ChangeEvent } from 'react';
import styles from './CountriesDropdown.module.css';
import { useStaticFormTsContext, type ModelPath } from '../FormProvider';
import { getDomJson } from '../domJson';
import { useIntlIdOrText } from '../Intl.utils';

export const CountriesDropdownSchema = FormNodeSchema.extend({
  type: z.literal('CountriesDropdown'),
  placeholder: z.string().optional(),
  value: z.string().optional(),
  modelPath: z.string().optional(),
});

export type CountriesDropdown = z.infer<typeof CountriesDropdownSchema>;

type Props = NodeProps<CountriesDropdown>;

const countriesJsonSchema = z.record(z.string(), z.string());

const getCountries = () => {
  const maybeCountriesData = getDomJson('countries');
  if (!maybeCountriesData) return [];
  const countriesData = countriesJsonSchema.parse(maybeCountriesData);
  return Object.entries(countriesData);
};

const countries = getCountries();

export const RenderCountriesDropdown = ({ formPath, node }: Props) => {
  const { useFormAndModel } = useStaticFormTsContext();
  const valueId = formPathJoin<CountriesDropdown>(formPath, 'value');
  const [value, setValue] = useFormAndModel(
    valueId,
    node.modelPath as ModelPath,
    node.value,
  );
  const labelText = useIntlIdOrText(node.labelIntlId, node.labelText);

  const handleChange = useCallback(
    (e: ChangeEvent<HTMLSelectElement>) => {
      const { target } = e;
      if (!(target instanceof HTMLSelectElement)) {
        throw Error('expected <select>');
      }
      setValue(target.value);
    },
    [setValue],
  );

  return (
    <select
      id="selectCountries"
      onChange={handleChange}
      value={value}
      aria-label={labelText}
      className={styles.select}
    >
      <option value="" disabled selected>
        {labelText}
      </option>
      {countries.map((country) => {
        return <option value={country[1]}>{country[0]}</option>;
      })}
    </select>
  );
};
