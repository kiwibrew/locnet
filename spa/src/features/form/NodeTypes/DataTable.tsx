import { Fragment, useMemo, useState } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
  getSortedRowModel,
  type Row,
  type SortDirection,
} from '@tanstack/react-table';
import { z } from 'zod';
import { FormNodeSchema } from '../base';
import { type NodeProps, type Nodes } from '../node';
import { useStaticFormTsContext, type FormPath } from '../FormProvider';
import {
  TiArrowUnsorted,
  TiArrowSortedDown,
  TiArrowSortedUp,
  TiChevronRight,
} from 'react-icons/ti'; // https://www.s-ings.com/typicons/
import styles from './DataTable.module.css';
import { formPathJoin } from '../path';
import { RenderNodes } from '../RenderNodes';
import { ScrollHorizontally } from '../../ScrollWrapper/ScrollHorizontally';
import { replaceNonNumberChars } from '../../../utils/strings';

export const DataTableSchema = FormNodeSchema.extend({
  type: z.literal('DataTable'),
  rows: z.record(z.string(), z.unknown()).array().optional(),
  columns: z
    .object({ title: z.string(), data: z.unknown() })
    .array()
    .optional(),
  isSortable: z.boolean(),
  hasChildren: z.boolean().optional(),
  numberRounding: z.number().optional(),
});

export type DataTable = z.infer<typeof DataTableSchema>;

type Props = NodeProps<DataTable>;

const emptyArray: unknown[] = [];

const NUMBER_THRESHOLD_RATIO = 0.7; // ratio of numbers to other chars in the string affects number detection. E.g. we don't want to count string "Backhaul required (year 10)" as a number, nor "Year 1 Traffic" because these are just string values

const isNumberishValue = (input: unknown): input is string => {
  if (typeof input === 'number') {
    return true;
  }
  if (typeof input !== 'string') {
    return false;
  }
  const inputAlphaNumeric = input.replace(/[^a-z0-9.-]/gi, '');
  const inputNumberString = replaceNonNumberChars(inputAlphaNumeric);
  // we compare against inputAlphaNumeric so that input '$1' is treated as numbers
  const numberRatio = inputNumberString.length / inputAlphaNumeric.length;
  const inputNumber = parseFloat(inputNumberString);
  return !Number.isNaN(inputNumber) && numberRatio > NUMBER_THRESHOLD_RATIO;
};

const sortNumberishValue = (
  rowA: Row<unknown>,
  rowB: Row<unknown>,
  columnId: string,
): number => {
  const aValue =
    rowA.original &&
    typeof rowA.original === 'object' &&
    columnId in rowA.original
      ? // @ts-expect-error todo improve ts
        rowA.original[columnId]
      : undefined;
  const bValue =
    rowB.original &&
    typeof rowB.original === 'object' &&
    columnId in rowB.original
      ? // @ts-expect-error todo improve ts
        rowB.original[columnId]
      : undefined;

  if (typeof aValue === 'number' && typeof bValue === 'number') {
    return aValue - bValue;
  }
  if (typeof aValue === 'string' && typeof bValue === 'string') {
    const aNumberString = replaceNonNumberChars(aValue);
    const bNumberString = replaceNonNumberChars(bValue);

    // console.log({ aNumberString, bNumberString });
    if (aNumberString.length > 0 || bNumberString.length > 0) {
      const aNumber = parseFloat(aNumberString);
      const bNumber = parseFloat(bNumberString);
      return aNumber - bNumber;
    }

    return aValue.localeCompare(bValue);
  }
  return 0;
};

const isRowTypeSection = (row: unknown): boolean => {
  return Boolean(
    row &&
    typeof row === 'object' &&
    'row_type' in row &&
    row.row_type === 'section',
  );
};

type TanstackColumns = Parameters<typeof useReactTable>[0]['columns'];
type TanstackColumnsColumn = TanstackColumns[number];

