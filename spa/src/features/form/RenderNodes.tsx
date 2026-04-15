import { RenderNode } from '../form/RenderNode';
import { type Nodes } from './node';

type Props = {
  nodes?: Nodes;
  id: string;
};

export const RenderNodes = ({ nodes, id }: Props) => {
  if (!nodes) {
    return null;
  }

  return (
    <>
      {nodes.map((node, index) => {
        const newId = `${id}.${index}`;
        return <RenderNode node={node} key={newId} formPath={newId} />;
      })}
    </>
  );
};
