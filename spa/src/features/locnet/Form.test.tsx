import { renderToStaticMarkup } from 'react-dom/server';
import { expect, test } from 'vitest';
import { ModelSubmissionErrorMessage } from './Form';
import { GEOSPATIAL_API_ERROR_MESSAGE } from './submit';

test('renders a model submission error as an accessible alert', () => {
  const html = renderToStaticMarkup(
    <ModelSubmissionErrorMessage
      output={{ type: 'error', message: GEOSPATIAL_API_ERROR_MESSAGE }}
    />,
  );

  expect(html).toContain('role="alert"');
  expect(html).toContain('The model could not be processed');
});

test('renders nothing when there is no model submission error', () => {
  expect(
    renderToStaticMarkup(<ModelSubmissionErrorMessage output={undefined} />),
  ).toBe('');
});
