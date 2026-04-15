import { useMemo } from 'react';
import { z } from 'zod';
import { FormNodeSchema } from '../base';
import { NodesSchema, type Node, type NodeProps } from '../node';
import { useStaticFormTsContext, type FormPath } from '../FormProvider';
import styles from './ExportTable.module.css'

import { RenderNodes } from '../RenderNodes';
import { formPathJoin } from '../path';

export const ExportTableSchema = FormNodeSchema.extend({
  type: z.literal('ExportTable'),
  rowsFormPath: z.string(),
  columnsFormPath: z.string(),
  isSortable: z.boolean(),
  numberRounding: z.number().optional(),
  get children() {
    return NodesSchema;
  },
});

export type ExportTable = z.infer<typeof ExportTableSchema>;

type Props = NodeProps<ExportTable>;

const emptyArray: unknown[] = [];

export const RenderExportTable = ({ node, formPath }: Props) => {
  const { useWatchFormStore, useFormStore } = useStaticFormTsContext();

  const childrenFormPath = formPathJoin<ExportTable>(formPath, 'children');
  const rows = useWatchFormStore(
    node.rowsFormPath as FormPath,
    emptyArray as Record<string, unknown>[] | undefined,
  );
  const columns = useWatchFormStore(
    node.columnsFormPath as FormPath,
    emptyArray as Record<string, unknown>[] | undefined,
  );

  const childrenNodes = useMemo((): Node[] => {
    const valueStore = useFormStore.getState();
    const childNodes: Node[] = [
      {
        type: 'DataTable',
        columns:
          columns?.map((column) => {
            const { title, data } = column;
            if (typeof title !== 'string') {
              console.error(column);
              throw Error('Expected title string. See console.');
            }
            return {
              title,
              data,
            };
          }) ?? [],
        rows,
        isSortable: node.isSortable,
        numberRounding: node.numberRounding
      },
    ];

    valueStore.set(childrenFormPath, childNodes);
    return childNodes;
  }, [useFormStore, childrenFormPath, node, rows, columns]);

  return (
    <div className={styles.container} data-sheet>
      <h3 className={styles.labelText} data-sheet-name>{node.labelText}</h3>
      <RenderNodes id={childrenFormPath} nodes={childrenNodes} />
    </div>
  );
};
