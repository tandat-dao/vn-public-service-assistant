"""Unit tests for synthesizer_node and build_synthesis_prompt.

All LLM calls are mocked — no real API calls are made.

Covers all 8 TASK-10 DoD test items:
  1. test_synthesizer_error_mode
  2. test_synthesizer_form_fill_complete_mode
  3. test_synthesizer_form_fill_partial_mode
  4. test_synthesizer_rag_only_mode_no_scope_notice
  5. test_synthesizer_rag_only_mode_with_scope_notice
  6. test_synthesizer_fallback_mode
  7. test_synthesizer_scope_level_mapping
  8. test_synthesizer_llm_failure_returns_hardcoded_fallback
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.prompts.synthesis_prompt import _scope_level_name


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chunk(article: str = "20", document_number: str = "62/2021/NĐ-CP"):
    """Build a minimal DocumentChunk (Pydantic) for use in state fixtures."""
    from app.schemas.rag import DocumentChunk

    return DocumentChunk(
        point_id=f"pt-{article}",
        legal_document_id="doc-001",
        document_number=document_number,
        article_number=article,
        content="Nội dung điều luật về đăng ký cư trú.",
        procedure_tags=["TTHC-001"],
        status="active",
        rrf_score=0.88,
    )


def _base_state(**overrides) -> dict:
    """Build a minimal valid AgentState dict for synthesizer tests."""
    state: dict = {
        "user_message": "Tôi cần đăng ký thường trú",
        "session_id": "sess-synth-test",
        "iteration_count": 0,
        "execution_plan": ["rag_fn"],
        "plan_cursor": 1,
        "errors": [],
        "retrieved_chunks": [],
        "citations": [],
        "conversation_history": [],
        "final_response": "",
        "response_metadata": {},
        "form_fill_complete": False,
        "unfilled_required_fields": [],
        "filled_form_path": None,
        "scope_used": None,
        "filing_jurisdiction": None,
        "target_procedure_id": None,
        "procedure_execution_plan": [],
        "personal_data": None,
        "domain": None,
    }
    state.update(overrides)
    return state


# ---------------------------------------------------------------------------
# Fixture: mock_llm
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm():
    """Patch _get_llm in synthesizer module to return an AsyncMock LLMService."""
    svc = MagicMock()
    svc.async_invoke = AsyncMock(return_value="Đây là câu trả lời giả từ LLM.")
    with patch("app.agents.nodes.synthesizer._get_llm", return_value=svc):
        yield svc


# ---------------------------------------------------------------------------
# Test 1 — error mode
# ---------------------------------------------------------------------------

async def test_synthesizer_error_mode(mock_llm):
    """Error mode fires when errors list is non-empty; LLM IS called."""
    from app.agents.nodes.synthesizer import synthesizer_node

    state = _base_state(
        errors=["Lỗi kết nối Qdrant"],
        retrieved_chunks=[],
    )

    result = await synthesizer_node(state)

    assert isinstance(result, dict)
    assert result["response_metadata"]["mode"] == "error"
    assert "final_response" in result
    mock_llm.async_invoke.assert_called_once()


# ---------------------------------------------------------------------------
# Test 2 — form fill complete mode
# ---------------------------------------------------------------------------

async def test_synthesizer_form_fill_complete_mode(mock_llm):
    """form_fill_complete mode fires when form_fill_complete is True."""
    from app.agents.nodes.synthesizer import synthesizer_node

    state = _base_state(
        form_fill_complete=True,
        filled_form_path="forms/sess-synth-test/TTHC-001.pdf",
        errors=[],
    )

    result = await synthesizer_node(state)

    assert result["response_metadata"]["mode"] == "form_fill_complete"
    assert "final_response" in result
    mock_llm.async_invoke.assert_called_once()


# ---------------------------------------------------------------------------
# Test 3 — form fill partial mode
# ---------------------------------------------------------------------------

async def test_synthesizer_form_fill_partial_mode(mock_llm):
    """form_fill_partial mode fires when unfilled_required_fields is non-empty."""
    from app.agents.nodes.synthesizer import synthesizer_node

    state = _base_state(
        form_fill_complete=False,
        unfilled_required_fields=["cmnd", "ngay_sinh"],
        filled_form_path="tmp/sess-synth-test/TTHC-001.pdf",
        errors=[],
    )

    result = await synthesizer_node(state)

    assert result["response_metadata"]["mode"] == "form_fill_partial"
    assert "final_response" in result
    mock_llm.async_invoke.assert_called_once()


# ---------------------------------------------------------------------------
# Test 4 — rag_only mode, no scope notice → LLM skipped
# ---------------------------------------------------------------------------

async def test_synthesizer_rag_only_mode_no_scope_notice(mock_llm):
    """RAG-only mode with matching jurisdiction → LLM NOT called (direct passthrough)."""
    from app.agents.nodes.synthesizer import synthesizer_node

    rag_answer = "Theo [Điều 20, Nghị định 62/2021/NĐ-CP], hồ sơ gồm có..."
    state = _base_state(
        retrieved_chunks=[_make_chunk()],
        form_fill_complete=False,
        unfilled_required_fields=[],
        errors=[],
        final_response=rag_answer,
        response_metadata={"rag_confidence": "high"},
        # Same scope → no fallback
        scope_used="VN-HCM",
        filing_jurisdiction="VN-HCM",
    )

    result = await synthesizer_node(state)

    assert result["response_metadata"]["mode"] == "rag_only"
    assert result["final_response"] == rag_answer
    assert result["response_metadata"]["scope_notice_included"] is False
    # LLM must NOT be called in this optimisation path
    mock_llm.async_invoke.assert_not_called()


# ---------------------------------------------------------------------------
# Test 5 — rag_only mode with scope notice → LLM IS called
# ---------------------------------------------------------------------------

async def test_synthesizer_rag_only_mode_with_scope_notice(mock_llm):
    """RAG-only mode with scope fallback → LLM IS called to weave in scope notice."""
    from app.agents.nodes.synthesizer import synthesizer_node

    state = _base_state(
        retrieved_chunks=[_make_chunk()],
        form_fill_complete=False,
        unfilled_required_fields=[],
        errors=[],
        final_response="Nội dung trả lời pháp lý.",
        response_metadata={"rag_confidence": "medium"},
        # Scope fallback: requested ward-level, but only national found
        filing_jurisdiction="VN-HCM-26968",
        scope_used="VN",
    )

    result = await synthesizer_node(state)

    assert result["response_metadata"]["mode"] == "rag_only"
    assert result["response_metadata"]["scope_notice_included"] is True
    mock_llm.async_invoke.assert_called_once()


# ---------------------------------------------------------------------------
# Test 6 — fallback mode
# ---------------------------------------------------------------------------

async def test_synthesizer_fallback_mode(mock_llm):
    """Fallback mode fires when no errors, no chunks, no form fill state."""
    from app.agents.nodes.synthesizer import synthesizer_node

    state = _base_state(
        retrieved_chunks=[],
        errors=[],
        form_fill_complete=False,
        unfilled_required_fields=[],
    )

    result = await synthesizer_node(state)

    assert result["response_metadata"]["mode"] == "fallback"
    assert "final_response" in result
    mock_llm.async_invoke.assert_called_once()


# ---------------------------------------------------------------------------
# Test 7 — scope level mapping (pure unit test, no synthesizer_node invocation)
# ---------------------------------------------------------------------------

def test_synthesizer_scope_level_mapping():
    """_scope_level_name maps scope codes to Vietnamese level names correctly."""
    # National: 1 part
    result_vn = _scope_level_name("VN")
    assert "quốc gia" in result_vn

    # Province / city: 2 parts
    result_hcm = _scope_level_name("VN-HCM")
    assert "thành phố" in result_hcm

    # Ward: 3 parts
    result_ward = _scope_level_name("VN-HCM-26968")
    assert "phường" in result_ward

    # Additional edge cases
    assert "quốc gia" in _scope_level_name("VN")
    assert "thành phố" in _scope_level_name("VN-DN")     # Đà Nẵng
    assert "phường" in _scope_level_name("VN-HCM-070")   # alternate ward code


# ---------------------------------------------------------------------------
# Test 8 — LLM failure returns hardcoded fallback
# ---------------------------------------------------------------------------

async def test_synthesizer_llm_failure_returns_hardcoded_fallback():
    """When LLM.async_invoke raises, synthesizer_node returns hardcoded fallback."""
    from app.agents.nodes.synthesizer import _HARDCODED_FALLBACK, synthesizer_node

    svc = MagicMock()
    svc.async_invoke = AsyncMock(side_effect=RuntimeError("LLM connection timeout"))

    with patch("app.agents.nodes.synthesizer._get_llm", return_value=svc):
        state = _base_state(
            errors=["Qdrant lỗi"],  # triggers error mode → LLM call
        )
        result = await synthesizer_node(state)

    # Must not raise — must return a dict
    assert isinstance(result, dict)
    assert "final_response" in result
    assert result["final_response"] == _HARDCODED_FALLBACK
    assert result["response_metadata"]["mode"] == "error"
