import { jsonRequest, request } from '../../../shared/api/client';
import { comparisonSchema, profileSchema } from './contracts';

export const comparisonApi = {
  extract(file: File, format: 'pdf' | 'docx', signal: AbortSignal) {
    return request('/documents/extract', { method: 'POST', headers: { 'Content-Type': 'application/octet-stream', 'X-Document-Format': format }, body: file, signal }, profileSchema);
  },
  review(text: string, signal: AbortSignal) {
    return request('/profile/review', jsonRequest({ text }, signal), profileSchema);
  },
  compare(cvText: string, vacancyText: string, selectedSkills: string[], signal: AbortSignal) {
    return request('/compare', jsonRequest({ cv_text: cvText, vacancy_text: vacancyText, selected_skills: selectedSkills }, signal), comparisonSchema);
  },
};
