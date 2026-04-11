"""Unit tests for plan_executor_node and route_plan_executor.

All worker function calls are mocked — no real infrastructure.

Covers all 8 TASK-11 plan_executor DoD test items:
  1. test_plan_executor_single_wave_no_dependencies
  2. test_plan_executor_dependency_respected
  3. test_plan_executor_form_filler_runs_after_ocr
  4. test_plan_executor_circuit_breaker_fires
  5. test_plan_executor_routes_to_synthesizer_when_plan_exhausted
  6. test_plan_executor_routes_to_self_when_plan_not_exhausted
  7. test_plan_executor_worker_exception_adds_to_errors
  8. test_node_registry_keys_match_valid_plan_steps
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_state(**overrides) -> dict:
    state: dict = {
        "user_message": "Tôi cần đăng ký thường trú",
        "session_id": "sess-pe-test",
        "iteration_count": 0,
        "execution_plan": [],
        "plan_cursor": 0,
        "errors": [],
        "retrieved_chunks": [],
        "citations": [],
        "personal_data": None,
    }
    state.update(overrides)
    return state


def _make_registry(
    rag_return: dict | None = None,
    ocr_return: dict | None = None,
    form_return: dict | None = None,
    rag_raises: Exception | None = None,
    ocr_raises: Exception | None = None,
) -> dict:
    """Build a fake NODE_REGISTRY dict with AsyncMock workers."""
    registry: dict = {}

    if rag_raises is not None:
        registry["rag_fn"] = AsyncMock(side_effect=rag_raises)
    else:
        registry["rag_fn"] = AsyncMock(return_value=rag_return or {"final_response": "RAG answer"})

    if ocr_raises is not None:
        registry["ocr_fn"] = AsyncMock(side_effect=ocr_raises)
    else:
        registry["ocr_fn"] = AsyncMock(return_value=ocr_return or {"document_type": "cccd"})

    registry["form_filler_fn"] = AsyncMock(return_value=form_return or {"form_fill_complete": True})
    return registry


# ---------------------------------------------------------------------------
# Test 1 — single wave, no dependencies: both rag_fn and ocr_fn run together
# ---------------------------------------------------------------------------

async def test_plan_executor_single_wave_no_dependencies():
    """rag_fn and ocr_fn have no dependencies — both run in the same wave."""
    registry = _make_registry()
    deps = {"rag_fn": [], "ocr_fn": [], "form_filler_fn": ["ocr_fn"]}

    state = _base_state(
        execution_plan=["rag_fn", "ocr_fn"],
        plan_cursor=0,
    )

    with patch("app.agents.nodes.plan_executor.NODE_REGISTRY", registry), \
         patch("app.agents.nodes.plan_executor.NODE_DEPENDENCIES", deps):
        from app.agents.nodes.plan_executor import plan_executor_node
        result = await plan_executor_node(state)

    # Both workers called exactly once
    registry["rag_fn"].assert_called_once_with(state)
    registry["ocr_fn"].assert_called_once_with(state)
    # Cursor advanced by wave size (2)
    assert result["plan_cursor"] == 2


# ---------------------------------------------------------------------------
# Test 2 — dependency respected: form_filler not in wave 1 when ocr hasn't run
# ---------------------------------------------------------------------------

async def test_plan_executor_dependency_respected():
    """form_filler_fn depends on ocr_fn — must NOT run in wave 1 when cursor=0."""
    registry = _make_registry()
    deps = {"rag_fn": [], "ocr_fn": [], "form_filler_fn": ["ocr_fn"]}

    state = _base_state(
        execution_plan=["ocr_fn", "form_filler_fn"],
        plan_cursor=0,
    )

    with patch("app.agents.nodes.plan_executor.NODE_REGISTRY", registry), \
         patch("app.agents.nodes.plan_executor.NODE_DEPENDENCIES", deps):
        from app.agents.nodes.plan_executor import plan_executor_node
        result = await plan_executor_node(state)

    # Only ocr_fn runs in wave 1
    registry["ocr_fn"].assert_called_once()
    registry["form_filler_fn"].assert_not_called()
    # Cursor advanced by 1 (only ocr_fn in wave)
    assert result["plan_cursor"] == 1


# ---------------------------------------------------------------------------
# Test 3 — form_filler runs after ocr: cursor=1 means ocr already ran
# ---------------------------------------------------------------------------

async def test_plan_executor_form_filler_runs_after_ocr():
    """With cursor=1, ocr_fn is in execution_plan[:1] — form_filler_fn is ready."""
    registry = _make_registry()
    deps = {"rag_fn": [], "ocr_fn": [], "form_filler_fn": ["ocr_fn"]}

    state = _base_state(
        execution_plan=["ocr_fn", "form_filler_fn"],
        plan_cursor=1,  # ocr_fn already ran
    )

    with patch("app.agents.nodes.plan_executor.NODE_REGISTRY", registry), \
         patch("app.agents.nodes.plan_executor.NODE_DEPENDENCIES", deps):
        from app.agents.nodes.plan_executor import plan_executor_node
        result = await plan_executor_node(state)

    # form_filler_fn runs, ocr_fn does not
    registry["form_filler_fn"].assert_called_once()
    registry["ocr_fn"].assert_not_called()
    assert result["plan_cursor"] == 2


# ---------------------------------------------------------------------------
# Test 4 — circuit-breaker: no workers called when plan_cursor >= MAX_PLAN_STEPS
# ---------------------------------------------------------------------------

async def test_plan_executor_circuit_breaker_fires():
    """Circuit-breaker fires when plan_cursor equals MAX_PLAN_STEPS (8)."""
    registry = _make_registry()
    deps = {"rag_fn": [], "ocr_fn": [], "form_filler_fn": ["ocr_fn"]}

    state = _base_state(
        execution_plan=["rag_fn"],
        plan_cursor=8,  # already at MAX_PLAN_STEPS
        errors=[],
    )

    with patch("app.agents.nodes.plan_executor.NODE_REGISTRY", registry), \
         patch("app.agents.nodes.plan_executor.NODE_DEPENDENCIES", deps), \
         patch("app.agents.nodes.plan_executor.MAX_PLAN_STEPS", 8):
        from app.agents.nodes.plan_executor import plan_executor_node
        result = await plan_executor_node(state)

    # No workers called
    registry["rag_fn"].assert_not_called()
    # Errors list is non-empty
    assert len(result.get("errors", [])) > 0


# ---------------------------------------------------------------------------
# Test 5 — route_plan_executor → synthesizer when plan exhausted
# ---------------------------------------------------------------------------

def test_plan_executor_routes_to_synthesizer_when_plan_exhausted():
    """After last wave, cursor == len(plan) → route to synthesizer_node."""
    from app.agents.nodes.plan_executor import route_plan_executor

    state = _base_state(
        execution_plan=["rag_fn"],
        plan_cursor=1,  # cursor == len(plan) → exhausted
    )

    assert route_plan_executor(state) == "synthesizer_node"


# ---------------------------------------------------------------------------
# Test 6 — route_plan_executor → self when plan not exhausted
# ---------------------------------------------------------------------------

def test_plan_executor_routes_to_self_when_plan_not_exhausted():
    """After wave 1 of a 2-step plan, cursor=1 < 2 → loop back."""
    from app.agents.nodes.plan_executor import route_plan_executor

    state = _base_state(
        execution_plan=["ocr_fn", "form_filler_fn"],
        plan_cursor=1,  # still one step left
    )

    assert route_plan_executor(state) == "plan_executor_node"


# ---------------------------------------------------------------------------
# Test 7 — worker exception: error appended, node does not raise
# ---------------------------------------------------------------------------

async def test_plan_executor_worker_exception_adds_to_errors():
    """An exception inside a worker is caught — errors[] is populated, node returns a dict."""
    registry = _make_registry(rag_raises=RuntimeError("Qdrant timeout"))
    deps = {"rag_fn": [], "ocr_fn": [], "form_filler_fn": ["ocr_fn"]}

    state = _base_state(
        execution_plan=["rag_fn"],
        plan_cursor=0,
        errors=[],
    )

    with patch("app.agents.nodes.plan_executor.NODE_REGISTRY", registry), \
         patch("app.agents.nodes.plan_executor.NODE_DEPENDENCIES", deps):
        from app.agents.nodes.plan_executor import plan_executor_node
        result = await plan_executor_node(state)

    assert isinstance(result, dict)
    assert len(result.get("errors", [])) > 0
    assert "rag_fn" in result["errors"][0] or "Lỗi" in result["errors"][0]


# ---------------------------------------------------------------------------
# Test 8 — NODE_REGISTRY consistency with VALID_PLAN_STEPS
# ---------------------------------------------------------------------------

def test_node_registry_keys_match_valid_plan_steps():
    """NODE_REGISTRY keys must exactly match VALID_PLAN_STEPS; no procedure_planner_fn."""
    from app.agents.node_registry import NODE_REGISTRY, VALID_PLAN_STEPS

    assert set(NODE_REGISTRY.keys()) == set(VALID_PLAN_STEPS)
    assert "procedure_planner_fn" not in NODE_REGISTRY
    assert "procedure_planner_fn" not in VALID_PLAN_STEPS
