
export type DocumentStatus = 'processing' | 'needs_review' | 'ready' | 'registered' | 'rejected';

export type TaxCode = string;

export interface LineItem {
  description: string | null;
  quantity: number | null;
  unit: string | null;
  unit_price: number | null;
  amount: number | null;
  tax_code: TaxCode | null;
}

export interface InvoiceFields {
  partner_code: string | null;
  registration_number: string | null;
  supplier_name: string | null;
  invoice_number: string | null;
  issue_date: string | null;
  due_date: string | null;
  currency: 'JPY';
  subtotal: number | null;
  tax_amount: number | null;
  total_amount: number | null;
  printed_total: number | null;
  lines: LineItem[];
  notes_excluded: string | null;
}

export type InvoiceFieldsUpdate = Omit<InvoiceFields, 'notes_excluded'>;

export interface Verification {
  crossfoot_ok: boolean;
  tax_ok: boolean;
  total_ok: boolean;
  printed_total_ok: boolean;
  partner_matched: boolean;
  duplicate_of: string | null;
  missing_required: string[];
  checks_passed: number;
  checks_total: number;
}

export interface Registration {
  attempted_at: string;
  http_status: number;
  accounting_id: string | null;
  error_code: string | null;
  error_message: string | null;
}

export interface InvoiceDocument {
  document_id: string;
  created_at: string;
  source_name: string;
  fields: InvoiceFields;
  verification: Verification;
  status: DocumentStatus;
  blocking_reasons: string[];
  extra_failures: string[];
  model_used: string;
  input_tokens: number;
  output_tokens: number;
  registration: Registration | null;
}

export interface DocumentListResponse {
  documents: InvoiceDocument[];
}

export interface StartOverResult {
  unregistered: number;
  documents_cleared: number;
  still_registered: number;
}


export interface HealthResponse {
  status: string;
  accounting_api_reachable: boolean;
}

export interface Partner {
  partner_code: string;
  name: string | null;
  registration_no: string | null;
  aliases: string[];
}

export interface TaxRate {
  code: string;
  rate: number;
}

export interface ReferenceData {
  partners: Partner[];
  tax_rates: TaxRate[];
  reachable: boolean;
  lookup_failure_reason: string;
}
