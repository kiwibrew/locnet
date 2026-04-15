import { useMemo } from 'react';
import DOMPurify from 'dompurify';
import { z } from 'zod';
import { FormNodeSchema } from '../base';
import { type NodeProps } from '../node';
import { useIntlIdOrText } from '../Intl.utils';
import styles from './Html.module.css';

export const HTMLSchema = FormNodeSchema.extend({
  type: z.literal('HTML'),
  intlId: z.string().optional(),
  html: z.string().optional(),
});

export type HTML = z.infer<typeof HTMLSchema>;

type Props = NodeProps<HTML>;

export const RenderHTML = ({ node }: Props) => {
  const html = useIntlIdOrText(node.intlId, node.html);

  const sanitisedHtml = useMemo(() => {
    if (html === undefined) return undefined;
    return { __html: DOMPurify.sanitize(html) };
  }, [html]);

  return (
    <div dangerouslySetInnerHTML={sanitisedHtml} className={styles.container} />
  );
};
