"""Unit tests for enrichment_node and procedure_planner_fn.

All DB calls are mocked — no real database connections are used.
Covers all TASK-09 DoD checklist items.

Key invariants verified:
  - enrichment_node two-condition guard (both directions)
  - procedure_planner_fn existence check returns Vietnamese error
  - Empty procedure_execution_plan never returned without errors[]
  - resolve_execution_plan() is called (not re-implemented)
  - procedure_planner_fn is NOT in NODE_REGISTRY
  - enrichment_node never makes an LLM call
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.agents.nodes.enrichment import enrichment_node
from app.agents.nodes.procedure_planner import procedure_planner_fn
from app.agents.node_registry import NODE_REGISTRY
from app.schemas.procedure import ProcedureExecutionPlan, ProcedureStep


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_procedure(code: str, name: str, uuid_str: str | None = None) -> MagicMock:
    """Build a mock Procedure ORM object."""
    proc = MagicMock()
    proc.code = code
    proc.name = name
    proc.id = uuid_str or str(uuid.uuid5(uuid.NAMESPACE_DNS, code))
    return proc


def _make_dep_orm(
    procedure_id: str,
    depends_on_procedure_id: str,
    is_mandatory: bool = True,
    condition_description: str | None = None,
) -> MagicMock:
    """Build a mock ProcedureDependency ORM object."""
    dep = MagicMock()
    dep.procedure_id = procedure_id
    dep.depends_on_procedure_id = depends_on_procedure_id
    dep.is_mandatory = is_mandatory
    dep.condition_description = condition_description
    return dep


def _make_scalars_result(items: list) -> MagicMock:
    """Build a mock execute() result whose .scalars().all() returns items."""
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = items
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    return result_mock


def _make_scalar_one_result(value) -> MagicMock:
    """Build a mock execute() result whose .scalar_one_or_none() returns value."""
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = value
    return result_mock


def _make_execution_plan(
    target: str = "TTHC-001",
    steps: list[ProcedureStep] | None = None,
) -> ProcedureExecutionPlan:
    """Build a minimal ProcedureExecutionPlan for use in mocks."""
    if steps is None:
        steps = [
            ProcedureStep(
                procedure_id=target,
                procedure_name="Test Procedure",
                status="pending",
                order=0,
            )
        ]
    return ProcedureExecutionPlan(
        target_procedure_id=target,
        steps=steps,
        missing_documents=[],
    )


def _make_db_session(side_effects: list) -> AsyncMock:
    """Build an AsyncMock DB session whose execute() has the given side effects."""
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=side_effects)
    return session


def _patch_get_db(session):
    """Return a context manager that patches get_db to yield session."""
    async def _fake_db_gen():
        yield session

    return patch(
        "app.agents.nodes.procedure_planner.get_db",
        new=lambda: _fake_db_gen(),
    )


# ---------------------------------------------------------------------------
# enrichment_node tests — two-condition guard
# ---------------------------------------------------------------------------


async def test_enrichment_node_noop_when_no_target_procedure_id():
    """Returns {} when target_procedure_id is None."""
    state = {
        "user_message": "Xin chào",
        "session_id": "s1",
        "iteration_count": 0,
        "target_procedure_id": None,
        "execution_plan": ["form_filler_fn"],
    }
    result = await enrichment_node(state)
    assert result == {}


async def test_enrichment_node_noop_when_target_procedure_id_missing_from_state():
    """Returns {} when target_procedure_id key is absent from state."""
    state = {
        "user_message": "hello",
        "session_id": "s1",
        "iteration_count": 0,
        "execution_plan": ["form_filler_fn"],
    }
    result = await enrichment_node(state)
    assert result == {}


async def test_enrichment_node_noop_when_form_filler_not_in_plan():
    """Returns {} when target_procedure_id is set but form_filler_fn is not in plan."""
    state = {
        "user_message": "Tôi muốn hỏi về thủ tục",
        "session_id": "s1",
        "iteration_count": 0,
        "target_procedure_id": "TTHC-001",
        "execution_plan": ["rag_fn"],  # no form_filler_fn
    }
    result = await enrichment_node(state)
    assert result == {}


async def test_enrichment_node_noop_when_plan_is_empty():
    """Returns {} when execution_plan is empty (no form_filler_fn present)."""
    state = {
        "user_message": "hỏi về thủ tục",
        "session_id": "s1",
        "iteration_count": 0,
        "target_procedure_id": "TTHC-001",
        "execution_plan": [],
    }
    result = await enrichment_node(state)
    assert result == {}


async def test_enrichment_node_noop_when_only_condition_2_true():
    """Condition 1 fails — returns {} even with form_filler_fn in plan."""
    state = {
        "user_message": "điền form",
        "session_id": "s1",
        "iteration_count": 0,
        "target_procedure_id": None,  # condition 1 false
        "execution_plan": ["ocr_fn", "form_filler_fn"],  # condition 2 true
    }
    result = await enrichment_node(state)
    assert result == {}


async def test_enrichment_node_noop_when_only_condition_1_true():
    """Condition 2 fails — returns {} even with a valid target_procedure_id."""
    state = {
        "user_message": "câu hỏi pháp luật",
        "session_id": "s1",
        "iteration_count": 0,
        "target_procedure_id": "TTHC-001",  # condition 1 true
        "execution_plan": ["rag_fn"],  # condition 2 false
    }
    result = await enrichment_node(state)
    assert result == {}


async def test_enrichment_node_calls_planner_when_both_conditions_true():
    """Calls procedure_planner_fn when both conditions are met."""
    expected_plan = _make_execution_plan("TTHC-001")

    state = {
        "user_message": "Đăng ký thường trú",
        "session_id": "s1",
        "iteration_count": 0,
        "target_procedure_id": "TTHC-001",
        "execution_plan": ["ocr_fn", "form_filler_fn"],
        "completed_procedures": [],
    }

    with patch(
        "app.agents.nodes.enrichment.procedure_planner_fn",
        new=AsyncMock(return_value={"procedure_execution_plan": expected_plan}),
    ) as mock_planner:
        result = await enrichment_node(state)

    mock_planner.assert_called_once_with(state)
    assert "procedure_execution_plan" in result
    assert result["procedure_execution_plan"] == expected_plan


async def test_enrichment_node_returns_empty_dict_not_none():
    """No-op path returns {} not None — LangGraph requires a dict on every node return."""
    state = {
        "user_message": "hello",
        "session_id": "s1",
        "iteration_count": 0,
        "target_procedure_id": None,
        "execution_plan": [],
    }
    result = await enrichment_node(state)
    assert result is not None
    assert isinstance(result, dict)
    assert result == {}


async def test_enrichment_node_never_makes_llm_call():
    """LLMService is never instantiated or called by enrichment_node."""
    state = {
        "user_message": "thường trú",
        "session_id": "s1",
        "iteration_count": 0,
        "target_procedure_id": "TTHC-001",
        "execution_plan": ["form_filler_fn"],
        "completed_procedures": [],
    }

    with (
        patch("app.agents.nodes.enrichment.procedure_planner_fn", new=AsyncMock(return_value={})),
        patch("app.services.llm.LLMService") as mock_llm,
    ):
        await enrichment_node(state)
        mock_llm.assert_not_called()


# ---------------------------------------------------------------------------
# procedure_planner_fn tests — existence check
# ---------------------------------------------------------------------------


async def test_procedure_planner_returns_error_for_unknown_id():
    """Unknown target_procedure_id → errors[] contains Vietnamese message."""
    state = {
        "user_message": "hello",
        "session_id": "s1",
        "iteration_count": 0,
        "target_procedure_id": "UNKNOWN-999",
        "completed_procedures": [],
    }

    session = _make_db_session(
        side_effects=[_make_scalar_one_result(None)]  # procedure not found
    )

    with _patch_get_db(session):
        result = await procedure_planner_fn(state)

    assert result["procedure_execution_plan"] == []
    assert len(result["errors"]) > 0
    assert "Thủ tục không được hỗ trợ trong hệ thống hiện tại." in result["errors"]


@pytest.mark.parametrize("bad_code", ["INVALID", "TTHC-999", "", "random-uuid-string"])
async def test_procedure_planner_never_returns_empty_plan_without_error(bad_code: str):
    """Any unknown procedure code → errors[] is non-empty alongside empty plan."""
    state = {
        "user_message": "test",
        "session_id": "s1",
        "iteration_count": 0,
        "target_procedure_id": bad_code,
        "completed_procedures": [],
    }

    session = _make_db_session(
        side_effects=[_make_scalar_one_result(None)]
    )

    with _patch_get_db(session):
        result = await procedure_planner_fn(state)

    assert result["procedure_execution_plan"] == []
    assert result.get("errors") and len(result["errors"]) > 0, (
        "Empty procedure_execution_plan must always be accompanied by a non-empty errors[]"
    )


# ---------------------------------------------------------------------------
# procedure_planner_fn tests — successful plan resolution
# ---------------------------------------------------------------------------


async def test_procedure_planner_calls_resolve_execution_plan():
    """resolve_execution_plan() from procedure_graph.py is called with correct args."""
    tthc_001_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "TTHC-001"))
    target_proc = _make_procedure("TTHC-001", "Đăng ký thường trú", tthc_001_id)

    state = {
        "user_message": "thường trú",
        "session_id": "s1",
        "iteration_count": 0,
        "target_procedure_id": "TTHC-001",
        "completed_procedures": [],
    }

    expected_plan = _make_execution_plan("TTHC-001")

    session = _make_db_session(
        side_effects=[
            _make_scalar_one_result(target_proc),           # existence check
            _make_scalars_result([target_proc]),            # all procedures
            _make_scalars_result([]),                       # all dependencies (none)
        ]
    )

    with (
        _patch_get_db(session),
        patch(
            "app.agents.nodes.procedure_planner.resolve_execution_plan",
            return_value=expected_plan,
        ) as mock_resolve,
    ):
        result = await procedure_planner_fn(state)

    mock_resolve.assert_called_once()
    call_kwargs = mock_resolve.call_args
    assert call_kwargs.kwargs["target_procedure_id"] == "TTHC-001"
    assert call_kwargs.kwargs["completed_ids"] == set()
    assert "procedure_execution_plan" in result
    assert result["procedure_execution_plan"] == expected_plan


async def test_procedure_planner_marks_completed_steps():
    """Steps in state['completed_procedures'] are passed to resolve_execution_plan."""
    tthc_001_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "TTHC-001"))
    tthc_003_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "TTHC-003"))

    proc_001 = _make_procedure("TTHC-001", "Đăng ký thường trú", tthc_001_id)
    proc_003 = _make_procedure("TTHC-003", "Xác nhận cư trú", tthc_003_id)

    # TTHC-003 depends on TTHC-001
    dep_orm = _make_dep_orm(tthc_003_id, tthc_001_id, is_mandatory=True)

    state = {
        "user_message": "xác nhận cư trú",
        "session_id": "s1",
        "iteration_count": 0,
        "target_procedure_id": "TTHC-003",
        "completed_procedures": ["TTHC-001"],  # TTHC-001 already done
    }

    expected_plan = _make_execution_plan("TTHC-003")

    session = _make_db_session(
        side_effects=[
            _make_scalar_one_result(proc_003),
            _make_scalars_result([proc_001, proc_003]),
            _make_scalars_result([dep_orm]),
        ]
    )

    with (
        _patch_get_db(session),
        patch(
            "app.agents.nodes.procedure_planner.resolve_execution_plan",
            return_value=expected_plan,
        ) as mock_resolve,
    ):
        await procedure_planner_fn(state)

    mock_resolve.assert_called_once()
    assert mock_resolve.call_args.kwargs["completed_ids"] == {"TTHC-001"}


async def test_procedure_planner_builds_schema_deps_from_orm():
    """ORM dependency rows are correctly converted to ProcedureDependency schema objects."""
    tthc_001_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "TTHC-001"))
    tthc_003_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "TTHC-003"))

    proc_001 = _make_procedure("TTHC-001", "Đăng ký thường trú", tthc_001_id)
    proc_003 = _make_procedure("TTHC-003", "Xác nhận cư trú", tthc_003_id)

    dep_orm = _make_dep_orm(tthc_003_id, tthc_001_id, is_mandatory=True, condition_description=None)

    state = {
        "user_message": "xác nhận",
        "session_id": "s1",
        "iteration_count": 0,
        "target_procedure_id": "TTHC-003",
        "completed_procedures": [],
    }

    captured_deps = []

    def capture_resolve(**kwargs):
        captured_deps.extend(kwargs["all_dependencies"])
        return _make_execution_plan("TTHC-003")

    session = _make_db_session(
        side_effects=[
            _make_scalar_one_result(proc_003),
            _make_scalars_result([proc_001, proc_003]),
            _make_scalars_result([dep_orm]),
        ]
    )

    with (
        _patch_get_db(session),
        patch(
            "app.agents.nodes.procedure_planner.resolve_execution_plan",
            side_effect=capture_resolve,
        ),
    ):
        await procedure_planner_fn(state)

    # Verify the schema dependency uses codes, not UUIDs
    assert len(captured_deps) == 1
    dep = captured_deps[0]
    assert dep.procedure_id == "TTHC-003"
    assert dep.depends_on_procedure_id == "TTHC-001"
    assert dep.is_mandatory is True


async def test_procedure_planner_with_no_dependencies():
    """Standalone procedure (no edges) resolves to a single-step plan."""
    tthc_002_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "TTHC-002"))
    proc_002 = _make_procedure("TTHC-002", "Đăng ký tạm trú", tthc_002_id)

    state = {
        "user_message": "tạm trú",
        "session_id": "s1",
        "iteration_count": 0,
        "target_procedure_id": "TTHC-002",
        "completed_procedures": [],
    }

    expected_plan = _make_execution_plan("TTHC-002")

    session = _make_db_session(
        side_effects=[
            _make_scalar_one_result(proc_002),
            _make_scalars_result([proc_002]),
            _make_scalars_result([]),  # no dependencies
        ]
    )

    with (
        _patch_get_db(session),
        patch(
            "app.agents.nodes.procedure_planner.resolve_execution_plan",
            return_value=expected_plan,
        ),
    ):
        result = await procedure_planner_fn(state)

    assert "procedure_execution_plan" in result
    assert "errors" not in result or result.get("errors") == []


async def test_procedure_planner_completed_procedures_defaults_to_empty():
    """Missing completed_procedures key in state defaults to empty set."""
    tthc_001_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "TTHC-001"))
    proc_001 = _make_procedure("TTHC-001", "Đăng ký thường trú", tthc_001_id)

    state = {
        "user_message": "thường trú",
        "session_id": "s1",
        "iteration_count": 0,
        "target_procedure_id": "TTHC-001",
        # completed_procedures intentionally absent
    }

    expected_plan = _make_execution_plan("TTHC-001")

    session = _make_db_session(
        side_effects=[
            _make_scalar_one_result(proc_001),
            _make_scalars_result([proc_001]),
            _make_scalars_result([]),
        ]
    )

    with (
        _patch_get_db(session),
        patch(
            "app.agents.nodes.procedure_planner.resolve_execution_plan",
            return_value=expected_plan,
        ) as mock_resolve,
    ):
        await procedure_planner_fn(state)

    # Should have been called with an empty set, not raise KeyError
    assert mock_resolve.call_args.kwargs["completed_ids"] == set()


# ---------------------------------------------------------------------------
# NODE_REGISTRY integrity test
# ---------------------------------------------------------------------------


def test_procedure_planner_fn_not_in_node_registry():
    """'procedure_planner_fn' must NOT be a key in NODE_REGISTRY.

    procedure_planner_fn is a plain helper called by enrichment_node — it is
    never a valid execution_plan step and must never appear in NODE_REGISTRY.
    """
    assert "procedure_planner_fn" not in NODE_REGISTRY, (
        "procedure_planner_fn must never be in NODE_REGISTRY. "
        "It is called directly by enrichment_node, not via plan_executor."
    )


def test_node_registry_has_exactly_the_expected_worker_keys():
    """NODE_REGISTRY must contain exactly: rag_fn, ocr_fn, form_filler_fn."""
    expected = {"rag_fn", "ocr_fn", "form_filler_fn"}
    assert set(NODE_REGISTRY.keys()) == expected, (
        f"NODE_REGISTRY keys {set(NODE_REGISTRY.keys())} != expected {expected}"
    )
