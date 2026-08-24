import math
from collections.abc import Sequence
from typing import Optional

from ...core import (
    DbDocument,
    DbInvoiceFields,
    DbRegistration,
    DbStoredDocument,
    DbVerification,
    DocumentStatus,
    ErrorMessage,
    MdModelUsage,
    MdRuleOutcome,
    RuleCode,
    TaxRateTable,
    Utils,
)
from ...repositories import DocumentRepository
from ..accounting_service import ReferenceDataProvider


class ValidationService:

    def __init__(
        self, repository: DocumentRepository, reference_data: ReferenceDataProvider
    ) -> None:
        self._repository = repository
        self._reference_data = reference_data

    def validate(
        self,
        stored: DbStoredDocument,
        fields: DbInvoiceFields,
        registration: Optional[DbRegistration],
        updated_at: str,
        extra_reasons: Sequence[str] = (),
        usage: Optional[MdModelUsage] = None,
    ) -> DbDocument:
        previous = stored.document
        partner, fields = self._reference_data.resolve_partner(fields)
        tax_table = self._reference_data.tax_table()
        duplicate_of = self._repository.find_registered(
            fields.partner_code, fields.invoice_number, previous.document_id
        )
        outcomes = self._run_rules(fields, tax_table, partner is not None, duplicate_of)
        blocking_reasons = [
            outcome.reason for outcome in outcomes if not outcome.passed and outcome.reason
        ]
        extra_failures = list(extra_reasons)
        document = DbDocument(
            document_id=previous.document_id,
            created_at=previous.created_at,
            source_name=previous.source_name,
            fields=fields,
            verification=self._summarise(outcomes, duplicate_of),
            status=self._resolve_status(blocking_reasons + extra_failures, registration),
            blocking_reasons=blocking_reasons,
            extra_failures=extra_failures,
            model_used=usage.model_used if usage else previous.model_used,
            input_tokens=usage.input_tokens if usage else previous.input_tokens,
            output_tokens=usage.output_tokens if usage else previous.output_tokens,
            registration=registration,
        )
        self._repository.save(
            DbStoredDocument(
                document=document,
                source_path=stored.source_path,
                created_at=stored.created_at,
                updated_at=updated_at,
            )
        )
        return document

    def _run_rules(
        self,
        fields: DbInvoiceFields,
        tax_table: TaxRateTable,
        partner_matched: bool,
        duplicate_of: Optional[str],
    ) -> tuple[MdRuleOutcome, ...]:
        tax_codes_present = self._check_tax_codes_present(fields)
        tax_codes_known = self._check_tax_codes_known(fields, tax_table)
        return (
            self._check_required_fields(fields),
            tax_codes_present,
            tax_codes_known,
            self._check_partner_matched(partner_matched),
            self._check_not_duplicate(duplicate_of),
            self._check_date_order(fields.issue_date, fields.due_date),
            self._check_crossfoot(fields),
            self._check_tax_recomputed(
                fields, tax_table, tax_codes_present.passed and tax_codes_known.passed
            ),
            self._check_total_consistent(fields),
            self._check_printed_total(fields),
        )

    def _check_required_fields(self, fields: DbInvoiceFields) -> MdRuleOutcome:
        required = (
            "partner_code",
            "invoice_number",
            "issue_date",
            "due_date",
            "subtotal",
            "tax_amount",
            "total_amount",
        )
        missing = [name for name in required if getattr(fields, name) in (None, "")]
        if not fields.lines:
            missing.append("lines")
        for index, line in enumerate(fields.lines):
            if not line.description:
                missing.append(f"lines[{index}].description")
            if not line.unit:
                missing.append(f"lines[{index}].unit")
        return self._outcome(
            RuleCode.REQUIRED_FIELDS,
            not missing,
            ErrorMessage.MISSING_REQUIRED_FIELDS.format(names=", ".join(missing)),
            missing,
        )

    def _check_tax_codes_present(self, fields: DbInvoiceFields) -> MdRuleOutcome:
        names = [
            f"lines[{index}].tax_code"
            for index, line in enumerate(fields.lines)
            if line.tax_code is None
        ]
        return self._outcome(
            RuleCode.TAX_CODE_PRESENT,
            not names,
            ErrorMessage.MISSING_TAX_CODE.format(names=", ".join(names)),
            names,
            scored=False,
        )

    def _check_tax_codes_known(
        self, fields: DbInvoiceFields, tax_table: TaxRateTable
    ) -> MdRuleOutcome:
        names = [
            f"lines[{index}].tax_code"
            for index, line in enumerate(fields.lines)
            if line.tax_code is not None and not tax_table.contains(line.tax_code)
        ]
        return self._outcome(
            RuleCode.TAX_CODE_KNOWN,
            not names,
            ErrorMessage.TAX_CODE_NOT_ACCEPTED.format(names=", ".join(names)),
            names,
            scored=False,
        )

    def _check_partner_matched(self, partner_matched: bool) -> MdRuleOutcome:
        reason = self._reference_data.lookup_failure_reason or ErrorMessage.PARTNER_NOT_IN_MASTER
        return self._outcome(RuleCode.PARTNER_MATCHED, partner_matched, reason)

    def _check_not_duplicate(self, duplicate_of: Optional[str]) -> MdRuleOutcome:
        return self._outcome(
            RuleCode.NOT_DUPLICATE,
            duplicate_of is None,
            ErrorMessage.DUPLICATE.format(document_id=duplicate_of),
        )

    def _check_date_order(
        self, issue_date: Optional[str], due_date: Optional[str]
    ) -> MdRuleOutcome:
        issued = Utils.parse_iso_date(issue_date)
        due = Utils.parse_iso_date(due_date)
        if issued is None or due is None:
            return self._outcome(RuleCode.DATE_ORDER, True, scored=False)
        return self._outcome(
            RuleCode.DATE_ORDER,
            due >= issued,
            ErrorMessage.DATE_ORDER.format(due_date=due_date, issue_date=issue_date),
            scored=False,
        )

    def _check_crossfoot(self, fields: DbInvoiceFields) -> MdRuleOutcome:
        line_total = self._line_total(fields)
        passed = fields.subtotal is not None and line_total == fields.subtotal
        return self._outcome(RuleCode.CROSSFOOT, passed, ErrorMessage.CROSSFOOT)

    def _check_tax_recomputed(
        self, fields: DbInvoiceFields, tax_table: TaxRateTable, tax_codes_usable: bool
    ) -> MdRuleOutcome:
        if not fields.lines or fields.tax_amount is None or not tax_codes_usable:
            return self._outcome(RuleCode.TAX_RECOMPUTED, False, ErrorMessage.TAX_RECOMPUTED)
        recomputed = sum(
            math.floor(amount * tax_table.rate_for(code))
            for code, amount in self._taxable_base_by_code(fields, tax_table)
        )
        return self._outcome(
            RuleCode.TAX_RECOMPUTED, recomputed == fields.tax_amount, ErrorMessage.TAX_RECOMPUTED
        )

    def _check_total_consistent(self, fields: DbInvoiceFields) -> MdRuleOutcome:
        if fields.subtotal is None or fields.tax_amount is None or fields.total_amount is None:
            return self._outcome(RuleCode.TOTAL_CONSISTENT, False, ErrorMessage.TOTAL_CONSISTENT)
        computed = fields.subtotal + fields.tax_amount
        return self._outcome(
            RuleCode.TOTAL_CONSISTENT, computed == fields.total_amount, ErrorMessage.TOTAL_CONSISTENT
        )

    def _check_printed_total(self, fields: DbInvoiceFields) -> MdRuleOutcome:
        if fields.total_amount is None or fields.printed_total is None:
            return self._outcome(RuleCode.PRINTED_TOTAL, False, ErrorMessage.PRINTED_TOTAL)
        return self._outcome(
            RuleCode.PRINTED_TOTAL,
            fields.total_amount == fields.printed_total,
            ErrorMessage.PRINTED_TOTAL,
        )

    def _summarise(
        self, outcomes: Sequence[MdRuleOutcome], duplicate_of: Optional[str]
    ) -> DbVerification:
        by_code = {outcome.code: outcome for outcome in outcomes}
        scored = [outcome for outcome in outcomes if outcome.scored]
        required = by_code.get(RuleCode.REQUIRED_FIELDS)
        return DbVerification(
            crossfoot_ok=by_code[RuleCode.CROSSFOOT].passed,
            tax_ok=by_code[RuleCode.TAX_RECOMPUTED].passed,
            total_ok=by_code[RuleCode.TOTAL_CONSISTENT].passed,
            printed_total_ok=by_code[RuleCode.PRINTED_TOTAL].passed,
            partner_matched=by_code[RuleCode.PARTNER_MATCHED].passed,
            duplicate_of=duplicate_of,
            missing_required=list(required.details) if required else [],
            checks_passed=sum(1 for outcome in scored if outcome.passed),
            checks_total=len(scored),
        )

    @staticmethod
    def _resolve_status(
        blocking_reasons: Sequence[str], registration: Optional[DbRegistration]
    ) -> DocumentStatus:
        if registration is not None:
            if registration.accounting_id:
                return DocumentStatus.REGISTERED
            if registration.http_status >= 400:
                return DocumentStatus.REJECTED
        return DocumentStatus.NEEDS_REVIEW if blocking_reasons else DocumentStatus.READY

    @staticmethod
    def _outcome(
        code: RuleCode,
        passed: bool,
        reason: Optional[str] = None,
        details: Sequence[str] = (),
        scored: bool = True,
    ) -> MdRuleOutcome:
        return MdRuleOutcome(
            code=code,
            passed=passed,
            scored=scored,
            reason=None if passed else reason,
            details=tuple(details),
        )

    @staticmethod
    def _line_total(fields: DbInvoiceFields) -> Optional[int]:
        if not fields.lines:
            return None
        amounts = [line.amount for line in fields.lines if line.amount is not None]
        if len(amounts) != len(fields.lines):
            return None
        return sum(amounts)

    @staticmethod
    def _taxable_base_by_code(
        fields: DbInvoiceFields, tax_table: TaxRateTable
    ) -> tuple[tuple[str, int], ...]:
        codes: list[str] = []
        totals: list[int] = []
        for line in fields.lines:
            if line.tax_code is None or line.amount is None:
                continue
            if not tax_table.contains(line.tax_code):
                continue
            if line.tax_code in codes:
                totals[codes.index(line.tax_code)] += line.amount
                continue
            codes.append(line.tax_code)
            totals.append(line.amount)
        return tuple(zip(codes, totals))
