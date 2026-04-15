import { z } from 'zod';
import { NodesSchema, type Node, type NodeProps } from '../node';
import { formPathJoin } from '../path';
import { RenderNodes } from '../RenderNodes';
import { getFrequencies } from './Frequencies.utils';
import { useMemo } from 'react';
import { useStaticFormTsContext } from '../FormProvider';
import styles from './Technologies.module.css';

export const FrequenciesSchema = z.object({
  type: z.literal('Frequencies'),
  get children() {
    return NodesSchema;
  },
  modelPath: z.string().optional(),
});
export type Frequencies = z.infer<typeof FrequenciesSchema>;
type FrequenciesProps = NodeProps<Frequencies>;

export const RenderFrequencies = ({ formPath }: FrequenciesProps) => {
  const { useFormStore } = useStaticFormTsContext();
  const childrenId = formPathJoin<Frequencies>(formPath, 'children');

  const childrenNodes = useMemo((): Node[] => {
    const valueStore = useFormStore.getState();
    const frequencies = getFrequencies().sort(
      (a, b) => a.frequency - b.frequency,
    );
    const frequencyNodes = frequencies.map((technology): Node => {
      const upperName = technology.frequency_name.toUpperCase();
      const isIsm = upperName.includes('ISM');
      const isGpon = upperName.includes('GPON');
      return {
        type: 'ToggleButton',
        value: technology.frequency.toString(),
        labelText: technology.frequency_name,
        ...(isIsm || isGpon
          ? {
              checked: true,
              disabled: true,
            }
          : {}),
      };
    });
    valueStore.set(childrenId, frequencyNodes);
    return frequencyNodes;
  }, [useFormStore, childrenId]);

  return (
    <div className={styles.container}>
      <RenderNodes id={childrenId} nodes={childrenNodes} />
    </div>
  );
};
