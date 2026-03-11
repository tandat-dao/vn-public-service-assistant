"""SQLAlchemy model for user sessions."""

import uuid

from sqlalchemy import ARRAY
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Session(Base, TimestampMixin):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    personal_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    completed_procedure_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )
    form_fill_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
