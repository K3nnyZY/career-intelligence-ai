import { describe, expect, it } from 'vitest';
import { comparison, profile } from '../../../test/fixtures';
import { canCompare, initialSession, sessionReducer } from './session';

function reviewedSession() {
  let state = sessionReducer(initialSession(), { type: 'profileReceived', profile });
  state = sessionReducer(state, { type: 'vacancyChanged', text: 'Required: SQL' });
  return sessionReducer(state, { type: 'confirmed', value: true });
}

describe('reviewed CV session invariants', () => {
  it('requires review and confirmation even if the job and CV contain text', () => {
    let state = sessionReducer(initialSession(), { type: 'cvChanged', text: 'SQL' });
    state = sessionReducer(state, { type: 'vacancyChanged', text: 'SQL' });
    state = sessionReducer(state, { type: 'confirmed', value: true });
    expect(canCompare(state)).toBe(false);
    expect(canCompare(reviewedSession())).toBe(true);
  });
  it('invalidates profile, selection, confirmation and results after editing the CV', () => {
    const complete = sessionReducer(reviewedSession(), { type: 'comparisonReceived', result: comparison });
    const state = sessionReducer(complete, { type: 'cvChanged', text: 'Changed CV' });
    expect(state.profile).toBeNull();
    expect(state.result).toBeNull();
    expect(state.selectedSkills).toEqual([]);
    expect(canCompare(state)).toBe(false);
  });
  it('requires confirmation after changing selected skills and honors empty selection', () => {
    let state = reviewedSession();
    for (const skill of profile.skills) state = sessionReducer(state, { type: 'skillToggled', skill });
    expect(state.selectedSkills).toEqual([]);
    expect(state.confirmed).toBe(false);
    state = sessionReducer(state, { type: 'confirmed', value: true });
    expect(canCompare(state)).toBe(true);
  });
  it('locks selection during requests and never accepts a skill outside the profile', () => {
    const state = sessionReducer(reviewedSession(), { type: 'started', operation: 'compare' });
    expect(canCompare(state)).toBe(false);
    expect(sessionReducer(state, { type: 'skillToggled', skill: 'sql' })).toEqual(state);
    const reviewed = reviewedSession();
    expect(sessionReducer(reviewed, { type: 'skillToggled', skill: 'invented' })).toEqual(reviewed);
  });
  it('removes all personal state on clear while a request is pending', () => {
    const state = sessionReducer(reviewedSession(), { type: 'started', operation: 'extract' });
    expect(sessionReducer(state, { type: 'cleared', announce: false })).toEqual(initialSession());
  });
});
