import { z } from 'zod';
import { NodesSchema, type Node, type NodeProps } from '../node';
import { formPathJoin } from '../path';
import { RenderNodes } from '../RenderNodes';
import { useMemo } from 'react';
import { useStaticFormTsContext } from '../FormProvider';
import styles from './Terrain.module.css';
import { getOrganisationTypesData } from './OrganisationType.utils';

export const OrganisationTypeSchema = z.object({
  type: z.literal('OrganisationType'),
  value: z.string().optional(),
  get children() {
    return NodesSchema;
  },
  modelPath: z.string().optional(),
});
export type OrganisationType = z.infer<typeof OrganisationTypeSchema>;
type OrganisationTypeProps = NodeProps<OrganisationType>;

export const RenderOrganisationType = ({ node, formPath }: OrganisationTypeProps) => {
  const { useFormStore } = useStaticFormTsContext();
  const childrenId = formPathJoin<OrganisationType>(formPath, 'children');

  const childrenNodes = useMemo((): Node[] => {
    const formStore = useFormStore.getState();
    const organisationTypesData = getOrganisationTypesData();
    const organisationNodes: Node[] = [
      {
        type: 'RadioToggleButtons',
        labelText: 'Organisation type',
        name: organisationTypesData.name,
        options: organisationTypesData.options,
        value: organisationTypesData.defaultValue,
        modelPath: node.modelPath,
        isRequired: true,
      },
      {
        type: 'FieldHelp',
        textIntlId: 'provider_type_desc',
      },
    ];
    formStore.set(childrenId, organisationNodes);
    return organisationNodes;
  }, [useFormStore, childrenId, node.modelPath]);

  return (
    <div className={styles.container}>
      <RenderNodes id={childrenId} nodes={childrenNodes} />
    </div>
  );
};
