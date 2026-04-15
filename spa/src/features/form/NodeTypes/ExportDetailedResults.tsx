import { useMemo } from 'react';
import { z } from 'zod';
import { FormNodeSchema } from '../base';
import { type Node, type NodeProps, type Nodes } from '../node';
import { useStaticFormTsContext, type FormPath } from '../FormProvider';
import styles from './ExportDetailedResults.module.css';
import { RenderNodes } from '../RenderNodes';
import { formPathJoin } from '../path';
import type { ExportTable } from './ExportTable';
import type { DataTable } from './DataTable';

export const ExportDetailedResultsSchema = FormNodeSchema.extend({
  type: z.literal('ExportDetailedResults'),
  datasetFormPath: z.string(),
  isSortable: z.boolean(),
});

export type ExportDetailedResults = z.infer<typeof ExportDetailedResultsSchema>;

type Props = NodeProps<ExportDetailedResults>;

const emptyArray: unknown[] = [];

export const RenderExportDetailedResults = ({ node, formPath }: Props) => {
  const { useWatchFormStore, useFormStore } = useStaticFormTsContext();

  const childrenFormPath = formPathJoin<ExportTable>(formPath, 'children');

  const dataset = useWatchFormStore(
    node.datasetFormPath as FormPath,
    emptyArray as Record<string, unknown>[] | undefined,
  );

  const rows = useMemo((): DataTable['rows'] => {
    // console.log('Rememozing rows for ', node.rowsFormPath);
    if (!dataset || dataset.length === 0) {
      return emptyArray as DataTable['rows'];
    }
    return dataset.map((row) => {
      const children: Nodes = [
        {
          type: 'ObjectTable',
          data: row,
        },
      ];
      return { ...row, children };
    });
  }, [dataset]);

  const columns = useMemo((): DataTable['columns'] => {
    // console.log('Rememozing rows for ', node.rowsFormPath);
    if (!dataset || dataset.length === 0) {
      return emptyArray as DataTable['columns'];
    }

    return [
      {
        title: 'Location',
        data: 'location_name',
      },
      {
        title: 'Network Type',
        data: 'network_type',
      },
      {
        title: 'Contention Ratio',
        data: 'network_type',
      },
      {
        title: 'Users supported',
        data: 'users_supported',
      },
      {
        title: 'Cost per Passing',
        data: 'cost_per_passing',
      },
    ];
  }, [dataset]);

  const childrenNodes = useMemo((): Node[] => {
    const valueStore = useFormStore.getState();
    const childNodes: Node[] = [
      {
        type: 'DataTable',
        columns:
          columns?.map((column) => {
            if (
              !column ||
              typeof column !== 'object' ||
              !('title' in column) ||
              !('data' in column)
            ) {
              console.error({ column });
              throw Error(
                'Expected column to have title and data. See console',
              );
            }
            const { title, data } = column;
            if (typeof title !== 'string') {
              console.error(column);
              throw Error('Expected title string. See console.');
            }
            return {
              title,
              data,
            };
          }),
        rows: rows?.map((row) => {
          if (!row || typeof row !== 'object') {
            console.error({ row });
            throw Error('Expected row to be an object. See console');
          }
          return row as Record<string, unknown>;
        }),
        isSortable: node.isSortable,
        hasChildren: true,
      },
    ];

    valueStore.set(childrenFormPath, childNodes);
    return childNodes;
  }, [useFormStore, childrenFormPath, node, rows, columns]);

  return (
    <div className={styles.container}>
      <h3 className={styles.labelText}>{node.labelText}</h3>
      <RenderNodes id={childrenFormPath} nodes={childrenNodes} />
    </div>
  );
};
