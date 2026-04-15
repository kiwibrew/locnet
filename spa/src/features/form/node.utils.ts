import { type EditableForm, type Node } from './node';

type AllKeys<T> = T extends unknown ? keyof T : never;

export const deepSearchByNodeFragment = (
  root: EditableForm,
  key: AllKeys<Node>,
  value: unknown,
): Node | undefined => {
  // Based on https://stackoverflow.com/a/56204398
  let nodeMatch: Node | undefined;

  // ignore response, just use JSON.stringify to deep search object
  void JSON.stringify(root, (_, obj) => {
    if (obj && typeof obj === 'object' && obj[key] === value) {
      nodeMatch = obj;
    }
    return obj;
  });

  return nodeMatch;
};
