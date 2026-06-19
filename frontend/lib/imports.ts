import { apiFetch } from '@/lib/api';

export type CanonicalField = 'frame' | 'motor' | 'color' | 'model';

export const CANONICAL_FIELDS: CanonicalField[] = ['frame', 'motor', 'color', 'model'];

export type ColumnMapping = Record<string, CanonicalField>;

export interface SheetPreview {
  sheet: string;
  has_header: boolean;
  columns: string[];
  column_mapping: Record<string, CanonicalField | null>;
  mapped_fields: Partial<Record<CanonicalField, string>>;
  rows: number;
}

export interface PreviewRow {
  sheet: string;
  frame?: string;
  motor?: string;
  color?: string;
  model?: string;
}

export interface InvalidRow {
  sheet: string;
  row: number;
  reasons: string[];
  data: Record<string, string>;
}

export interface Issue {
  level: string;
  message: string;
  sheet?: string | null;
}

export interface Validation {
  is_valid: boolean;
  message: string;
}

export interface ImportPreviewResponse {
  filename: string;
  sheets: SheetPreview[];
  detected_fields: CanonicalField[];
  preview_data: PreviewRow[];
  invalid_rows: InvalidRow[];
  invalid_rows_count: number;
  issues: Issue[];
  validation: Validation;
}

export interface UploadResult {
  import_id: number;
  message: string;
  total_records: number;
  successful_imports: number;
  failed_imports: number;
}

export interface ImportRecord {
  id: number;
  filename: string;
  original_filename: string;
  total_records: number;
  successful_imports: number;
  failed_imports: number;
  user_id: number;
  status: string;
  batch_period: string | null;
  product_type: string | null;
  notes: string | null;
  import_date: string;
  completed_at: string | null;
}

export interface ImportError {
  id: number;
  import_id: number;
  row_number: number;
  error_message: string;
  raw_data: string | null;
  created_at: string;
}

export interface ModelEquivalence {
  id: number;
  manufacturer_model: string;
  internal_model: string;
  notes: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface ModelEquivalenceInput {
  manufacturer_model: string;
  internal_model: string;
  notes?: string | null;
}

export interface UploadMetadata {
  batch_period?: string | null;
  product_type?: string | null;
  columnMapping?: ColumnMapping | null;
}

export interface Pagination {
  skip?: number;
  limit?: number;
}

const IMPORTS_BASE = '/api/v1/imports';
const EQUIVALENCES_BASE = '/api/v1/model-equivalences';

function pageQuery(pagination?: Pagination): string {
  if (!pagination) return '';
  const params = new URLSearchParams();
  if (pagination.skip !== undefined) params.set('skip', String(pagination.skip));
  if (pagination.limit !== undefined) params.set('limit', String(pagination.limit));
  const query = params.toString();
  return query ? `?${query}` : '';
}

export async function previewImport(
  file: File,
  columnMapping: ColumnMapping | null | undefined,
  token: string | null | undefined,
): Promise<ImportPreviewResponse> {
  const formData = new FormData();
  formData.append('file', file);
  if (columnMapping && Object.keys(columnMapping).length > 0) {
    formData.append('column_mapping', JSON.stringify(columnMapping));
  }
  return apiFetch<ImportPreviewResponse>(`${IMPORTS_BASE}/preview`, {
    method: 'POST',
    token,
    body: formData,
  });
}

export async function uploadImport(
  file: File,
  metadata: UploadMetadata,
  token: string | null | undefined,
): Promise<UploadResult> {
  const formData = new FormData();
  formData.append('file', file);
  if (metadata.batch_period) formData.append('batch_period', metadata.batch_period);
  if (metadata.product_type) formData.append('product_type', metadata.product_type);
  if (metadata.columnMapping && Object.keys(metadata.columnMapping).length > 0) {
    formData.append('column_mapping', JSON.stringify(metadata.columnMapping));
  }
  return apiFetch<UploadResult>(`${IMPORTS_BASE}/upload`, {
    method: 'POST',
    token,
    body: formData,
  });
}

export async function listImports(
  token: string | null | undefined,
  pagination?: Pagination,
): Promise<ImportRecord[]> {
  return apiFetch<ImportRecord[]>(`${IMPORTS_BASE}/${pageQuery(pagination)}`, { token });
}

export async function getImport(
  id: number,
  token: string | null | undefined,
): Promise<ImportRecord> {
  return apiFetch<ImportRecord>(`${IMPORTS_BASE}/${id}`, { token });
}

export async function getImportErrors(
  id: number,
  token: string | null | undefined,
  pagination?: Pagination,
): Promise<ImportError[]> {
  return apiFetch<ImportError[]>(`${IMPORTS_BASE}/${id}/errors${pageQuery(pagination)}`, { token });
}

export async function deleteImport(
  id: number,
  token: string | null | undefined,
): Promise<void> {
  await apiFetch<unknown>(`${IMPORTS_BASE}/${id}`, { method: 'DELETE', token });
}

export async function listModelEquivalences(
  token: string | null | undefined,
  pagination?: Pagination,
): Promise<ModelEquivalence[]> {
  return apiFetch<ModelEquivalence[]>(`${EQUIVALENCES_BASE}/${pageQuery(pagination)}`, { token });
}

export async function listUnmappedModels(
  token: string | null | undefined,
): Promise<string[]> {
  return apiFetch<string[]>(`${EQUIVALENCES_BASE}/unmapped`, { token });
}

export async function getModelEquivalence(
  id: number,
  token: string | null | undefined,
): Promise<ModelEquivalence> {
  return apiFetch<ModelEquivalence>(`${EQUIVALENCES_BASE}/${id}`, { token });
}

export async function createModelEquivalence(
  payload: ModelEquivalenceInput,
  token: string | null | undefined,
): Promise<ModelEquivalence> {
  return apiFetch<ModelEquivalence>(`${EQUIVALENCES_BASE}/`, {
    method: 'POST',
    token,
    json: payload,
  });
}

export async function updateModelEquivalence(
  id: number,
  payload: Partial<ModelEquivalenceInput>,
  token: string | null | undefined,
): Promise<ModelEquivalence> {
  return apiFetch<ModelEquivalence>(`${EQUIVALENCES_BASE}/${id}`, {
    method: 'PUT',
    token,
    json: payload,
  });
}

export async function deleteModelEquivalence(
  id: number,
  token: string | null | undefined,
): Promise<void> {
  await apiFetch<unknown>(`${EQUIVALENCES_BASE}/${id}`, { method: 'DELETE', token });
}
