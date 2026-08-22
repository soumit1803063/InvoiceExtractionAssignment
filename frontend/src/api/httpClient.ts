export const API_BASE_PATH = '/api';

export class RequestFailedError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'RequestFailedError';
    this.status = status;
  }
}

export function buildApiUrl(path: string): string {
  return `${API_BASE_PATH}${path.startsWith('/') ? path : `/${path}`}`;
}

function extractMessageFromBody(body: unknown, fallback: string): string {
  if (typeof body === 'string' && body.trim() !== '') {
    return body.trim();
  }
  if (body !== null && typeof body === 'object') {
    const record = body as Record<string, unknown>;
    for (const key of ['error_message', 'message', 'detail', 'error']) {
      const value = record[key];
      if (typeof value === 'string' && value.trim() !== '') {
        return value.trim();
      }
    }
  }
  return fallback;
}

export interface RawResponse {
  status: number;
  ok: boolean;
  body: unknown;
}

export async function sendRequest(path: string, init?: RequestInit): Promise<RawResponse> {
  let response: Response;
  const sendsJsonBody = init?.body !== undefined && !(init.body instanceof FormData);
  try {
    response = await fetch(buildApiUrl(path), {
      ...init,
      headers: {
        Accept: 'application/json',
        ...(sendsJsonBody ? { 'Content-Type': 'application/json; charset=utf-8' } : {}),
        ...init?.headers
      }
    });
  } catch (cause) {
    throw new RequestFailedError(
      cause instanceof Error && cause.name === 'AbortError'
        ? 'Request was cancelled.'
        : 'Cannot reach the server. Check that the backend is running.',
      0
    );
  }

  const contentType = response.headers.get('content-type') ?? '';
  let body: unknown = null;
  if (contentType.includes('application/json')) {
    body = await response.json().catch(() => null);
  } else {
    body = await response.text().catch(() => '');
  }

  return { status: response.status, ok: response.ok, body };
}

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await sendRequest(path, init);
  if (!response.ok) {
    throw new RequestFailedError(
      extractMessageFromBody(response.body, `Request failed with status ${response.status}.`),
      response.status
    );
  }
  return response.body as T;
}

export async function requestBlob(path: string, init?: RequestInit): Promise<Blob> {
  let response: Response;
  try {
    response = await fetch(buildApiUrl(path), init);
  } catch {
    throw new RequestFailedError('Cannot reach the server. Check that the backend is running.', 0);
  }
  if (!response.ok) {
    throw new RequestFailedError(`Request failed with status ${response.status}.`, response.status);
  }
  return response.blob();
}
