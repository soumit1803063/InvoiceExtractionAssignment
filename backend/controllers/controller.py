from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from ..core import (
    DbDocument,
    ErrorMessage,
    ReqFieldsUpdate,
    ResDocumentList,
    ResHealth,
    ResReferenceData,
    ResRegister,
    Utils,
)
from ..services.accounting_service import HttpAccountingGateway
from ..services.document_service import InvoiceIntakeService
from ..services.extraction import SUPPORTED_SUFFIXES


def build_router(intake: InvoiceIntakeService, gateway: HttpAccountingGateway) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/health", response_model=ResHealth)
    def read_health() -> ResHealth:
        return ResHealth(status="ok", accounting_api_reachable=gateway.is_reachable())

    @router.get("/reference-data", response_model=ResReferenceData)
    def read_reference_data() -> ResReferenceData:
        return ResReferenceData(
            partners=list(intake.partners()),
            tax_rates=list(intake.tax_table()),
            reachable=gateway.is_reachable(),
            lookup_failure_reason=intake.lookup_failure_reason,
        )

    @router.post("/documents/upload", response_model=DbDocument)
    async def upload_document(file: UploadFile = File(...)) -> DbDocument:
        content = await file.read()
        if not content:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, ErrorMessage.EMPTY_UPLOAD)
        name = Utils.safe_file_name(file.filename or "")
        if Path(name).suffix.lower() not in SUPPORTED_SUFFIXES:
            raise HTTPException(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, ErrorMessage.UNSUPPORTED_UPLOAD
            )
        return intake.upload(name, content)

    @router.post("/documents/scan", response_model=ResDocumentList)
    def scan_documents() -> ResDocumentList:
        return ResDocumentList(documents=intake.scan())

    @router.get("/documents", response_model=ResDocumentList)
    def list_documents() -> ResDocumentList:
        return ResDocumentList(documents=intake.list_documents())

    @router.get("/documents/{document_id}", response_model=DbDocument)
    def read_document(document_id: str) -> DbDocument:
        document = intake.get_document(document_id)
        if document is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, ErrorMessage.DOCUMENT_NOT_FOUND)
        return document

    @router.put("/documents/{document_id}", response_model=DbDocument)
    def update_document(document_id: str, request: ReqFieldsUpdate) -> DbDocument:
        document = intake.update_fields(document_id, request.fields)
        if document is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, ErrorMessage.DOCUMENT_NOT_FOUND)
        return document

    @router.post("/documents/{document_id}/reprocess", response_model=DbDocument)
    def reprocess_document(document_id: str) -> DbDocument:
        document = intake.reprocess(document_id)
        if document is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, ErrorMessage.DOCUMENT_NOT_FOUND)
        return document

    @router.post("/documents/{document_id}/register", response_model=ResRegister)
    def register_document(document_id: str) -> ResRegister:
        outcome = intake.register(document_id)
        if outcome is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, ErrorMessage.DOCUMENT_NOT_FOUND)
        document, registration = outcome
        return ResRegister(document=document, registration=registration)

    @router.get("/documents/{document_id}/preview")
    def read_preview(document_id: str) -> FileResponse:
        preview = intake.preview(document_id)
        if preview is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, ErrorMessage.PREVIEW_NOT_FOUND)
        path, media_type = preview
        return FileResponse(path, media_type=media_type, headers={"Cache-Control": "no-store"})

    return router
