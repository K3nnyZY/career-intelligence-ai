import { useCallback, useEffect, useReducer, useRef } from 'react';
import { comparisonApi } from '../api/comparisonApi';
import { canCompare, initialSession, sessionReducer } from './session';
import type { Operation } from './session';

export function useComparison() {
  const [state, dispatch] = useReducer(sessionReducer, undefined, () => initialSession());
  const pending = useRef<AbortController | null>(null);
  const generation = useRef(0);

  const cancel = useCallback(() => {
    generation.current += 1;
    pending.current?.abort();
    pending.current = null;
  }, []);

  const clear = useCallback((announce = true) => {
    cancel();
    dispatch({ type: 'cleared', announce });
  }, [cancel]);

  useEffect(() => {
    const hide = () => clear(false);
    const show = (event: PageTransitionEvent) => { if (event.persisted) clear(false); };
    window.addEventListener('pagehide', hide);
    window.addEventListener('pageshow', show);
    return () => {
      cancel();
      window.removeEventListener('pagehide', hide);
      window.removeEventListener('pageshow', show);
    };
  }, [cancel, clear]);

  async function execute<T>(operation: Operation, work: (signal: AbortSignal) => Promise<T>, complete: (data: T) => void) {
    cancel();
    const ticket = generation.current;
    const controller = new AbortController();
    pending.current = controller;
    dispatch({ type: 'started', operation });
    try {
      const data = await work(controller.signal);
      if (ticket === generation.current) complete(data);
    } catch (error) {
      if (ticket === generation.current && !(error instanceof Error && error.name === 'AbortError')) {
        dispatch({ type: 'failed', message: error instanceof Error ? error.message : 'No se pudo completar la operación.' });
      }
    } finally {
      if (ticket === generation.current) pending.current = null;
    }
  }

  function upload(file: File) {
    if (state.operation) return;
    const format = file.name.split('.').pop()?.toLowerCase();
    if ((format !== 'pdf' && format !== 'docx') || !file.size || file.size > 5 * 1024 * 1024) {
      dispatch({ type: 'failed', message: 'Selecciona un PDF o DOCX de entre 1 byte y 5 MiB.' });
      return;
    }
    return execute('extract', (signal) => comparisonApi.extract(file, format, signal),
      (profile) => dispatch({ type: 'profileReceived', profile }));
  }

  function review() {
    if (state.operation || !state.cvText.trim()) return;
    return execute('review', (signal) => comparisonApi.review(state.cvText, signal),
      (profile) => dispatch({ type: 'profileReceived', profile }));
  }

  function compare() {
    if (!canCompare(state)) return;
    return execute('compare', (signal) => comparisonApi.compare(state.cvText, state.vacancyText, state.selectedSkills, signal),
      (result) => dispatch({ type: 'comparisonReceived', result }));
  }

  return { state, busy: state.operation !== null, canCompare: canCompare(state), upload, review, compare, clear,
    changeCV: (text: string) => dispatch({ type: 'cvChanged', text }),
    changeVacancy: (text: string) => dispatch({ type: 'vacancyChanged', text }),
    toggleSkill: (skill: string) => dispatch({ type: 'skillToggled', skill }),
    confirm: (value: boolean) => dispatch({ type: 'confirmed', value }),
  };
}

export type ComparisonController = ReturnType<typeof useComparison>;
