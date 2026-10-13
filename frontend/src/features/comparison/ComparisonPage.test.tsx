import { act, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { App } from '../../app/App';
import { comparison, profile } from '../../test/fixtures';

describe('CV review and matching flow', () => {
  it('reviews, confirms selected skills and renders evidence from both texts', async () => {
    const user = userEvent.setup();
    const fetch = vi.fn().mockResolvedValueOnce(Response.json(profile)).mockResolvedValueOnce(Response.json(comparison));
    vi.stubGlobal('fetch', fetch);
    render(<App />);
    await user.type(screen.getByLabelText('Texto del CV · editable'), profile.text);
    await user.type(screen.getByLabelText('Descripción completa'), 'Required: SQL and Python');
    expect(screen.getByRole('button', { name: 'Comparar con mi perfil' })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Actualizar extracción' }));
    await screen.findByRole('checkbox', { name: 'python' });
    await user.click(screen.getByRole('checkbox', { name: 'python' }));
    await user.click(screen.getByRole('checkbox', { name: 'Revisé el texto y las habilidades seleccionadas.' }));
    await user.click(screen.getByRole('button', { name: 'Comparar con mi perfil' }));
    await screen.findByRole('heading', { name: 'Una lectura con respaldo' });
    const options = fetch.mock.calls[1]?.[1] as RequestInit;
    expect(JSON.parse(options.body as string).selected_skills).toEqual(['sql']);
    expect(screen.getByText('SQL requerido')).toBeInTheDocument();
    expect(screen.getAllByText(profile.text).length).toBeGreaterThan(0);
    expect(screen.getByText('Sin evidencia en el CV')).toBeInTheDocument();
    await user.type(screen.getByLabelText('Texto del CV · editable'), ' corrected');
    expect(screen.queryByRole('heading', { name: 'Una lectura con respaldo' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Comparar con mi perfil' })).toBeDisabled();
  });
  it('aborts requests and ignores late responses after clearing the session', async () => {
    const user = userEvent.setup();
    let resolve: (value: Response) => void = () => { throw new Error('Not started'); };
    const response = new Promise<Response>((complete) => { resolve = complete; });
    const fetch = vi.fn().mockReturnValue(response);
    vi.stubGlobal('fetch', fetch);
    render(<App />);
    await user.type(screen.getByLabelText('Texto del CV · editable'), 'private-cv-marker');
    await user.click(screen.getByRole('button', { name: 'Actualizar extracción' }));
    await user.click(screen.getByRole('button', { name: 'Borrar sesión' }));
    const options = fetch.mock.calls[0]?.[1] as RequestInit;
    expect(options.signal?.aborted).toBe(true);
    await act(async () => { resolve(Response.json(profile)); await response; });
    expect(screen.getByLabelText('Texto del CV · editable')).toHaveValue('');
    expect(screen.queryByRole('checkbox', { name: 'python' })).not.toBeInTheDocument();
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });
  it('discards the session on pagehide and on restoration from browser history', async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByLabelText('Texto del CV · editable'), 'private-cv-marker');
    fireEvent(window, new Event('pagehide'));
    expect(screen.getByLabelText('Texto del CV · editable')).toHaveValue('');
    await user.type(screen.getByLabelText('Descripción completa'), 'private-job-marker');
    fireEvent(window, new PageTransitionEvent('pageshow', { persisted: true }));
    expect(screen.getByLabelText('Descripción completa')).toHaveValue('');
  });
});
