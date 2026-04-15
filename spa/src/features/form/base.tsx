import z from 'zod';

export const IntlId = z.string(); // FIXME: use codegen to generate accurate ids as z.literal()

export const NodeSchema = z.object({});

export const FormNodeSchema = NodeSchema.extend({
  labelIntlId: IntlId.optional(),
  labelText: z.string().optional(),
  descriptionIntlId: z.string().optional(),
  descriptionText: z.string().optional(),
});

export const FieldMeta = z.object({
  error: z.string().optional(),
  isTouched: z.boolean(),
});
