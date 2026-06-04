import { z } from 'zod';

export const OcrProcessRequestSchema = z.object({
  imageUrl: z
    .string({ required_error: 'imageUrl is required' })
    .url({ message: 'imageUrl must be a valid URL' })
    .refine(
      (url) => url.startsWith('http://') || url.startsWith('https://'),
      { message: 'imageUrl must use http or https protocol' }
    ),

  provider: z
    .enum(['openai', 'google'], {
      errorMap: () => ({ message: "provider must be 'openai' or 'google'" }),
    })
    .optional(),

  languages: z
    .array(z.string().min(1).max(10))
    .min(1, 'languages must have at least one entry')
    .max(10, 'languages must have at most 10 entries')
    .optional(),
});

export type ValidatedOcrRequest = z.infer<typeof OcrProcessRequestSchema>;