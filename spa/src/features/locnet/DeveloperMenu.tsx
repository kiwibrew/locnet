import { useCallback, useRef } from 'react';
import { useStaticFormTsContext } from '../form/FormProvider';
import styles from './DeveloperMenu.module.css';
import type { EditableLocNetForm } from './formData';
import { sampleData, useLoadBuilderInput } from './helper';
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
  
  const loadSampleData = useCallback(async () => {
    const { current: detailsElement } = detailsRef;
    if (!detailsElement) {
      throw Error('Expected <details> element');
    }
    detailsElement.open = false;
    await loadBuilderInput(sampleData);
  }, [loadBuilderInput]);

  const detailsRef = useRef<HTMLDetailsElement>(null);

  return (
    <div className={styles.debug}>
      <details ref={detailsRef} className={styles.details}>
        <summary className={styles.summary}>Developer options</summary>
        <div className={styles.debugBody}>
          <div className={styles.buttonTray}>
            <button
              onClick={loadSampleData}
              className={styles.loadSampleDataButton}
            >
              load sample data
            </button>
          </div>
          <div>
            {modelerAPIOutput && (
              <>
                <h3>modelerAPIOutput</h3>
                <pre style={{ marginBottom: '100px' }}>
                  {JSON.stringify(modelerAPIOutput, null, 2)}{' '}
                </pre>
              </>
            )}
            <h3>Model query to POST</h3>
            <pre>
              {JSON.stringify(locnetModelToBuilderInput(modelData), null, 2)}
            </pre>
          </div>
        </div>
      </details>
    </div>
  );
};
