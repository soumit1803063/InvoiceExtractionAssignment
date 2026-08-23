from typing import Optional, Union
from collections.abc import Sequence
from pathlib import Path

from ...settings import Settings
from ...core import (
    AiInvoice,
    AiLineItem,
    DbInvoiceFields,
    DbLineItem,
    ErrorCode,
    ErrorMessage,
    IntakeError,
    MdExtractionResult,
    MdPage,
    MdTaxBreakdown,
    Utils,
    coerce_tax_code,
)
from pydantic import ValidationError

from agno.agent import Agent
from agno.media import Image

from .agents import Agents
from .transcriber import Transcribers
from .orientation import OrientationCorrector

PathLike = Union[Path, str]

PDF_SUFFIXES = (".pdf",)
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png")
SUPPORTED_SUFFIXES = PDF_SUFFIXES + IMAGE_SUFFIXES
PAGE_SEPARATOR = "\n\n"
PAGE_HEADING = "<!-- page {page_number} -->\n"
FAILURE_SEPARATOR = "; "


class ExtractionService:

    def __init__(
        self,
        settings: Settings,
        transcribers: Transcribers,
        agents: Agents,
        orientation: OrientationCorrector,
    ) -> None:
        self._dpi = settings.render_dpi
        self._reader = transcribers.plain()
        self._text_agents = agents.text_chain()
        self._vision_agents = agents.vision_chain()
        self._orientation = orientation
        self._instructions = settings.extract_prompt

    def extract(self, file_path: PathLike) -> MdExtractionResult:
        try:
            return MdExtractionResult(fields=ExtractionService.to_invoice_fields(self._read(file_path)))
        except IntakeError as error:
            return MdExtractionResult(error_message=self.reason_for(error))

    def _read(self, path: PathLike) -> AiInvoice:
        try:
            return self._read_pdf(path)
        except IntakeError:
            return self._read_images(path)
        

    def _read_images(self, path: PathLike) -> AiInvoice:
        images = [
            Image(content=page.content, mime_type=page.media_type)
            for page in self._to_page_images(path)
        ]
        return self._structure(self._vision_agents, self._instructions, images)

    def _read_pdf(self, path: PathLike) -> AiInvoice:
        page = MdPage(
            page_number=1,
            media_type=Utils.media_type_for_path(path),
            content=Utils.read_bytes(path),
        )
        markdown = self._reader.to_markdown(page)
        if not markdown.strip():
            raise IntakeError(ErrorCode.CONTENT_REJECTED, ErrorMessage.EMPTY_DOCUMENT)
        return self._structure(self._text_agents, self._instructions +"\n\n<--here is the invoice in markdown format-->\n\n" +markdown)
    
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
    ) -> AiInvoice:
        if not agents:
            raise IntakeError(ErrorCode.STRUCTURING_FAILED, ErrorMessage.NO_STRUCTURING_MODEL)
        failures = []
        for agent in agents:
            model_id = getattr(getattr(agent, "model", None), "id", "?")
            try:
                answer = agent.run(prompt, images=list(images) if images else None).content
            except Exception as error:
                failures.append(f"{model_id}: {error}")
                continue
            if isinstance(answer, AiInvoice):
                return answer
            salvaged = ExtractionService._salvage(answer)
            if salvaged is not None:
                return salvaged
            failures.append(f"{model_id}: {ErrorMessage.UNUSABLE_RESPONSE}: {str(answer)[:160]}")
        raise IntakeError(ErrorCode.STRUCTURING_FAILED, FAILURE_SEPARATOR.join(failures))

    @staticmethod
    def _salvage(answer: object) -> Optional[AiInvoice]:
        parsed = Utils.parse_first_json_object(str(answer))
        if not isinstance(parsed, dict):
            return None
        try:
            return AiInvoice.model_validate(parsed)
        except ValidationError:
            return None

    @staticmethod
    def reason_for(error: IntakeError) -> str:
        if error.code == ErrorCode.CONTENT_REJECTED:
            return ErrorMessage.CONTENT_REJECTED.format(detail=error.message)
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
