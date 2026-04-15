import { z } from 'zod';
import { useCallback, type ChangeEvent } from 'react';
import { FormNodeSchema } from '../base';
import { type NodeProps } from '../node';
import { useStaticFormTsContext } from '../FormProvider';
import { formPathJoin } from '../path';
import styles from './FieldHelp.module.css';
import { Text } from '../Intl';

export const FieldHelpSchema = FormNodeSchema.extend({
  type: z.literal('FieldHelp'),
  isOpen: z.boolean().optional(),
  textIntlId: z.string().optional(),
  text: z.string().optional(),
});

export type FieldHelp = z.infer<typeof FieldHelpSchema>;

type Props = NodeProps<FieldHelp>;

export const RenderFieldHelp = ({ formPath, node }: Props) => {
  const { useWatchFormStore, useFormStore } = useStaticFormTsContext();

  const isOpenId = formPathJoin<FieldHelp>(formPath, 'isOpen');
  const isOpen = useWatchFormStore(isOpenId, node.isOpen);

  const handleChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const { target } = e;
      if (!(target instanceof HTMLInputElement)) {
        throw Error('expected <input>');
      }
      if (target.type !== 'checkbox') {
        throw Error('Expected checkbox');
      }
      useFormStore.getState().set(isOpenId, target.checked);
    },
    [useFormStore, isOpenId],
  );

  return (
    <>
      <label className={styles.label}>
        <input
          id={isOpenId}
          name={isOpenId}
          type="checkbox"
          className={styles.checkbox}
          checked={isOpen}
          onChange={handleChange}
        />
        <QuestionMarkCircle isOpen={isOpen} />
      </label>
      {isOpen && (
        <div className={styles.helpText}>
          <Text intlId={node.textIntlId} text={node.text} />
        </div>
      )}
    </>
  );
};

type QuestionMarkCircleProps = {
  isOpen?: boolean;
};

// Also used by `Select`
export const QuestionMarkCircle = ({ isOpen }: QuestionMarkCircleProps) => {
  return (
    <span
      className={[
        styles.questionMarkCircle,
        isOpen && styles.questionMarkCircle_isOpen,
      ].join(' ')}
      aria-label="Toggle field help"
    >
      ?
    </span>
  );
};
