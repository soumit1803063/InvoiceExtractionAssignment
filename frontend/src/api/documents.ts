import { buildApiUrl, requestBlob, requestJson } from './httpClient';
import type {
  DocumentListResponse,
  HealthResponse,
  InvoiceDocument,
  InvoiceFieldsUpdate,
  ReferenceData,
  StartOverResult
} from '../types/contract';

function abortable(signal?: AbortSignal): RequestInit {
  return signal ? { signal } : {};
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


export async function startOver(signal?: AbortSignal): Promise<StartOverResult> {
  return requestJson<StartOverResult>('/documents', { method: 'DELETE', ...abortable(signal) });
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


export function buildDocumentPreviewUrl(documentId: string): string {
  return buildApiUrl(`/documents/${encodeURIComponent(documentId)}/preview`);
}

export async function fetchDocumentPreview(documentId: string, signal?: AbortSignal): Promise<Blob> {
  return requestBlob(`/documents/${encodeURIComponent(documentId)}/preview`, abortable(signal));
}
