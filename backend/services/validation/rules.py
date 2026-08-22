from typing import Optional
import math
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from datetime import date

from ...core import (
    DbInvoiceFields,
    DbLineItem,
    ErrorMessage,
    MdRuleOutcome,
    MdVerificationContext,
    TaxRateTable,
)

REQUIRED_FIELD_NAMES = (
    "partner_code",
    "invoice_number",
    "issue_date",
    "due_date",
    "subtotal",
    "tax_amount",
    "total_amount",
)
LINES_FIELD_NAME = "lines"
LINE_DESCRIPTION_FIELD = "lines[{index}].description"
LINE_UNIT_FIELD = "lines[{index}].unit"
LINE_TAX_CODE_FIELD = "lines[{index}].tax_code"
EMPTY_VALUES = (None, "")

CROSSFOOT = "crossfoot"
TAX_RECOMPUTED = "tax_recomputed"
TOTAL_CONSISTENT = "total_consistent"
PRINTED_TOTAL = "printed_total"
PARTNER_MATCHED = "partner_matched"
NOT_DUPLICATE = "not_duplicate"
REQUIRED_FIELDS = "required_fields"
TAX_CODE_PRESENT = "tax_code_present"
TAX_CODE_KNOWN = "tax_code_known"
DATE_ORDER = "date_order"


class InvoiceCalculator:

    @staticmethod
    def line_total(fields: DbInvoiceFields) -> Optional[int]:
        if not fields.lines:
            return None
        amounts = [line.amount for line in fields.lines if line.amount is not None]
        if len(amounts) != len(fields.lines):
            return None
        return sum(amounts)

    @staticmethod
    def computed_total(fields: DbInvoiceFields) -> Optional[int]:
        if fields.subtotal is None or fields.tax_amount is None:
            return None
        return fields.subtotal + fields.tax_amount

    @staticmethod
    def taxable_base_by_code(
        fields: DbInvoiceFields, table: TaxRateTable
    ) -> tuple[tuple[str, int], ...]:
        codes: list[str] = []
        totals: list[int] = []
        for line in fields.lines:
            if line.tax_code is None or line.amount is None or not table.contains(line.tax_code):
                continue
            if line.tax_code in codes:
                totals[codes.index(line.tax_code)] += line.amount
                continue
            codes.append(line.tax_code)
            totals.append(line.amount)
        return tuple(zip(codes, totals))

    @staticmethod
    def recomputed_tax(fields: DbInvoiceFields, table: TaxRateTable) -> int:
        return sum(
            math.floor(amount * table.rate_for(code))
            for code, amount in InvoiceCalculator.taxable_base_by_code(fields, table)
        )

    @staticmethod
    def line_indexes_where(
        fields: DbInvoiceFields, predicate: Callable[[DbLineItem], bool]
    ) -> list[int]:
        return [index for index, line in enumerate(fields.lines) if predicate(line)]


def parse_iso_date(value: Optional[str]) -> Optional[date]:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


class IVerificationRule(ABC):

    code = ""
    scored = True
    message = ""

    @abstractmethod
    def evaluate(self, context: MdVerificationContext) -> MdRuleOutcome:
        ...

    def outcome(
        self, passed: bool, reason: Optional[str] = None, details: Sequence[str] = ()
    ) -> MdRuleOutcome:
        return MdRuleOutcome(
            code=self.code,
            passed=passed,
            scored=self.scored,
            reason=None if passed else reason,
            details=tuple(details),
        )


class RequiredFieldsRule(IVerificationRule):

    code = REQUIRED_FIELDS
    message = ErrorMessage.MISSING_REQUIRED_FIELDS

    def evaluate(self, context: MdVerificationContext) -> MdRuleOutcome:
        fields = context.fields
        missing = [
            name for name in REQUIRED_FIELD_NAMES if getattr(fields, name) in EMPTY_VALUES
        ]
        if not fields.lines:
            missing.append(LINES_FIELD_NAME)
        for index, line in enumerate(fields.lines):
            if not line.description:
                missing.append(LINE_DESCRIPTION_FIELD.format(index=index))
            if not line.unit:
                missing.append(LINE_UNIT_FIELD.format(index=index))
        return self.outcome(not missing, self.message.format(names=", ".join(missing)), missing)


class TaxCodePresentRule(IVerificationRule):

    code = TAX_CODE_PRESENT
    scored = False
    message = ErrorMessage.MISSING_TAX_CODE

    def evaluate(self, context: MdVerificationContext) -> MdRuleOutcome:
        names = [
            LINE_TAX_CODE_FIELD.format(index=index)
            for index in InvoiceCalculator.line_indexes_where(
                context.fields, lambda line: line.tax_code is None
            )
        ]
        return self.outcome(not names, self.message.format(names=", ".join(names)), names)


