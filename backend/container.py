from functools import cached_property

from .core import IAccountingGateway, IDocumentRepository, ITranscriber
from .services.extraction import (
    Agents,
    ExtractionService,
    MarkitdownTranscriber,
)
from .services.accounting_service import HttpAccountingGateway, ReferenceDataProvider
from .services.document_service import InvoiceIntakeService, SqlModelDocumentRepository
from .services.validation_service import VerificationService
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
    def transcriber(self) -> ITranscriber:
        return MarkitdownTranscriber(self._settings)

    @cached_property
    def agents(self) -> Agents:
        return Agents(self._settings)

    @cached_property
    def extraction_service(self) -> ExtractionService:
        return ExtractionService(self._settings, self.transcriber, self.agents)

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
