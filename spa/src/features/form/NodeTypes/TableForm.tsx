import { z } from 'zod';
import { type NodeProps, NodesSchema } from '../node';
import { formPathJoin } from '../path';
import { RenderNodes } from '../RenderNodes';
import { useStaticFormTsContext, type ModelPath } from '../FormProvider';
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
} from 'react';
import styles from './TableForm.module.css';
import { Text } from '../Intl';
import { useIntlIdOrText } from '../Intl.utils';

// TABLE

export const TableFormSchema = z.object({
  type: z.literal('TableForm'),
  get columns() {
    return NodesSchema;
  },
  get rows() {
    return NodesSchema;
  },
});
export type TableForm = z.infer<typeof TableFormSchema>;
type TableFormProps = NodeProps<TableForm>;

export const RenderTableForm = ({ node, formPath }: TableFormProps) => {
  const columnsId = formPathJoin<TableForm>(formPath, 'columns');
  const rowsId = formPathJoin<TableForm>(formPath, 'rows');
  return (
    <table>
      <thead>
        <tr>
          <RenderNodes id={columnsId} nodes={node.columns} />
        </tr>
      </thead>
      <tbody>
        <RenderNodes id={rowsId} nodes={node.rows} />
      </tbody>
    </table>
  );
};

/**
 * Columns
 */

export const TableFormColumnTextSchema = z.object({
  type: z.literal('TableFormColumnText'),
  textIntlId: z.string().optional(),
  text: z.string().optional(),
});

type TableFormColumnText = z.infer<typeof TableFormColumnTextSchema>;
type TableFormColumnTextrops = NodeProps<TableFormColumnText>;
export const RenderTableFormColumnText = ({
  node,
}: TableFormColumnTextrops) => {
  return (
    <th className={styles.TableFormColumnText_th}>
      <Text intlId={node.textIntlId} text={node.text} />
    </th>
  );
};

/**
 * Rows
 */

export const TableFormRowHeaderSchema = z.object({
  type: z.literal('TableFormRowHeader'),
  textIntlId: z.string().optional(),
  text: z.string().optional(),
  colSpan: z.number(),
});
export type TableFormRowHeader = z.infer<typeof TableFormRowHeaderSchema>;
type TableFormRowHeaderProps = NodeProps<TableFormRowHeader>;
export const RenderTableFormRowHeader = ({ node }: TableFormRowHeaderProps) => {
  return (
    <tr className={styles.TableFormRowHeader_tr}>
      <td colSpan={node.colSpan} className={styles.TableFormRowHeader_td}>
        <Text intlId={node.textIntlId} text={node.text} />
      </td>
    </tr>
  );
};

export const TableFormRowCellsSchema = z.object({
  type: z.literal('TableFormRowCells'),
  get cells() {
    return NodesSchema;
  },
});
export type TableFormRowCells = z.infer<typeof TableFormRowCellsSchema>;
type TableFormRowCellsProps = NodeProps<TableFormRowCells>;
export const RenderTableFormRowCells = ({
  node,
  formPath,
}: TableFormRowCellsProps) => {
  return (
    <tr className={styles.TableFormRowCells_tr}>
      <RenderNodes
        id={formPathJoin<TableFormRowCells>(formPath, 'cells')}
        nodes={node.cells}
      />
    </tr>
  );
};

/**
 * Cells
 */

export const TableFormCellTextSchema = z.object({
  type: z.literal('TableFormCellText'),
  textIntlId: z.string().optional(),
  text: z.string().optional(),
  textSize: z.union([z.literal('sm'), z.literal('md')]).optional(),
  leftPadding: z.union([z.literal('sm'), z.literal('md')]).optional(),
});
export type TableFormCellText = z.infer<typeof TableFormCellTextSchema>;
export type TableFormCellTextProps = NodeProps<TableFormCellText>;
export const RenderTableFormCellText = ({
  formPath,
  node,
}: TableFormCellTextProps) => {
  return (
    <td
      id={formPath}
      className={[
        node.leftPadding === 'md'
          ? styles.TableFormCellText_td_paddingMedium
          : styles.TableFormCellText_td_paddingSmall,
        node.textSize === 'sm'
          ? styles.TableFormCellText_td_textSizeSmall
          : styles.TableFormCellText_td_textSizeMedium,
      ].join(' ')}
    >
      <Text intlId={node.textIntlId} text={node.text} />
    </td>
  );
};

