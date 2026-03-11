"""SQLAlchemy models for legal documents and the procedure↔document association."""

import uuid
from datetime import date, datetime

from sqlalchemy import Column, Date, ForeignKey, Integer, String, Table, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

# Many-to-many association table: procedures ↔ legal documents
ProcedureLegalDoc = Table(
    "procedure_legal_docs",
    Base.metadata,
    Column("procedure_id", UUID(as_uuid=True), ForeignKey("procedures.id"), primary_key=True),
    Column(
        "legal_document_id",
        UUID(as_uuid=True),
        ForeignKey("legal_documents.id"),
        primary_key=True,
    ),
)


class LegalDocument(Base, TimestampMixin):
    __tablename__ = "legal_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    document_number: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    document_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    issuing_authority: Mapped[str | None] = mapped_column(String(200), nullable=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingested_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    chunk_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
