from collections.abc import Sequence
from typing import Optional, Protocol, TypeVar
from .db import DbStoredDocument
from .md import MdPageImage
from .requests import ReqRegistration
from .responses import PartnerDirectory, ResRegistrationReceipt, TaxRateTable


TEntity = TypeVar("TEntity")
TKey = TypeVar("TKey")


class IRepository(Protocol[TEntity, TKey]):

    def get(self, key: TKey) -> Optional[TEntity]:
        ...

    def list_all(self) -> Sequence[TEntity]:
        ...

    def save(self, entity: TEntity) -> None:
        ...


class IDocumentRepository(IRepository[DbStoredDocument, str], Protocol):

    def find_duplicate(
        self, partner_code: Optional[str], invoice_number: Optional[str], exclude_document_id: Optional[str]
    ) -> Optional[str]:
        ...

    def find_by_source_path(self, source_path: str) -> Optional[DbStoredDocument]:
        ...


class IAccountingGateway(Protocol):

    def is_reachable(self) -> bool:
        ...

    def fetch_partners(self) -> PartnerDirectory:
        ...

    def fetch_tax_rates(self) -> TaxRateTable:
        ...

    def register_invoice(self, request: ReqRegistration) -> ResRegistrationReceipt:
        ...


class ITranscriber(Protocol):

    def to_markdown(self, page: MdPageImage) -> str:
        ...
