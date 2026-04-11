"""Semantic form field mapper — uses LLM to map PersonalData fields to PDF field names.

The mapper calls the LLM once per unique (form_id, field-list) pair.
Subsequent calls for the same form reuse the cached structural mapping
(PersonalData attr → PDF field name), only substituting the new PersonalData
values — no additional LLM call is made.

Zero infrastructure dependencies beyond LLMService (injected via constructor).
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

import structlog

from app.agents.prompts.form_mapping_prompt import (
    FORM_MAPPING_SYSTEM_PROMPT,
    build_form_mapping_user_message,
)
from app.schemas.personal_data import Address, PersonalData
from app.services.llm import LLMService

log = structlog.get_logger(__name__)

# Fields that are provenance metadata, not personal data — exclude from LLM input.
_PROVENANCE_FIELDS: frozenset[str] = frozenset({
    "source_document_type",
    "source_image_path",
    "extraction_confidence",
    "field_confidences",
    "extracted_at",
})

# All valid PersonalData attribute names (computed once at import time).
_VALID_PD_ATTRS: frozenset[str] = frozenset(PersonalData.model_fields.keys())


def _format_value(val: Any) -> str:
    """Convert a PersonalData field value to a string suitable for a form field."""
    if val is None:
        return ""
    if isinstance(val, Address):
        parts = [val.street, val.ward, val.district, val.province or val.city]
        return ", ".join(p for p in parts if p)
    if isinstance(val, date) and not isinstance(val, datetime):
        return val.strftime("%d/%m/%Y")
    return str(val)


def _build_available_pd(personal_data: PersonalData) -> dict[str, str]:
    """Return a flat dict of non-None PersonalData attribute names → string values.

    Provenance fields are excluded — the LLM does not need to know them.
    """
    result: dict[str, str] = {}
    for field_name in PersonalData.model_fields:
        if field_name in _PROVENANCE_FIELDS:
            continue
        val = getattr(personal_data, field_name)
        if val is not None:
            result[field_name] = _format_value(val)
    return result


def _apply_mapping(
    field_to_attr: dict[str, str | None],
    personal_data: PersonalData,
) -> dict[str, str]:
    """Apply a cached structural mapping to the current PersonalData values."""
    result: dict[str, str] = {}
    for form_field, attr_name in field_to_attr.items():
        if attr_name is None:
            result[form_field] = ""
        else:
            val = getattr(personal_data, attr_name, None)
            result[form_field] = _format_value(val)
    return result


class FormFieldMapper:
    """LLM-driven mapper from PDF form field names to PersonalData values.

    The LLM is called at most once per (form_id, sorted field list) pair.
    The structural mapping (PDF field → PersonalData attr name) is cached
    in memory; only the value lookup changes between users.
    """

    def __init__(self, llm_service: LLMService) -> None:
        self._llm = llm_service
        # Cache: cache_key → {pdf_field_name: pd_attr_name | None}
        self._cache: dict[str, dict[str, str | None]] = {}

    async def map(
        self,
        personal_data: PersonalData,
        form_fields: list[str],
        form_id: str,
    ) -> dict[str, str]:
        """Return a dict mapping each PDF form field name to its filled value.

        Values are taken from ``personal_data`` using LLM-derived semantic
        matching.  Returns ``""`` for any field that cannot be matched.

        Args:
            personal_data: The current accumulated PersonalData to draw values from.
            form_fields: List of PDF form field names that need to be filled.
            form_id: Identifier for this form template (used as cache key).

        Returns:
            Dict of {pdf_field_name: value_string}.  All form_fields are
            present as keys; unmatched fields map to ``""``.
        """
        if not form_fields:
            return {}

        cache_key = f"{form_id}:{':'.join(sorted(form_fields))}"

        # ── Cache hit: reuse structural mapping, substitute new values ────────
        if cache_key in self._cache:
            log.debug("FormFieldMapper: cache hit", form_id=form_id)
            return _apply_mapping(self._cache[cache_key], personal_data)

        # ── Cache miss: call LLM to derive structural mapping ─────────────────
        available = _build_available_pd(personal_data)
        user_msg = build_form_mapping_user_message(form_fields, available)
        messages = [{"role": "user", "content": user_msg}]

        raw_response = await self._llm.async_invoke(
            system=FORM_MAPPING_SYSTEM_PROMPT,
            messages=messages,
            max_tokens=512,
        )

        try:
            parsed: dict = json.loads(raw_response)
        except (json.JSONDecodeError, ValueError):
            log.warning(
                "FormFieldMapper: LLM returned non-JSON — returning empty mapping",
                form_id=form_id,
                raw=raw_response[:200],
            )
            # Store an all-null mapping so we don't retry on the next call.
            self._cache[cache_key] = {f: None for f in form_fields}
            return {f: "" for f in form_fields}

        # Sanitise: only keep mappings to valid PersonalData attr names.
        field_to_attr: dict[str, str | None] = {}
        for form_field in form_fields:
            attr_name = parsed.get(form_field)
            if attr_name is None or attr_name not in _VALID_PD_ATTRS:
                field_to_attr[form_field] = None
            else:
                field_to_attr[form_field] = attr_name

        self._cache[cache_key] = field_to_attr
        log.debug(
            "FormFieldMapper: cached new mapping",
            form_id=form_id,
            mapped_count=sum(1 for v in field_to_attr.values() if v is not None),
            total=len(form_fields),
        )

        return _apply_mapping(field_to_attr, personal_data)
