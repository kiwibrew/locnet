import { z } from 'zod';
import { NodesSchema, type Node, type NodeProps } from '../node';
import { formPathJoin } from '../path';
import { RenderNodes } from '../RenderNodes';
import { useMemo } from 'react';
import { useStaticFormTsContext } from '../FormProvider';
import styles from './Terrain.module.css';
import { getTerrainsData } from './Terrain.utils';

export const TerrainSchema = z.object({
  type: z.literal('Terrain'),
  get children() {
    return NodesSchema;
  },
  modelPath: z.string().optional(),
});
export type Terrain = z.infer<typeof TerrainSchema>;
type TerrainProps = NodeProps<Terrain>;

export const RenderTerrain = ({ node, formPath }: TerrainProps) => {
  const { useFormStore } = useStaticFormTsContext();
  const childrenId = formPathJoin<Terrain>(formPath, 'children');

  const childrenNodes = useMemo((): Node[] => {
    const formStore = useFormStore.getState();
    const terrains = getTerrainsData();
    const hasNone = terrains.some((t) => t.name === 'None');
    const terrainNodes: Node[] = [
      {
        type: 'Select',
        labelText: 'Terrain profile',
        placeholderText: 'Choose...',
        options: terrains.map((terrain) => {
          return {
            value: terrain.name,
            labelText: terrain.name,
          };
        }),
        value: hasNone ? 'None' : '',
        modelPath: node.modelPath,
        fieldHelpIntlId: 'terrain_profile_desc'
      },
    ];
    formStore.set(childrenId, terrainNodes);
    return terrainNodes;
  }, [useFormStore, childrenId, node]);

  return (
    <div className={styles.container}>
      <RenderNodes id={childrenId} nodes={childrenNodes} />
    </div>
  );
};
