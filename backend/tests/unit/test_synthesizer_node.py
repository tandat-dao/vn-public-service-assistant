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


# ---------------------------------------------------------------------------
# Guided procedure wizard — TASK-APP-18
# ---------------------------------------------------------------------------

async def test_synthesizer_guided_step_mode_detected(mock_llm):
    """guided_step mode fires when guided_step is set; step advances 0 → 1 after INTRO."""
    from app.agents.nodes.synthesizer import synthesizer_node

    state = _base_state(
        guided_step=0,
        guided_procedure_id="TTHC-001",
        errors=[],
        retrieved_chunks=[],
        form_fill_complete=False,
        unfilled_required_fields=[],
    )

    result = await synthesizer_node(state)

    assert result["response_metadata"]["mode"] == "guided_step"
    # INTRO (step 0) → next step is 1 (AWAIT_CCCD)
    assert result["response_metadata"]["guided_step"] == 1
    assert result["response_metadata"]["guided_procedure_id"] == "TTHC-001"
    assert "final_response" in result
    mock_llm.async_invoke.assert_called_once()


async def test_synthesizer_includes_retrieved_sources_in_metadata(mock_llm):
    """response_metadata includes retrieved_sources for rag_only mode (no scope notice).

    DoD checks:
    - retrieved_sources is present and is a list
    - length matches number of chunks with non-empty article_number + document_number
    - no content entry exceeds 600 characters (backend cap)
    - article_number and document_number match the corresponding chunk fields
    """
    from app.agents.nodes.synthesizer import synthesizer_node
    from app.schemas.rag import DocumentChunk

    chunk_short = DocumentChunk(
        point_id="pt-19",
        legal_document_id="doc-001",
        document_number="62/2021/NĐ-CP",
        article_number="19",
        content="Nội dung điều 19 về đăng ký thường trú.",
        procedure_tags=["TTHC-001"],
        status="active",
        rrf_score=0.9,
    )
    # content longer than 1200 chars — must be capped
    chunk_long = DocumentChunk(
        point_id="pt-5",
        legal_document_id="doc-002",
        document_number="104/2022/NĐ-CP",
        article_number="5",
        content="X" * 1300,
        procedure_tags=["TTHC-002"],
        status="active",
        rrf_score=0.7,
    )

    rag_answer = "Theo [Điều 19, Nghị định 62/2021/NĐ-CP], hồ sơ gồm..."
    state = _base_state(
        retrieved_chunks=[chunk_short, chunk_long],
        final_response=rag_answer,
        response_metadata={"rag_confidence": "high"},
        # Same scope → no scope notice → LLM not called (fast path)
        scope_used="VN",
        filing_jurisdiction="VN",
        errors=[],
        form_fill_complete=False,
        unfilled_required_fields=[],
    )

    result = await synthesizer_node(state)

    assert result["response_metadata"]["mode"] == "rag_only"
    sources = result["response_metadata"]["retrieved_sources"]
    assert isinstance(sources, list)
    # Both chunks have non-empty article_number and document_number → both included
    assert len(sources) == 2
    # Content cap enforced
    for source in sources:
        assert len(source["content"]) <= 1200
    article_numbers = {s["article_number"] for s in sources}
    doc_numbers = {s["document_number"] for s in sources}
    # After FIX A: numeric article_numbers are normalized with "Điều " prefix
    assert "Điều 19" in article_numbers
    assert "Điều 5" in article_numbers
    assert "62/2021/NĐ-CP" in doc_numbers
    assert "104/2022/NĐ-CP" in doc_numbers
    # LLM must NOT be called in the no-scope-notice optimisation path
    mock_llm.async_invoke.assert_not_called()


async def test_synthesizer_guided_step3_clears_guided_mode(mock_llm):
    """At step 3 (COMPLETE), guided mode ends — guided_procedure_id and guided_step become None."""
    from app.agents.nodes.synthesizer import synthesizer_node

    state = _base_state(
        guided_step=3,
        guided_procedure_id="TTHC-002",
        errors=[],
        retrieved_chunks=[],
        form_fill_complete=False,
        unfilled_required_fields=[],
    )

    result = await synthesizer_node(state)

    assert result["response_metadata"]["mode"] == "guided_step"
    assert result["response_metadata"]["guided_procedure_id"] is None
    assert result["response_metadata"]["guided_step"] is None
    assert "final_response" in result




# ---------------------------------------------------------------------------
# Guided wizard extended to new procedures — State 2 directs to page form
# ---------------------------------------------------------------------------

