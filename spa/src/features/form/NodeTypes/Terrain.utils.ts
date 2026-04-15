import { z } from 'zod';
import { getDomJson } from '../domJson';

export const TerrainsSchema = z
  .object({
    element: z.string(),
    name: z.string(),
    value: z.number(),
  })
  .strict()
  .array();

export const getTerrainsData = () => {
  const maybeTerrainData = getDomJson('terrain');
  if (!maybeTerrainData) return [];
  return TerrainsSchema.parse(maybeTerrainData);
};