export const TableFormCellInputTextSchema = z.object({
  type: z.literal('TableFormCellInputText'),
  labelIntlId: z.string(),
  value: z.string().optional(),
});
export type TableFormCellInputText = z.infer<
  typeof TableFormCellInputTextSchema
>;
type TableFormCellInputTextProps = NodeProps<TableFormCellInputText>;
export const RenderTableFormCellInputText = ({
  formPath,
  node,
}: TableFormCellInputTextProps) => {
  const { useWatchFormStore } = useStaticFormTsContext();
  const valueId = formPathJoin<TableFormCellInputText>(formPath, 'value');
  const value = useWatchFormStore(valueId, node.value);

  return (
    <td>
      <input id={formPath} name={formPath} type="text" value={value} />
    </td>
  );
};

export const TableFormCellInputNumberSchema = z.object({
  type: z.literal('TableFormCellInputNumber'),
  labelIntlId: z.string(),
  min: z.number().optional(),
  max: z.number().optional(),
  step: z.number().optional(),
  value: z.number().optional(),
  unit: z.string().optional(),
  'aria-labelledby': z.string().optional(),
  'aria-describedby': z.string().optional(),
  modelPath: z.string(),
  defaultNeedsConfirmation: z.boolean(),
  defaultNeedsConfirmationText: z.string().optional(),
  defaultNeedsConfirmationIntlId: z.string().optional(),
  isReadOnly: z.boolean().optional(),
});
export type TableFormCellInputNumber = z.infer<
  typeof TableFormCellInputNumberSchema
