import { expect, test } from 'vitest';
import { getExampleLabel } from './examples';

test('creates a display label from an example filename', () => {
  expect(getExampleLabel('indonesia_example.json')).toBe('Indonesia Example');
  expect(getExampleLabel('philippines_example.json')).toBe(
    'Philippines Example',
  );
});
