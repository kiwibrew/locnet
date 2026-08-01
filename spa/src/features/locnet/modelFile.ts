const padTimePart = (value: number): string => value.toString().padStart(2, '0');

export const CURRENT_MODEL_VERSION = 2;

export const isLegacyModelFile = (value: unknown): boolean => {
  if (typeof value !== 'object' || value === null) return false;
  const version = (value as { model_version?: unknown }).model_version;
  return typeof version !== 'number' || version < CURRENT_MODEL_VERSION;
};

export const getModelFileName = (
  iso_3: string,
  localTime: Date = new Date(),
): string => {
  const date = [
    localTime.getFullYear(),
    padTimePart(localTime.getMonth() + 1),
    padTimePart(localTime.getDate()),
  ].join('-');
  const time = [
    padTimePart(localTime.getHours()),
    padTimePart(localTime.getMinutes()),
    padTimePart(localTime.getSeconds()),
  ].join('-');

  return `cn_model_${iso_3.toLowerCase()}_${date}_${time}.json`;
};
