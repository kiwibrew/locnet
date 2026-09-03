import type { BuilderInput, CharacteristicsRequest } from './api-generated-client';
import { AuthenticatedApiClient } from '../auth/apiClient';
import { boundsResponseSchema, builderInputSchema } from './api-generated-zod';
import type { EditableLocNetForm } from './formData';
import { debouncePromise } from './utils';
import { authenticatedHeaders } from '../auth/session';

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
  const apiClient = new AuthenticatedApiClient({
    headers: authenticatedHeaders(),
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

let boundsAbortController: AbortController | undefined = undefined;

const getBoundsInner = async (
  props: CharacteristicsRequest,
): Promise<EditableLocNetForm['api']['bounds']> => {
  console.log('Requesting bounds of ', props.iso_3);
  if (boundsAbortController) {
    boundsAbortController.abort();
  }
  boundsAbortController = new AbortController();

  try {
    const response = await fetch(
      `/api/bounds/${encodeURIComponent(props.iso_3)}`,
      { signal: boundsAbortController.signal },
    );
    if (!response.ok) {
      throw Error(`Server returned ${response.status}`);
    }
    const responseBody: unknown = await response.json();
    const { data: bounds, error } =
      boundsResponseSchema.safeParse(responseBody);
    if (error) {
      throw Error('The server returned invalid bounds data.');
    }
    return bounds;
  } catch (e) {
    return {
      type: 'error',
      message: String(e),
    };
  }
};

export const getBounds = debouncePromise(getBoundsInner, API_DEBOUNCE_TIME_MS);

export const validateBuilderInput = async (
  input: unknown,
): Promise<BuilderInput> => {
  const response = await fetch('/api/modeler/validate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authenticatedHeaders(),
    },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    throw Error(await getValidationErrorMessage(response));
  }

  const responseBody: unknown = await response.json();
  const { data: builderInput, error } =
    builderInputSchema.safeParse(responseBody);
  if (error) {
    console.error('Invalid BuilderInput returned by validation endpoint', error);
    throw Error('The server returned an invalid model. Please try again.');
  }
  return builderInput;
};

const getValidationErrorMessage = async (response: Response): Promise<string> => {
  const responseBody: unknown = await response.json().catch(() => undefined);
  if (
    typeof responseBody === 'object' &&
    responseBody !== null &&
    'detail' in responseBody
  ) {
    const { detail } = responseBody;
    if (typeof detail === 'string') {
      return detail;
    }
    if (Array.isArray(detail)) {
      const firstError = detail[0];
      if (
        typeof firstError === 'object' &&
        firstError !== null &&
        'msg' in firstError &&
        typeof firstError.msg === 'string'
      ) {
        const location =
          'loc' in firstError && Array.isArray(firstError.loc)
            ? ` (${firstError.loc.join('.')})`
            : '';
        return `${firstError.msg}${location}`;
      }
    }
  }
  return `The model file is invalid (server returned ${response.status}).`;
};