>;
type TableFormCellInputNumberProps = NodeProps<TableFormCellInputNumber>;
export const RenderTableFormCellInputNumber = ({
  node,
  formPath,
}: TableFormCellInputNumberProps) => {
  const { useFormAndModel } = useStaticFormTsContext();
  const [hasValidityError, setHasValidityError] = useState<boolean>(
    Boolean(node.defaultNeedsConfirmation),
  );
  const defaultNeedsConfirmationValidityMessage = useIntlIdOrText(
    node.defaultNeedsConfirmationIntlId,
    node.defaultNeedsConfirmationText,
  );
  const valueId = formPathJoin<TableFormCellInputNumber>(formPath, 'value');
  const [value, setValue] = useFormAndModel(
    valueId,
    node.modelPath as ModelPath,
    node.value,
  );
  const htmlInputElementRef = useRef<HTMLInputElement>(null);
  const defaultNeedsConfirmationHasFocusedOnceRef = useRef<boolean>(false);

  useEffect(() => {
    if (node.isReadOnly && node.defaultNeedsConfirmation) {
      console.error(
        '[TableFormCellInputNumber]',
        valueId,
        " has both isReadOnly and defaultNeedsConfirmation which means users can't confirm value. This is probably a bug.",
      );
    }

    // set DOM Input validity of field on mount
    if (!node.defaultNeedsConfirmation) {
      return;
    }
    const { current: htmlInputElement } = htmlInputElementRef;
    if (htmlInputElement === null) {
      console.error(
        "Element ref not ready yet. This shouldn't happen",
        valueId,
      );
    }
    if (!(htmlInputElement instanceof HTMLInputElement)) {
      console.error('Expected <input> but was ', htmlInputElement);
      return;
    }
    htmlInputElement.setCustomValidity(
      defaultNeedsConfirmationValidityMessage ?? 'Default needs confirmation',
    );
  }, [
    node.isReadOnly,
    node.defaultNeedsConfirmation,
    valueId,
    defaultNeedsConfirmationValidityMessage,
  ]);

  const updateValidity = useCallback(() => {
    const { current: htmlInputElement } = htmlInputElementRef;
    if (!htmlInputElement) return;
    if (!(htmlInputElement instanceof HTMLInputElement)) {
      console.error('Expected <input> but was ', htmlInputElement);
      return;
    }
    const isInvalid = !htmlInputElement.checkValidity();
    setHasValidityError(() => isInvalid);
  }, [htmlInputElementRef, setHasValidityError]);

  const handleChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const { target } = e;
      if (!(target instanceof HTMLInputElement)) {
        throw Error('expected <input>');
      }
      setValue(parseFloat(target.value));
      updateValidity();
    },
    [setValue, updateValidity],
  );

  const moveFocus = useCallback(() => {
    const input = document.getElementById(valueId);
    if (!(input instanceof HTMLInputElement)) {
      throw Error(`Couldn't find #${valueId}`);
    }
    input.focus();
  }, [valueId]);

  useEffect(() => {
    const { current: htmlInputElement } = htmlInputElementRef;
    if (htmlInputElement === null) {
      console.error(
        "Element ref not ready yet. This shouldn't happen",
        valueId,
      );
    }
    if (!(htmlInputElement instanceof HTMLInputElement)) {
      console.error('Expected <input> but was ', htmlInputElement);
      return;
    }

    const isInputValid = htmlInputElement.checkValidity();
    setHasValidityError((prevValue) => {
      if (prevValue === isInputValid) {
        return prevValue;
      }
      return !isInputValid;
    });
  }, [valueId, value, setHasValidityError]);

  const handleConfirmValue = useCallback(() => {
    if (!node.defaultNeedsConfirmation) {
      return;
    }
    if (defaultNeedsConfirmationHasFocusedOnceRef.current === true) {
      return;
    }

    const { current: htmlInputElement } = htmlInputElementRef;
    if (htmlInputElement === null) {
      console.error(
        "Element ref not ready yet. This shouldn't happen",
        valueId,
      );
    }
    if (!(htmlInputElement instanceof HTMLInputElement)) {
      console.error('Expected <input> but was ', htmlInputElement);
      return;
    }
    htmlInputElement.setCustomValidity(
      '', // set as valid because the user has interacted with this field
    );
    defaultNeedsConfirmationHasFocusedOnceRef.current = true;
    updateValidity();
  }, [
    node.defaultNeedsConfirmation,
    updateValidity,
    htmlInputElementRef,
    valueId,
    defaultNeedsConfirmationHasFocusedOnceRef,
  ]);

  useEffect(() => {
    updateValidity();
  }, [valueId, value, updateValidity]);

  return (
    <td className={styles.TableFormCellInputNumber_td} onClick={moveFocus}>
      <div
        className={[
          styles.TableFormCellInputNumber_inputContainer,
          hasValidityError
            ? styles.TableFormCellInputNumber_inputContainer_error
            : '',
          node.isReadOnly
            ? styles.TableFormCellInputNumber_inputContainer_readOnly
            : '',
        ].join(' ')}
      >
        <input
          ref={htmlInputElementRef}
          type="number"
          id={valueId}
          name={valueId}
          min={
            // if readOnly the user can't fix min error so don't cause one
            node.isReadOnly ? undefined : node.min
          }
          max={
            // if readOnly the user can't fix max error so don't cause one
            node.isReadOnly ? undefined : node.max
          }
          step={
            // if readOnly the user can't fix step error so don't cause one
            node.isReadOnly ? undefined : node.step
          }
          value={value}
          onInput={handleConfirmValue}
          onKeyDown={handleConfirmValue}
          onChange={handleChange}
          className={styles.TableFormCellInputNumber_inputNumber}
          aria-describedby={node['aria-describedby']}
          aria-labelledby={node['aria-labelledby']}
          readOnly={node.isReadOnly}
        />
        {node.unit && (
          <span className={styles.TableFormCellInputNumber_inputNumberUnit}>
            {node.unit}
          </span>
        )}
      </div>
    </td>
  );
};
