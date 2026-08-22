from functools import cached_property

from .core import IAccountingGateway, IDocumentRepository
from .services.extraction import (
    Agents,
    ExtractionService,
    Transcribers,
    OrientationCorrector,
)
from .services.accounting_service import HttpAccountingGateway, ReferenceDataProvider
from .repositories import SqlModelDocumentRepository
from .services.document_service import InvoiceIntakeService
from .services.validation import VerificationService
from .settings import Settings


class ApplicationContainer:

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def settings(self) -> Settings:
        return self._settings

    @cached_property
    def accounting_gateway(self) -> IAccountingGateway:
        return HttpAccountingGateway(
            self._settings.accounting_base_url,
            self._settings.accounting_api_key,
            self._settings.accounting_timeout_seconds,
        )

    @cached_property
    def document_repository(self) -> IDocumentRepository:
        return SqlModelDocumentRepository(self._settings.database_path)

    @cached_property
    def transcribers(self) -> Transcribers:
        return Transcribers(self._settings)

    @cached_property
    def agents(self) -> Agents:
        return Agents(self._settings)

    @cached_property
    def orientation(self) -> OrientationCorrector:
        return OrientationCorrector(self._settings)

    @cached_property
    def extraction_service(self) -> ExtractionService:
        return ExtractionService(
            self._settings, self.transcribers, self.agents, self.orientation
        )

    @cached_property
    def verification_service(self) -> VerificationService:
        return VerificationService()

    @cached_property
    def reference_data(self) -> ReferenceDataProvider:
        return ReferenceDataProvider(self.accounting_gateway)

    @cached_property
    def intake_service(self) -> InvoiceIntakeService:
        return InvoiceIntakeService(
            settings=self._settings,
            repository=self.document_repository,
            reference_data=self.reference_data,
            extraction=self.extraction_service,
            verification=self.verification_service,
        )
