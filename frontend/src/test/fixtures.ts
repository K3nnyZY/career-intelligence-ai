import type { Comparison, Profile } from '../features/comparison/api/contracts';

const quote = 'Implementé SQL y Python.';
const sql = { skill: 'sql', matched_text: 'SQL', start: 11, end: 14, quote, quote_start: 0, quote_end: quote.length, requirement: 'mentioned' as const };
const python = { ...sql, skill: 'python', matched_text: 'Python', start: 17, end: 23 };

export const profile: Profile = {
  text: quote, skills: ['python', 'sql'], evidence: [sql, python],
  experience_signals: [{ quote, start: 0, end: quote.length, skills: ['python', 'sql'] }],
  extractor_version: 'evidence_rules_v1', taxonomy_version: 'test', warnings: ['Revisa el texto extraído.'],
};
export const comparison: Comparison = {
  schema_version: '1.0', extractor_version: 'evidence_rules_v1', taxonomy_version: 'test', evidence_source: 'reviewed_cv_text',
  groups: {
    required: { matched: ['sql'], missing_evidence: ['python'], coverage: .5 },
    desirable: { matched: [], missing_evidence: ['docker'], coverage: 0 },
    unspecified: { matched: [], missing_evidence: [], coverage: null },
  },
  skills: [
    { skill: 'sql', requirement: 'required', status: 'matched', vacancy_evidence: [{ ...sql, requirement: 'required', quote: 'SQL requerido' }], cv_evidence: [sql] },
    { skill: 'python', requirement: 'required', status: 'missing_evidence', vacancy_evidence: [{ ...python, requirement: 'required', quote: 'Python requerido' }], cv_evidence: [] },
  ],
  highlights: [{ ...profile.experience_signals[0]!, relevant_skills: ['sql'] }],
  excluded_mentions: [], warnings: ['Cobertura; no es probabilidad de contratación.'],
};
