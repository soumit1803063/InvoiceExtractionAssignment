from typing import Optional, Union
import threading
import uuid
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from ..core import (
    DbDocument,
    ErrorCode,
    ErrorMessage,
    IntakeError,
    DbInvoiceFields,
    DbRegistration,
    DbStoredDocument,
    DbVerification,
    DocumentStatus,
    IDocumentRepository,
    MdVerificationContext,
    PartnerDirectory,
    SourceKind,
    TaxRateTable,
    Utils,
)
from ..settings import Settings
from .accounting_service import ReferenceDataProvider, ReqRegistrationFactory
from .extraction import SUPPORTED_SUFFIXES, ExtractionService
from .validation import ReportReader, VerificationService

PathLike = Union[Path, str]
Preview = tuple[Path, str]


class DocumentPolicy:

    @staticmethod
    def registration_succeeded(registration: Optional[DbRegistration]) -> bool:
        return registration is not None and bool(registration.accounting_id)

    @staticmethod
    def registration_rejected(registration: Optional[DbRegistration]) -> bool:
        return registration is not None and registration.http_status >= 400

    @staticmethod
    def resolve_status(
        blocking_reasons: Sequence[str], registration: Optional[DbRegistration]
    ) -> DocumentStatus:
        if registration is not None:
            if DocumentPolicy.registration_succeeded(registration):
                return DocumentStatus.REGISTERED
            if DocumentPolicy.registration_rejected(registration):
                return DocumentStatus.REJECTED
        return DocumentStatus.NEEDS_REVIEW if blocking_reasons else DocumentStatus.READY

    @staticmethod
    def is_registered(document: DbDocument) -> bool:
        return DocumentPolicy.registration_succeeded(document.registration)

    @staticmethod
    def refusal_reason(document: DbDocument) -> str:
        return "; ".join(document.blocking_reasons)


