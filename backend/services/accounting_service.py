import time
from collections.abc import Callable
from typing import Optional

import requests

from ..core import (
    DbInvoiceFields,
    ErrorCode,
    IntakeError,
    ErrorMessage,
    PartnerDirectory,
    ReqRegistration,
    ReqRegistrationLine,
    ResPartner,
    ResRegistrationReceipt,
    ResTaxRate,
    TaxRateTable,
    Utils,
)


CACHE_SECONDS = 60
LINE_KEYS_ALLOWING_NONE = ("quantity", "unit_price")
API_KEY_HEADER = "X-API-Key"
CONTENT_TYPE_HEADER = "Content-Type"
JSON_CONTENT_TYPE = "application/json"
HEALTH_PATH = "/health"
PARTNERS_PATH = "/partners"
TAX_CODES_PATH = "/tax-codes"
INVOICES_PATH = "/invoices"
DEFAULT_TIMEOUT_SECONDS = 10
NO_RESPONSE_HTTP_STATUS = 0
SUCCESS_STATUS_FLOOR = 200
SUCCESS_STATUS_CEILING = 300
PARTNERS_KEY = "partners"
TAX_CODES_KEY = "tax_codes"
TAX_CODE_KEY = "tax_code"
TAX_RATE_KEY = "rate"
ACCOUNTING_ID_KEY = "accounting_id"


class ReqRegistrationFactory:

    @staticmethod
    def of(fields: DbInvoiceFields) -> ReqRegistration:
        return ReqRegistration(
            partner_code=fields.partner_code,
            invoice_number=fields.invoice_number,
            issue_date=fields.issue_date,
            due_date=fields.due_date,
            currency=fields.currency,
            lines=[
                ReqRegistrationLine(
                    description=line.description,
                    quantity=line.quantity,
                    unit=line.unit,
                    unit_price=line.unit_price,
                    amount=line.amount,
                    tax_code=line.tax_code,
                )
                for line in fields.lines
            ],
            subtotal=fields.subtotal,
            tax_amount=fields.tax_amount,
            total_amount=fields.total_amount,
        )

    @staticmethod
    def to_body(request: ReqRegistration) -> dict[str, object]:
        body = Utils.drop_none_values(
            {
                "partner_code": request.partner_code,
                "invoice_number": request.invoice_number,
                "issue_date": request.issue_date,
                "due_date": request.due_date,
                "currency": request.currency,
                "lines": [
                    Utils.drop_none_values(line.model_dump(), LINE_KEYS_ALLOWING_NONE)
                    for line in request.lines
                ],
                "subtotal": request.subtotal,
                "tax_amount": request.tax_amount,
                "total_amount": request.total_amount,
            }
        )
        return Utils.remove_surrogates_from_payload(body)


