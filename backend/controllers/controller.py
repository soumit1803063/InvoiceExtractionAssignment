from pathlib import Path

from fastapi import APIRouter, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.responses import Response
from starlette.types import Scope
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..container import ApplicationContainer
from ..core import DbDocument, ErrorMessage, ResReferenceData, ReqFieldsUpdate, ResDocumentList, ResHealth, ResRegister, Utils
from ..services.extraction import SUPPORTED_SUFFIXES
from ..settings import Settings

API_PREFIX = "/api"
APPLICATION_TITLE = "Invoice Intake"
APPLICATION_VERSION = "1.0.0"
HEALTH_STATUS_OK = "ok"
INDEX_FILE_NAME = "index.html"
NO_CACHE_HEADERS = {"Cache-Control": "no-store"}
NOT_FOUND_STATUS = 404
BAD_REQUEST_STATUS = 400
UNSUPPORTED_TYPE_STATUS = 415


class SinglePageApplicationFiles(StaticFiles):

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as error:
            if error.status_code != NOT_FOUND_STATUS:
                raise
            return await super().get_response(INDEX_FILE_NAME, scope)


class DocumentsRouter:

    @staticmethod
    def build(container: ApplicationContainer) -> APIRouter:
        router = APIRouter(prefix=API_PREFIX)
        intake = container.intake_service
        gateway = container.accounting_gateway

        @router.get("/health", response_model=ResHealth)
        def read_health() -> ResHealth:
            return ResHealth(
                status=HEALTH_STATUS_OK,
                accounting_api_reachable=gateway.is_reachable(),
            )

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
                raise HTTPException(status_code=BAD_REQUEST_STATUS, detail=ErrorMessage.EMPTY_UPLOAD)
            name = Utils.safe_file_name(file.filename or "")
            if Path(name).suffix.lower() not in SUPPORTED_SUFFIXES:
                raise HTTPException(
                    status_code=UNSUPPORTED_TYPE_STATUS, detail=ErrorMessage.UNSUPPORTED_UPLOAD
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
                raise HTTPException(status_code=NOT_FOUND_STATUS, detail=ErrorMessage.DOCUMENT_NOT_FOUND)
            return document

        @router.put("/documents/{document_id}", response_model=DbDocument)
        def update_document(document_id: str, request: ReqFieldsUpdate) -> DbDocument:
            document = intake.update_fields(document_id, request.fields)
            if document is None:
                raise HTTPException(status_code=NOT_FOUND_STATUS, detail=ErrorMessage.DOCUMENT_NOT_FOUND)
            return document

        @router.post("/documents/{document_id}/reprocess", response_model=DbDocument)
        def reprocess_document(document_id: str) -> DbDocument:
            document = intake.reprocess(document_id)
            if document is None:
                raise HTTPException(
                    status_code=NOT_FOUND_STATUS, detail=ErrorMessage.DOCUMENT_NOT_FOUND
                )
            return document

        @router.post("/documents/{document_id}/register", response_model=ResRegister)
        def register_document(document_id: str) -> ResRegister:
            outcome = intake.register(document_id)
            if outcome is None:
                raise HTTPException(status_code=NOT_FOUND_STATUS, detail=ErrorMessage.DOCUMENT_NOT_FOUND)
            document, registration = outcome
            return ResRegister(document=document, registration=registration)

        @router.get("/documents/{document_id}/preview")
        def read_preview(document_id: str) -> object:
            preview = intake.preview(document_id)
            if preview is None:
                raise HTTPException(status_code=NOT_FOUND_STATUS, detail=ErrorMessage.PREVIEW_NOT_FOUND)
            path, media_type = preview
            return FileResponse(path, media_type=media_type, headers=NO_CACHE_HEADERS)

        return router


class ApplicationFactory:

    @staticmethod
    def mount_frontend(app: FastAPI, frontend_directory: Path) -> bool:
        if not frontend_directory.is_dir():
            return False
        app.mount(
            "/",
            SinglePageApplicationFiles(directory=frontend_directory, html=True),
            name="frontend",
        )
        return True

    @staticmethod
    def create(settings: Settings) -> FastAPI:
        container = ApplicationContainer(settings)
        container.intake_service.restart_stranded()
        app = FastAPI(title=APPLICATION_TITLE, version=APPLICATION_VERSION)
        app.include_router(DocumentsRouter.build(container))
        ApplicationFactory.mount_frontend(app, settings.frontend_directory)
        return app


def create_app(settings: Settings) -> FastAPI:
    return ApplicationFactory.create(settings)
