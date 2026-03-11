"""initial_schema

Revision ID: 0001
Revises:
Create Date: 2026-03-05 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # procedure_categories
    op.create_table(
        "procedure_categories",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("name_slug", sa.String(200), nullable=True),
        sa.Column("ministry", sa.String(200), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name_slug"),
    )

    # procedures
    op.create_table(
        "procedures",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("legal_basis", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("processing_time_days", sa.Integer, nullable=True),
        sa.Column("fee_vnd", sa.Integer, nullable=True),
        sa.Column("competent_authority", sa.String(200), nullable=True),
        sa.Column("is_online", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["category_id"], ["procedure_categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    # procedure_dependencies
    op.create_table(
        "procedure_dependencies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("procedure_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("depends_on_procedure_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_mandatory", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("condition_description", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(["procedure_id"], ["procedures.id"]),
        sa.ForeignKeyConstraint(["depends_on_procedure_id"], ["procedures.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("procedure_id", "depends_on_procedure_id"),
    )

    # form_templates
    op.create_table(
        "form_templates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("procedure_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("form_code", sa.String(50), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("version", sa.String(20), nullable=True),
        sa.Column("pdf_template_path", sa.Text, nullable=False),
        sa.Column("fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["procedure_id"], ["procedures.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("form_code"),
    )

    # legal_documents
    op.create_table(
        "legal_documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("document_number", sa.String(100), nullable=True),
        sa.Column("document_type", sa.String(50), nullable=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("issuing_authority", sa.String(200), nullable=True),
        sa.Column("issue_date", sa.Date, nullable=True),
        sa.Column("effective_date", sa.Date, nullable=True),
        sa.Column("pdf_path", sa.Text, nullable=True),
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("chunk_count", sa.Integer, server_default=sa.text("0"), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_number"),
    )

    # procedure_legal_docs (association table)
    op.create_table(
        "procedure_legal_docs",
        sa.Column("procedure_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("legal_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["procedure_id"], ["procedures.id"]),
        sa.ForeignKeyConstraint(["legal_document_id"], ["legal_documents.id"]),
        sa.PrimaryKeyConstraint("procedure_id", "legal_document_id"),
    )

    # sessions
    op.create_table(
        "sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("personal_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "completed_procedure_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=True,
        ),
        sa.Column("form_fill_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("sessions")
    op.drop_table("procedure_legal_docs")
    op.drop_table("legal_documents")
    op.drop_table("form_templates")
    op.drop_table("procedure_dependencies")
    op.drop_table("procedures")
    op.drop_table("procedure_categories")
