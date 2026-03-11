"""Pydantic schemas for procedures and the execution plan DAG."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ProcedureBase(BaseModel):
    code: str
    name: str
    description: str | None = None
    legal_basis: list[str] | None = None
    processing_time_days: int | None = None
    fee_vnd: int | None = None
    competent_authority: str | None = None
    is_online: bool = False


class ProcedureCreate(ProcedureBase):
    category_id: uuid.UUID | None = None


class ProcedureRead(ProcedureBase):
    id: uuid.UUID
    category_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProcedureDependency(BaseModel):
    procedure_id: str
    depends_on_procedure_id: str
    is_mandatory: bool = True
    condition_description: str | None = None


class ProcedureStep(BaseModel):
    procedure_id: str
    procedure_name: str
    status: Literal["completed", "pending", "blocked"]
    order: int


class ProcedureExecutionPlan(BaseModel):
    target_procedure_id: str
    steps: list[ProcedureStep]
    missing_documents: list[str] = []
