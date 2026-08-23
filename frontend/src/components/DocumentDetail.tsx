import { useState } from 'react';
import { saveDocumentFields } from '../api/documents';
import {
  EDITABLE_DATE_FIELD_LABELS,
  EDITABLE_MONEY_FIELD_LABELS,
  EDITABLE_TEXT_FIELD_LABELS,
  collectDraftProblems,
  countLinesMissingUnit,
  createEmptyEditableLine,
  hasDraftChanged,
  toContractInvoiceFields,
  toEditableInvoice
} from '../model/invoiceDraft';
import type { EditableInvoice, EditableInvoiceLine, EditableInvoiceScalarKey } from '../model/invoiceDraft';
import { useWords } from '../i18n';
import type { InvoiceDocument } from '../types/contract';
import { isIntegerInputValid, isIsoDateValid } from '../utils/parsing';
import { AccountingReference } from './AccountingReference';
import { EditableTextField } from './EditableTextField';
import { LineItemsTable } from './LineItemsTable';
import { MessageBanner } from './MessageBanner';
import { SourcePreview } from './SourcePreview';
import { StatusBadge } from './StatusBadge';
import { VerificationPanel } from './VerificationPanel';

interface DocumentDetailProps {
  document: InvoiceDocument;
  duplicateSourceName: string | null;
  onDocumentUpdated: (updatedDocument: InvoiceDocument) => void;
}

