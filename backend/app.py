from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.types import Scope

from .controllers.controller import build_router
from .repositories import DocumentRepository
from .services.accounting_service import HttpAccountingGateway, ReferenceDataProvider
from .services.document_service import InvoiceIntakeService
from .services.extraction import Agents, ExtractionService, OrientationCorrector, Transcribers
from .services.validation import ValidationService
from .settings import Settings


class SinglePageApplicationFiles(StaticFiles):

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as error:
            if error.status_code != 404:
                raise
            return await super().get_response("index.html", scope)


def create_app(settings: Settings) -> FastAPI:
    gateway = HttpAccountingGateway(
        settings.accounting_base_url,
        settings.accounting_api_key,
        settings.accounting_timeout_seconds,
    )
    reference_data = ReferenceDataProvider(gateway)
    repository = DocumentRepository(settings.database_path)
    extraction = ExtractionService(
        settings,
        Transcribers(settings),
        Agents(settings),
        OrientationCorrector(settings),
    )
    intake = InvoiceIntakeService(
        settings=settings,
        repository=repository,
        reference_data=reference_data,
        extraction=extraction,
        validation=ValidationService(repository, reference_data),
    )
    intake.restart_stranded()

    app = FastAPI(title="Invoice Intake", version="1.0.0")
    app.include_router(build_router(intake, gateway))
    if settings.frontend_directory.is_dir():
        app.mount(
            "/",
            SinglePageApplicationFiles(directory=settings.frontend_directory, html=True),
            name="frontend",
        )
    return app
