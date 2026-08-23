from collections.abc import Iterator, Sequence
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr
from ..utils import Utils
from .db import DbDocument, DbInvoiceFields
from .fields import Rate


MINIMUM_ALIAS_LENGTH = 3


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


class ResRegistrationReceipt(BaseModel):

    model_config = ConfigDict(frozen=True)

    accounting_id: Optional[StrictStr] = None
    http_status: StrictInt = 0


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

    def by_printed_name(self, supplier_name: Optional[str]) -> Optional[ResPartner]:
        printed = PartnerDirectory._comparable(supplier_name)
        if not printed:
            return None
        exact = [
            partner
            for partner in self._partners
            if printed in PartnerDirectory._known_names(partner)
        ]
        if len(exact) == 1:
            return exact[0]
        contained = [
            partner
            for partner in self._partners
            if any(
                len(name) >= MINIMUM_ALIAS_LENGTH and name in printed
                for name in PartnerDirectory._known_names(partner)
            )
        ]
        return contained[0] if len(contained) == 1 else None

    def match(self, fields: DbInvoiceFields) -> Optional[ResPartner]:
        return (
            self.by_registration_number(fields.registration_number)
            or self.by_code(fields.partner_code)
            or self.by_printed_name(fields.supplier_name)
        )

    @staticmethod
    def _known_names(partner: ResPartner) -> set[str]:
        return {
            PartnerDirectory._comparable(name)
            for name in [partner.name, *partner.aliases]
            if PartnerDirectory._comparable(name)
        }

    @staticmethod
    def _comparable(value: Optional[str]) -> str:
        return "".join(Utils.normalize_full_width_to_ascii(value or "").split()).casefold()
