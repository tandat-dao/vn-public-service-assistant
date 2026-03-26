"""Unit tests — ORM models match the migration schema (0001_initial_schema.py).

All assertions use SQLAlchemy table metadata only — no DB connection required.
"""

import uuid

import pytest
from sqlalchemy import ARRAY
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.form_template import FormTemplate
from app.models.legal_document import LegalDocument, ProcedureLegalDoc
from app.models.procedure import Procedure, ProcedureCategory, ProcedureDependency
from app.models.session import Session


def _col(model, name):
    return model.__table__.columns[name]


# ---------------------------------------------------------------------------
# Table names
# ---------------------------------------------------------------------------

class TestTableNames:
    def test_procedure_categories(self):
        assert ProcedureCategory.__tablename__ == "procedure_categories"

    def test_procedures(self):
        assert Procedure.__tablename__ == "procedures"

    def test_procedure_dependencies(self):
        assert ProcedureDependency.__tablename__ == "procedure_dependencies"

    def test_form_templates(self):
        assert FormTemplate.__tablename__ == "form_templates"

    def test_legal_documents(self):
        assert LegalDocument.__tablename__ == "legal_documents"

    def test_sessions(self):
        assert Session.__tablename__ == "sessions"

    def test_procedure_legal_docs_association(self):
        assert ProcedureLegalDoc.name == "procedure_legal_docs"


# ---------------------------------------------------------------------------
# Primary keys — UUID, named "id"
# ---------------------------------------------------------------------------

class TestPrimaryKeys:
    @pytest.mark.parametrize("model", [
        ProcedureCategory, Procedure, ProcedureDependency,
        FormTemplate, LegalDocument, Session,
    ])
    def test_pk_is_uuid_named_id(self, model):
        pk_cols = [c for c in model.__table__.columns if c.primary_key]
        assert len(pk_cols) == 1
        assert pk_cols[0].name == "id"
        assert isinstance(pk_cols[0].type, UUID)


# ---------------------------------------------------------------------------
# JSONB columns
# ---------------------------------------------------------------------------

class TestJsonbColumns:
    def test_session_personal_data_is_jsonb(self):
        col = _col(Session, "personal_data")
        assert isinstance(col.type, JSONB)
        assert col.nullable

    def test_session_form_fill_state_is_jsonb(self):
        col = _col(Session, "form_fill_state")
        assert isinstance(col.type, JSONB)
        assert col.nullable

    def test_form_template_fields_is_jsonb(self):
        col = _col(FormTemplate, "fields")
        assert isinstance(col.type, JSONB)
        assert not col.nullable


# ---------------------------------------------------------------------------
# ARRAY(UUID) — sessions.completed_procedure_ids
# ---------------------------------------------------------------------------

class TestArrayColumns:
    def test_completed_procedure_ids_is_array(self):
        col = _col(Session, "completed_procedure_ids")
        assert isinstance(col.type, ARRAY)
        assert col.nullable


# ---------------------------------------------------------------------------
# Dependency edge columns
# ---------------------------------------------------------------------------

class TestDependencyEdgeColumns:
    def test_procedure_id_fk(self):
        col = _col(ProcedureDependency, "procedure_id")
        assert not col.nullable

    def test_depends_on_procedure_id_fk(self):
        col = _col(ProcedureDependency, "depends_on_procedure_id")
        assert not col.nullable

    def test_condition_description_nullable(self):
        col = _col(ProcedureDependency, "condition_description")
        assert col.nullable


# ---------------------------------------------------------------------------
# Smoke test: resolve_execution_plan returns non-trivial plan with new edges
# ---------------------------------------------------------------------------

class TestDagSmoke:
    def test_ttdn003_plan_is_non_trivial(self):
        from app.core.procedure_graph import resolve_execution_plan
        from app.schemas.procedure import ProcedureDependency as DepSchema

        ttdn_001 = str(uuid.uuid5(uuid.NAMESPACE_DNS, "TTDN-001"))
        ttdn_002 = str(uuid.uuid5(uuid.NAMESPACE_DNS, "TTDN-002"))
        ttdn_003 = str(uuid.uuid5(uuid.NAMESPACE_DNS, "TTDN-003"))

        deps = [
            DepSchema(
                procedure_id=ttdn_003,
                depends_on_procedure_id=ttdn_001,
                is_mandatory=True,
            ),
            DepSchema(
                procedure_id=ttdn_003,
                depends_on_procedure_id=ttdn_002,
                is_mandatory=False,
                condition_description="Nếu là cư dân tạm trú",
            ),
        ]

        names = {ttdn_001: "Đăng ký thường trú", ttdn_002: "Đăng ký tạm trú", ttdn_003: "Xác nhận cư trú"}
        plan = resolve_execution_plan(ttdn_003, deps, completed_ids=set(), procedure_names=names)

        procedure_ids_in_plan = [step.procedure_id for step in plan.steps]
        # All 3 procedures must appear in the plan
        assert ttdn_001 in procedure_ids_in_plan
        assert ttdn_002 in procedure_ids_in_plan
        assert ttdn_003 in procedure_ids_in_plan
        # TTDN-003 must come last
        assert procedure_ids_in_plan.index(ttdn_003) > procedure_ids_in_plan.index(ttdn_001)
