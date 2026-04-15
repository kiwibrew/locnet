import { test, expect } from 'vitest';
import { deepSearchByNodeFragment } from './node.utils';
import type { EditableForm } from './node';

test('search empty form', () => {
  const root: EditableForm = {
    nodes: [],
    set() {},
    api: {},
  };

  expect(
    deepSearchByNodeFragment(root, 'labelIntlId', 'sel_lang'),
  ).toBeUndefined();
});

test('search deeply form', () => {
  const root: EditableForm = {
    nodes: [
      {
        type: 'Disclosure',
        labelIntlId: '',
        children: [{ type: 'FieldHelp', labelIntlId: 'find me' }],
      },
      {
        type: 'Inert',
      },
      {
        type: 'Inert',
      },
    ],
    set() {},
    api: {},
  };

  expect(deepSearchByNodeFragment(root, 'labelIntlId', 'find me')).toEqual({
    type: 'FieldHelp',
    labelIntlId: 'find me',
  });
});