class InvoiceIntakeService:

    def __init__(
        self,
        settings: Settings,
        repository: IDocumentRepository,
        reference_data: ReferenceDataProvider,
        extraction: ExtractionService,
        verification: VerificationService,
    ) -> None:
        self._settings = settings
        self._repository = repository
        self._reference_data = reference_data
        self._extraction = extraction
        self._verification = verification
        self._registration_lock = threading.Lock()

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _new_document_id() -> str:
        return str(uuid.uuid4())

    def partners(self) -> PartnerDirectory:
        return self._reference_data.partners()

    @property
    def lookup_failure_reason(self) -> str:
        return self._reference_data.lookup_failure_reason

    def tax_table(self) -> TaxRateTable:
        return self._reference_data.tax_table()

    def list_documents(self) -> list[DbDocument]:
        return [stored.document for stored in self._repository.list_all()]

    def get_document(self, document_id: str) -> Optional[DbDocument]:
        stored = self._repository.get(document_id)
        return stored.document if stored else None

    def upload(self, file_name: str, content: bytes) -> DbDocument:
        directory = Path(self._settings.invoice_directory)
        directory.mkdir(parents=True, exist_ok=True)
        target = Utils.unique_path(directory, file_name)
        target.write_bytes(content)
        return self._enqueue(target)

    def _enqueue(self, path: PathLike) -> DbDocument:
        resolved = str(Path(path).resolve())
        existing = self._repository.find_by_source_path(resolved)
        if existing is not None:
            return existing.document
        timestamp = self._utc_now_iso()
        document = DbDocument(
            document_id=self._new_document_id(),
            created_at=timestamp,
            source_name=Path(path).name,
            source_kind=self._extraction.classify(path),
            fields=DbInvoiceFields(),
            verification=DbVerification(),
            status=DocumentStatus.PROCESSING,
        )
        self._repository.save(
            DbStoredDocument(
                document=document,
                source_path=resolved,
                created_at=timestamp,
                updated_at=timestamp,
            )
        )
        self._start_processing(document.document_id)
        return document

    def _start_processing(self, document_id: str) -> None:
        worker = threading.Thread(target=self._run_processing, args=(document_id,), daemon=True)
        worker.start()

    def _run_processing(self, document_id: str) -> None:
        try:
            self._process(document_id)
        except Exception as error:
            self._record_processing_failure(document_id, error)

    def _record_processing_failure(self, document_id: str, error: Exception) -> None:
        stored = self._repository.get(document_id)
        if stored is None:
            return
        self._rebuild_and_save(
            stored,
            stored.document.fields,
            stored.document.registration,
            extra_reasons=[ErrorMessage.PROCESSING_FAILED.format(detail=error)],
        )

    def restart_stranded(self) -> list[DbDocument]:
        stranded = [
            stored.document
            for stored in self._repository.list_all()
            if stored.document.status == DocumentStatus.PROCESSING
        ]
        for document in stranded:
            self._start_processing(document.document_id)
        return stranded

    def _process(self, document_id: str) -> Optional[DbDocument]:
        stored = self._repository.get(document_id)
        if stored is None:
            return None
        outcome = self._extraction.extract(stored.source_path)
        reasons = [outcome.error_message] if outcome.error_message else []
        previous = stored.document.registration
        kept = previous if DocumentPolicy.registration_succeeded(previous) else None
        document = self._rebuild_and_save(stored, outcome.fields, kept, extra_reasons=reasons)
        return self._register_when_clean(document)

    def reprocess(self, document_id: str) -> Optional[DbDocument]:
        stored = self._repository.get(document_id)
        if stored is None:
            return None
        document = stored.document.model_copy(
            update={"status": DocumentStatus.PROCESSING, "blocking_reasons": []}
        )
        self._repository.save(
            stored.model_copy(update={"document": document, "updated_at": self._utc_now_iso()})
        )
        self._start_processing(document_id)
        return document

    def scan(self) -> list[DbDocument]:
        self._reference_data.refresh(force=True)
        for path in Utils.iter_files_with_suffixes(
            self._settings.invoice_directory, SUPPORTED_SUFFIXES
        ):
            self._enqueue(path)
        return self.list_documents()

    def _build_document(
        self,
        document_id: str,
        created_at: str,
        source_name: str,
        source_kind: SourceKind,
        fields: DbInvoiceFields,
        registration: Optional[DbRegistration],
        extra_reasons: Sequence[str] = (),
    ) -> DbDocument:
        partner, fields = self._reference_data.resolve_partner(fields)
        duplicate_of = self._repository.find_duplicate(
            fields.partner_code, fields.invoice_number, document_id
        )
        report = self._verification.verify(
            MdVerificationContext(
                fields=fields,
                tax_table=self._reference_data.tax_table(),
                partner_matched=partner is not None,
                duplicate_of=duplicate_of,
                partner_lookup_reason=self._reference_data.lookup_failure_reason,
            )
        )
        blocking_reasons = list(extra_reasons) + ReportReader.blocking_reasons(report)
        return DbDocument(
            document_id=document_id,
            created_at=created_at,
            source_name=source_name,
            source_kind=source_kind,
            fields=fields,
            verification=ReportReader.to_verification(report),
            status=DocumentPolicy.resolve_status(blocking_reasons, registration),
            blocking_reasons=blocking_reasons,
            registration=registration,
        )

    def _rebuild_and_save(
        self,
        stored: DbStoredDocument,
        fields: DbInvoiceFields,
        registration: Optional[DbRegistration],
        extra_reasons: Sequence[str] = (),
    ) -> DbDocument:
        previous = stored.document
        document = self._build_document(
            document_id=previous.document_id,
            created_at=previous.created_at,
            source_name=previous.source_name,
            source_kind=previous.source_kind,
            fields=fields,
            registration=registration,
            extra_reasons=extra_reasons,
        )
        self._repository.save(
            DbStoredDocument(
                document=document,
                source_path=stored.source_path,
                created_at=stored.created_at,
                updated_at=self._utc_now_iso(),
            )
        )
        return document

    def update_fields(self, document_id: str, fields: DbInvoiceFields) -> Optional[DbDocument]:
        stored = self._repository.get(document_id)
        if stored is None:
            return None
        previous = stored.document.registration
        kept = previous if DocumentPolicy.registration_succeeded(previous) else None
        document = self._rebuild_and_save(stored, fields, kept)
        return self._register_when_clean(document)

    def _register_when_clean(self, document: DbDocument) -> DbDocument:
        if document.blocking_reasons or DocumentPolicy.is_registered(document):
            return document
        outcome = self.register(document.document_id)
        return outcome[0] if outcome else document

    def register(self, document_id: str) -> Optional[tuple[DbDocument, DbRegistration]]:
        stored = self._repository.get(document_id)
        if stored is None:
            return None
        previous = stored.document
        if DocumentPolicy.is_registered(previous):
            return previous, previous.registration
        if previous.blocking_reasons:
            registration = DbRegistration(
                attempted_at=self._utc_now_iso(),
                http_status=0,
                error_code=ErrorCode.VERIFICATION_BLOCKED,
                error_message=DocumentPolicy.refusal_reason(previous),
            )
        else:
            registration = self._send_registration(previous.fields)
        document = self._rebuild_and_save(stored, previous.fields, registration)
        return document, registration

    def _send_registration(self, fields: DbInvoiceFields) -> DbRegistration:
        attempted_at = self._utc_now_iso()
        request = ReqRegistrationFactory.of(fields)
        try:
            with self._registration_lock:
                receipt = self._reference_data.gateway.register_invoice(request)
        except IntakeError as error:
            return DbRegistration(
                attempted_at=attempted_at,
                http_status=error.status,
                error_code=error.code,
                error_message=error.message,
            )
        return DbRegistration(
            attempted_at=attempted_at,
            http_status=receipt.http_status,
            accounting_id=receipt.accounting_id,
        )

    def preview(self, document_id: str) -> Optional[Preview]:
        stored = self._repository.get(document_id)
        if stored is None:
            return None
        path = Path(stored.source_path)
        if not path.is_file():
            return None
        return path, Utils.media_type_for_path(path)
