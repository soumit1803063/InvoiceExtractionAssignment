import re
from collections.abc import Iterator, Sequence
from enum import StrEnum
from typing import (
    Annotated,
    Literal,
    Optional,
    Protocol,
    TypeVar,
    Union,
)

from sqlmodel import Field as Column
from sqlmodel import SQLModel

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
)

from .utils import Utils






def coerce_amount(value: object) -> Optional[int]:
    return Utils.parse_amount(value)


def coerce_date(value: object) -> Optional[str]:
    return Utils.parse_japanese_date(value)


def coerce_text(value: object) -> Optional[str]:
    return Utils.normalize_display_text(value) or None


def coerce_registration_number(value: object) -> Optional[str]:
    if value is None:
        return None
    found = re.search(r"T\d{13}", Utils.normalize_full_width_to_ascii(value))
    return found.group(0) if found else None


def coerce_identifier(value: object) -> Optional[str]:
    text = Utils.normalize_display_text(value)
    if not text:
        return None
    for separator in (":", "："):
        if separator in text:
            text = text.rsplit(separator, 1)[1]
    text = re.sub(r"[（(][^）)]*[）)]\s*$", "", text).strip()
    return text or None


def coerce_tax_code(value: object) -> Optional[str]:
    if value is None:
        return None
    text = Utils.normalize_full_width_to_ascii(value).strip().upper()
    if re.match(r"^T\d{2,}$", text):
        return text
    percent = Utils.parse_percent_value(text)
    if percent is None:
        percent = Utils.parse_amount(text)
    if percent is None:
        return None
    code = f"T{percent:02d}"
    return code if re.match(r"^T\d{2,}$", code) else None


def coerce_rate(value: object) -> object:
    if isinstance(value, bool):
        return value
    return float(value) if isinstance(value, int) else value


Amount = Annotated[Optional[StrictInt], BeforeValidator(coerce_amount)]
IsoDate = Annotated[Optional[StrictStr], BeforeValidator(coerce_date)]
DisplayText = Annotated[Optional[StrictStr], BeforeValidator(coerce_text)]
Identifier = Annotated[Optional[StrictStr], BeforeValidator(coerce_identifier)]
RegistrationNumber = Annotated[Optional[StrictStr], BeforeValidator(coerce_registration_number)]
TaxCode = Annotated[Optional[StrictStr], BeforeValidator(coerce_tax_code)]
Rate = Annotated[StrictFloat, BeforeValidator(coerce_rate)]
RawAmount = Optional[Union[StrictInt, StrictStr]]
RawText = Optional[StrictStr]


class SourceKind(StrEnum):
    TEXT_PDF = "text_pdf"
    IMAGE_PDF = "image_pdf"
    IMAGE = "image"


class IntakeError(Exception):

    def __init__(self, code: "ErrorCode", message: str, status: int = 0) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


class ErrorCode(StrEnum):
    ACCOUNTING_API_ERROR = "ACCOUNTING_API_ERROR"
    ACCOUNTING_API_UNREACHABLE = "ACCOUNTING_API_UNREACHABLE"
    CONTENT_REJECTED = "CONTENT_REJECTED"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    STRUCTURING_FAILED = "STRUCTURING_FAILED"
    TRANSCRIPTION_FAILED = "TRANSCRIPTION_FAILED"
    UNAUTHORIZED = "UNAUTHORIZED"
    VERIFICATION_BLOCKED = "VERIFICATION_BLOCKED"