class ReferenceDataProvider:

    def __init__(
        self,
        gateway: "HttpAccountingGateway",
        cache_seconds: int = CACHE_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._gateway = gateway
        self._cache_seconds = cache_seconds
        self._clock = clock
        self._partners = PartnerDirectory()
        self._tax_table = TaxRateTable()
        self._lookup_failure_reason = ""
        self._fetched_at: Optional[float] = None

    @property
    def gateway(self) -> "HttpAccountingGateway":
        return self._gateway

    @property
    def lookup_failure_reason(self) -> str:
        return self._lookup_failure_reason

    def _is_stale(self) -> bool:
        if self._fetched_at is None:
            return True
        return self._clock() - self._fetched_at > self._cache_seconds

    @staticmethod
    def _reason_for(error: IntakeError) -> str:
        if error.code == ErrorCode.UNAUTHORIZED:
            return ErrorMessage.PARTNERS_UNAUTHORIZED
        if error.code == ErrorCode.ACCOUNTING_API_UNREACHABLE:
            return ErrorMessage.PARTNERS_UNREACHABLE
        return ""

    def refresh(self, force: bool = False) -> None:
        if not force and not self._partners.is_empty and not self._is_stale():
            return
        try:
            self._partners = self._gateway.fetch_partners()
            self._lookup_failure_reason = ""
            self._fetched_at = self._clock()
        except IntakeError as error:
            self._lookup_failure_reason = self._reason_for(error)
        try:
            self._tax_table = self._gateway.fetch_tax_rates()
        except IntakeError:
            pass

    def partners(self) -> PartnerDirectory:
        self.refresh()
        return self._partners

    def tax_table(self) -> TaxRateTable:
        self.refresh()
        return self._tax_table

    def resolve_partner(
        self, fields: DbInvoiceFields
    ) -> tuple[Optional[ResPartner], DbInvoiceFields]:
        partner = self.partners().match(fields)
        if partner is None:
            return None, fields
        return partner, fields.model_copy(
            update={
                "partner_code": partner.partner_code,
                "supplier_name": fields.supplier_name or partner.name,
            }
        )


class HttpAccountingGateway:

    def __init__(
        self, base_url: str, api_key: str, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    ) -> None:
        self._base_url = (base_url or "").rstrip("/")
        self._api_key = api_key or ""
        self._timeout_seconds = timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {API_KEY_HEADER: self._api_key, CONTENT_TYPE_HEADER: JSON_CONTENT_TYPE}

    def _send(
        self, method: str, path: str, json_body: object = None
    ) -> tuple[int, dict[str, object]]:
        try:
            response = requests.request(
                method,
                f"{self._base_url}{path}",
                headers=self._headers(),
                json=json_body,
                timeout=self._timeout_seconds,
            )
        except requests.RequestException as error:
            raise IntakeError(
                ErrorCode.ACCOUNTING_API_UNREACHABLE,
                ErrorMessage.UNREACHABLE,
                NO_RESPONSE_HTTP_STATUS,
            ) from error
        try:
            body = response.json()
        except ValueError as error:
            raise IntakeError(
                ErrorCode.MALFORMED_RESPONSE, ErrorMessage.MALFORMED_BODY, response.status_code
            ) from error
        envelope_error = body.get("error") or {}
        error_code = envelope_error.get("code")
        is_success = error_code is None and (
            SUCCESS_STATUS_FLOOR <= response.status_code < SUCCESS_STATUS_CEILING
        )
        if not is_success:
            raise IntakeError(
                error_code or ErrorCode.ACCOUNTING_API_ERROR,
                envelope_error.get("message") or ErrorMessage.ACCOUNTING_REJECTED,
                response.status_code,
            )
        return response.status_code, body.get("data") or {}

    def is_reachable(self) -> bool:
        try:
            self._send("GET", HEALTH_PATH)
        except IntakeError:
            return False
        return True

    def fetch_partners(self) -> PartnerDirectory:
        _, data = self._send("GET", PARTNERS_PATH)
        entries = data.get(PARTNERS_KEY) or []
        return PartnerDirectory(ResPartner(**entry) for entry in entries)

    def fetch_tax_rates(self) -> TaxRateTable:
        _, data = self._send("GET", TAX_CODES_PATH)
        rates = []
        for entry in data.get(TAX_CODES_KEY) or []:
            code = entry.get(TAX_CODE_KEY)
            rate = entry.get(TAX_RATE_KEY)
            if code and isinstance(rate, (int, float)) and not isinstance(rate, bool):
                rates.append(ResTaxRate(code=code, rate=rate))
        return TaxRateTable(rates)

    def register_invoice(self, request: ReqRegistration) -> ResRegistrationReceipt:
        http_status, data = self._send(
            "POST", INVOICES_PATH, json_body=ReqRegistrationFactory.to_body(request)
        )
        accounting_id = data.get(ACCOUNTING_ID_KEY)
        return ResRegistrationReceipt(
            accounting_id=accounting_id if isinstance(accounting_id, str) else None,
            http_status=http_status,
        )
