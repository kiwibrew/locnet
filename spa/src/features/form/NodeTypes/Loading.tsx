import { z } from 'zod';
import { FormNodeSchema } from '../base';
import { type NodeProps } from '../node';
import { useStaticFormTsContext } from '../FormProvider';
import { formPathJoin } from '../path';
import style from './Loading.module.css';

export const LoadingSchema = FormNodeSchema.extend({
  type: z.literal('Loading'),
  isLoading: z.boolean().optional(),
});

export type Loading = z.infer<typeof LoadingSchema>;

type Props = NodeProps<Loading>;

export const RenderLoading = (props: Props) => {
  const { useFormAndModel } = useStaticFormTsContext();
  const isLoadingPath = formPathJoin<Loading>(props.formPath, 'isLoading');
  const [isLoading] = useFormAndModel(isLoadingPath, undefined, false);
  if (isLoading) {
    return (
      <div className={style.spinnerContainer}>
        <div className={style.spinner} aria-live="polite" aria-atomic>
          Loading
        </div>
      </div>
    );
  }
  return null;
};
