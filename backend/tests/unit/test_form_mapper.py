"""Unit tests for app/core/form_field_mapper.py.

Covers all TASK-08 DoD items for FormFieldMapper:
  - LLM called once on cache miss
  - Cache hit skips LLM on second call, applies updated PersonalData values
  - Bad JSON from LLM returns empty mapping without raising
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.form_field_mapper import FormFieldMapper
from app.schemas.personal_data import PersonalData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pd(full_name: str = "Nguyễn Văn A", id_number: str = "012345678") -> PersonalData:
    return PersonalData(
        full_name=full_name,
        id_number=id_number,
        source_document_type="cccd",
        source_image_path="path/cccd.jpg",
        extraction_confidence=0.9,
        field_confidences={"full_name": 0.95, "id_number": 0.9},
        extracted_at=datetime(2024, 1, 1),
    )


def _mock_llm(json_response: dict | None = None, raw_response: str | None = None) -> MagicMock:
    """Return a mock LLMService whose async_invoke returns a JSON string."""
    svc = MagicMock()
    if raw_response is not None:
        svc.async_invoke = AsyncMock(return_value=raw_response)
    else:
        svc.async_invoke = AsyncMock(
            return_value=json.dumps(json_response or {})
        )
    return svc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFormFieldMapper:

    # 5 — LLM is called on cache miss
    @pytest.mark.asyncio
    async def test_calls_llm_on_cache_miss(self):
        llm = _mock_llm({"ho_ten": "full_name", "so_cccd": "id_number"})
        mapper = FormFieldMapper(llm_service=llm)

        result = await mapper.map(
            personal_data=_pd(),
            form_fields=["ho_ten", "so_cccd"],
            form_id="TTHC-001",
        )

        llm.async_invoke.assert_called_once()
        assert result["ho_ten"] == "Nguyễn Văn A"
        assert result["so_cccd"] == "012345678"

    # 6 — second call with same form_id + fields reuses cache; LLM called only once
    @pytest.mark.asyncio
    async def test_uses_cache_on_second_call(self):
        llm = _mock_llm({"ho_ten": "full_name", "so_cccd": "id_number"})
        mapper = FormFieldMapper(llm_service=llm)

        pd_first = _pd(full_name="Nguyễn Văn A", id_number="111111111")
        pd_second = _pd(full_name="Trần Thị B", id_number="222222222")

        await mapper.map(personal_data=pd_first, form_fields=["ho_ten", "so_cccd"], form_id="TTHC-001")
        result2 = await mapper.map(personal_data=pd_second, form_fields=["ho_ten", "so_cccd"], form_id="TTHC-001")

        # LLM called only once total across both map() calls.
        assert llm.async_invoke.call_count == 1
        # Second result reflects pd_second's values.
        assert result2["ho_ten"] == "Trần Thị B"
        assert result2["so_cccd"] == "222222222"

    # 7 — bad JSON from LLM returns empty mapping without raising
    @pytest.mark.asyncio
    async def test_bad_json_returns_empty_mapping(self):
        llm = _mock_llm(raw_response="This is not valid JSON at all }")
        mapper = FormFieldMapper(llm_service=llm)

        result = await mapper.map(
            personal_data=_pd(),
            form_fields=["ho_ten", "so_cccd", "ngay_sinh"],
            form_id="TTHC-002",
        )

        # All values should be empty strings — no exception raised.
        assert result == {"ho_ten": "", "so_cccd": "", "ngay_sinh": ""}

    # — different form_id triggers new LLM call (separate cache key)
    @pytest.mark.asyncio
    async def test_different_form_id_triggers_new_llm_call(self):
        llm = _mock_llm({"ho_ten": "full_name"})
        mapper = FormFieldMapper(llm_service=llm)

        await mapper.map(personal_data=_pd(), form_fields=["ho_ten"], form_id="TTHC-001")
        await mapper.map(personal_data=_pd(), form_fields=["ho_ten"], form_id="TTHC-002")

        assert llm.async_invoke.call_count == 2

    # — null from LLM produces empty string for that field
    @pytest.mark.asyncio
    async def test_null_mapping_produces_empty_string(self):
        llm = _mock_llm({"ho_ten": "full_name", "unknown_field": None})
        mapper = FormFieldMapper(llm_service=llm)

        result = await mapper.map(
            personal_data=_pd(),
            form_fields=["ho_ten", "unknown_field"],
            form_id="TTHC-003",
        )

        assert result["ho_ten"] == "Nguyễn Văn A"
        assert result["unknown_field"] == ""

    # — invalid PersonalData attr name from LLM is silently ignored (→ "")
    @pytest.mark.asyncio
    async def test_invalid_pd_attr_from_llm_produces_empty_string(self):
        llm = _mock_llm({"ho_ten": "nonexistent_field_xyz"})
        mapper = FormFieldMapper(llm_service=llm)

        result = await mapper.map(
            personal_data=_pd(),
            form_fields=["ho_ten"],
            form_id="TTHC-001",
        )
        assert result["ho_ten"] == ""
