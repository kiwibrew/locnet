import { useEffect, useRef, type Ref } from 'react';
import { useStaticFormTsContext, type FormPath } from './FormProvider';

export const useCustomErrorRef = (
  formPath: FormPath,
): Ref<HTMLInputElement | null> => {
  const { useWatchFormStore } = useStaticFormTsContext();

  const errorMessage = useWatchFormStore(formPath, undefined);

  const ref = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const { current: inputElement } = ref;
    if (!inputElement) {
      console.error("Couldn't find input element for useCustomError. Was return ref not assigned?");
      return;
    }
    inputElement.setCustomValidity(errorMessage ?? '')
  }, [errorMessage]);

  return ref;
};
