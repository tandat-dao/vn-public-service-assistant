"""SQLAlchemy models for procedures and their dependency graph."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    ARRAY,
    Boolean,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.form_template import FormTemplate


class ProcedureCategory(Base, TimestampMixin):
    __tablename__ = "procedure_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_slug: Mapped[str | None] = mapped_column(String(200), unique=True, nullable=True)
    ministry: Mapped[str | None] = mapped_column(String(200), nullable=True)

    procedures: Mapped[list["Procedure"]] = relationship("Procedure", back_populates="category")


class Procedure(Base, TimestampMixin):
    __tablename__ = "procedures"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("procedure_categories.id"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    legal_basis: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    processing_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fee_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    competent_authority: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_online: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    category: Mapped["ProcedureCategory | None"] = relationship(
        "ProcedureCategory", back_populates="procedures"
    )
    dependencies_as_dependent: Mapped[list["ProcedureDependency"]] = relationship(
        "ProcedureDependency",
        foreign_keys="ProcedureDependency.procedure_id",
        back_populates="procedure",
    )
    dependencies_as_prerequisite: Mapped[list["ProcedureDependency"]] = relationship(
        "ProcedureDependency",
        foreign_keys="ProcedureDependency.depends_on_procedure_id",
        back_populates="prerequisite",
    )
    form_templates: Mapped[list["FormTemplate"]] = relationship(
        "FormTemplate", back_populates="procedure"
    )


class ProcedureDependency(Base):
    __tablename__ = "procedure_dependencies"
    __table_args__ = (
        UniqueConstraint("procedure_id", "depends_on_procedure_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    procedure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("procedures.id"), nullable=False
    )
    depends_on_procedure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("procedures.id"), nullable=False
    )
    is_mandatory: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    condition_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    procedure: Mapped["Procedure"] = relationship(
        "Procedure", foreign_keys=[procedure_id], back_populates="dependencies_as_dependent"
    )
    prerequisite: Mapped["Procedure"] = relationship(
        "Procedure",
        foreign_keys=[depends_on_procedure_id],
        back_populates="dependencies_as_prerequisite",
    )
