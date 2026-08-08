import { useCallback, useRef, useState, type ChangeEvent } from 'react';
import { useStaticFormTsContext } from '../form/FormProvider';
import { useIntlIdOrText } from '../form/Intl.utils';
import styles from './DeveloperMenu.module.css';
import { builderInputSchema } from './api-generated-zod';
import { getExampleFilenames, getExampleLabel } from './examples';
import type { EditableLocNetForm } from './formData';
import { useLoadBuilderInput } from './helper';
import type { LocNetModel } from './model';
import { locnetModelToBuilderInput } from './submit';

export const DeveloperMenu = () => {
  const { useWatchFormStore, useWatchModelStore } = useStaticFormTsContext();
  const modelData = useWatchModelStore('root', {} as LocNetModel);
  const modelerAPIOutput = useWatchFormStore(
    'api.modelerAPIOutput',
    undefined as EditableLocNetForm['api']['modelerAPIOutput'],
  );

  const loadBuilderInput = useLoadBuilderInput();
  const detailsRef = useRef<HTMLDetailsElement>(null);
  const [isLoadingExample, setIsLoadingExample] = useState(false);
  const loadExampleText =
    useIntlIdOrText('load_example', undefined) ?? 'Load Example Data';
  const exampleFilenames = getExampleFilenames();

  const loadExample = useCallback(
    async (event: ChangeEvent<HTMLSelectElement>) => {
      const filename = event.currentTarget.value;
      event.currentTarget.value = '';
      if (!filename || isLoadingExample) {
        return;
      }

      setIsLoadingExample(true);
      try {
        const response = await fetch(
          `/documentation-assets/examples/${encodeURIComponent(filename)}`,
        );
        if (!response.ok) {
          throw Error(`The server returned HTTP ${response.status}.`);
        }
        const builderInput = builderInputSchema.parse(await response.json());
        await loadBuilderInput(builderInput);
        if (detailsRef.current) {
          detailsRef.current.open = false;
        }
      } catch (error) {
        console.error('Unable to load example data', error);
        const message =
          error instanceof Error
            ? error.message
            : 'An unexpected error occurred.';
        alert(`Could not load example: ${message}`);
      } finally {
        setIsLoadingExample(false);
      }
    },
    [isLoadingExample, loadBuilderInput],
  );

  return (
    <div className={styles.debug}>
      <details
        ref={detailsRef}
        className={styles.details}
        data-testid="developer_options"
      >
        <summary className={styles.summary}>Developer options</summary>
        <div className={styles.debugBody}>
          <select
            className={styles.exampleSelect}
            defaultValue=""
            onChange={loadExample}
            disabled={isLoadingExample}
            aria-label={loadExampleText}
            data-testid="load_example"
          >
            <option value="">{loadExampleText}</option>
            {exampleFilenames.map((filename) => (
              <option key={filename} value={filename}>
                {getExampleLabel(filename)}
              </option>
            ))}
          </select>
          <hr />
          <h3>Model input</h3>
          <pre data-testid="model_input">
            {JSON.stringify(locnetModelToBuilderInput(modelData), null, 2)}
          </pre>
          {modelerAPIOutput && (
            <>
              <hr />
              <h3>Model output</h3>
              <pre data-testid="model_output">
                {JSON.stringify(modelerAPIOutput, null, 2)}
              </pre>
            </>
          )}
        </div>
      </details>
    </div>
  );
};