async def test_synthesizer_guided_step2_tthc_cr_001_directs_to_page_form():
    """State 2 for TTHC-CR-001 returns hardcoded page-form guidance without calling LLM."""
    from app.agents.nodes.synthesizer import synthesizer_node

    svc = MagicMock()
    svc.async_invoke = AsyncMock(return_value="LLM response that must NOT be used")

    state = _base_state(
        guided_step=2,
        guided_procedure_id="TTHC-CR-001",
        errors=[],
        retrieved_chunks=[],
        form_fill_complete=False,
        unfilled_required_fields=[],
    )

    with patch("app.agents.nodes.synthesizer._get_llm", return_value=svc):
        result = await synthesizer_node(state)

    assert result["response_metadata"]["mode"] == "guided_step"
    assert result["response_metadata"]["guided_step"] == 2
    assert result["response_metadata"]["filled_form_path"] is None
    assert "Tải xuống tờ khai đã điền" in result["final_response"]
    svc.async_invoke.assert_not_called()


async def test_synthesizer_guided_step2_tthc_cr_002_directs_to_page_form():
    """State 2 for TTHC-CR-002 returns hardcoded page-form guidance without calling LLM."""
    from app.agents.nodes.synthesizer import synthesizer_node

    svc = MagicMock()
    svc.async_invoke = AsyncMock(return_value="LLM response that must NOT be used")

    state = _base_state(
        guided_step=2,
        guided_procedure_id="TTHC-CR-002",
        errors=[],
        retrieved_chunks=[],
        form_fill_complete=False,
        unfilled_required_fields=[],
    )

    with patch("app.agents.nodes.synthesizer._get_llm", return_value=svc):
        result = await synthesizer_node(state)

    assert result["response_metadata"]["mode"] == "guided_step"
    assert result["response_metadata"]["guided_step"] == 2
    assert result["response_metadata"]["filled_form_path"] is None
    assert "Tải xuống tờ khai đã điền" in result["final_response"]
    svc.async_invoke.assert_not_called()


async def test_synthesizer_guided_step2_tthc_ad_001_directs_to_page_form():
    """State 2 for TTHC-AD-001 returns hardcoded page-form guidance without calling LLM."""
    from app.agents.nodes.synthesizer import synthesizer_node

    svc = MagicMock()
    svc.async_invoke = AsyncMock(return_value="LLM response that must NOT be used")

    state = _base_state(
        guided_step=2,
        guided_procedure_id="TTHC-AD-001",
        errors=[],
        retrieved_chunks=[],
        form_fill_complete=False,
        unfilled_required_fields=[],
    )

    with patch("app.agents.nodes.synthesizer._get_llm", return_value=svc):
        result = await synthesizer_node(state)

    assert result["response_metadata"]["mode"] == "guided_step"
    assert result["response_metadata"]["guided_step"] == 2
    assert result["response_metadata"]["filled_form_path"] is None
    assert "Tải xuống tờ khai đã điền" in result["final_response"]
    svc.async_invoke.assert_not_called()


async def test_synthesizer_guided_step2_tthc_ad_002_directs_to_page_form():
    """State 2 for TTHC-AD-002 returns hardcoded page-form guidance without calling LLM."""
    from app.agents.nodes.synthesizer import synthesizer_node

    svc = MagicMock()
    svc.async_invoke = AsyncMock(return_value="LLM response that must NOT be used")

    state = _base_state(
        guided_step=2,
        guided_procedure_id="TTHC-AD-002",
        errors=[],
        retrieved_chunks=[],
        form_fill_complete=False,
        unfilled_required_fields=[],
    )

    with patch("app.agents.nodes.synthesizer._get_llm", return_value=svc):
        result = await synthesizer_node(state)

    assert result["response_metadata"]["mode"] == "guided_step"
    assert result["response_metadata"]["guided_step"] == 2
    assert result["response_metadata"]["filled_form_path"] is None
    assert "Tải xuống tờ khai đã điền" in result["final_response"]
    svc.async_invoke.assert_not_called()


# ---------------------------------------------------------------------------
# Out-of-scope query guard — Change 3
# ---------------------------------------------------------------------------

async def test_synthesizer_out_of_scope_returns_fixed_response():
    """out_of_scope mode returns fixed Vietnamese refusal with zero LLM calls."""
    from app.agents.nodes.synthesizer import synthesizer_node

    svc = MagicMock()
    svc.async_invoke = AsyncMock(return_value="LLM response that must NOT be used")

    state = _base_state(out_of_scope=True)

    with patch("app.agents.nodes.synthesizer._get_llm", return_value=svc):
        result = await synthesizer_node(state)

    assert result["response_metadata"]["mode"] == "out_of_scope"
    assert "thủ tục hành chính" in result["final_response"]
    svc.async_invoke.assert_not_called()


