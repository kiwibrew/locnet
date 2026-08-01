import {
  useCallback,
  useRef,
  useState,
  type ChangeEvent,
  type MouseEvent,
} from 'react';
import { useStaticFormTsContext } from '../form/FormProvider';
import { builderInputSchema } from './api-generated-zod';
import { validateBuilderInput } from './api';
import { useLoadBuilderInput } from './helper';
import type { LocNetModel } from './model';
import { getModelFileName, isLegacyModelFile } from './modelFile';
import { locnetModelToBuilderInput } from './submit';
import styles from './ModelFileControls.module.css';
import { useIntlIdOrText } from '../form/Intl.utils';

export const ModelFileControls = () => {
  const { useWatchModelStore } = useStaticFormTsContext();
  const modelData = useWatchModelStore('root', {} as LocNetModel);
  const loadBuilderInput = useLoadBuilderInput();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isLoading, setIsLoading] = useState(false);
  const oldModelWarning = useIntlIdOrText('warning_old_model', undefined);

  const chooseModelFile = useCallback(
    (event: MouseEvent<HTMLAnchorElement>) => {
      event.preventDefault();
      if (!isLoading) {
        fileInputRef.current?.click();
      }
    },
    [isLoading],
  );

  const loadModel = useCallback(
    async (event: ChangeEvent<HTMLInputElement>) => {
      const [file] = event.currentTarget.files ?? [];
      // Allow selecting the same file again after a validation error.
      event.currentTarget.value = '';
      if (!file || isLoading) {
        return;
      }

      setIsLoading(true);
      try {
        const fileContents = await file.text();
        let unvalidatedInput: unknown;
        try {
          unvalidatedInput = JSON.parse(fileContents);
        } catch {
          throw Error('The selected file is not valid JSON.');
        }

        if (isLegacyModelFile(unvalidatedInput)) {
          alert(
            oldModelWarning ??
              'This model was saved by an older version. Aggregate area and household inputs will be derived from its locations, and new location fields may be required.',
          );
        }

        // The endpoint uses the Python BuilderInput class as its request model.
        const builderInput = await validateBuilderInput(unvalidatedInput);
        await loadBuilderInput(builderInput);
      } catch (error) {
        console.error('Unable to load model file', error);
        alert(`Could not load model: ${getErrorMessage(error)}`);
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, loadBuilderInput, oldModelWarning],
  );

  const saveModel = useCallback(
    (event: MouseEvent<HTMLAnchorElement>) => {
      event.preventDefault();

      // This is the same structure displayed as "Model query to POST" in
      // Developer options, so saved files can be loaded directly later.
      const { data: builderInput, error } = builderInputSchema.safeParse(
        locnetModelToBuilderInput(modelData),
      );
      if (error) {
        const firstIssue = error.issues[0];
        const location = firstIssue?.path.join('.') ?? 'the current model';
        alert(
          `Could not save model: ${location} ${firstIssue?.message ?? 'is invalid'}.`,
        );
        return;
      }

      const modelBlob = new Blob([JSON.stringify(builderInput, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(modelBlob);
      const downloadLink = document.createElement('a');
      downloadLink.href = url;
      downloadLink.download = getModelFileName(builderInput.iso_3);
      downloadLink.click();
      URL.revokeObjectURL(url);
    },
    [modelData],
  );

  return (
    <>
      <li>
        <a
          href="#load-model"
          className={styles.modelFileLink}
          onClick={chooseModelFile}
          aria-disabled={isLoading}
          data-testid="load_model"
        >
          Load Model
        </a>
        <input
          ref={fileInputRef}
          className={styles.fileInput}
          type="file"
          accept="application/json,.json"
          aria-label="Choose model file"
          onChange={loadModel}
          data-testid="load_model_file"
        />
      </li>
      <li>
        <a
          href="#save-model"
          className={styles.modelFileLink}
          onClick={saveModel}
          data-testid="save_model"
        >
          Save Model
        </a>
      </li>
    </>
  );
};

const getErrorMessage = (error: unknown): string =>
  error instanceof Error ? error.message : 'An unexpected error occurred.';
