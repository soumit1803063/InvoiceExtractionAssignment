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
    MdPageImage,
    MdTaxBreakdown,
    SourceKind,
    Utils,
    coerce_tax_code,
)
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
        self._transcribers = transcribers.fallback_chain()
        self._agents = agents.fallback_chain()
        self._orientation = orientation

    def extract(self, file_path: PathLike) -> MdExtractionResult:
        try:
            markdown = self._convert_file_to_markdown(file_path)
            extraction_result = self._extract_from_markdown(markdown)
            return MdExtractionResult(fields=ExtractionService.to_invoice_fields(extraction_result))
        except IntakeError as error:
            return MdExtractionResult(error_message=self.reason_for(error))

    def _convert_file_to_markdown(self, path: PathLike) -> str:
        pages = []
        for page_image in self._to_page_images(path):
            heading = PAGE_HEADING.format(page_number=page_image.page_number)
            pages.append(heading + self._transcribe_page(page_image))
        return PAGE_SEPARATOR.join(pages)

    def _transcribe_page(self, page: MdPageImage) -> str:
        failures = []
        for transcriber in self._transcribers:
            try:
                return transcriber.to_markdown(page)
            except IntakeError as error:
                failures.append(f"{transcriber.model_id or 'no model'}: {error.message}")
        raise IntakeError(ErrorCode.TRANSCRIPTION_FAILED, FAILURE_SEPARATOR.join(failures))

    def _to_page_images(self, path: PathLike) -> Sequence[MdPageImage]:
        media_type = Utils.media_type_for_path(path)
        if media_type != Utils.PDF_MEDIA_TYPE:
            page = MdPageImage(
                page_number=1, media_type=media_type, content=Utils.read_bytes(path)
            )
            return (self._orientation.upright(page),)
        return tuple(
            self._orientation.upright(
                MdPageImage(page_number=number, media_type=Utils.PNG_MEDIA_TYPE, content=png)
            )
            for number, png in enumerate(Utils.iter_pdf_page_pngs(path, self._dpi), start=1)
        )

    def _extract_from_markdown(self, markdown: str) -> AiInvoice:
        if not self._agents:
            raise IntakeError(ErrorCode.STRUCTURING_FAILED, ErrorMessage.NO_STRUCTURING_MODEL)
        failures = []
        for agent in self._agents:
            try:
                answer = agent.run(markdown).content
            except Exception as error:
                failures.append(str(error))
                continue
            if isinstance(answer, AiInvoice):
                return answer
            failures.append(ErrorMessage.UNUSABLE_RESPONSE)
        raise IntakeError(ErrorCode.STRUCTURING_FAILED, FAILURE_SEPARATOR.join(failures))

    @staticmethod
    def classify(path: PathLike) -> SourceKind:
        suffix = Path(path).suffix.lower()
        if suffix in IMAGE_SUFFIXES:
            return SourceKind.IMAGE
        if Utils.count_pdf_text_characters(path) > 0:
            return SourceKind.TEXT_PDF
        return SourceKind.IMAGE_PDF

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
