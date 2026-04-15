import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid } from 'recharts';
import { z } from 'zod';
import { FormNodeSchema } from '../base';
import { type NodeProps } from '../node';
import { useStaticFormTsContext, type FormPath } from '../FormProvider';
import styles from './ExportScatterChart.module.css';

export const ExportScatterChartSchema = FormNodeSchema.extend({
  type: z.literal('ExportScatterChart'),
  dataFormPath: z.string(),
});

export type ExportScatterChart = z.infer<typeof ExportScatterChartSchema>;

type Props = NodeProps<ExportScatterChart>;

export const RenderExportScatterChart = ({ node, formPath }: Props) => {
  const { useWatchFormStore } = useStaticFormTsContext();

  const data = useWatchFormStore(
    node.dataFormPath as FormPath,
    [] as Record<string, unknown>[],
  );

  return (
    <>
      <div key={formPath} className={styles.container} data-sheet>
        <h3 className={styles.labelText} data-sheet-name>{node.labelText}</h3>
        <ScatterChart
          className={styles.chart}
          responsive
          margin={{
            top: 20,
            right: 0,
            bottom: 0,
            left: 0,
          }}
        >
          <CartesianGrid />

          <XAxis
            type="number"
            dataKey="x"
            min={0}
            max={1}
            name="Households penetration rate"
          />
          <YAxis
            type="number"
            dataKey="y"
            name="User change - proportion of income"
          />

          <Scatter
            name={node.labelText}
            data={data}
            fill="#27246c"
            line
          />
        </ScatterChart>
      </div>
    </>
  );
};