class ErrorMessage(StrEnum):
    CROSSFOOT = "Line amounts do not add up to the printed subtotal"
    DATE_ORDER = "Due date {due_date} is earlier than issue date {issue_date}"
    DUPLICATE = "Same partner and invoice number were already read from document {document_id}"
    MISSING_REQUIRED_FIELDS = "Missing required fields: {names}"
    MISSING_TAX_CODE = "Missing tax code on: {names}"
    PARTNER_NOT_IN_MASTER = (
        "Supplier registration number does not match any partner in the accounting master"
    )
    PRINTED_TOTAL = "Recomputed total does not match the total printed on the document"
    TAX_RECOMPUTED = "Tax amount does not match the tax recalculated per tax code from the lines"
    TAX_CODE_NOT_ACCEPTED = "Tax code not accepted by the accounting system on: {names}"
    TOTAL_CONSISTENT = "Subtotal plus tax does not equal the total amount"

    CONTENT_REJECTED = "content_rejected: {detail}"
    UNREADABLE_DOCUMENT = "Could not read the document: {detail}"
    EMPTY_TRANSCRIPTION = "the transcriber returned no text for this page"
    NO_TRANSCRIBER = "no transcription provider is configured"
    PROCESSING_FAILED = "Reading the document failed: {detail}"
    PROCESSING_INTERRUPTED = "Reading was interrupted before it finished, so it was started again"
    UNUSABLE_RESPONSE = "the agent did not return an invoice"

    ACCOUNTING_REJECTED = "The accounting API rejected the request"
    MALFORMED_BODY = "The accounting API returned a body that is not JSON"
    UNREACHABLE = "The accounting API could not be reached"
    PARTNERS_UNAUTHORIZED = (
        "The accounting API rejected the configured API key, "
        "so the partner master could not be read"
    )
    PARTNERS_UNREACHABLE = (
        "The accounting API could not be reached, so the partner master could not be read"
    )

    DOCUMENT_NOT_FOUND = "No document with that id"
    PREVIEW_NOT_FOUND = "No preview available for that document"
    EMPTY_UPLOAD = "The uploaded file was empty"
    UNSUPPORTED_UPLOAD = "Only .pdf, .jpg, .jpeg and .png invoices are accepted"


class DocumentStatus(StrEnum):
    PROCESSING = "processing"
    NEEDS_REVIEW = "needs_review"
    READY = "ready"
    REGISTERED = "registered"
    REJECTED = "rejected"


class ResTaxRate(BaseModel):

    model_config = ConfigDict(frozen=True)

    code: StrictStr
    rate: Rate


class ResPartner(BaseModel):

    model_config = ConfigDict(frozen=True, extra="ignore")

    partner_code: StrictStr
    name: Optional[StrictStr] = None
    registration_no: Optional[StrictStr] = None
    aliases: list[StrictStr] = Field(default_factory=list)


class DbLineItem(BaseModel):

    model_config = ConfigDict(validate_assignment=True)

    description: DisplayText = None
    quantity: Amount = None
    unit: DisplayText = None
    unit_price: Amount = None
    amount: Amount = None
    tax_code: TaxCode = None


class DbInvoiceFields(BaseModel):

    model_config = ConfigDict(validate_assignment=True)

    partner_code: Identifier = None
    registration_number: RegistrationNumber = None
    supplier_name: DisplayText = None
    invoice_number: Identifier = None
    issue_date: IsoDate = None
    due_date: IsoDate = None
    currency: Literal["JPY"] = "JPY"
    subtotal: Amount = None
    tax_amount: Amount = None
    total_amount: Amount = None
    printed_total: Amount = None
    notes_excluded: DisplayText = None
    lines: list[DbLineItem] = Field(default_factory=list)


class DbVerification(BaseModel):

    model_config = ConfigDict(frozen=True)

    crossfoot_ok: StrictBool = False
    tax_ok: StrictBool = False
    total_ok: StrictBool = False
    printed_total_ok: StrictBool = False
    partner_matched: StrictBool = False
    duplicate_of: Optional[StrictStr] = None
    missing_required: list[StrictStr] = Field(default_factory=list)
    checks_passed: StrictInt = 0
    checks_total: StrictInt = 0


class DbRegistration(BaseModel):

    model_config = ConfigDict(frozen=True)

    attempted_at: StrictStr
    http_status: StrictInt
    accounting_id: Optional[StrictStr] = None
    error_code: Optional[StrictStr] = None
    error_message: Optional[StrictStr] = None


class DbDocument(BaseModel):

    model_config = ConfigDict(frozen=True)

    document_id: StrictStr
    created_at: StrictStr
    source_name: StrictStr
    source_kind: SourceKind
    fields: DbInvoiceFields
    verification: DbVerification
    status: DocumentStatus
    blocking_reasons: list[StrictStr] = Field(default_factory=list)
    registration: Optional[DbRegistration] = None


class DbStoredDocument(BaseModel):

    model_config = ConfigDict(frozen=True)

    document: DbDocument
    source_path: StrictStr
    created_at: StrictStr
    updated_at: StrictStr


class ReqRegistrationLine(BaseModel):

    model_config = ConfigDict(frozen=True)

    description: Optional[StrictStr] = None
    quantity: Optional[StrictInt] = None
    unit: Optional[StrictStr] = None
    unit_price: Optional[StrictInt] = None
    amount: Optional[StrictInt] = None
    tax_code: Optional[StrictStr] = None


