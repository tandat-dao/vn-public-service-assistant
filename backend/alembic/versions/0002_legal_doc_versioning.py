"""Add superseded_by FK column to legal_documents for versioning.

Revision ID: 0002
Revises:     0001
Create Date: 2026-03-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "legal_documents",
        sa.Column(
            "superseded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("legal_documents.id"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("legal_documents", "superseded_by")
