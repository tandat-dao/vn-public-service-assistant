"""procedure_planner_fn — pre-flight enrichment helper.

Called DIRECTLY by enrichment_node. This is NOT a LangGraph graph node
and is NOT registered in NODE_REGISTRY. It must never appear as a valid
execution_plan step.

Responsibilities:
  1. Existence check — returns a named error if target_procedure_id is unknown.
  2. Load all dependency edges from PostgreSQL.
  3. Call resolve_execution_plan() from procedure_graph.py — NEVER re-implement
     topological sort logic here.

An empty procedure_execution_plan is NEVER a valid return without a
corresponding errors[] entry. Silent failure is prohibited.
"""

from sqlalchemy import select

from app.agents.state import AgentState
from app.core.procedure_graph import resolve_execution_plan
from app.dependencies import get_db
from app.models.procedure import Procedure
from app.models.procedure import ProcedureDependency as ProcedureDependencyModel
from app.schemas.procedure import ProcedureDependency


async def procedure_planner_fn(state: AgentState) -> dict:
    """Resolve procedure dependencies and build an ordered execution plan.

    Args:
        state: Current AgentState. Reads:
            - state["target_procedure_id"]: procedure code (e.g. "TTHC-001")
            - state["completed_procedures"]: list of completed procedure codes

    Returns:
        On success:
            {"procedure_execution_plan": ProcedureExecutionPlan}
        On unknown procedure_id or empty plan:
            {"procedure_execution_plan": [], "errors": ["<Vietnamese message>"]}
    """
    target_code: str = state.get("target_procedure_id")  # type: ignore[assignment]

    async for db in get_db():
        # ------------------------------------------------------------------
        # Step 1 — Existence check (out-of-scope validation, Layer 1)
        # ------------------------------------------------------------------
        proc_result = await db.execute(
            select(Procedure).where(Procedure.code == target_code)
        )
        target_proc = proc_result.scalar_one_or_none()

        if target_proc is None:
            return {
                "procedure_execution_plan": [],
                "errors": ["Thủ tục không được hỗ trợ trong hệ thống hiện tại."],
            }

        # ------------------------------------------------------------------
        # Step 2 — Load all procedures to build code ↔ id mapping and names
        # ------------------------------------------------------------------
        all_procs_result = await db.execute(select(Procedure))
        all_procs = list(all_procs_result.scalars().all())

        # UUID string → procedure code
        id_to_code: dict[str, str] = {str(p.id): p.code for p in all_procs}
        # procedure code → display name (for ProcedureStep.procedure_name)
        procedure_names: dict[str, str] = {p.code: p.name for p in all_procs}

        # ------------------------------------------------------------------
        # Step 3 — Load all dependency edges and convert to schema objects
        # (using codes, not UUIDs, so they match target_procedure_id format)
        # ------------------------------------------------------------------
        all_deps_result = await db.execute(select(ProcedureDependencyModel))
        all_deps_orm = list(all_deps_result.scalars().all())

        schema_deps: list[ProcedureDependency] = []
        for dep in all_deps_orm:
            proc_code = id_to_code.get(str(dep.procedure_id))
            depends_on_code = id_to_code.get(str(dep.depends_on_procedure_id))
            if proc_code and depends_on_code:
                schema_deps.append(
                    ProcedureDependency(
                        procedure_id=proc_code,
                        depends_on_procedure_id=depends_on_code,
                        is_mandatory=dep.is_mandatory,
                        condition_description=dep.condition_description,
                    )
                )

        # ------------------------------------------------------------------
        # Step 4 — Topological sort via procedure_graph.py
        # NEVER re-implement topological sort logic here (CLAUDE.md Rule 1)
        # ------------------------------------------------------------------
        completed_ids: set[str] = set(state.get("completed_procedures") or [])
        execution_plan = resolve_execution_plan(
            target_procedure_id=target_code,
            all_dependencies=schema_deps,
            completed_ids=completed_ids,
            procedure_names=procedure_names,
        )

        return {"procedure_execution_plan": execution_plan}
