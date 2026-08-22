import type { Words } from '../i18n';
import type { InvoiceFields, InvoiceFieldsUpdate, LineItem, TaxCode } from '../types/contract';
import { isIntegerInputValid, isIsoDateValid, nullableToText, parseIntegerOrNull, textToNullableString } from '../utils/parsing';

export interface EditableInvoiceLine {
  description: string;
  quantity: string;
  unit: string;
  unit_price: string;
  amount: string;
  tax_code: TaxCode | '';
}

export interface EditableInvoice {
  partner_code: string;
  registration_number: string;
  supplier_name: string;
  invoice_number: string;
  issue_date: string;
  due_date: string;
  subtotal: string;
  tax_amount: string;
  total_amount: string;
  printed_total: string;
  lines: EditableInvoiceLine[];
}

export type EditableInvoiceScalarKey = Exclude<keyof EditableInvoice, 'lines'>;

export interface EditableFieldDescriptor {
  key: EditableInvoiceScalarKey;
  word: keyof Words;
}

export const EDITABLE_TEXT_FIELD_LABELS: EditableFieldDescriptor[] = [
  { key: 'supplier_name', word: 'supplierName' },
  { key: 'partner_code', word: 'partnerCode' },
  { key: 'registration_number', word: 'registrationNumber' },
  { key: 'invoice_number', word: 'invoiceNumber' }
];

export const EDITABLE_DATE_FIELD_LABELS: EditableFieldDescriptor[] = [
  { key: 'issue_date', word: 'issueDate' },
  { key: 'due_date', word: 'dueDate' }
];

export const EDITABLE_MONEY_FIELD_LABELS: EditableFieldDescriptor[] = [
  { key: 'subtotal', word: 'subtotal' },
  { key: 'tax_amount', word: 'tax' },
  { key: 'total_amount', word: 'totalAmount' },
  { key: 'printed_total', word: 'printedTotal' }
];

export function toEditableLine(line: LineItem): EditableInvoiceLine {
  return {
    description: nullableToText(line.description),
    quantity: nullableToText(line.quantity),
    unit: nullableToText(line.unit),
    unit_price: nullableToText(line.unit_price),
    amount: nullableToText(line.amount),
    tax_code: line.tax_code ?? ''
  };
}

export function createEmptyEditableLine(): EditableInvoiceLine {
  return { description: '', quantity: '', unit: '', unit_price: '', amount: '', tax_code: '' };
}

export function toEditableInvoice(fields: InvoiceFields): EditableInvoice {
  return {
    partner_code: nullableToText(fields.partner_code),
    registration_number: nullableToText(fields.registration_number),
    supplier_name: nullableToText(fields.supplier_name),
    invoice_number: nullableToText(fields.invoice_number),
    issue_date: nullableToText(fields.issue_date),
    due_date: nullableToText(fields.due_date),
    subtotal: nullableToText(fields.subtotal),
    tax_amount: nullableToText(fields.tax_amount),
    total_amount: nullableToText(fields.total_amount),
    printed_total: nullableToText(fields.printed_total),
    lines: (fields.lines ?? []).map(toEditableLine)
  };
}

export function toContractInvoiceFields(editable: EditableInvoice): InvoiceFieldsUpdate {
  return {
    partner_code: textToNullableString(editable.partner_code),
    registration_number: textToNullableString(editable.registration_number),
    supplier_name: textToNullableString(editable.supplier_name),
    invoice_number: textToNullableString(editable.invoice_number),
    issue_date: textToNullableString(editable.issue_date),
    due_date: textToNullableString(editable.due_date),
    currency: 'JPY',
    subtotal: parseIntegerOrNull(editable.subtotal),
    tax_amount: parseIntegerOrNull(editable.tax_amount),
    total_amount: parseIntegerOrNull(editable.total_amount),
    printed_total: parseIntegerOrNull(editable.printed_total),
    lines: editable.lines.map((line) => ({
      description: textToNullableString(line.description),
      quantity: parseIntegerOrNull(line.quantity),
      unit: textToNullableString(line.unit),
      unit_price: parseIntegerOrNull(line.unit_price),
      amount: parseIntegerOrNull(line.amount),
      tax_code: line.tax_code === '' ? null : line.tax_code
    }))
  };
}

export function countLinesMissingUnit(editable: EditableInvoice): number {
  return editable.lines.filter((line) => line.unit.trim() === '').length;
}

export function collectDraftProblems(editable: EditableInvoice, words: Words): string[] {
  const problems: string[] = [];
  for (const field of EDITABLE_MONEY_FIELD_LABELS) {
    if (!isIntegerInputValid(editable[field.key])) {
      problems.push(`${words[field.word]} ${words.mustBeWholeYen}`);
    }
  }
  for (const field of EDITABLE_DATE_FIELD_LABELS) {
    if (!isIsoDateValid(editable[field.key])) {
      problems.push(`${words[field.word]} ${words.mustBeIsoDate}`);
    }
  }
  editable.lines.forEach((line, index) => {
    const position = index + 1;
    if (!isIntegerInputValid(line.quantity)) {
      problems.push(`${words.lineNumber} ${position}: ${words.quantity} ${words.mustBeWholeYen}`);
    }
    if (!isIntegerInputValid(line.unit_price)) {
      problems.push(`${words.lineNumber} ${position}: ${words.unitPrice} ${words.mustBeWholeYen}`);
    }
    if (!isIntegerInputValid(line.amount)) {
      problems.push(`${words.lineNumber} ${position}: ${words.amount} ${words.mustBeWholeYen}`);
    }
  });
  return problems;
}

export function hasDraftChanged(editable: EditableInvoice, original: InvoiceFields): boolean {
  return JSON.stringify(toContractInvoiceFields(editable)) !== JSON.stringify(normalizeContractFields(original));
}

function normalizeContractFields(fields: InvoiceFields): InvoiceFieldsUpdate {
  return toContractInvoiceFields(toEditableInvoice(fields));
}
