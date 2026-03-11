"""Procedures API routes."""

from fastapi import APIRouter

from app.schemas.procedure import (
    ProcedureCreate,
    ProcedureDependency,
    ProcedureExecutionPlan,
    ProcedureRead,
)

router = APIRouter()


@router.get("", response_model=list[ProcedureRead])
async def list_procedures() -> list[ProcedureRead]:
    """List all procedures."""
    raise NotImplementedError


@router.post("", response_model=ProcedureRead)
async def create_procedure(data: ProcedureCreate) -> ProcedureRead:
    """Create a new procedure."""
    raise NotImplementedError


@router.get("/{procedure_id}", response_model=ProcedureRead)
async def get_procedure(procedure_id: str) -> ProcedureRead:
    """Get a single procedure by ID."""
    raise NotImplementedError


@router.get("/{procedure_id}/plan", response_model=ProcedureExecutionPlan)
async def get_procedure_plan(procedure_id: str) -> ProcedureExecutionPlan:
    """Resolve and return the execution plan for a target procedure."""
    raise NotImplementedError


@router.get("/{procedure_id}/dependencies", response_model=list[ProcedureDependency])
async def get_procedure_dependencies(procedure_id: str) -> list[ProcedureDependency]:
    """Return the dependency list for a procedure."""
    raise NotImplementedError