class TaxCodeKnownRule(IVerificationRule):

    code = TAX_CODE_KNOWN
    scored = False
    message = ErrorMessage.TAX_CODE_NOT_ACCEPTED

    def evaluate(self, context: MdVerificationContext) -> MdRuleOutcome:
        table = context.tax_table
        names = [
            LINE_TAX_CODE_FIELD.format(index=index)
            for index in InvoiceCalculator.line_indexes_where(
                context.fields,
                lambda line: line.tax_code is not None and not table.contains(line.tax_code),
            )
        ]
        return self.outcome(not names, self.message.format(names=", ".join(names)), names)


class PartnerMatchedRule(IVerificationRule):

    code = PARTNER_MATCHED
    message = ErrorMessage.PARTNER_NOT_IN_MASTER

    def evaluate(self, context: MdVerificationContext) -> MdRuleOutcome:
        return self.outcome(
            context.partner_matched, context.partner_lookup_reason or self.message
        )


class NotDuplicateRule(IVerificationRule):

    code = NOT_DUPLICATE
    message = ErrorMessage.DUPLICATE

    def evaluate(self, context: MdVerificationContext) -> MdRuleOutcome:
        return self.outcome(
            context.duplicate_of is None,
            self.message.format(document_id=context.duplicate_of),
        )


class DateOrderRule(IVerificationRule):

    code = DATE_ORDER
    scored = False
    message = ErrorMessage.DATE_ORDER

    def evaluate(self, context: MdVerificationContext) -> MdRuleOutcome:
        fields = context.fields
        issue_date = parse_iso_date(fields.issue_date)
        due_date = parse_iso_date(fields.due_date)
        if issue_date is None or due_date is None:
            return self.outcome(True)
        return self.outcome(
            due_date >= issue_date,
            self.message.format(due_date=fields.due_date, issue_date=fields.issue_date),
        )


class CrossfootRule(IVerificationRule):

    code = CROSSFOOT
    message = ErrorMessage.CROSSFOOT

    def evaluate(self, context: MdVerificationContext) -> MdRuleOutcome:
        fields = context.fields
        line_total = InvoiceCalculator.line_total(fields)
        if fields.subtotal is None or line_total is None:
            return self.outcome(False, self.message)
        return self.outcome(line_total == fields.subtotal, self.message)


class TaxRecomputedRule(IVerificationRule):

    code = TAX_RECOMPUTED
    message = ErrorMessage.TAX_RECOMPUTED

    def evaluate(self, context: MdVerificationContext) -> MdRuleOutcome:
        fields = context.fields
        if not fields.lines or fields.tax_amount is None:
            return self.outcome(False, self.message)
        if not TaxCodePresentRule().evaluate(context).passed:
            return self.outcome(False, self.message)
        if not TaxCodeKnownRule().evaluate(context).passed:
            return self.outcome(False, self.message)
        recomputed = InvoiceCalculator.recomputed_tax(fields, context.tax_table)
        return self.outcome(recomputed == fields.tax_amount, self.message)


class TotalConsistentRule(IVerificationRule):

    code = TOTAL_CONSISTENT
    message = ErrorMessage.TOTAL_CONSISTENT

    def evaluate(self, context: MdVerificationContext) -> MdRuleOutcome:
        fields = context.fields
        computed = InvoiceCalculator.computed_total(fields)
        if computed is None or fields.total_amount is None:
            return self.outcome(False, self.message)
        return self.outcome(computed == fields.total_amount, self.message)


class PrintedTotalRule(IVerificationRule):

    code = PRINTED_TOTAL
    message = ErrorMessage.PRINTED_TOTAL

    def evaluate(self, context: MdVerificationContext) -> MdRuleOutcome:
        fields = context.fields
        if fields.total_amount is None or fields.printed_total is None:
            return self.outcome(False, self.message)
        return self.outcome(fields.total_amount == fields.printed_total, self.message)


DEFAULT_RULES = (
    RequiredFieldsRule(),
    TaxCodePresentRule(),
    TaxCodeKnownRule(),
    PartnerMatchedRule(),
    NotDuplicateRule(),
    DateOrderRule(),
    CrossfootRule(),
    TaxRecomputedRule(),
    TotalConsistentRule(),
    PrintedTotalRule(),
)
