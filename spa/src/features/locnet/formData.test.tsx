import { test, expect } from 'vitest';
import { locNetForm, type EditableLocNetForm } from './formData';

test('Form data exists', async () => {
  // This shouldn't error as the Editable type should be same but broader
  const editableForm: EditableLocNetForm = {
    nodes: locNetForm.nodes,
    set() {},
    api: {
      characteristics: undefined,
      bounds: undefined,
      modelerAPIOutput: undefined
    },
  };
  expect(editableForm).toBeTruthy();

  // Verify editing works correctly
  const editingTest: EditableLocNetForm = {
    ...locNetForm,
    set() {},
  };

  // this is a trivial test, and the real test is the TypeScript
  expect(editingTest).toBeTruthy();
});

test('starts with country selection and does not repeat the introduction', () => {
  expect(locNetForm.nodes[0]).toMatchObject({
    type: 'CountriesDropdown',
    labelIntlId: 'sel_country',
  });
  expect(JSON.stringify(locNetForm)).not.toContain('"introduction"');
});
