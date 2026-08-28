import { z } from 'zod';
import { getDomJson } from '../form/domJson';

const exampleFilenamesSchema = z.array(z.string());

export const getExampleFilenames = (): string[] =>
  exampleFilenamesSchema.parse(getDomJson('example_filenames') ?? []);

export const getExampleLabel = (filename: string): string =>
  filename
    .replace(/\.json$/i, '')
    .split('_')
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
