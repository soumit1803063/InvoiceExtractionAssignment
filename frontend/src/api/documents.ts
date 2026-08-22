import { buildApiUrl, requestBlob, requestJson, sendRequest, RequestFailedError } from './httpClient';
import type {
  DocumentListResponse,
  HealthResponse,
  InvoiceDocument,
  InvoiceFieldsUpdate,
  ReferenceData,
  RegisterResponse
} from '../types/contract';

function abortable(signal?: AbortSignal): RequestInit {
  return signal ? { signal } : {};
}

function hasRegisterShape(body: unknown): body is RegisterResponse {
  return (
    body !== null &&
    typeof body === 'object' &&
    'document' in (body as Record<string, unknown>) &&
    'registration' in (body as Record<string, unknown>)
  );
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return requestJson<HealthResponse>('/health', abortable(signal));
}

export async function fetchReferenceData(signal?: AbortSignal): Promise<ReferenceData> {
  return requestJson<ReferenceData>('/reference-data', abortable(signal));
}

export async function fetchDocuments(signal?: AbortSignal): Promise<InvoiceDocument[]> {
  const response = await requestJson<DocumentListResponse>('/documents', abortable(signal));
  return response?.documents ?? [];
}

export async function scanDocuments(signal?: AbortSignal): Promise<InvoiceDocument[]> {
  const response = await requestJson<DocumentListResponse>('/documents/scan', {
    method: 'POST',
    ...abortable(signal)
  });
  return response?.documents ?? [];
}

export async function saveDocumentFields(
  documentId: string,
  fields: InvoiceFieldsUpdate,
  signal?: AbortSignal
): Promise<InvoiceDocument> {
  return requestJson<InvoiceDocument>(`/documents/${encodeURIComponent(documentId)}`, {
    method: 'PUT',
    body: JSON.stringify({ fields }),
    ...abortable(signal)
  });
}

export async function registerDocument(documentId: string, signal?: AbortSignal): Promise<RegisterResponse> {
  const response = await sendRequest(`/documents/${encodeURIComponent(documentId)}/register`, {
    method: 'POST',
    ...abortable(signal)
  });
  if (hasRegisterShape(response.body)) {
    return response.body;
  }
  throw new RequestFailedError(
    `Registration did not return a result (status ${response.status}).`,
    response.status
  );
}

export async function clearDocuments(signal?: AbortSignal): Promise<DocumentListResponse> {
  return requestJson<DocumentListResponse>('/documents', { method: 'DELETE', ...abortable(signal) });
}

export async function uploadDocument(file: File, signal?: AbortSignal): Promise<InvoiceDocument> {
  const form = new FormData();
  form.append('file', file);
  return requestJson<InvoiceDocument>('/documents/upload', {
    method: 'POST',
    body: form,
    ...abortable(signal)
  });
}

export async function reprocessDocument(documentId: string, signal?: AbortSignal): Promise<InvoiceDocument> {
  return requestJson<InvoiceDocument>(`/documents/${encodeURIComponent(documentId)}/reprocess`, {
    method: 'POST',
    ...abortable(signal)
  });
}

export function buildDocumentPreviewUrl(documentId: string): string {
  return buildApiUrl(`/documents/${encodeURIComponent(documentId)}/preview`);
}

export async function fetchDocumentPreview(documentId: string, signal?: AbortSignal): Promise<Blob> {
  return requestBlob(`/documents/${encodeURIComponent(documentId)}/preview`, abortable(signal));
}
