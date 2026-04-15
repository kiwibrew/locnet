import { z } from 'zod';
import { FormNodeSchema } from '../base';
import { type NodeProps } from '../node';
import { useIntlIdOrText } from '../Intl.utils';

export const TextSchema = FormNodeSchema.extend({
  type: z.literal('Text'),
  intlId: z.string().optional(),
  text: z.string().optional(),
});

export type Text = z.infer<typeof TextSchema>;

type Props = NodeProps<Text>;

export const RenderText = ({ node }: Props) => {
  const text = useIntlIdOrText(node.intlId, node.text);

  return <>{text}</>;
};
