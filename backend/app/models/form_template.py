"""SQLAlchemy model for PDF form templates."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.procedure import Procedure


class FormTemplate(Base, TimestampMixin):
    __tablename__ = "form_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    procedure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("procedures.id"), nullable=False
    )
    form_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pdf_template_path: Mapped[str] = mapped_column(Text, nullable=False)
    fields: Mapped[dict] = mapped_column(JSONB, nullable=False)

    procedure: Mapped["Procedure"] = relationship("Procedure", back_populates="form_templates")
