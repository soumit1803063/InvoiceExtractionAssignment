from enum import StrEnum


class IntakeError(Exception):

    def __init__(self, code: "ErrorCode", message: str, status: int = 0) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


class ErrorCode(StrEnum):
    ACCOUNTING_API_ERROR = "ACCOUNTING_API_ERROR"
    ACCOUNTING_API_UNREACHABLE = "ACCOUNTING_API_UNREACHABLE"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    STRUCTURING_FAILED = "STRUCTURING_FAILED"
    TRANSCRIPTION_FAILED = "TRANSCRIPTION_FAILED"
    UNAUTHORIZED = "UNAUTHORIZED"


class ErrorMessage(StrEnum):
    CROSSFOOT = "Line amounts do not add up to the printed subtotal"
    DATE_ORDER = "Due date {due_date} is earlier than issue date {issue_date}"
    DUPLICATE = "Same partner and invoice number were already read from document {document_id}"
    MISSING_REQUIRED_FIELDS = "Missing required fields: {names}"
    MISSING_TAX_CODE = "Missing tax code on: {names}"
    PARTNER_NOT_IN_MASTER = (
        "Supplier registration number does not match any partner in the accounting master"
    )
    PRINTED_TOTAL = "Recomputed total does not match the total printed on the document"
    TAX_RECOMPUTED = "Tax amount does not match the tax recalculated per tax code from the lines"
    TAX_CODE_NOT_ACCEPTED = "Tax code not accepted by the accounting system on: {names}"
    TOTAL_CONSISTENT = "Subtotal plus tax does not equal the total amount"

    UNREADABLE_DOCUMENT = "Could not read the document: {detail}"
    EMPTY_TRANSCRIPTION = "the transcriber returned no text for this page"
    NO_STRUCTURING_MODEL = "no structuring model is configured"
    REGISTRATION_REFUSED = "The accounting system refused this invoice: {detail}"
    PROCESSING_FAILED = "Reading the document failed: {detail}"
    UNUSABLE_RESPONSE = "the agent did not return an invoice"

    ACCOUNTING_REJECTED = "The accounting API rejected the request"
    MALFORMED_BODY = "The accounting API returned a body that is not JSON"
    UNREACHABLE = "The accounting API could not be reached"
    PARTNERS_UNAUTHORIZED = (
        "The accounting API rejected the configured API key, "
        "so the partner master could not be read"
    )
    PARTNERS_UNREACHABLE = (
        "The accounting API could not be reached, so the partner master could not be read"
    )

    DOCUMENT_NOT_FOUND = "No document with that id"
    PREVIEW_NOT_FOUND = "No preview available for that document"
    EMPTY_UPLOAD = "The uploaded file was empty"
    UNSUPPORTED_UPLOAD = "Only .pdf, .jpg, .jpeg and .png invoices are accepted"


class RuleCode(StrEnum):
    REQUIRED_FIELDS = "required_fields"
    TAX_CODE_PRESENT = "tax_code_present"
    TAX_CODE_KNOWN = "tax_code_known"
    PARTNER_MATCHED = "partner_matched"
    NOT_DUPLICATE = "not_duplicate"
    DATE_ORDER = "date_order"
    CROSSFOOT = "crossfoot"
    TAX_RECOMPUTED = "tax_recomputed"
    TOTAL_CONSISTENT = "total_consistent"
    PRINTED_TOTAL = "printed_total"


class DocumentStatus(StrEnum):
    PROCESSING = "processing"
    NEEDS_REVIEW = "needs_review"
    READY = "ready"
    REGISTERED = "registered"
    REJECTED = "rejected"