class ReqRegistration(BaseModel):

    model_config = ConfigDict(frozen=True)

    partner_code: Optional[StrictStr] = None
    invoice_number: Optional[StrictStr] = None
    issue_date: Optional[StrictStr] = None
    due_date: Optional[StrictStr] = None
    currency: Literal["JPY"] = "JPY"
    lines: list[ReqRegistrationLine] = Field(default_factory=list)
    subtotal: Optional[StrictInt] = None
    tax_amount: Optional[StrictInt] = None
    total_amount: Optional[StrictInt] = None


class ResRegistrationReceipt(BaseModel):

    model_config = ConfigDict(frozen=True)

    accounting_id: Optional[StrictStr] = None
    http_status: StrictInt = 0


class AiLineItem(BaseModel):
    description: RawText = Field(
        None, description="品名・摘要 列に印字された品名。印字が無ければ null"
    )
    quantity: RawAmount = Field(
        None, description="数量 列の整数。印字が無ければ null。推測して埋めない"
    )
    unit: RawText = Field(
        None,
        description="単位 列に印字された文字をそのまま写す。例: 個 式 箱 本 袋 件 時間 セット。印字が無ければ null。推測して埋めない",
    )
    unit_price: RawAmount = Field(
        None, description="単価 列の整数。印字が無ければ null。推測して埋めない"
    )
    amount: RawAmount = Field(
        None,
        description="金額 列の整数。カンマや ¥ は取り除く。△ または ▲ が付く行は負の数にする",
    )
    tax_code: RawText = Field(
        None, description="税率 10% の行は T10、8% の行は T08。判断できなければ null"
    )


class AiTaxRow(BaseModel):
    percent: RawAmount = Field(
        None, description="消費税の行に印字された税率の数値。10% なら 10、8% なら 8"
    )
    taxable_amount: RawAmount = Field(
        None, description="消費税の行の（対象 ...）に印字された、その税率の対象金額"
    )
    tax_amount: RawAmount = Field(None, description="その税率で計算された消費税額")


class AiInvoice(BaseModel):
    registration_number: RawText = Field(
        None, description="登録番号。T で始まる13桁の数字。無ければ null"
    )
    supplier_name: RawText = Field(
        None, description="請求元の会社名。御中 が付く受取側の会社名ではない"
    )
    invoice_number: RawText = Field(
        None, description="請求書番号の値だけ。ラベルは含めない"
    )
    issue_date: RawText = Field(
        None, description="発行日。YYYY-MM-DD。令和N年は西暦 N+2018 年に直す"
    )
    due_date: RawText = Field(
        None, description="お支払期日。YYYY-MM-DD。令和N年は西暦 N+2018 年に直す"
    )
    subtotal: RawAmount = Field(None, description="小計。税抜の合計金額")
    tax_amount: RawAmount = Field(
        None, description="消費税額。消費税の行が複数ある場合はその合算値"
    )
    total_amount: RawAmount = Field(None, description="合計。税込の合計金額")
    printed_total: RawAmount = Field(
        None, description="御請求金額 などの枠に印字された税込金額"
    )
    notes_excluded: RawText = Field(
        None,
        description="手書きの書き込みや欄外の注記など、構造化データに含めなかった内容をそのまま書き写す。無ければ null",
    )
    tax_rows: list[AiTaxRow] = Field(
        default_factory=list,
        description="消費税の行を税率ごとに書き出す。例: 消費税 8%（対象 103,200） 8,256",
    )
    lines: list[AiLineItem] = Field(
        default_factory=list,
        description="明細行。小計・消費税・合計 の行は含めない",
    )


class MdPageImage(BaseModel):

    model_config = ConfigDict(frozen=True)

    page_number: StrictInt
    media_type: StrictStr
    content: bytes


class MdTaxBreakdown(BaseModel):

    model_config = ConfigDict(frozen=True)

    total_tax: Optional[StrictInt] = None
    codes_by_amount: tuple[tuple[StrictInt, StrictStr], ...] = Field(default_factory=tuple)
    fallback_code: Optional[StrictStr] = None


class MdExtractionResult(BaseModel):

    model_config = ConfigDict(frozen=True)
    
    fields: DbInvoiceFields = Field(default_factory=DbInvoiceFields)
    error_message: StrictStr = ""


class MdRuleOutcome(BaseModel):

    model_config = ConfigDict(frozen=True)

    code: StrictStr
    passed: StrictBool
    scored: StrictBool
    reason: Optional[StrictStr] = None
    details: tuple[StrictStr, ...] = Field(default_factory=tuple)


class MdVerificationReport(BaseModel):

    model_config = ConfigDict(frozen=True)

    outcomes: tuple[MdRuleOutcome, ...] = Field(default_factory=tuple)
    duplicate_of: Optional[StrictStr] = None


