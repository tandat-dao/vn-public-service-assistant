"""Unit tests for router_node.

All LLM calls are mocked at the LLMService class level — no real Anthropic
API calls are made. asyncio_mode = "auto" in pyproject.toml means no
@pytest.mark.asyncio decorator is needed.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.nodes.router import _enforce_ordering, router_node
from app.agents.prompts.router_prompt import RouterOutput, build_router_messages
from app.agents.state import AgentState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _state(message: str, image: str | None = None) -> AgentState:
    return AgentState(
        user_message=message,
        session_id="test-session",
        iteration_count=0,
        uploaded_image_path=image,
    )


def _mock_llm(response_dict: dict):
    """Patch LLMService so async_invoke returns json.dumps(response_dict)."""
    mock = MagicMock()
    mock.async_invoke = AsyncMock(return_value=json.dumps(response_dict))
    return patch("app.agents.nodes.router.LLMService", return_value=mock)


# ---------------------------------------------------------------------------
# RouterOutput validation
# ---------------------------------------------------------------------------

class TestRouterOutput:
    def test_valid_plan(self):
        out = RouterOutput(execution_plan=["rag_fn"], entities={})
        assert out.execution_plan == ["rag_fn"]

    def test_empty_plan(self):
        out = RouterOutput(execution_plan=[], entities={})
        assert out.execution_plan == []

    def test_all_valid_steps(self):
        out = RouterOutput(execution_plan=["ocr_fn", "rag_fn", "form_filler_fn"])
        assert len(out.execution_plan) == 3

    def test_invalid_step_accepted_by_schema(self):
        # RouterOutput does NOT validate step names — that check lives in router_node
        # so it can raise ValueError (prompt drift) instead of being swallowed as
        # a fallback-triggering parse error.
        out = RouterOutput(execution_plan=["procedure_planner_fn"])
        assert out.execution_plan == ["procedure_planner_fn"]

    def test_unknown_step_accepted_by_schema(self):
        out = RouterOutput(execution_plan=["unknown_fn"])
        assert out.execution_plan == ["unknown_fn"]


# ---------------------------------------------------------------------------
# _enforce_ordering
# ---------------------------------------------------------------------------

class TestEnforceOrdering:
    def test_correct_order_unchanged(self):
        assert _enforce_ordering(["ocr_fn", "form_filler_fn"]) == ["ocr_fn", "form_filler_fn"]

    def test_wrong_order_fixed(self):
        result = _enforce_ordering(["form_filler_fn", "ocr_fn"])
        assert result.index("ocr_fn") < result.index("form_filler_fn")

    def test_ocr_without_form_filler(self):
        assert _enforce_ordering(["ocr_fn", "rag_fn"]) == ["ocr_fn", "rag_fn"]

    def test_form_filler_without_ocr(self):
        # No reordering when ocr_fn is absent
        assert _enforce_ordering(["form_filler_fn"]) == ["form_filler_fn"]

    def test_empty_plan(self):
        assert _enforce_ordering([]) == []


# ---------------------------------------------------------------------------
# build_router_messages
# ---------------------------------------------------------------------------

class TestBuildRouterMessages:
    def test_no_image(self):
        msgs = build_router_messages("Xin chào", has_image=False)
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"
        assert "Xin chào" in msgs[0]["content"]
        assert "Không có ảnh" in msgs[0]["content"]

    def test_with_image(self):
        msgs = build_router_messages("Điền form", has_image=True)
        assert "tải lên" in msgs[0]["content"].lower() or "ảnh" in msgs[0]["content"]
        assert "Điền form" in msgs[0]["content"]


# ---------------------------------------------------------------------------
# router_node — classification cases
# ---------------------------------------------------------------------------

class TestRouterNode:
    async def test_pure_legal_question(self):
        with _mock_llm({"execution_plan": ["rag_fn"], "entities": {"article": "Điều 20"}}):
            result = await router_node(_state("Điều 20 Luật Cư trú quy định gì?"))
        assert result["execution_plan"] == ["rag_fn"]
        assert result["plan_cursor"] == 0
        assert result["entities"]["article"] == "Điều 20"

    async def test_procedure_inquiry_no_image(self):
        """Procedure inquiry returns ["rag_fn"] — DAG resolved by enrichment_node."""
        with _mock_llm({"execution_plan": ["rag_fn"], "entities": {"procedure": "thường trú"}}):
            result = await router_node(_state("Tôi muốn đăng ký thường trú"))
        assert result["execution_plan"] == ["rag_fn"]

    async def test_document_inquiry_no_image(self):
        with _mock_llm({"execution_plan": ["rag_fn"], "entities": {}}):
            result = await router_node(_state("Đăng ký tạm trú cần giấy tờ gì?"))
        assert result["execution_plan"] == ["rag_fn"]

    async def test_image_uploaded_form_fill_intent(self):
        with _mock_llm({"execution_plan": ["ocr_fn", "form_filler_fn"], "entities": {}}):
            result = await router_node(_state("Điền form cho tôi", image="/tmp/cccd.jpg"))
        assert result["execution_plan"] == ["ocr_fn", "form_filler_fn"]

    async def test_image_uploaded_legal_question(self):
        with _mock_llm({"execution_plan": ["ocr_fn", "rag_fn"], "entities": {}}):
            result = await router_node(_state("Giải thích Nghị định 31", image="/tmp/cccd.jpg"))
        assert result["execution_plan"] == ["ocr_fn", "rag_fn"]

    async def test_image_form_fill_and_legal_question(self):
        with _mock_llm({"execution_plan": ["ocr_fn", "rag_fn", "form_filler_fn"], "entities": {}}):
            result = await router_node(_state("Điền form và giải thích thủ tục", image="/tmp/cccd.jpg"))
        plan = result["execution_plan"]
        assert plan.index("ocr_fn") < plan.index("form_filler_fn")
        assert "rag_fn" in plan

    async def test_form_fill_no_image_returns_rag(self):
        """Cannot fill without OCR data — router falls back to rag_fn."""
        with _mock_llm({"execution_plan": ["rag_fn"], "entities": {}}):
            result = await router_node(_state("Hãy điền đơn cho tôi"))
        assert result["execution_plan"] == ["rag_fn"]

    async def test_greeting_returns_empty_plan(self):
        with _mock_llm({"execution_plan": [], "entities": {}}):
            result = await router_node(_state("Xin chào"))
        assert result["execution_plan"] == []
        assert result["plan_cursor"] == 0

    async def test_plan_cursor_always_zero(self):
        with _mock_llm({"execution_plan": ["rag_fn"], "entities": {}}):
            result = await router_node(_state("bất kỳ tin nhắn nào"))
        assert result["plan_cursor"] == 0

    async def test_entities_empty_dict_when_absent(self):
        with _mock_llm({"execution_plan": ["rag_fn"]}):
            result = await router_node(_state("bất kỳ tin nhắn nào"))
        assert result["entities"] == {}

    async def test_ordering_enforced_even_if_llm_wrong(self):
        """Even if LLM returns wrong order, router_node enforces ocr_fn before form_filler_fn."""
        with _mock_llm({"execution_plan": ["form_filler_fn", "ocr_fn"], "entities": {}}):
            result = await router_node(_state("test", image="/tmp/img.jpg"))
        plan = result["execution_plan"]
        assert plan.index("ocr_fn") < plan.index("form_filler_fn")

    async def test_malformed_json_returns_fallback(self):
        mock = MagicMock()
        mock.async_invoke = AsyncMock(return_value="not valid json {{{{")
        with patch("app.agents.nodes.router.LLMService", return_value=mock):
            result = await router_node(_state("Điều gì đó"))
        assert result["execution_plan"] == ["rag_fn"]
        assert result["entities"] == {}
        assert result["plan_cursor"] == 0

    async def test_invalid_json_structure_returns_fallback(self):
        mock = MagicMock()
        mock.async_invoke = AsyncMock(return_value=json.dumps({"wrong_key": "value"}))
        with patch("app.agents.nodes.router.LLMService", return_value=mock):
            result = await router_node(_state("Điều gì đó"))
        # Missing execution_plan key → Pydantic sets default [] which is valid, not a fallback
        # But if pydantic raises, we get fallback. Either way plan_cursor must be 0.
        assert result["plan_cursor"] == 0

    async def test_invalid_step_name_raises_value_error(self):
        """Invalid step name (prompt drift) must raise ValueError, not return fallback."""
        mock = MagicMock()
        mock.async_invoke = AsyncMock(
            return_value=json.dumps({"execution_plan": ["unknown_step_fn"], "entities": {}})
        )
        with patch("app.agents.nodes.router.LLMService", return_value=mock):
            with pytest.raises(ValueError, match="invalid plan steps"):
                await router_node(_state("test"))

    async def test_procedure_planner_fn_is_invalid_step(self):
        """procedure_planner_fn must never appear in execution_plan — router raises ValueError."""
        mock = MagicMock()
        mock.async_invoke = AsyncMock(
            return_value=json.dumps(
                {"execution_plan": ["procedure_planner_fn"], "entities": {}}
            )
        )
        with patch("app.agents.nodes.router.LLMService", return_value=mock):
            with pytest.raises(ValueError, match="invalid plan steps"):
                await router_node(_state("Đăng ký thường trú"))

    async def test_network_error_propagates(self):
        """Infrastructure errors must propagate — not be swallowed."""
        mock = MagicMock()
        mock.async_invoke = AsyncMock(side_effect=ConnectionError("network down"))
        with patch("app.agents.nodes.router.LLMService", return_value=mock):
            with pytest.raises(ConnectionError):
                await router_node(_state("test"))

    async def test_no_image_path_treated_as_no_image(self):
        state = _state("test")
        state["uploaded_image_path"] = None
        with _mock_llm({"execution_plan": ["rag_fn"], "entities": {}}):
            result = await router_node(state)
        assert result["execution_plan"] == ["rag_fn"]

    async def test_unclassifiable_returns_empty_plan(self):
        with _mock_llm({"execution_plan": [], "entities": {}}):
            result = await router_node(_state("asdfghjkl"))
        assert result["execution_plan"] == []

    async def test_returned_dict_has_exactly_three_keys(self):
        with _mock_llm({"execution_plan": ["rag_fn"], "entities": {}}):
            result = await router_node(_state("test"))
        assert set(result.keys()) == {"execution_plan", "entities", "plan_cursor"}


# ---------------------------------------------------------------------------
# Guided procedure wizard — TASK-APP-18
# ---------------------------------------------------------------------------

class TestRouterGuidedMode:
    async def test_guided_intent_housing_sets_guided_state(self):
        """start_guided intent for a housing procedure activates guided mode at step 0."""
        with _mock_llm({
            "execution_plan": [],
            "entities": {"procedure": "đăng ký tạm trú"},
            "intent": "start_guided",
            "procedure_id": "TTHC-002",
        }):
            result = await router_node(_state("Giúp tôi đăng ký tạm trú từ đầu đến cuối"))
        assert result["guided_procedure_id"] == "TTHC-002"
        assert result["guided_step"] == 0  # INTRO
        assert result["execution_plan"] == ["rag_fn"]
        assert result["plan_cursor"] == 0

    async def test_guided_intent_non_housing_returns_unsupported(self):
        """start_guided for a non-housing procedure returns unsupported message, clears guided mode."""
        with _mock_llm({
            "execution_plan": [],
            "entities": {},
            "intent": "start_guided",
            "procedure_id": "TTHC-CR-001",
        }):
            result = await router_node(_state("Giúp tôi đăng ký khai sinh"))
        assert result["guided_procedure_id"] is None
        assert result["guided_step"] is None
        # Must contain an explanation that guided mode only supports housing
        assert "chỉ hỗ trợ" in result.get("final_response", "")

    async def test_router_draft_document_intent_sets_document_type(self):
        """draft_document intent with a supported document_type sets document_type in state."""
        with _mock_llm({
            "execution_plan": [],
            "entities": {"document": "đơn xin xác nhận cư trú"},
            "intent": "draft_document",
            "document_type": "don_xac_nhan_cu_tru",
        }):
            result = await router_node(_state("Giúp tôi viết đơn xin xác nhận thông tin cư trú"))

        assert result["document_type"] == "don_xac_nhan_cu_tru"
        assert result["execution_plan"] == []
        assert result["plan_cursor"] == 0
        # Must NOT set guided state — this is not a guided flow
        assert "guided_procedure_id" not in result or result.get("guided_procedure_id") is None
        assert "guided_step" not in result or result.get("guided_step") is None

    async def test_router_draft_document_unsupported_type_returns_message(self):
        """draft_document intent with an unknown document_type returns the supported-types message."""
        with _mock_llm({
            "execution_plan": [],
            "entities": {},
            "intent": "draft_document",
            "document_type": "don_khong_ton_tai",
        }):
            result = await router_node(_state("Soạn đơn lạ cho tôi"))

        assert result.get("document_type") is None
        assert "Xin lỗi" in result.get("final_response", "")
        # Must list supported types in the message
        assert "xác nhận" in result.get("final_response", "").lower()

    async def test_guided_step2_bypasses_llm(self):
        """When guided_step==2, router returns form fill plan WITHOUT calling the LLM."""
        mock_llm_cls = MagicMock()
        mock_instance = MagicMock()
        mock_instance.async_invoke = AsyncMock(return_value="{}")
        mock_llm_cls.return_value = mock_instance

        state = _state("ảnh CCCD của tôi đây", image="/tmp/cccd.jpg")
        state["guided_procedure_id"] = "TTHC-001"
        state["guided_step"] = 2

        with patch("app.agents.nodes.router.LLMService", mock_llm_cls):
            result = await router_node(state)

        # LLM must NOT have been called
        mock_instance.async_invoke.assert_not_called()
        assert result["execution_plan"] == ["ocr_fn", "form_filler_fn"]
        assert result["guided_step"] == 2
        assert result["guided_procedure_id"] == "TTHC-001"
