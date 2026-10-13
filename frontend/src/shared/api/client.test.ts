import { describe, expect, it, vi } from 'vitest';
import { z } from 'zod';
import { request } from './client';

describe('HTTP response boundary', () => {
  it('rejects incompatible responses without exposing their contents', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json({ secret: 'private-marker' })));
    await expect(request('/profile/review', {}, z.object({ text: z.string() }))).rejects.toThrow('contrato esperado');
  });
  it('uses no cache or cookies and passes the abort signal', async () => {
    const fetch = vi.fn().mockResolvedValue(Response.json({ ok: true }));
    vi.stubGlobal('fetch', fetch);
    const controller = new AbortController();
    await request('/health', { signal: controller.signal }, z.object({ ok: z.boolean() }));
    expect(fetch).toHaveBeenCalledWith('/health', expect.objectContaining({ cache: 'no-store', credentials: 'omit', signal: controller.signal }));
  });
  it('preserves typed error messages returned by the backend', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json({ detail: 'Usa un PDF sin contraseña.' }, { status: 422 })));
    await expect(request('/documents/extract', {}, z.object({ text: z.string() }))).rejects.toThrow('sin contraseña');
  });
  it('uses a useful local connection message instead of raw network errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('private-network-detail')));
    await expect(request('/compare', {}, z.object({ text: z.string() }))).rejects.toThrow('API local');
  });
});
