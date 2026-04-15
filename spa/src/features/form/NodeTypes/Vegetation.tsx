import { z } from 'zod';
import { NodesSchema, type Node, type NodeProps } from '../node';
import { formPathJoin } from '../path';
import { RenderNodes } from '../RenderNodes';
import { useMemo } from 'react';
import { useStaticFormTsContext } from '../FormProvider';
import styles from './Vegetation.module.css';
import { getVegetationsData } from './Vegetation.utils';

export const VegetationSchema = z.object({
  type: z.literal('Vegetation'),
  get children() {
    return NodesSchema;
  },
  modelPath: z.string().optional(),
});
export type Vegetation = z.infer<typeof VegetationSchema>;
type VegetationProps = NodeProps<Vegetation>;

export const RenderVegetation = ({ node, formPath }: VegetationProps) => {
  const { useFormStore } = useStaticFormTsContext();
  const childrenId = formPathJoin<Vegetation>(formPath, 'children');

  const childrenNodes = useMemo((): Node[] => {
    const formStore = useFormStore.getState();
    const vegetations = getVegetationsData();
    const hasNone = vegetations.some((v) => v.name === 'None');
    const vegetationNodes: Node[] = [
      {
        type: 'Select',
        labelText: 'Vegetation profile',
        placeholderText: 'Choose...',
        options: vegetations.map((vegetation) => {
          return {
            value: vegetation.name,
            labelText: vegetation.name,
          };
        }),
        value: hasNone ? 'None' : '',
        modelPath: node.modelPath,
        fieldHelpIntlId: 'veg_profile_desc',
      },
    ];
    formStore.set(childrenId, vegetationNodes);
    return vegetationNodes;
  }, [useFormStore, childrenId, node.modelPath]);

  return (
    <div className={styles.container}>
      <RenderNodes id={childrenId} nodes={childrenNodes} />
    </div>
  );
};
