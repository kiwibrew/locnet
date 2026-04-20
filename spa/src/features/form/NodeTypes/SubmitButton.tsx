import { z } from 'zod';
import { FormNodeSchema } from '../base';
import { type NodeProps } from '../node';
import styles from './SubmitButton.module.css';
import { Text } from '../Intl';
import { useStaticFormTsContext } from '../FormProvider';

export const SubmitButtonSchema = FormNodeSchema.extend({
  type: z.literal('SubmitButton'),
  value: z.string().optional(),
});

export type SubmitButton = z.infer<typeof SubmitButtonSchema>;

type Props = NodeProps<SubmitButton>;

export const RenderSubmitButton = ({ node, formPath }: Props) => {
  const { useWatchFormMetaStore } = useStaticFormTsContext();

  const isSubmitting = useWatchFormMetaStore('value.isSubmitting', false as boolean);

  return (
    <div className={styles.submitButtonContainer}>
      <button
        type="submit"
        disabled={isSubmitting}
        id={formPath}
        className={styles.submitButton}
        data-testid={node.labelIntlId}
      >
        <Text intlId={node.labelIntlId} text={node.labelText} />
      </button>
    </div>
  );
};
