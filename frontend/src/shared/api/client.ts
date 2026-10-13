import type { z } from 'zod';

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function request<T>(path: string, options: RequestInit, schema: z.ZodType<T>): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, { ...options, cache: 'no-store', credentials: 'omit' });
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw error;
    throw new ApiError('No se pudo conectar con la API local. Comprueba que esté en ejecución.', 0);
  }
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new ApiError('La API no devolvió una respuesta válida.', response.status);
  }
  if (!response.ok) {
    const detail = typeof payload === 'object' && payload !== null && 'detail' in payload ? payload.detail : null;
    throw new ApiError(typeof detail === 'string' ? detail : 'No se pudo procesar la solicitud.', response.status);
  }
  const result = schema.safeParse(payload);
  if (!result.success) throw new ApiError('La respuesta de la API no coincide con el contrato esperado. Actualiza la aplicación.', response.status);
  return result.data;
}

export function jsonRequest(payload: unknown, signal: AbortSignal): RequestInit {
  return { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), signal };
}
