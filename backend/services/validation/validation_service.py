from typing import Optional
from collections.abc import Sequence

from ...core import (
    DbVerification,
    MdRuleOutcome,
    MdVerificationContext,
    MdVerificationReport,
)
from .rules import (
    CROSSFOOT,
    DEFAULT_RULES,
    PARTNER_MATCHED,
    PRINTED_TOTAL,
    REQUIRED_FIELDS,
    TAX_RECOMPUTED,
    TOTAL_CONSISTENT,
    IVerificationRule,
)


class VerificationService:

    def __init__(self, rules: Sequence[IVerificationRule] = DEFAULT_RULES) -> None:
        self._rules = tuple(rules)

    @property
    def rules(self) -> tuple[IVerificationRule, ...]:
        return self._rules

    def verify(self, context: MdVerificationContext) -> MdVerificationReport:
        return MdVerificationReport(
            outcomes=tuple(rule.evaluate(context) for rule in self._rules),
            duplicate_of=context.duplicate_of,
        )


class ReportReader:

    @staticmethod
    def outcome_for(report: MdVerificationReport, code: str) -> Optional[MdRuleOutcome]:
        for outcome in report.outcomes:
            if outcome.code == code:
                return outcome
        return None

    @staticmethod
    def passed(report: MdVerificationReport, code: str) -> bool:
        outcome = ReportReader.outcome_for(report, code)
        return bool(outcome and outcome.passed)

    @staticmethod
    def blocking_reasons(report: MdVerificationReport) -> list[str]:
        return [
            outcome.reason
            for outcome in report.outcomes
            if not outcome.passed and outcome.reason
        ]

    @staticmethod
    def scored_outcomes(report: MdVerificationReport) -> list[MdRuleOutcome]:
        return [outcome for outcome in report.outcomes if outcome.scored]

    @staticmethod
    def to_verification(report: MdVerificationReport) -> DbVerification:
        required = ReportReader.outcome_for(report, REQUIRED_FIELDS)
        scored = ReportReader.scored_outcomes(report)
        return DbVerification(
            crossfoot_ok=ReportReader.passed(report, CROSSFOOT),
            tax_ok=ReportReader.passed(report, TAX_RECOMPUTED),
            total_ok=ReportReader.passed(report, TOTAL_CONSISTENT),
            printed_total_ok=ReportReader.passed(report, PRINTED_TOTAL),
            partner_matched=ReportReader.passed(report, PARTNER_MATCHED),
            duplicate_of=report.duplicate_of,
            missing_required=list(required.details) if required else [],
            checks_passed=sum(1 for outcome in scored if outcome.passed),
            checks_total=len(scored),
        )
