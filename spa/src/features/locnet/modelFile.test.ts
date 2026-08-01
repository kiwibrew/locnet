import { expect, test } from 'vitest';
import { getModelFileName, isLegacyModelFile } from './modelFile';

test('uses a lower-case ISO code and local timestamp in model file names', () => {
  const localTime = new Date(2026, 6, 17, 9, 5, 3);

  expect(getModelFileName('NZL', localTime)).toBe(
    'cn_model_nzl_2026-07-17_09-05-03.json',
  );
});

test('identifies saved models without the current model version as legacy', () => {
  expect(isLegacyModelFile({ area_sqkm: 100 })).toBe(true);
  expect(isLegacyModelFile({ model_version: 2 })).toBe(false);
  expect(isLegacyModelFile(null)).toBe(false);
});
