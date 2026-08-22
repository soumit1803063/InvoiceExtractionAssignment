from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr
from .db import DbInvoiceFields


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
