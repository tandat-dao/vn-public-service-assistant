"""Unit tests for RedisService.

All tests use a mocked Redis client — no real Redis connection required.
"""

import json
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from app.schemas.personal_data import PersonalData
from app.schemas.session import SessionData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fernet_key() -> str:
    return Fernet.generate_key().decode()


def _make_service(fernet_key: str):
    """Return a RedisService with mocked Redis client and the given Fernet key."""
    from app.services.redis_service import RedisService

    mock_client = AsyncMock()

    with patch("app.services.redis_service.settings") as mock_settings:
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_settings.REDIS_PASSWORD = ""
        mock_settings.REDIS_ENCRYPTION_KEY = fernet_key

        with patch("redis.asyncio.from_url", return_value=mock_client):
            svc = RedisService()
            svc._client = mock_client
            return svc, mock_client


def _make_personal_data() -> PersonalData:
    return PersonalData(
        full_name="Nguyễn Văn A",
        date_of_birth=date(1990, 5, 15),
        id_number="012345678901",
        source_document_type="CCCD",
        source_image_path="/tmp/test.jpg",
        extraction_confidence=0.95,
        field_confidences={"full_name": 0.98, "id_number": 0.99},
        extracted_at=datetime(2026, 3, 26, 10, 0, 0),
    )


# ---------------------------------------------------------------------------
# Test: save_session encrypts value
# ---------------------------------------------------------------------------

class TestSaveSession:
    async def test_save_session_encrypts_value(self):
        """Value written to redis must be Fernet ciphertext, not plaintext JSON."""
        key = _make_fernet_key()
        svc, mock_client = _make_service(key)

        captured: list[bytes] = []

        async def _set(k, v, ex=None):
            captured.append(v)

        mock_client.set = _set

        data = SessionData(session_id="s1")
        await svc.save_session("s1", data)

        assert len(captured) == 1
        raw = captured[0]
        # Must be bytes
        assert isinstance(raw, bytes)
        # Must NOT be valid JSON (it is ciphertext)
        try:
            json.loads(raw.decode())
            pytest.fail("Stored value is plaintext JSON — should be ciphertext")
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass  # expected

    async def test_save_session_sets_ttl_3600(self):
        """save_session must pass ex=3600 to redis.set()."""
        key = _make_fernet_key()
        svc, mock_client = _make_service(key)

        captured_kwargs: list[dict] = []

        async def _set(k, v, ex=None):
            captured_kwargs.append({"ex": ex})

        mock_client.set = _set

        await svc.save_session("s2", SessionData(session_id="s2"))

        assert captured_kwargs[0]["ex"] == 3600

    async def test_save_session_trims_history_to_6(self):
        """save_session must compact conversation_history when it exceeds 6 turns.

        With 10 turns: oldest turns are condensed into a synthetic summary entry
        (role="assistant", content prefixed "Tóm tắt trước đó: ") and the most
        recent turns are kept. Result is bounded to at most 7 entries (1 summary + 6).
        """
        key = _make_fernet_key()
        svc, mock_client = _make_service(key)

        history = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
        data = SessionData(session_id="s3", conversation_history=history)

        stored_bytes: list[bytes] = []

        async def _set(k, v, ex=None):
            stored_bytes.append(v)

        mock_client.set = _set

        await svc.save_session("s3", data)

        fernet = Fernet(key.encode())
        from app.services.redis_service import _datetime_decoder
        plaintext = fernet.decrypt(stored_bytes[0])
        stored_data = json.loads(plaintext, object_hook=_datetime_decoder)

        stored_history = stored_data["conversation_history"]
        # History must be bounded (compaction: 1 synthetic + recent turns, ≤ 7 total)
        assert len(stored_history) <= 7
        # Most recent message must always be preserved
        assert stored_history[-1]["content"] == "msg 9"
        # First entry is the synthetic compaction summary
        assert stored_history[0]["role"] == "assistant"
        assert stored_history[0]["content"].startswith("Tóm tắt trước đó: ")


# ---------------------------------------------------------------------------
# Test: get_session
# ---------------------------------------------------------------------------

