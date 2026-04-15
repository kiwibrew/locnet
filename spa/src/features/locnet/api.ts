import { ApiClient, type CharacteristicsRequest } from './api-generated-client';
import type { EditableLocNetForm } from './formData';
import { debouncePromise } from './utils';

const API_DEBOUNCE_TIME_MS = 200;

let characteristicsAbortController: AbortController | undefined = undefined;

const getCharacteristicsInner = async (
  props: CharacteristicsRequest,
): Promise<EditableLocNetForm['api']['characteristics']> => {
  console.log('Requesting characteristics of ', props.iso_3);
  if (characteristicsAbortController) {
    characteristicsAbortController.abort();
  }
  characteristicsAbortController = new AbortController();
  const apiClient = new ApiClient({
    // @ts-expect-error this is not in typing but seems to work
    signal: characteristicsAbortController.signal,
  });

  try {
    const defaultsDetails =
      await apiClient.apiPOSTEndpoints.getCharacteristicsApiCharacteristicsPost(
        props,
      );
    return defaultsDetails;
  } catch (e) {
    return {
      type: 'error',
      message: String(e),
    };
  }
};

export const getCharacteristics = debouncePromise(
  getCharacteristicsInner,
  API_DEBOUNCE_TIME_MS,
);
