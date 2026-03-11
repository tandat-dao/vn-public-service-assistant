"""Unit tests for app/core/procedure_graph.py.

Uses deterministic UUID strings throughout — no uuid.uuid4() calls in fixtures.
"""

import pytest

from app.core.procedure_graph import (
    build_adjacency_list,
    find_missing_prerequisites,
    resolve_execution_plan,
    topological_sort,
)
from app.schemas.procedure import ProcedureDependency

# ---------------------------------------------------------------------------
# Deterministic test IDs
# ---------------------------------------------------------------------------
A = "aaaaaaaa-0000-0000-0000-000000000001"
B = "bbbbbbbb-0000-0000-0000-000000000002"
C = "cccccccc-0000-0000-0000-000000000003"
D = "dddddddd-0000-0000-0000-000000000004"

NAMES = {A: "Procedure A", B: "Procedure B", C: "Procedure C", D: "Procedure D"}


def dep(procedure_id: str, depends_on: str, mandatory: bool = True) -> ProcedureDependency:
    return ProcedureDependency(
        procedure_id=procedure_id,
        depends_on_procedure_id=depends_on,
        is_mandatory=mandatory,
    )


# ---------------------------------------------------------------------------
# 1. Linear chain: A depends on B depends on C → plan for A = [C, B, A]
# ---------------------------------------------------------------------------
def test_linear_chain_order():
    deps = [dep(A, B), dep(B, C)]
    plan = resolve_execution_plan(A, deps, completed_ids=set(), procedure_names=NAMES)
    ids = [s.procedure_id for s in plan.steps]
    assert ids.index(C) < ids.index(B) < ids.index(A)


def test_linear_chain_statuses_all_pending():
    deps = [dep(A, B), dep(B, C)]
    plan = resolve_execution_plan(A, deps, completed_ids=set(), procedure_names=NAMES)
    statuses = {s.procedure_id: s.status for s in plan.steps}
    assert statuses[C] == "pending"
    assert statuses[B] == "blocked"   # C not yet completed
    assert statuses[A] == "blocked"   # B not yet completed


# ---------------------------------------------------------------------------
# 2. Diamond dependency: A→B, A→C, B→D, C→D → D first, then B&C (any order), then A
# ---------------------------------------------------------------------------
def test_diamond_dependency_d_first():
    deps = [dep(A, B), dep(A, C), dep(B, D), dep(C, D)]
    plan = resolve_execution_plan(A, deps, completed_ids=set(), procedure_names=NAMES)
    ids = [s.procedure_id for s in plan.steps]
    assert ids.index(D) < ids.index(B)
    assert ids.index(D) < ids.index(C)
    assert ids.index(B) < ids.index(A)
    assert ids.index(C) < ids.index(A)


# ---------------------------------------------------------------------------
# 3. Cycle detection: A→B, B→A → topological_sort raises ValueError
# ---------------------------------------------------------------------------
def test_cycle_detection_raises():
    adj = build_adjacency_list([dep(A, B), dep(B, A)])
    with pytest.raises(ValueError, match="Cycle detected"):
        topological_sort(adj)


# ---------------------------------------------------------------------------
# 4. Already completed: B is completed → plan still includes B, status=completed
# ---------------------------------------------------------------------------
def test_completed_step_marked():
    deps = [dep(A, B), dep(B, C)]
    plan = resolve_execution_plan(A, deps, completed_ids={B}, procedure_names=NAMES)
    statuses = {s.procedure_id: s.status for s in plan.steps}
    assert statuses[B] == "completed"


# ---------------------------------------------------------------------------
# 5. Blocked step: C not completed, B depends on C → B is blocked
# ---------------------------------------------------------------------------
def test_blocked_step():
    deps = [dep(A, B), dep(B, C)]
    plan = resolve_execution_plan(A, deps, completed_ids=set(), procedure_names=NAMES)
    statuses = {s.procedure_id: s.status for s in plan.steps}
    assert statuses[B] == "blocked"


# ---------------------------------------------------------------------------
# 6. No dependencies: standalone procedure returns plan with just itself, pending
# ---------------------------------------------------------------------------
def test_no_dependencies_standalone():
    plan = resolve_execution_plan(A, [], completed_ids=set(), procedure_names=NAMES)
    assert len(plan.steps) == 1
    assert plan.steps[0].procedure_id == A
    assert plan.steps[0].status == "pending"


# ---------------------------------------------------------------------------
# 7. find_missing_prerequisites: plan=[C,B,A], completed={C} → returns [B, A]
# ---------------------------------------------------------------------------
def test_find_missing_prerequisites():
    plan_order = [C, B, A]
    missing = find_missing_prerequisites(plan_order, completed={C})
    assert C not in missing
    assert B in missing
    assert A in missing
    # Order must be preserved
    assert missing.index(B) < missing.index(A)
