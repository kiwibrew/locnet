import { z } from 'zod';
import { NodeSchema } from '../base';
import { NodesSchema, type NodeProps } from '../node';
import { RenderNodes } from '../RenderNodes';
import { formPathJoin } from '../path';
import { useStaticFormTsContext } from '../FormProvider';

export const InertSchema = NodeSchema.extend({
  type: z.literal('Inert'),
  isInert: z.boolean().optional(),
  get children() {
    return NodesSchema;
  },
});

export type Inert = z.infer<typeof InertSchema>;

type Props = NodeProps<Inert>;

export const RenderInert = ({ node, formPath }: Props) => {
  const { useFormAndModel } = useStaticFormTsContext();
  const isInertId = formPathJoin<Inert>(formPath, 'isInert');
  const childrenId = formPathJoin<Inert>(formPath, 'children');
  const [isInert] = useFormAndModel(isInertId, undefined, node.isInert, true);
  const isInertBool = Boolean(isInert);

  return (
    <>
      <div
        style={{
          position: 'relative',
          display: 'block',
          overflow: isInertBool ? 'hidden' : 'visible',
          height: isInertBool ? '0px' : 'auto',
        }}
      >
        {!isInert && <RenderNodes id={childrenId} nodes={node.children} />}
      </div>
    </>
  );
};
