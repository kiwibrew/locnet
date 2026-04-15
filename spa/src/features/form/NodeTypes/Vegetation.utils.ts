import { z } from 'zod';
import { getDomJson } from '../domJson';

export const VegetationsSchema = z
  .object({
    element: z.string(),
    name: z.string(),
    value: z.number(),
  })
  .strict()
  .array();

export const getVegetationsData = () => {
  const maybeVegetationData = getDomJson('vegetation');
  if (!maybeVegetationData) return [];
  return VegetationsSchema.parse(maybeVegetationData);
};
