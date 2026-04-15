import { z } from 'zod';
import { formPathJoin } from '../path';
import { FormNodeSchema } from '../base';
import { type NodeProps } from '../node';
import styles from './RadioToggleButtons.module.css';
import { useStaticFormTsContext, type ModelPath } from '../FormProvider';
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
} from 'react';
import { Text } from '../Intl';

export const OptionSchema = z.object({
  value: z.string(),
  intlId: z.string().optional(),
  text: z.string().optional(),
});

export type Option = z.infer<typeof OptionSchema>;

export const RadioToggleButtonsSchema = FormNodeSchema.extend({
  type: z.literal('RadioToggleButtons'),
  name: z.string(),
  value: z.string().optional(),
  options: OptionSchema.array(),
  isRequired: z.boolean().optional(),
  modelPath: z.string().optional(),
});

export type RadioToggleButtons = z.infer<typeof RadioToggleButtonsSchema>;

type Props = NodeProps<RadioToggleButtons>;

const useHandleChange = (setValue: (value: string) => void) => {
  return useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const { target } = e;
      if (!(target instanceof HTMLInputElement)) {
        throw Error('expected <input>');
      }
      if (target.type !== 'radio') {
        throw Error('Expected radio');
      }
      setValue(target.value);
    },
    [setValue],
  );
};

export const RenderRadioToggleButtons = ({ node, formPath }: Props) => {
  const { useFormAndModel } = useStaticFormTsContext();

  const valueId = formPathJoin<RadioToggleButtons>(formPath, 'value');
  const [value, setValue] = useFormAndModel(valueId, node.modelPath as ModelPath, node.value);
  const optionsId = formPathJoin<RadioToggleButtons>(formPath, 'options');
  const handleChange = useHandleChange(setValue);

  return (
    <div className={styles.container}>
      {node.options.map((option, index, arr) => {
        const optionId = `${optionsId}.${index}`;
        return (
          <RenderToggleButton
            option={option}
            name={node.name}
            id={optionId}
            isFirst={index === 0}
            isLast={index === arr.length - 1}
            value={value}
            isRequired={node.isRequired}
            handleChange={handleChange}
          />
        );
      })}
    </div>
  );
};

type RenderToggleButtonProps = {
  option: Option;
  id: string;
  name: string;
  value?: string | undefined;
  isFirst: boolean;
  isLast: boolean;
  isRequired?: boolean;
  handleChange: ReturnType<typeof useHandleChange>;
};

const RenderToggleButton = ({
  id,
  option,
  name,
  value,
  isFirst,
  isLast,
  isRequired,
  handleChange,
}: RenderToggleButtonProps) => {
  const [hasValidityError, setHasValidityError] = useState<boolean>(false);
  const htmlInputElementRef = useRef<HTMLInputElement>(null);

  const handleChangeWrapper = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const { target } = e;
      if (!(target instanceof HTMLInputElement)) {
        throw Error('expected <input>');
      }
      handleChange(e);
      const isValid = target.checkValidity();
      setHasValidityError(!isValid);
    },
    [handleChange, setHasValidityError],
  );

  useEffect(() => {
    const { current: htmlInputElement } = htmlInputElementRef;
    if (htmlInputElement === null) {
      console.error("Element ref not ready yet. This shouldn't happen", id);
    }
    if (!(htmlInputElement instanceof HTMLInputElement)) {
      console.error('Expected <input> but was ', htmlInputElement);
      return;
    }
    const isInputValid = htmlInputElement.checkValidity();
    setHasValidityError(!isInputValid);
  }, [id, value, setHasValidityError]);

  return (
    <label
      className={[
        styles.label,
        isFirst && styles.label_isFirst,
        isLast && styles.label_isLast,
        option.value === value
          ? styles.label_selected
          : styles.label_unselected,
        hasValidityError ? styles.label_error : '',
      ].join(' ')}
    >
      <input
        ref={htmlInputElementRef}
        id={id}
        name={name}
        type="radio"
        value={option.value}        
        checked={option.value === value}
        onChange={handleChangeWrapper}
        className={styles.radio}
        required={isRequired}
      />
      <Text intlId={option.intlId} text={option.text} />
    </label>
  );
};
