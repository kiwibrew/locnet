import { z } from 'zod';
import { getDomJson } from '../domJson';

const FrequenciesSchema = z
  .object({
    frequency: z.number(),
    frequency_name: z.string(),
  })
  .strict()
  .array();

export const getFrequencies = () => {
  const maybeFrequenciesData = getDomJson('frequencies');
  if (!maybeFrequenciesData) return [];
  return FrequenciesSchema.parse(maybeFrequenciesData);
};
