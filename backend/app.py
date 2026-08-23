from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .controllers.controller import build_router
from .repositories import DocumentRepository
from .services.accounting_service import HttpAccountingGateway, ReferenceDataProvider
from .services.document_service import InvoiceIntakeService
from .services.extraction import (
    Agents,
    ExtractionService,
    MarkitdownTranscriber,
    OrientationCorrector,
)
from .services.validation import ValidationService
from .settings import Settings


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
        MarkitdownTranscriber(),
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
            StaticFiles(directory=settings.frontend_directory, html=True),
            name="frontend",
        )
    return app
