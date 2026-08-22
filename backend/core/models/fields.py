import re
from typing import Annotated, Optional, Union
from pydantic import BeforeValidator, StrictFloat, StrictInt, StrictStr
from ..utils import Utils


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
