"""Add domain column to procedures, administrative_units table, scope_coverage table.

Revision ID: 0003
Revises:     0002
Create Date: 2026-03-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Thing 1 — domain column on procedures table
    op.add_column(
        "procedures",
        sa.Column(
            "domain",
            sa.String(50),
            nullable=False,
            server_default="housing",
        ),
    )

    # Thing 2 — administrative_units table
    op.create_table(
        "administrative_units",
        sa.Column("code", sa.String(20), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("administrative_level", sa.String(20), nullable=False),
        sa.Column(
            "parent_code",
            sa.String(20),
            sa.ForeignKey("administrative_units.code"),
            nullable=True,
        ),
    )

    # Thing 3 — scope_coverage table
    op.create_table(
        "scope_coverage",
        sa.Column("location_scope", sa.String(50), nullable=False),
        sa.Column(
            "procedure_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("procedures.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("domain", sa.String(50), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_ingested_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("location_scope", "procedure_id"),
    )


def downgrade() -> None:
    op.drop_table("scope_coverage")
    op.drop_table("administrative_units")
    op.drop_column("procedures", "domain")
