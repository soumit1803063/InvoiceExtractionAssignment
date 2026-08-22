from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr
from sqlmodel import Field as Column
from sqlmodel import SQLModel
from .enums import DocumentStatus, SourceKind
from .fields import Amount, DisplayText, Identifier, IsoDate, RegistrationNumber, TaxCode


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