class TestGetSession:
    async def test_get_session_decrypts_correctly(self):
        """Manually encrypted SessionData must be correctly returned by get_session."""
        key = _make_fernet_key()
        svc, mock_client = _make_service(key)

        original = SessionData(
            session_id="s4",
            completed_procedure_ids=["TTHC-001"],
            conversation_history=[{"role": "user", "content": "xin chào"}],
        )

        # Encrypt manually with the same key
        fernet = Fernet(key.encode())
        from app.services.redis_service import _DatetimeEncoder
        payload = original.model_dump(mode="python")
        ciphertext = fernet.encrypt(json.dumps(payload, cls=_DatetimeEncoder).encode())

        mock_client.get = AsyncMock(return_value=ciphertext)

        result = await svc.get_session("s4")

        assert result is not None
        assert result.session_id == "s4"
        assert result.completed_procedure_ids == ["TTHC-001"]

    async def test_get_session_returns_none_for_missing_key(self):
        """get_session must return None when the key does not exist in Redis."""
        key = _make_fernet_key()
        svc, mock_client = _make_service(key)

        mock_client.get = AsyncMock(return_value=None)

        result = await svc.get_session("nonexistent")
        assert result is None

    async def test_get_session_returns_none_on_decryption_failure(self):
        """get_session must return None (not raise) when decryption fails."""
        key = _make_fernet_key()
        svc, mock_client = _make_service(key)

        mock_client.get = AsyncMock(return_value=b"not-valid-ciphertext")

        result = await svc.get_session("corrupted")
        assert result is None  # must not raise

    async def test_personaldata_survives_roundtrip(self):
        """date, datetime, and confidence scores must survive JSON serialisation."""
        key = _make_fernet_key()
        svc, mock_client = _make_service(key)

        pd = _make_personal_data()
        data = SessionData(session_id="s5", personal_data=pd)

        stored: list[bytes] = []

        async def _set(k, v, ex=None):
            stored.append(v)

        async def _get(k):
            return stored[0] if stored else None

        mock_client.set = _set
        mock_client.get = _get

        await svc.save_session("s5", data)
        recovered = await svc.get_session("s5")

        assert recovered is not None
        assert recovered.personal_data is not None
        assert recovered.personal_data.date_of_birth == date(1990, 5, 15)
        assert recovered.personal_data.extracted_at == datetime(2026, 3, 26, 10, 0, 0)
        assert recovered.personal_data.extraction_confidence == 0.95
        assert recovered.personal_data.field_confidences["full_name"] == 0.98


# ---------------------------------------------------------------------------
# Test: response cache
# ---------------------------------------------------------------------------

class TestResponseCache:
    async def test_cache_response_uses_provided_ttl(self):
        """cache_response must pass the caller-supplied ttl, not a hardcoded value."""
        key = _make_fernet_key()
        svc, mock_client = _make_service(key)

        captured: list[dict] = []

        async def _set(k, v, ex=None):
            captured.append({"ex": ex})

        mock_client.set = _set

        await svc.cache_response("my-key", "cached value", ttl=120)

        assert captured[0]["ex"] == 120  # not 3600

    async def test_cache_roundtrip(self):
        """cache_response + get_cached_response must return the original value."""
        key = _make_fernet_key()
        svc, mock_client = _make_service(key)

        store: dict[str, bytes] = {}

        async def _set(k, v, ex=None):
            store[k] = v

        async def _get(k):
            return store.get(k)

        mock_client.set = _set
        mock_client.get = _get

        await svc.cache_response("k1", "hello world", ttl=300)
        result = await svc.get_cached_response("k1")
        assert result == "hello world"


# ---------------------------------------------------------------------------
# Test: citizen personal data carry-forward
# ---------------------------------------------------------------------------