class ResHealth(BaseModel):

    model_config = ConfigDict(frozen=True)

    status: StrictStr
    accounting_api_reachable: StrictBool


class ResDocumentList(BaseModel):

    model_config = ConfigDict(frozen=True)

    documents: list[DbDocument]


class ResReferenceData(BaseModel):

    model_config = ConfigDict(frozen=True)

    partners: list[ResPartner] = Field(default_factory=list)
    tax_rates: list[ResTaxRate] = Field(default_factory=list)
    reachable: StrictBool = False
    lookup_failure_reason: StrictStr = ""


class ReqFieldsUpdate(BaseModel):

    model_config = ConfigDict(frozen=True)

    fields: DbInvoiceFields


class ResRegister(BaseModel):

    model_config = ConfigDict(frozen=True)

    document: DbDocument
    registration: DbRegistration



class TaxRateTable:

    def __init__(self, rates: Sequence[ResTaxRate] = ()) -> None:
        self._rates = tuple(rates)

    def __bool__(self) -> bool:
        return bool(self._rates)

    def __iter__(self) -> Iterator[ResTaxRate]:
        return iter(self._rates)

    @property
    def codes(self) -> tuple[str, ...]:
        return tuple(rate.code for rate in self._rates)

    def contains(self, code: Optional[str]) -> bool:
        return code in self.codes

    def rate_for(self, code: Optional[str]) -> Optional[float]:
        for rate in self._rates:
            if rate.code == code:
                return rate.rate
        return None


class PartnerDirectory:

    def __init__(self, partners: Sequence[ResPartner] = ()) -> None:
        self._partners = tuple(partners)

    def __iter__(self) -> Iterator[ResPartner]:
        return iter(self._partners)

    @property
    def is_empty(self) -> bool:
        return not self._partners

    def by_registration_number(self, registration_number: Optional[str]) -> Optional[ResPartner]:
        if not registration_number:
            return None
        for partner in self._partners:
            if partner.registration_no == registration_number:
                return partner
        return None

    def by_code(self, partner_code: Optional[str]) -> Optional[ResPartner]:
        if not partner_code:
            return None
        for partner in self._partners:
            if partner.partner_code == partner_code:
                return partner
        return None

    def match(self, fields: DbInvoiceFields) -> Optional[ResPartner]:
        return self.by_registration_number(fields.registration_number) or self.by_code(
            fields.partner_code
        )


class MdVerificationContext(BaseModel):

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    fields: DbInvoiceFields
    tax_table: TaxRateTable = Field(default_factory=TaxRateTable)
    partner_matched: StrictBool = False
    duplicate_of: Optional[StrictStr] = None
    partner_lookup_reason: StrictStr = ""


TEntity = TypeVar("TEntity")
TKey = TypeVar("TKey")


class IRepository(Protocol[TEntity, TKey]):

    def get(self, key: TKey) -> Optional[TEntity]:
        ...

    def list_all(self) -> Sequence[TEntity]:
        ...

    def save(self, entity: TEntity) -> None:
        ...


class IDocumentRepository(IRepository[DbStoredDocument, str], Protocol):

    def find_duplicate(
        self, partner_code: Optional[str], invoice_number: Optional[str], exclude_document_id: Optional[str]
    ) -> Optional[str]:
        ...

    def find_by_source_path(self, source_path: str) -> Optional[DbStoredDocument]:
        ...


class IAccountingGateway(Protocol):

    def is_reachable(self) -> bool:
        ...

    def fetch_partners(self) -> PartnerDirectory:
        ...

    def fetch_tax_rates(self) -> TaxRateTable:
        ...

    def register_invoice(self, request: ReqRegistration) -> ResRegistrationReceipt:
        ...


class ITranscriber(Protocol):

    def to_markdown(self, page: MdPageImage) -> str:
        ...


class DbDocumentRow(SQLModel, table=True):

    __tablename__ = "documents"

    document_id: StrictStr = Column(primary_key=True)
    created_at: StrictStr
    updated_at: StrictStr
    source_name: StrictStr
    source_path: StrictStr = Column(index=True)
    source_kind: StrictStr
    partner_code: Optional[StrictStr] = Column(default=None, index=True)
    invoice_number: Optional[StrictStr] = Column(default=None, index=True)
    fields_json: StrictStr
    verification_json: StrictStr
    status: StrictStr
    blocking_reasons_json: StrictStr
    registration_json: Optional[StrictStr] = Column(default=None)

