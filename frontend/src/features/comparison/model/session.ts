import type { Comparison, Profile } from '../api/contracts';

export type Operation = 'extract' | 'review' | 'compare';
export interface Session {
  cvText: string;
  vacancyText: string;
  profile: Profile | null;
  selectedSkills: string[];
  confirmed: boolean;
  result: Comparison | null;
  operation: Operation | null;
  feedback: { tone: 'info' | 'error'; text: string };
}

export function initialSession(message = ''): Session {
  return { cvText: '', vacancyText: '', profile: null, selectedSkills: [], confirmed: false,
    result: null, operation: null, feedback: { tone: 'info', text: message } };
}

type Action =
  | { type: 'cvChanged'; text: string }
  | { type: 'vacancyChanged'; text: string }
  | { type: 'skillToggled'; skill: string }
  | { type: 'confirmed'; value: boolean }
  | { type: 'started'; operation: Operation }
  | { type: 'profileReceived'; profile: Profile }
  | { type: 'comparisonReceived'; result: Comparison }
  | { type: 'failed'; message: string }
  | { type: 'cleared'; announce: boolean };

export function canCompare(state: Session): boolean {
  return !state.operation && !!state.profile && state.profile.text === state.cvText &&
    state.confirmed && !!state.vacancyText.trim();
}

export function sessionReducer(state: Session, action: Action): Session {
  switch (action.type) {
    case 'cvChanged':
      return { ...state, cvText: action.text, profile: null, selectedSkills: [], confirmed: false, result: null, feedback: { tone: 'info', text: '' } };
    case 'vacancyChanged':
      return { ...state, vacancyText: action.text, result: null };
    case 'skillToggled':
      if (!state.profile?.skills.includes(action.skill) || state.operation) return state;
      return { ...state, selectedSkills: state.selectedSkills.includes(action.skill)
        ? state.selectedSkills.filter((skill) => skill !== action.skill) : [...state.selectedSkills, action.skill],
        confirmed: false, result: null };
    case 'confirmed':
      return { ...state, confirmed: !!state.profile && state.profile.text === state.cvText && action.value, result: action.value ? state.result : null };
    case 'started':
      return { ...state, operation: action.operation, result: null,
        ...(action.operation === 'extract' ? { profile: null, selectedSkills: [], confirmed: false } : {}),
        feedback: { tone: 'info', text: 'Procesando en este equipo…' } };
    case 'profileReceived':
      return { ...state, cvText: action.profile.text, profile: action.profile, selectedSkills: [...action.profile.skills],
        confirmed: false, operation: null, result: null,
        feedback: { tone: 'info', text: 'Extracción lista. Revisa el texto y confirma las habilidades antes de comparar.' } };
    case 'comparisonReceived':
      return { ...state, result: action.result, operation: null,
        feedback: { tone: 'info', text: 'Comparación lista. Los fragmentos corresponden al CV que revisaste.' } };
    case 'failed':
      return { ...state, operation: null, feedback: { tone: 'error', text: action.message } };
    case 'cleared':
      return initialSession(action.announce ? 'Sesión borrada. La aplicación no mantiene archivos ni perfiles guardados.' : '');
  }
}
