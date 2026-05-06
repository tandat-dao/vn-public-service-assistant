"""Integration tests for Redis session persistence.

Requires Redis to be running at localhost:6379.
All tests are skipped gracefully if Redis is not available.

Run:
    cd backend && PYTHONPATH=. .venv/Scripts/pytest tests/integration/test_session_persistence.py -v
"""

from __future__ import annotations

from datetime import datetime

import pytest


# ---------------------------------------------------------------------------
# Test 9: save and load preserves all session fields
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.asyncio
async def test_save_and_load_session_preserves_fields(redis_service, session_id):
    """Save a SessionData with PersonalData and history, reload and verify all fields intact."""
    from app.schemas.personal_data import PersonalData
    from app.schemas.session import SessionData

    session = SessionData(
        session_id=session_id,
        conversation_history=[
            {"role": "user", "content": "Xin chào"},
            {"role": "assistant", "content": "Xin chào, tôi có thể giúp gì?"},
        ],
        personal_data=PersonalData(
            full_name="Nguyễn Văn A",
            id_number="001234567890",
            source_document_type="cccd",
            source_image_path="/tmp/test.jpg",
            extraction_confidence=0.95,
            extracted_at=datetime(2026, 1, 1, 12, 0, 0),
        ),
    )

    await redis_service.save_session(session_id, session)
    loaded = await redis_service.get_session(session_id)

    assert loaded is not None, "Expected loaded session to be non-None"
    assert loaded.session_id == session_id
    assert len(loaded.conversation_history) == 2
    assert loaded.personal_data is not None
    assert loaded.personal_data.full_name == "Nguyễn Văn A"
    assert loaded.personal_data.id_number == "001234567890"

    # Cleanup
    await redis_service.delete_session(session_id)


# ---------------------------------------------------------------------------
# Test 10: history compaction at 6 turns
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.asyncio
async def test_history_compaction_at_6_turns(redis_service, session_id):
    """History exceeding 6 turns is compacted to a summary + recent turns on save."""
    from app.schemas.session import SessionData

    # Build 8 turns (16 messages)
    history = []
    for i in range(8):
        history.append({"role": "user", "content": f"Câu hỏi {i}"})
        history.append({"role": "assistant", "content": f"Trả lời {i}"})

    session = SessionData(
        session_id=session_id,
        conversation_history=history,
    )

    await redis_service.save_session(session_id, session)
    loaded = await redis_service.get_session(session_id)

    assert loaded is not None
    # After compaction: at most 6 turns (compacted summary + recent turns)
    # The exact count depends on _compact_history — it compacts to (max_turns - 1) recent turns
    # plus 1 synthetic summary, capped at max_turns = 6.
    # 16 messages → compacted to ≤ 6 entries
    assert len(loaded.conversation_history) <= 6, (
        f"Expected ≤ 6 history entries after compaction, got {len(loaded.conversation_history)}: "
        f"{loaded.conversation_history}"
    )

    # Cleanup
    await redis_service.delete_session(session_id)


# ---------------------------------------------------------------------------
# Test 11: loading a non-existent session returns None
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.asyncio
async def test_session_not_found_returns_none(redis_service):
    """Loading a session that was never saved returns None without raising."""
    result = await redis_service.get_session("nonexistent-integration-test-session-xyz")
    assert result is None, (
        f"Expected None for non-existent session, got {type(result).__name__}"
    )
