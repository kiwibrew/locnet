import { z } from 'zod';
import { getDomJson } from '../domJson';

const TechnologiesSchema = z
  .object({
    technology: z.string(),
    technology_name: z.string(),
  })
  .strict()
  .array();

export const getTechnologies = () => {
  const maybeCategoriesData = getDomJson('technologies');
  if (!maybeCategoriesData) return [];
  return TechnologiesSchema.parse(maybeCategoriesData);
};
