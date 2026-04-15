import { z } from 'zod';
import { formPathJoin } from '../path';
import { FormNodeSchema } from '../base';
import { NodesSchema, type NodeProps } from '../node';
import styles from './ToggleButton.module.css';
import { useStaticFormTsContext } from '../FormProvider';
import { useCallback, type ChangeEvent } from 'react';
import { Text } from '../Intl';

export const ToggleButtonSchema = FormNodeSchema.extend({
  type: z.literal('ToggleButton'),
  value: z.string(),
  checked: z.boolean().optional(),
  disabled: z.boolean().optional(),
  modelPath: z.string().optional(),
  get children() {
    return NodesSchema;
  },
});

export type ToggleButton = z.infer<typeof ToggleButtonSchema>;

type Props = NodeProps<ToggleButton>;

export const RenderToggleButton = ({ node, formPath }: Props) => {
  const { useFormAndModel } = useStaticFormTsContext();

  const checkedId = formPathJoin<ToggleButton>(formPath, 'checked');
  const [isChecked, setIsChecked] = useFormAndModel(checkedId, node.modelPath, node.checked);

  const handleChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const { target } = e;
      if (!(target instanceof HTMLInputElement)) {
        throw Error('expected <input>');
      }
      if (target.type !== 'checkbox') {
        throw Error('Expected checkbox');
      }
      setIsChecked(target.checked);
    },
    [setIsChecked],
  );

  return (
    <div>
      <label
        className={[
          styles.label,
          isChecked ? styles.label_selected : styles.label_unselected,
        ].join(' ')}
      >
        <input
          id={checkedId}
          name={checkedId}
          type="checkbox"
          value={node.value}
          className={styles.input}
          checked={isChecked}
          disabled={node.disabled}
          onChange={handleChange}
        />
        <Text intlId={node.labelIntlId} text={node.labelText} />
      </label>
      {node.descriptionIntlId && (
        <div className={styles.description}>
          <Text intlId={node.descriptionIntlId} />
        </div>
      )}
    </div>
  );
};
