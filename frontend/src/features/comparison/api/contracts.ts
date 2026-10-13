import { z } from 'zod';

export const requirementSchema = z.enum(['required', 'desirable', 'unspecified']);
const evidenceSchema = z.object({
  skill: z.string(), matched_text: z.string(), start: z.number().int().nonnegative(), end: z.number().int().nonnegative(),
  quote: z.string(), quote_start: z.number().int().nonnegative(), quote_end: z.number().int().nonnegative(),
  requirement: z.enum(['required', 'desirable', 'unspecified', 'mentioned', 'excluded']),
});
const experienceSchema = z.object({ quote: z.string(), start: z.number().int(), end: z.number().int(), skills: z.array(z.string()) });
export const profileSchema = z.object({
  text: z.string(), skills: z.array(z.string()), evidence: z.array(evidenceSchema),
  experience_signals: z.array(experienceSchema), extractor_version: z.string(), taxonomy_version: z.string(),
  warnings: z.array(z.string()), document_format: z.enum(['pdf', 'docx']).optional(),
});
const groupSchema = z.object({ matched: z.array(z.string()), missing_evidence: z.array(z.string()), coverage: z.number().min(0).max(1).nullable() });
export const comparisonSchema = z.object({
  schema_version: z.literal('1.0'), extractor_version: z.string(), taxonomy_version: z.string(),
  evidence_source: z.literal('reviewed_cv_text'),
  groups: z.object({ required: groupSchema, desirable: groupSchema, unspecified: groupSchema }),
  skills: z.array(z.object({ skill: z.string(), requirement: requirementSchema,
    status: z.enum(['matched', 'missing_evidence']), vacancy_evidence: z.array(evidenceSchema), cv_evidence: z.array(evidenceSchema) })),
  highlights: z.array(experienceSchema.extend({ relevant_skills: z.array(z.string()) })),
  excluded_mentions: z.array(evidenceSchema), warnings: z.array(z.string()),
});

export type Profile = z.infer<typeof profileSchema>;
export type Comparison = z.infer<typeof comparisonSchema>;
export type Requirement = z.infer<typeof requirementSchema>;
export type Evidence = z.infer<typeof evidenceSchema>;