# ---------------------------------------------------------------------------
# RAG empty degradation — Fix B
# ---------------------------------------------------------------------------

async def test_synthesizer_rag_empty_mode_detected():
    """rag_empty mode fires when rag_returned_empty=True and intent is Q&A."""
    from app.agents.nodes.synthesizer import _determine_mode, synthesizer_node

    svc = MagicMock()
    svc.async_invoke = AsyncMock(return_value="LLM response that must NOT be used")

    state = _base_state(
        rag_returned_empty=True,
        intent="rag_only",
        errors=[],
        retrieved_chunks=[],
        form_fill_complete=False,
        unfilled_required_fields=[],
    )

    assert _determine_mode(state) == "rag_empty"

    with patch("app.agents.nodes.synthesizer._get_llm", return_value=svc):
        result = await synthesizer_node(state)

    assert result["response_metadata"]["mode"] == "rag_empty"
    assert "chưa tìm thấy" in result["final_response"]
    assert result["response_metadata"]["rag_confidence"] == 0.0
    svc.async_invoke.assert_not_called()


async def test_synthesizer_rag_empty_not_triggered_for_form_fill():
    """rag_empty must NOT fire when intent is 'form_fill'."""
    from app.agents.nodes.synthesizer import _determine_mode

    state = _base_state(
        rag_returned_empty=True,
        intent="form_fill",
        errors=[],
        retrieved_chunks=[],
        form_fill_complete=False,
        unfilled_required_fields=[],
    )

    mode = _determine_mode(state)
    assert mode != "rag_empty"


async def test_synthesizer_rag_empty_not_triggered_for_guided():
    """rag_empty must NOT fire when intent is 'start_guided'."""
    from app.agents.nodes.synthesizer import _determine_mode

    state = _base_state(
        rag_returned_empty=True,
        intent="start_guided",
        errors=[],
        retrieved_chunks=[],
        form_fill_complete=False,
        unfilled_required_fields=[],
    )

    mode = _determine_mode(state)
    assert mode != "rag_empty"


async def test_synthesizer_out_of_scope_is_highest_priority():
    """out_of_scope mode fires even when rag results and form_fill_complete are set."""
    from app.agents.nodes.synthesizer import _determine_mode, synthesizer_node

    svc = MagicMock()
    svc.async_invoke = AsyncMock(return_value="LLM response that must NOT be used")

    state = _base_state(
        out_of_scope=True,
        retrieved_chunks=[_make_chunk()],
        form_fill_complete=True,
        errors=["some error"],
    )

    # _determine_mode must return "out_of_scope" before checking errors or anything else
    assert _determine_mode(state) == "out_of_scope"

    with patch("app.agents.nodes.synthesizer._get_llm", return_value=svc):
        result = await synthesizer_node(state)

    assert result["response_metadata"]["mode"] == "out_of_scope"
    svc.async_invoke.assert_not_called()


# ---------------------------------------------------------------------------
# FIX A — article_number prefix in retrieved_sources
# ---------------------------------------------------------------------------

async def test_retrieved_sources_article_number_has_dieu_prefix():
    """Numeric article_number in retrieved_sources is prefixed with 'Điều '.

    DoD checks:
    - article_number="14" → sources entry has article_number="Điều 14"
    - Prevents frontend substring match false-positives (e.g. "1" matching "14")
    """
    from app.agents.nodes.synthesizer import synthesizer_node
    from app.schemas.rag import DocumentChunk

    chunk = DocumentChunk(
        point_id="pt-14",
        legal_document_id="doc-003",
        document_number="52/2010/QH12",
        article_number="14",
        content="Nội dung điều 14 về điều kiện nhận con nuôi.",
        procedure_tags=["TTHC-AD-001"],
        status="active",
        rrf_score=0.9,
    )

    rag_answer = "Theo [Điều 14, 52/2010/QH12], điều kiện nhận con nuôi gồm..."
    state = _base_state(
        retrieved_chunks=[chunk],
        final_response=rag_answer,
        response_metadata={"rag_confidence": "high"},
        scope_used="VN",
        filing_jurisdiction="VN",
        errors=[],
        form_fill_complete=False,
        unfilled_required_fields=[],
    )

    svc = MagicMock()
    svc.async_invoke = AsyncMock(return_value="unused")

    with patch("app.agents.nodes.synthesizer._get_llm", return_value=svc):
        result = await synthesizer_node(state)

    sources = result["response_metadata"]["retrieved_sources"]
    assert len(sources) == 1
    assert sources[0]["article_number"] == "Điều 14", (
        f"Expected 'Điều 14', got {sources[0]['article_number']!r}"
    )
    assert sources[0]["article_number"].startswith("Điều ")