class TestCitizenPersonalData:
    async def test_get_citizen_personal_data_returns_none_when_absent(self):
        """get_citizen_personal_data must return None (not raise) when key absent."""
        key = _make_fernet_key()
        svc, mock_client = _make_service(key)

        mock_client.get = AsyncMock(return_value=None)

        result = await svc.get_citizen_personal_data("test-citizen-id")
        assert result is None

    async def test_save_and_get_citizen_personal_data_roundtrip(self):
        """PersonalData must survive Fernet encrypt → decrypt roundtrip under citizen key."""
        key = _make_fernet_key()
        svc, mock_client = _make_service(key)

        store: dict[str, bytes] = {}

        async def _set(k, v, ex=None):
            store[k] = v

        async def _get(k):
            return store.get(k)

        mock_client.set = _set
        mock_client.get = _get

        pd = _make_personal_data()
        await svc.save_citizen_personal_data("test-citizen-id", pd)

        # Verify key format
        expected_key = "citizen:test-citizen-id:personal_data"
        assert expected_key in store

        result = await svc.get_citizen_personal_data("test-citizen-id")

        assert result is not None
        assert result.full_name == "Nguyễn Văn A"
        assert result.id_number == "012345678901"


# ---------------------------------------------------------------------------
# Test: _compact_history
# ---------------------------------------------------------------------------

class TestCompactHistory:
    async def test_compact_history_no_op_under_threshold(self):
        """History with <= 6 turns must be returned unchanged (no LLM call, no summary)."""
        key = _make_fernet_key()
        svc, _ = _make_service(key)

        history = [{"role": "user", "content": f"msg {i}"} for i in range(5)]
        result = await svc._compact_history(history)

        assert result is history  # same object — unchanged

    async def test_compact_history_boundary_exactly_max(self):
        """History with exactly max_turns (6) entries must be returned unchanged."""
        key = _make_fernet_key()
        svc, _ = _make_service(key)

        history = [{"role": "user", "content": f"msg {i}"} for i in range(6)]
        result = await svc._compact_history(history)

        assert result is history  # same object — no summary prepended

    async def test_compact_history_fires_at_turn_7(self):
        """History with 7 turns must trigger compaction; result length must be <= 7."""
        key = _make_fernet_key()
        svc, _ = _make_service(key)

        history = [{"role": "user", "content": f"msg {i}"} for i in range(7)]

        mock_llm = MagicMock()
        mock_llm.async_invoke = AsyncMock(return_value="Tóm tắt hội thoại")

        result = await svc._compact_history(history, llm_service=mock_llm)

        assert len(result) <= 7
        # LLM must have been called once to summarise the oldest turns
        mock_llm.async_invoke.assert_awaited_once()
        # First entry is the synthetic summary with LLM output
        assert result[0]["role"] == "assistant"
        assert result[0]["content"] == "Tóm tắt trước đó: Tóm tắt hội thoại"
        # Most recent message is preserved
        assert result[-1]["content"] == "msg 6"

    async def test_compact_history_fallback_no_llm(self):
        """8 turns with llm_service=None must return <= 7 entries using concatenation fallback."""
        key = _make_fernet_key()
        svc, _ = _make_service(key)

        history = [{"role": "user", "content": f"msg {i}"} for i in range(8)]
        result = await svc._compact_history(history, llm_service=None)

        assert len(result) <= 7
        # First entry is the synthetic summary entry
        assert result[0]["role"] == "assistant"
        assert result[0]["content"].startswith("Tóm tắt trước đó:")
        # Most recent message preserved
        assert result[-1]["content"] == "msg 7"

    async def test_save_session_calls_compact(self):
        """save_session must await _compact_history — verifies wiring."""
        key = _make_fernet_key()
        svc, mock_client = _make_service(key)

        stored_bytes: list[bytes] = []

        async def _set(k, v, ex=None):
            stored_bytes.append(v)

        mock_client.set = _set

        history = [{"role": "user", "content": f"msg {i}"} for i in range(4)]
        data = SessionData(session_id="sc1", conversation_history=history)

        compact_result = [{"role": "user", "content": "compacted"}]

        with patch.object(svc, "_compact_history", new=AsyncMock(return_value=compact_result)) as mock_compact:
            await svc.save_session("sc1", data)
            mock_compact.assert_awaited_once_with(history)