export const RenderDataTable = ({ node, formPath }: Props) => {
  const { useWatchFormStore } = useStaticFormTsContext();

  const [sorting, setSorting] = useState<SortingState>([]);

  const rowsPath = formPathJoin<DataTable>(formPath, 'rows');
  const rows = useWatchFormStore(rowsPath, node.rows);

  const columnsPath = formPathJoin<DataTable>(formPath, 'columns');
  const columns = useWatchFormStore(columnsPath, node.columns);

  const rowsForTanstackTable = useMemo(() => {
    // console.log('Rememozing rows for ', node.rowsFormPath);
    if (!rows || rows.length === 0) return emptyArray;
    return rows;
  }, [rows]);

  const columnsForTanstackTable = useMemo(() => {
    if (!columns) return emptyArray as TanstackColumnsColumn[];
    const columnHelper = createColumnHelper<Record<string, number | string>>();
    // console.log('Rememozing columns for ', node.rowsFormPath);
    const columnDefs = columns.map((column): TanstackColumnsColumn => {
      const { data, title } = column;
      if (typeof data !== 'string' || typeof title !== 'string') {
        console.error('Expected string values for column', column);
        throw Error(`Column wasn't stringy. See console.`);
      }

      const rowValues = rows?.map((row) => row[data]) ?? [];
      const columnHasNumbers = rowValues.some(isNumberishValue);

      const columnDef = columnHelper.accessor(data, {
        header: () => title,
        cell: (props) => {
          const value = props.getValue();
          if (typeof value === 'number' || isNumberishValue(value)) {
            const numberValue =
              typeof value === 'number'
                ? value
                : parseFloat(replaceNonNumberChars(String(value)));

            const formattedNumber = new Intl.NumberFormat('en-US', {
              // Format with thousands separator
              minimumFractionDigits: node.numberRounding ?? 2,
              maximumFractionDigits: node.numberRounding ?? 2,
            }).format(numberValue);
            return (
              <div className={styles.cellNumber} data-number={formattedNumber}>
                {formattedNumber}
              </div>
            );
          }

          if (
            props.row.original &&
            typeof props.row.original === 'object' &&
            'row_type' in props.row.original
          ) {
            if (props.row.original.row_type === 'section') {
              return <span className={styles.cellSection}>{value}</span>;
            }
          }
          return value;
        },
        enableSorting: columnHasNumbers,
        sortingFn: columnHasNumbers ? sortNumberishValue : 'alphanumeric',
      }) as TanstackColumnsColumn;

      return columnDef;
    });

    if (node.hasChildren) {
      columnDefs.unshift({
        id: 'expander',
        header: () => null,
        cell: ({ row }) => {
          const canExpand = row.getCanExpand();
          if (!canExpand) {
            return null;
          }
          const isExpanded = row.getIsExpanded();
          return canExpand ? (
            <button
              type="button"
              onClick={row.getToggleExpandedHandler()}
              className={styles.expandButton}
              aria-expanded={isExpanded}
            >
              <TiChevronRight
                className={[
                  styles.expandButtonIcon,
                  isExpanded ? styles.expandButtonIsExpandedIcon : '',
                ].join(' ')}
              />
            </button>
          ) : (
            ''
          );
        },
      });
    }

    return columnDefs;
  }, [columns, rows, node.hasChildren, node.numberRounding]);

  const table = useReactTable({
    data: rowsForTanstackTable,
    columns: columnsForTanstackTable,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    state: { sorting },
    getSubRows: (originalRow) =>
      originalRow &&
      typeof originalRow === 'object' &&
      'children' in originalRow
        ? (originalRow.children as Nodes)
        : undefined,
  });

  return (
    <ScrollHorizontally>
      <div className={styles.tableContainer} key={formPath}>
        <table className={styles.table}>
          <thead className={styles.thead}>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header, _index, arr) => {
                  const isSortable =
                    node.isSortable && header.column.getCanSort();
                  const sortDirection = header.column.getIsSorted();

                  return (
                    <th
                      key={header.id}
                      className={[
                        styles.th,
                        isSortable ? styles.sortableTh : '',
                        getColumnWidthClass(arr.length),
                      ].join(' ')}
                    >
                      {flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}

                      {isSortable ? (
                        <button
                          type="button"
                          className={[
                            styles.sortButton,
                            sortDirection === false
                              ? styles.sortButtonNotSorted
                              : '',
                          ].join(' ')}
                          onClick={() =>
                            setSorting((prevSort) => {
                              const prevSortDirection: false | SortDirection =
                                prevSort.length === 0
                                  ? false
                                  : prevSort[0].desc
                                    ? 'desc'
                                    : 'asc';

                              switch (prevSortDirection) {
                                case false:
                                  return [
                                    {
                                      desc: false,
                                      id: header.id,
                                    },
                                  ];
                                case 'asc':
                                  return [
                                    {
                                      desc: true,
                                      id: header.id,
                                    },
                                  ];
                                case 'desc':
                                  return [];
                              }
                            })
                          }
                        >
                          {sortDirection === false ? (
                            <TiArrowUnsorted className={styles.sortIcon} />
                          ) : sortDirection === 'asc' ? (
                            <TiArrowSortedUp className={styles.sortIcon} />
                          ) : (
                            <TiArrowSortedDown className={styles.sortIcon} />
                          )}
                        </button>
                      ) : null}
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => {
              const { original } = row;
              const childrenFormPath =
                `${formPath}.rows.${row.index}` as FormPath;
              return (
                <Fragment>
                  <tr key={row.id}>
                    {row
                      .getVisibleCells()
                      .filter((cell, index) => {
                        return isRowTypeSection(cell.row.original) === false
                          ? true
                          : index === 0;
                      })
                      .map((cell, _index, arr) => {
                        const colSpan = isRowTypeSection(cell.row.original)
                          ? 999
                          : undefined;
                        return (
                          <td
                            key={cell.id}
                            className={[
                              styles.td,
                              '|',
                              getColumnWidthClass(arr.length),
                              '|',
                            ].join(' ')}
                            colSpan={colSpan}
                          >
                            {flexRender(
                              cell.column.columnDef.cell,
                              cell.getContext(),
                            )}
                          </td>
                        );
                      })}
                  </tr>
                  {row.getIsExpanded() &&
                  original &&
                  typeof original === 'object' &&
                  'children' in original ? (
                    <tr>
                      <td colSpan={row.getVisibleCells().length}>
                        <RenderNodes
                          id={childrenFormPath}
                          nodes={original.children as Nodes}
                        />
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </ScrollHorizontally>
  );
};

const getColumnWidthClass = (l: number) => {
  switch (l) {
    case 0:
    case 1:
      return styles.column1_1;
    case 2:
      return styles.column1_2;
    case 3:
      return styles.column1_3;
    case 4:
      return styles.column1_4;
    case 5:
      return styles.column1_5;
    case 6:
      return styles.column1_6;
    case 7:
      return styles.column1_7;
    case 8:
      return styles.column1_8;
    case 9:
      return styles.column1_9;
    case 10:
      return styles.column1_10;
    case 11:
      return styles.column1_11;
    case 12:
      return styles.column1_12;
    case 13:
      return styles.column1_13;
    case 14:
      return styles.column1_14;
    case 15:
      return styles.column1_15;
    case 16:
      return styles.column1_16;
    case 17:
      return styles.column1_17ish;
    default:
  }
};
