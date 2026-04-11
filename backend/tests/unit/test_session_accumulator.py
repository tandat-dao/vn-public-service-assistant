"""Unit tests for app/core/session_accumulator.py.

Covers all TASK-08 DoD items for SessionDataAccumulator:
  - Higher-confidence value wins per field
  - existing wins on confidence tie
  - existing=None → incoming returned unchanged
  - both=None → None returned
  - merge never mutates either input
"""

from datetime import date, datetime

import pytest

from app.core.session_accumulator import SessionDataAccumulator
from app.schemas.personal_data import PersonalData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pd(
    full_name: str | None = "Nguyễn Văn A",
    full_name_conf: float = 0.9,
    id_number: str | None = "012345678",
    id_number_conf: float = 0.8,
    source: str = "cccd",
    extraction_confidence: float = 0.85,
    **extra_confs: float,
) -> PersonalData:
    """Build a minimal PersonalData for testing."""
    confs: dict[str, float] = {}
    if full_name is not None:
        confs["full_name"] = full_name_conf
    if id_number is not None:
        confs["id_number"] = id_number_conf
    confs.update(extra_confs)
    return PersonalData(
        full_name=full_name,
        id_number=id_number,
        source_document_type=source,
        source_image_path=f"path/{source}.jpg",
        extraction_confidence=extraction_confidence,
        field_confidences=confs,
        extracted_at=datetime(2024, 1, 1),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSessionDataAccumulator:

    def setup_method(self):
        self.acc = SessionDataAccumulator()

    # 1 — higher confidence wins per field
    def test_merge_higher_confidence_wins(self):
        """Field A higher in incoming, field B higher in existing — each should win."""
        existing = _pd(
            full_name="Nguyễn Văn A",
            full_name_conf=0.5,
            id_number="000000001",
            id_number_conf=0.95,
        )
        incoming = _pd(
            full_name="Nguyễn Văn A (fixed)",
            full_name_conf=0.95,   # higher → should win
            id_number="999999999",
            id_number_conf=0.4,    # lower → existing should win
        )
        result = self.acc.merge(existing, incoming)
        assert result is not None
        assert result.full_name == "Nguyễn Văn A (fixed)"   # incoming wins
        assert result.id_number == "000000001"               # existing wins

    # 2 — existing=None returns incoming unchanged
    def test_merge_existing_none_returns_incoming(self):
        incoming = _pd(full_name="Test User")
        result = self.acc.merge(None, incoming)
        assert result is incoming

    # 3 — both None returns None
    def test_merge_both_none_returns_none(self):
        result = self.acc.merge(None, None)
        assert result is None

    # 4 — equal confidence keeps existing
    def test_merge_equal_confidence_keeps_existing(self):
        existing = _pd(full_name="Existing Name", full_name_conf=0.7)
        incoming = _pd(full_name="Incoming Name", full_name_conf=0.7)  # same conf
        result = self.acc.merge(existing, incoming)
        assert result is not None
        assert result.full_name == "Existing Name"

    # 5 — merge does not mutate either input
    def test_merge_does_not_mutate_inputs(self):
        existing = _pd(full_name="Original A", full_name_conf=0.5)
        incoming = _pd(full_name="New B", full_name_conf=0.9)
        original_existing_name = existing.full_name
        original_incoming_name = incoming.full_name
        self.acc.merge(existing, incoming)
        assert existing.full_name == original_existing_name
        assert incoming.full_name == original_incoming_name

    # 6 — incoming=None keeps existing unchanged
    def test_merge_incoming_none_returns_existing(self):
        existing = _pd(full_name="Keep Me")
        result = self.acc.merge(existing, None)
        assert result is existing

    # 7 — field only present in one side is carried through
    def test_merge_one_sided_field_carried_through(self):
        """date_of_birth only in incoming — should appear in merged result."""
        existing = _pd(full_name="A", full_name_conf=0.9)
        incoming = PersonalData(
            full_name=None,
            date_of_birth=date(1990, 1, 1),
            source_document_type="cccd",
            source_image_path="path.jpg",
            extraction_confidence=0.8,
            field_confidences={"date_of_birth": 0.9},
            extracted_at=datetime(2024, 1, 1),
        )
        result = self.acc.merge(existing, incoming)
        assert result is not None
        assert result.full_name == "A"
        assert result.date_of_birth == date(1990, 1, 1)

    # 8 — merged field_confidences takes max per key
    def test_merge_field_confidences_takes_max(self):
        existing = _pd(full_name="A", full_name_conf=0.6, id_number_conf=0.9)
        incoming = _pd(full_name="B", full_name_conf=0.8, id_number_conf=0.5)
        result = self.acc.merge(existing, incoming)
        assert result is not None
        assert result.field_confidences["full_name"] == 0.8    # max(0.6, 0.8)
        assert result.field_confidences["id_number"] == 0.9   # max(0.9, 0.5)

    # 9 — provenance uses incoming source fields
    def test_merge_provenance_uses_incoming_source(self):
        existing = _pd(source="cccd")
        incoming = _pd(source="passport")
        result = self.acc.merge(existing, incoming)
        assert result is not None
        assert result.source_document_type == "passport"

    # 10 — extraction_confidence takes max
    def test_merge_extraction_confidence_takes_max(self):
        existing = _pd(extraction_confidence=0.6)
        incoming = _pd(extraction_confidence=0.9)
        result = self.acc.merge(existing, incoming)
        assert result is not None
        assert result.extraction_confidence == 0.9
