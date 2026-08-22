from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr
from .db import DbInvoiceFields


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


class ReqFieldsUpdate(BaseModel):

    model_config = ConfigDict(frozen=True)

    fields: DbInvoiceFields