export function DocumentDetail({ document, duplicateSourceName, onDocumentUpdated }: DocumentDetailProps) {
  const [draft, setDraft] = useState<EditableInvoice>(() => toEditableInvoice(document.fields));
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [wasSaved, setWasSaved] = useState(false);
  const words = useWords();

  const isProcessing = document.status === 'processing';
  const isRegistered = document.status === 'registered';
  const isReadOnly = isProcessing || isRegistered;
  const draftProblems = collectDraftProblems(draft, words);
  const hasUnsavedChanges = hasDraftChanged(draft, document.fields);
  const missingUnitCount = countLinesMissingUnit(draft);
  const canSave = hasUnsavedChanges && draftProblems.length === 0 && !isSaving && !isReadOnly;

  function updateScalarField(fieldKey: EditableInvoiceScalarKey, nextValue: string) {
    setWasSaved(false);
    setDraft((current) => ({ ...current, [fieldKey]: nextValue }));
  }

  function updateLineField(lineIndex: number, fieldKey: keyof EditableInvoiceLine, nextValue: string) {
    setWasSaved(false);
    setDraft((current) => ({
      ...current,
      lines: current.lines.map((line, index) => (index === lineIndex ? { ...line, [fieldKey]: nextValue } : line))
    }));
  }

  function addLine() {
    setWasSaved(false);
    setDraft((current) => ({ ...current, lines: [...current.lines, createEmptyEditableLine()] }));
  }

  function removeLine(lineIndex: number) {
    setWasSaved(false);
    setDraft((current) => ({ ...current, lines: current.lines.filter((_, index) => index !== lineIndex) }));
  }

  function revertDraft() {
    setWasSaved(false);
    setSaveError(null);
    setDraft(toEditableInvoice(document.fields));
  }

  async function saveDraft() {
    setIsSaving(true);
    setSaveError(null);
    setWasSaved(false);
    try {
      const updatedDocument = await saveDocumentFields(document.document_id, toContractInvoiceFields(draft));
      onDocumentUpdated(updatedDocument);
      setDraft(toEditableInvoice(updatedDocument.fields));
      setWasSaved(true);
    } catch (cause) {
      setSaveError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setIsSaving(false);
    }
  }


  return (
    <div className="detail">
      <header className="detail__header">
        <div className="detail__identity">
          <h1 className="detail__title">{document.source_name}</h1>
          <p className="detail__meta">
            <StatusBadge status={document.status} />
            <span className="detail__hash" title={document.document_id}>
              {document.document_id.slice(0, 12)}
            </span>
          </p>
        </div>
        <div className="detail__actions">
          {isRegistered ? null : (
            <>
              {hasUnsavedChanges && !isReadOnly ? <span className="detail__dirty">{words.unsavedCorrections}</span> : null}
              <button type="button" className="button button--ghost" onClick={revertDraft} disabled={!hasUnsavedChanges || isSaving}>
                {words.revert}
              </button>
              <button type="button" className="button button--primary" onClick={saveDraft} disabled={!canSave}>
                {isSaving ? words.saving : words.saveAndRevalidate}
              </button>
            </>
          )}
        </div>
      </header>

      {isProcessing ? (
        <MessageBanner tone="info" title={words.stillBeingRead}>
          <p>
            {words.pageBeingTranscribedStructuredFields}
          </p>
        </MessageBanner>
      ) : null}


      {saveError ? (
        <MessageBanner tone="danger" title={words.correctionsWereNotSaved}>
          <p>{saveError}</p>
        </MessageBanner>
      ) : null}

      {wasSaved && !hasUnsavedChanges ? (
        <MessageBanner tone="success" title={words.correctionsSavedVerificationReRun} />
      ) : null}

      {document.extra_failures.length > 0 ? (
        <MessageBanner tone="danger" title={words.otherFailures}>
          <p>{words.otherFailuresExplained}</p>
          <ul className="banner__list">
            {document.extra_failures.map((failure) => (
              <li key={failure}>{failure}</li>
            ))}
          </ul>
        </MessageBanner>
      ) : null}

      {draftProblems.length > 0 ? (
        <MessageBanner tone="warning" title={words.fixTheseBeforeSaving}>
          <ul className="banner__list">
            {draftProblems.map((problem) => (
              <li key={problem}>{problem}</li>
            ))}
          </ul>
        </MessageBanner>
      ) : null}

      {document.input_tokens > 0 || document.output_tokens > 0 ? (
        <section className="panel panel--usage">
          <header className="panel__header">
            <h2 className="panel__title">{words.tokensUsed}</h2>
          </header>
          <dl className="usage">
            <div className="usage__item">
              <dt>{words.modelUsed}</dt>
              <dd><code>{document.model_used || '—'}</code></dd>
            </div>
            <div className="usage__item">
              <dt>{words.inputTokens}</dt>
              <dd>{document.input_tokens.toLocaleString()}</dd>
            </div>
            <div className="usage__item">
              <dt>{words.outputTokens}</dt>
              <dd>{document.output_tokens.toLocaleString()}</dd>
            </div>
          </dl>
        </section>
      ) : null}

      <div className="detail__columns">
        <div className="detail__column detail__column--source">
          <SourcePreview documentId={document.document_id} sourceName={document.source_name} />
        </div>

        <div className="detail__column detail__column--data">
          <section className="panel">
            <header className="panel__header">
              <h2 className="panel__title">
                {words.invoiceFields}
              </h2>
              <span className="panel__summary">{words.currency}: JPY</span>
            </header>

            <div className="field-grid">
              {EDITABLE_TEXT_FIELD_LABELS.map((field) => (
                <EditableTextField
                  key={field.key}
                  label={words[field.word]}
                  value={draft[field.key]}
                  isDisabled={isReadOnly}
                  onValueChange={(nextValue) => updateScalarField(field.key, nextValue)}
                />
              ))}
              {EDITABLE_DATE_FIELD_LABELS.map((field) => (
                <EditableTextField
                  key={field.key}
                  label={words[field.word]}
                  value={draft[field.key]}
                  placeholder="YYYY-MM-DD"
                  isDisabled={isReadOnly}
                  isInvalid={!isIsoDateValid(draft[field.key])}
                  invalidMessage="Use YYYY-MM-DD"
                  onValueChange={(nextValue) => updateScalarField(field.key, nextValue)}
                />
              ))}
              {EDITABLE_MONEY_FIELD_LABELS.map((field) => (
                <EditableTextField
                  key={field.key}
                  label={`${words[field.word]} (JPY)`}
                  value={draft[field.key]}
                  isDisabled={isReadOnly}
                  alignEnd
                  isInvalid={!isIntegerInputValid(draft[field.key])}
                  invalidMessage="Whole yen only, no decimals"
                  onValueChange={(nextValue) => updateScalarField(field.key, nextValue)}
                />
              ))}
            </div>
          </section>

          <LineItemsTable
            lines={draft.lines}
            subtotalText={draft.subtotal}
            isDisabled={isReadOnly}
            onLineFieldChange={updateLineField}
            onAddLine={addLine}
            onRemoveLine={removeLine}
          />


          {missingUnitCount > 0 && !isReadOnly ? (
            <MessageBanner tone="warning" title={`${missingUnitCount} ${words.unitsStillToFill}`}>
              <p>{words.registrationStaysBlockedUntilEvery}</p>
            </MessageBanner>
          ) : null}

          <AccountingReference fields={document.fields} />

          <VerificationPanel
            verification={document.verification}
            blockingReasons={document.blocking_reasons}
            fields={document.fields}
            duplicateSourceName={duplicateSourceName}
          />
        </div>
      </div>
    </div>
  );
}
