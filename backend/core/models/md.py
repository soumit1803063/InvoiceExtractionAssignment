from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr
from .db import DbInvoiceFields


class MdPage(BaseModel):

    model_config = ConfigDict(frozen=True)

    page_number: StrictInt
    media_type: StrictStr
    content: bytes


class MdTaxBreakdown(BaseModel):

    model_config = ConfigDict(frozen=True)

    total_tax: Optional[StrictInt] = None
    codes_by_amount: tuple[tuple[StrictInt, StrictStr], ...] = Field(default_factory=tuple)
    fallback_code: Optional[StrictStr] = None


class MdModelUsage(BaseModel):

    model_config = ConfigDict(frozen=True)

    model_used: StrictStr = ""
    input_tokens: StrictInt = 0
    output_tokens: StrictInt = 0


class MdExtractionResult(BaseModel):

    model_config = ConfigDict(frozen=True)
    
    fields: DbInvoiceFields = Field(default_factory=DbInvoiceFields)
    error_message: StrictStr = ""
    model_used: StrictStr = ""
    input_tokens: StrictInt = 0
    output_tokens: StrictInt = 0


class MdRuleOutcome(BaseModel):

    model_config = ConfigDict(frozen=True)

    code: StrictStr
    passed: StrictBool
    scored: StrictBool
    reason: Optional[StrictStr] = None
    details: tuple[StrictStr, ...] = Field(default_factory=tuple)


