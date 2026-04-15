type SoftDeletableObj = Record<string, unknown>;
type SoftDeletableArr = SoftDeletableObj[];
type SoftDeletable = SoftDeletableObj | SoftDeletableArr;

export const removeSoftDeletes = <T extends SoftDeletable | undefined>(
  model: T,
): T => {
  if (!model) {
    return model;
  }

  if (Array.isArray(model)) {
    return model
      .filter(
        (obj) =>
          Boolean(obj) &&
          typeof obj === 'object' &&
          'isSoftDeleted' in obj &&
          !obj.isSoftDeleted,
      )
      .map((obj) => removeSoftDeletes(obj)) as T;
  }

  const keysWithArraysWithSoftDeletes = Object.keys(model).filter(
    (key) =>
      Array.isArray(model[key]) &&
      model[key].some((val) => val && 'isSoftDeleted' in val),
  );

  return {
    ...model,
    ...keysWithArraysWithSoftDeletes.reduce((acc, key) => {
      let value = model[key];
      if (Array.isArray(value)) {
        value = value.filter((item) => {
          return !item.isSoftDeleted;
        }).map(item => removeSoftDeletes(item));
      }
      acc[key] = value;
      return acc;
    }, {} as Partial<SoftDeletableObj>),
  };
};
