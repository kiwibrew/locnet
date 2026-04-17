export const assertNever = (value: never) => {
  console.error('Unexpected', value);
  throw new Error('Code should be unreachable');
};
