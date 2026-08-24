from typing import Optional
import json
from pathlib import Path

from sqlalchemy import inspect
from sqlmodel import Session, SQLModel, create_engine, select

from ..core import (
    PathLike,
    DbDocument,
    DbDocumentRow,
    DbStoredDocument,
    Utils,
)

CONNECTION_TIMEOUT_SECONDS = 30.0


class DocumentRepository:

    def __init__(self, database_path: PathLike) -> None:
        self._database_path = Path(database_path)
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(
            f"sqlite:///{self._database_path.as_posix()}",
            connect_args={"check_same_thread": False, "timeout": CONNECTION_TIMEOUT_SECONDS},
        )
        self._drop_table_if_schema_changed()
        SQLModel.metadata.create_all(self._engine)

    def _drop_table_if_schema_changed(self) -> None:
        table = DbDocumentRow.__table__
        inspector = inspect(self._engine)
        if not inspector.has_table(table.name):
            return
        on_disk = {column["name"] for column in inspector.get_columns(table.name)}
        if on_disk == {column.name for column in table.columns}:
            return
        table.drop(self._engine)

    @staticmethod
    def _to_row(entity: DbStoredDocument) -> DbDocumentRow:
        document = entity.document
        registration = document.registration
        return DbDocumentRow(
            document_id=document.document_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            source_name=document.source_name,
            source_path=entity.source_path,
            partner_code=document.fields.partner_code,
            invoice_number=document.fields.invoice_number,
            fields_json=Utils.dump_json(document.fields.model_dump()),
            verification_json=Utils.dump_json(document.verification.model_dump()),
            status=str(document.status),
            blocking_reasons_json=Utils.dump_json(document.blocking_reasons),
            extra_failures_json=Utils.dump_json(document.extra_failures),
            model_used=document.model_used,
            input_tokens=document.input_tokens,
            output_tokens=document.output_tokens,
            registration_json=(
                Utils.dump_json(registration.model_dump()) if registration else None
            ),
        )

    @staticmethod
    def _to_stored_document(row: DbDocumentRow) -> DbStoredDocument:
        document = DbDocument(
            document_id=row.document_id,
            created_at=row.created_at,
            source_name=row.source_name,
            fields=json.loads(row.fields_json),
            verification=json.loads(row.verification_json),
            status=row.status,
            blocking_reasons=json.loads(row.blocking_reasons_json),
            extra_failures=json.loads(row.extra_failures_json),
            model_used=row.model_used,
            input_tokens=row.input_tokens,
            output_tokens=row.output_tokens,
            registration=json.loads(row.registration_json) if row.registration_json else None,
        )
        return DbStoredDocument(
            document=document,
            source_path=row.source_path,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def save(self, entity: DbStoredDocument) -> None:
        incoming = self._to_row(entity)
        with Session(self._engine) as session:
            existing = session.get(DbDocumentRow, incoming.document_id)
            if existing is None:
                session.add(incoming)
            else:
                for name, value in incoming.model_dump().items():
                    setattr(existing, name, value)
                session.add(existing)
            session.commit()

    def get(self, document_id: str) -> Optional[DbStoredDocument]:
        with Session(self._engine) as session:
            row = session.get(DbDocumentRow, document_id)
            return self._to_stored_document(row) if row else None

    def list_all(self) -> list[DbStoredDocument]:
        with Session(self._engine) as session:
            rows = session.exec(
                select(DbDocumentRow).order_by(DbDocumentRow.created_at, DbDocumentRow.source_name)
            ).all()
            return [self._to_stored_document(row) for row in rows]

    def find_by_source_path(self, source_path: str) -> Optional[DbStoredDocument]:
        with Session(self._engine) as session:
            row = session.exec(
                select(DbDocumentRow).where(DbDocumentRow.source_path == source_path)
            ).first()
            return self._to_stored_document(row) if row else None

    def delete(self, document_id: str) -> None:
        with Session(self._engine) as session:
            row = session.get(DbDocumentRow, document_id)
            if row is None:
                return
            session.delete(row)
            session.commit()

    def find_duplicate(
        self, partner_code: Optional[str], invoice_number: Optional[str], exclude_document_id: Optional[str]
    ) -> Optional[str]:
        if not partner_code or not invoice_number:
            return None
        with Session(self._engine) as session:
            row = session.exec(
                select(DbDocumentRow)
                .where(DbDocumentRow.partner_code == partner_code)
                .where(DbDocumentRow.invoice_number == invoice_number)
                .where(DbDocumentRow.document_id != (exclude_document_id or ""))
                .order_by(DbDocumentRow.created_at)
            ).first()
            return row.document_id if row else None
