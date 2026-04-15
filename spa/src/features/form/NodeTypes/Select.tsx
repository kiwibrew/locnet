import { z } from 'zod';
import { formPathJoin } from '../path';
import { FormNodeSchema } from '../base';
import { type NodeProps } from '../node';
import { useStaticFormTsContext, type ModelPath } from '../FormProvider';
import { useCallback, type ChangeEvent } from 'react';
import styles from './Select.module.css';
import { Text } from '../Intl';
import { useIntlIdOrText } from '../Intl.utils';
import { QuestionMarkCircle } from './FieldHelp';

const OptionSchema = z.object({
  value: z.string(),
  labelIntlId: z.string().optional(),
  labelText: z.string().optional(),
});

export type Option = z.infer<typeof OptionSchema>;

export const SelectSchema = FormNodeSchema.extend({
  type: z.literal('Select'),
  value: z.string().optional(),
  placeholderText: z.string().optional(),
  placeholderIntlId: z.string().optional(),
  options: OptionSchema.array().optional(),
  modelPath: z.string().optional(),
  fieldHelpText: z.string().optional(),
  fieldHelpIntlId: z.string().optional(),
  fieldHelpIsOpen: z.boolean().optional(),
});

export type Select = z.infer<typeof SelectSchema>;

type Props = NodeProps<Select>;

export const RenderSelect = ({ node, formPath }: Props) => {
  const { useFormAndModel } = useStaticFormTsContext();

  const labelId = formPathJoin<Select>(formPath, 'labelIntlId');
  const valueId = formPathJoin<Select>(formPath, 'value');
  const [value, setValue] = useFormAndModel(
    valueId,
    node.modelPath as ModelPath,
    node.value,
  );

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

  const isFieldHelpOpenId = formPathJoin<Select>(formPath, 'fieldHelpIsOpen');
  const [isFieldHelpOpen, setIsFieldHelpOpen] = useFormAndModel(
    isFieldHelpOpenId,
    undefined,
    node.fieldHelpIsOpen ?? false,
  );
  const handleFieldHelpChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const { target } = e;
      if (!(target instanceof HTMLInputElement)) {
        throw Error('expected <input>');
      }
      if (target.type !== 'checkbox') {
        throw Error('Expected checkbox');
      }
      setIsFieldHelpOpen(target.checked);
    },
    [setIsFieldHelpOpen],
  );

  return (
    <>
      <div className={styles.container}>
        <label id={labelId} className={styles.label}>
          <span>
            <Text intlId={node.labelIntlId} text={node.labelText} />
            {(node.labelIntlId || node.labelText) && ':'}
          </span>
          <select
            onChange={handleChange}
            value={value}
            aria-label={useIntlIdOrText(node.labelIntlId, node.labelText)}
            className={styles.select}
          >
            {node.placeholderIntlId ||
              (node.placeholderText && <RenderPlaceholder {...node} />)}
            {node.options?.map((option) => {
              return <RenderOption {...option} />;
            })}
          </select>
        </label>
        {Boolean(node.fieldHelpIntlId || node.fieldHelpText) && (
          <>
            <label className={styles.fieldHelpLabel}>
              <input
                id={isFieldHelpOpenId}
                name={isFieldHelpOpenId}
                type="checkbox"
                className={styles.fieldHelpCheckbox}
                checked={isFieldHelpOpen}
                onChange={handleFieldHelpChange}
              />
              <QuestionMarkCircle isOpen={isFieldHelpOpen} />
            </label>
          </>
        )}
      </div>
      {isFieldHelpOpen && (
        <div className={styles.fieldHelpText}>
          <Text intlId={node.fieldHelpIntlId} text={node.fieldHelpText} />
        </div>
      )}
      {node.descriptionIntlId && (
        <div className={styles.description}>
          <Text intlId={node.descriptionIntlId} />
        </div>
      )}
    </>
  );
};

const RenderOption = (props: Option) => {
  return (
    <option value={props.value}>
      <Text intlId={props.labelIntlId} text={props.labelText} />
    </option>
  );
};

const RenderPlaceholder = ({ placeholderIntlId, placeholderText }: Select) => {
  return (
    <option value="" disabled selected>
      {useIntlIdOrText(placeholderIntlId, placeholderText)}
    </option>
  );
};
