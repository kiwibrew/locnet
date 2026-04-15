import { z } from 'zod';
import { sha512 } from '@noble/hashes/sha2.js';
import { bytesToHex } from '@noble/hashes/utils.js';
import { type Node, type NodeProps, NodesSchema } from '../node';
import { formPathJoin } from '../path';
import { RenderNodes } from '../RenderNodes';
import { useMemo } from 'react';
import { useStaticFormTsContext } from '../FormProvider';
import styles from './CategoryTableForm.module.css';
import type { DefaultsDetail } from '../../locnet/api-generated-client';
import { ScrollHorizontally } from '../../ScrollWrapper/ScrollHorizontally';

export const CategoryTableFormSchema = z.object({
  type: z.literal('CategoryTableForm'),
  get columns() {
    return NodesSchema;
  },
  categories: z.string().array(),
  rows: z
    .object({
      labelIntlId: z.string(),
      value: z.string(),
      units: z.string(),
      explanation: z.string(),
    })
    .array()
    .optional(),
  labelToModelPathOverride: z.record(z.string(), z.string()),
});
export type CategoryTableForm = z.infer<typeof CategoryTableFormSchema>;
type CategoryTableFormProps = NodeProps<CategoryTableForm>;

export const RenderCategoryTableForm = ({
  node,
  formPath,
}: CategoryTableFormProps) => {
  const { useFormStore, useWatchFormStore } = useStaticFormTsContext();
  const columnsId = formPathJoin<CategoryTableForm>(formPath, 'columns');
  const rowsId = formPathJoin<CategoryTableForm>(formPath, 'rows');
  const apiCharacteristics = useWatchFormStore(
    'api.characteristics',
    [] as DefaultsDetail[],
  );
  const rows = useMemo((): Node[] => {
    if (!apiCharacteristics) return [];
    const formState = useFormStore.getState();
    formState.set(rowsId, []);
    const selectedCategories = apiCharacteristics
      .filter((item) => node.categories.includes(item.category))
      .sort((a, b) => a.category.localeCompare(b.category));
    const newNodes = selectedCategories.flatMap(
      (selectedCategory, index, arr): Node | Node[] => {
        const isANewCategory =
          index === 0 || selectedCategory.category !== arr[index - 1].category;

        const cell0Id = [formPath, 'rows', index + 1, 'cells', '0'].join('.');
        const cell2Id = [formPath, 'rows', index + 1, 'cells', '2'].join('.');

        // https://trello.com/c/eiyqWXZ1/168-household-calculatorjs
        const isReadOnly = [
          'users_per_household',
          'total_potential_users',
          'paf_usd_hour',
        ].includes(selectedCategory.variable);

        const defaultNeedsConfirmation =
          !isReadOnly && Boolean(selectedCategory.noDefault);

        const cellsNode: Node = {
          type: 'TableFormRowCells',
          cells: [
            {
              type: 'TableFormCellText',
              textIntlId: selectedCategory.variable,
              leftPadding: 'md',
            },
            {
              type: 'TableFormCellInputNumber',
              labelIntlId: selectedCategory.variable,
              min: selectedCategory.min,
              max: selectedCategory.max,
              step: selectedCategory.step,
              value: selectedCategory.value,
              unit: selectedCategory.unit,
              'aria-labelledby': cell0Id,
              'aria-describedby': cell2Id,
              modelPath:
                node.labelToModelPathOverride[selectedCategory.variable] ??
                selectedCategory.variable,
              defaultNeedsConfirmation,
              defaultNeedsConfirmationText:
                'No default value for your country available. Please confirm the value.',
              isReadOnly,
            },
            {
              type: 'TableFormCellText',
              textSize: 'sm',
              textIntlId: `${selectedCategory.variable}_desc`,
            },
          ],
        };

        if (isANewCategory) {
          return [
            {
              type: 'TableFormRowHeader',
              textIntlId: selectedCategory.category,
              colSpan: 3,
            },
            cellsNode,
          ];
        }

        return cellsNode;
      },
    );
    formState.set(rowsId, newNodes);
    return newNodes;
  }, [
    apiCharacteristics,
    useFormStore,
    rowsId,
    formPath,
    node.categories,
    node.labelToModelPathOverride,
  ]);

  // generate a unique React key to force React to unmount/remount children nodes when the apiCharacteristics changes
  const apiCharacteristicsKey = useMemo(() => {
    const data = Uint8Array.from(JSON.stringify(apiCharacteristics));
    const digest = sha512.create().update(data).digest();
    return bytesToHex(digest);
  }, [apiCharacteristics]);

  if (!apiCharacteristics) {
    return 'Loading...';
  }

  return (
    <ScrollHorizontally>
      <table key={formPath} className={styles.CategoryTableForm_table}>
        <thead>
          <tr>
            <RenderNodes id={columnsId} nodes={node.columns} />
          </tr>
        </thead>
        <tbody>
          <RenderNodes
            key={
              // see apiCharacteristicsKey docstring
              apiCharacteristicsKey
            }
            id={rowsId}
            nodes={rows}
          />
        </tbody>
      </table>
    </ScrollHorizontally>
  );
};
