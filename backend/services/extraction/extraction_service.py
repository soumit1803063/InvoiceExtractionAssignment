import threading
from typing import Optional
from collections.abc import Sequence

from ...settings import Settings
from ...core import (
    PathLike,
    AiInvoice,
    AiLineItem,
    DbInvoiceFields,
    DbLineItem,
    ErrorCode,
    ErrorMessage,
    IntakeError,
    MdExtractionResult,
    MdModelUsage,
    MdPage,
    MdTaxBreakdown,
    Utils,
    coerce_tax_code,
)
from pydantic import ValidationError

from agno.agent import Agent
from agno.media import Image
from agno.run.agent import RunOutput

from .agents import Agents
from .transcriber import MarkitdownTranscriber
from .orientation import OrientationCorrector


PDF_SUFFIXES = (".pdf",)
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png")
SUPPORTED_SUFFIXES = PDF_SUFFIXES + IMAGE_SUFFIXES
FAILURE_SEPARATOR = "; "
TRANSCRIPT_SECTION_MARKER = "\n\n<--here is the invoice in markdown format-->\n\n"
IMAGE_MESSAGE = "invoice image(s) attached"


class ExtractionService:

    def __init__(
        self,
        settings: Settings,
        reader: MarkitdownTranscriber,
        agents: Agents,
        orientation: OrientationCorrector,
    ) -> None:
        self._dpi = settings.render_dpi
        self._reader = reader
        self._text_agents = agents.text_chain()
        self._vision_agents = agents.vision_chain()
        self._orientation = orientation
        self._agent_timeout_seconds = settings.model_timeout_seconds

    def extract(self, file_path: PathLike) -> MdExtractionResult:
        try:
            invoice, usage = self._read(file_path)
        except IntakeError as error:
            return MdExtractionResult(error_message=self.reason_for(error))
        return MdExtractionResult(
            fields=ExtractionService.to_invoice_fields(invoice),
            model_used=usage.model_used,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
        )

    def _read(self, path: PathLike) -> tuple[AiInvoice, MdModelUsage]:
        try:
            return self._read_pdf(path)
        except IntakeError:
            return self._read_images(path)

    def _read_images(self, path: PathLike) -> tuple[AiInvoice, MdModelUsage]:
        images = [
            Image(content=page.content, mime_type=page.media_type)
            for page in self._to_page_images(path)
        ]
        return self._structure(self._vision_agents, IMAGE_MESSAGE, images)

    def _read_pdf(self, path: PathLike) -> tuple[AiInvoice, MdModelUsage]:
        page = MdPage(
            page_number=1,
            media_type=Utils.media_type_for_path(path),
            content=Utils.read_bytes(path),
        )
        markdown = self._reader.to_markdown(page)
        prompt = TRANSCRIPT_SECTION_MARKER + markdown
        return self._structure(self._text_agents, prompt)

    def _to_page_images(self, path: PathLike) -> Sequence[MdPage]:
        media_type = Utils.media_type_for_path(path)
        if media_type != Utils.PDF_MEDIA_TYPE:
            page = MdPage(
                page_number=1, media_type=media_type, content=Utils.read_bytes(path)
            )
            return (self._orientation.upright(page),)
        return tuple(
            self._orientation.upright(
                MdPage(page_number=number, media_type=Utils.PNG_MEDIA_TYPE, content=png)
            )
            for number, png in enumerate(Utils.iter_pdf_page_pngs(path, self._dpi), start=1)
        )

    def _structure(
        self, agents: Sequence[Agent], prompt: str, images: Optional[Sequence[Image]] = None
    ) -> tuple[AiInvoice, MdModelUsage]:
        if not agents:
            raise IntakeError(ErrorCode.STRUCTURING_FAILED, ErrorMessage.NO_STRUCTURING_MODEL)
        failures = []
        for agent in agents:
            model_id = getattr(getattr(agent, "model", None), "id", "?")
            try:
                outcome = self._run_bounded(agent, prompt, images)
            except TimeoutError:
                failures.append(f"{model_id}: timed out after {self._agent_timeout_seconds}s")
                continue
            except Exception as error:
                failures.append(f"{model_id}: {error}")
                continue
            usage = ExtractionService._usage_of(outcome, model_id)
            if usage.output_tokens == 0:
                failures.append(f"{model_id}: {ErrorMessage.UNUSABLE_RESPONSE}: no output tokens")
                continue
            answer = outcome.content
            invoice = (
                answer
                if isinstance(answer, AiInvoice)
                else ExtractionService._parse_invoice_from_text(answer)
            )
            if invoice is not None and not ExtractionService._is_empty(invoice):
                return invoice, usage
            failures.append(f"{model_id}: {ErrorMessage.UNUSABLE_RESPONSE}: {str(answer)[:160]}")
        raise IntakeError(ErrorCode.STRUCTURING_FAILED, FAILURE_SEPARATOR.join(failures))

    @staticmethod
    def _is_empty(invoice: AiInvoice) -> bool:
        return not invoice.lines and invoice.invoice_number is None and invoice.total_amount is None

    def _run_bounded(
        self, agent: Agent, prompt: str, images: Optional[Sequence[Image]]
    ) -> RunOutput:
        outcome_holder: list[RunOutput] = []
        error_holder: list[BaseException] = []

        def target() -> None:
            try:
                outcome_holder.append(agent.run(prompt, images=list(images) if images else None))
            except BaseException as error:
                error_holder.append(error)

        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout=self._agent_timeout_seconds)
        if outcome_holder:
            return outcome_holder[0]
        if error_holder:
            raise error_holder[0]
        raise TimeoutError(f"agent.run did not complete within {self._agent_timeout_seconds}s")

    @staticmethod
    def _usage_of(outcome: object, model_id: str) -> MdModelUsage:
        metrics = getattr(outcome, "metrics", None)
        return MdModelUsage(
            model_used=model_id,
            input_tokens=int(getattr(metrics, "input_tokens", 0) or 0),
            output_tokens=int(getattr(metrics, "output_tokens", 0) or 0),
        )

    @staticmethod
    def _parse_invoice_from_text(answer: object) -> Optional[AiInvoice]:
        parsed = Utils.parse_first_json_object(str(answer))
        if not isinstance(parsed, dict):
            return None
        try:
            return AiInvoice.model_validate(parsed)
        except ValidationError:
            return None

    @staticmethod
    def reason_for(error: IntakeError) -> str:
        return ErrorMessage.UNREADABLE_DOCUMENT.format(detail=error.message)

    @staticmethod
    def to_invoice_fields(invoice: AiInvoice) -> DbInvoiceFields:
        tax_breakdown = ExtractionService.read_tax_breakdown(invoice)
        printed_tax = tax_breakdown.total_tax
        return DbInvoiceFields(
            registration_number=invoice.registration_number,
            supplier_name=invoice.supplier_name,
            invoice_number=invoice.invoice_number,
            issue_date=invoice.issue_date,
            due_date=invoice.due_date,
            subtotal=invoice.subtotal,
            tax_amount=printed_tax if printed_tax is not None else invoice.tax_amount,
            total_amount=invoice.total_amount,
            printed_total=invoice.printed_total,
            notes_excluded=invoice.notes_excluded,
            lines=ExtractionService.read_line_items(invoice, tax_breakdown),
        )

    @staticmethod
    def read_line_items(
        invoice: AiInvoice, tax_breakdown: MdTaxBreakdown
    ) -> list[DbLineItem]:
        line_items = []
        for ai_line in invoice.lines:
            tax_code = ExtractionService.calculate_line_tax_code(ai_line, tax_breakdown)
            line_items.append(
                DbLineItem(
                    description=ai_line.description,
                    quantity=ai_line.quantity,
                    unit=ai_line.unit,
                    unit_price=ai_line.unit_price,
                    amount=ai_line.amount,
                    tax_code=tax_code,
                )
            )
        return line_items

    @staticmethod
    def calculate_line_tax_code(
        ai_line: AiLineItem, tax_breakdown: MdTaxBreakdown
    ) -> Optional[str]:
        amount = Utils.parse_amount(ai_line.amount)
        for taxable_amount, code in tax_breakdown.codes_by_amount:
            if amount == taxable_amount:
                return code
        return coerce_tax_code(ai_line.tax_code) or tax_breakdown.fallback_code

    @staticmethod
    def read_tax_breakdown(invoice: AiInvoice) -> MdTaxBreakdown:
        printed_codes, taxable_amounts, total_tax = ExtractionService._read_printed_tax_rows(
            invoice
        )
        line_amounts = [Utils.parse_amount(ai_line.amount) for ai_line in invoice.lines]
        codes_by_amount = ExtractionService._match_codes_by_amount(
            line_amounts, printed_codes, taxable_amounts
        )
        fallback_code = ExtractionService._read_fallback_code(
            invoice, line_amounts, codes_by_amount
        )
        return MdTaxBreakdown(
            total_tax=total_tax,
            codes_by_amount=codes_by_amount,
            fallback_code=fallback_code,
        )

    @staticmethod
    def _read_printed_tax_rows(
        invoice: AiInvoice,
    ) -> tuple[list[str], list[int], Optional[int]]:
        printed_codes: list[str] = []
        taxable_amounts: list[int] = []
        tax_amounts: list[Optional[int]] = []
        every_taxable_amount_printed = True
        for tax_row in invoice.tax_rows:
            tax_code = coerce_tax_code(tax_row.percent)
            if tax_code is None:
                continue
            tax_amounts.append(Utils.parse_amount(tax_row.tax_amount))
            taxable_amount = Utils.parse_amount(tax_row.taxable_amount)
            if taxable_amount is None:
                every_taxable_amount_printed = False
                continue
            if tax_code in printed_codes:
                taxable_amounts[printed_codes.index(tax_code)] += taxable_amount
                continue
            printed_codes.append(tax_code)
            taxable_amounts.append(taxable_amount)
        if not every_taxable_amount_printed:
            printed_codes, taxable_amounts = [], []

        total_tax = None
        if tax_amounts and all(amount is not None for amount in tax_amounts):
            total_tax = sum(tax_amounts)
        return printed_codes, taxable_amounts, total_tax

    @staticmethod
    def _match_codes_by_amount(
        line_amounts: Sequence[Optional[int]],
        printed_codes: Sequence[str],
        taxable_amounts: Sequence[int],
    ) -> tuple[tuple[int, str], ...]:
        if len(printed_codes) == 1:
            return tuple(
                (amount, printed_codes[0]) for amount in line_amounts if amount is not None
            )
        if not printed_codes or not line_amounts:
            return ()
        if any(amount is None for amount in line_amounts):
            return ()
        matched = Utils.find_unique_partition_matching_targets(
            line_amounts, printed_codes, taxable_amounts
        )
        if matched is None:
            return ()
        return tuple(zip(line_amounts, matched))

    @staticmethod
    def _read_fallback_code(
        invoice: AiInvoice,
        line_amounts: Sequence[Optional[int]],
        codes_by_amount: Sequence[tuple[int, str]],
    ) -> Optional[str]:
        settled = []
        for ai_line, amount in zip(invoice.lines, line_amounts):
            matched_code = next(
                (code for taxable, code in codes_by_amount if taxable == amount), None
            )
            settled.append(matched_code or coerce_tax_code(ai_line.tax_code))
        codes_in_use = {code for code in settled if code}
        return codes_in_use.pop() if len(codes_in_use) == 1 else None
