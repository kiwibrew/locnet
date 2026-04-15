import { z } from 'zod';
import { NodesSchema, type Node, type NodeProps } from '../node';
import { formPathJoin } from '../path';
import { RenderNodes } from '../RenderNodes';
import { getTechnologies } from './Technologies.utils';
import { useMemo } from 'react';
import { useStaticFormTsContext } from '../FormProvider';
import styles from './Technologies.module.css';

export const TechnologiesSchema = z.object({
  type: z.literal('Technologies'),
  get children() {
    return NodesSchema;
  },
  modelPath: z.string().optional(),
});
export type Technologies = z.infer<typeof TechnologiesSchema>;
type TechnologiesProps = NodeProps<Technologies>;

export const RenderTechnologies = ({ formPath }: TechnologiesProps) => {
  const { useFormStore } = useStaticFormTsContext();
  const childrenId = formPathJoin<Technologies>(formPath, 'children');

  const childrenNodes = useMemo((): Node[] => {
    const formStore = useFormStore.getState();
    const technologies = getTechnologies().sort((a, b) =>
      a.technology.localeCompare(b.technology),
    );
    const technologyNodes = technologies.map((technology): Node => {
      return {
        type: 'ToggleButton',
        value: technology.technology,
        labelIntlId: technology.technology_name,
      };
    });
    formStore.set(childrenId, technologyNodes);
    return technologyNodes;
  }, [useFormStore, childrenId]);

  return (
    <div className={styles.container}>
      <RenderNodes id={childrenId} nodes={childrenNodes} />
    </div>
  );
};
