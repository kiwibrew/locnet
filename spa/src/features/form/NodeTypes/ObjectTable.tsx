import { z } from 'zod';
import { startCase } from 'lodash-es';
import { type NodeProps } from '../node';
import { formPathJoin } from '../path';
import { useMemo } from 'react';
import { useStaticFormTsContext } from '../FormProvider';
import styles from './ObjectTable.module.css';

export const ObjectTableSchema = z.object({
  type: z.literal('ObjectTable'),
  data: z.record(z.string(), z.unknown()),
});

export type ObjectTable = z.infer<typeof ObjectTableSchema>;
type TechnologiesProps = NodeProps<ObjectTable>;

export const RenderObjectTable = ({ node, formPath }: TechnologiesProps) => {
  const { useWatchFormStore } = useStaticFormTsContext();
  const dataPath = formPathJoin<ObjectTable>(formPath, 'data');
  const data = useWatchFormStore(dataPath, node.data);

  const entries = useMemo(() => Object.entries(data), [data]);

  return (
    <div className={styles.tableContainer}>
      <table className={styles.table}>
        <tbody>
          {entries.map(([key, value]) => {
            return (
              <tr>
                <th className={styles.th}>
                  {startCase(key.replace(/_/g, ' '))}
                </th>
                <td className={styles.td}>{String(value)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
