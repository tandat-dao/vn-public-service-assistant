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
        """save_session must trim conversation_history to the last 6 entries."""
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

        assert len(stored_data["conversation_history"]) == 6
        # Must be the LAST 6, not the first 6
        assert stored_data["conversation_history"][0]["content"] == "msg 4"
        assert stored_data["conversation_history"][-1]["content"] == "msg 9"


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
            completed_procedure_ids=["TTDN-001"],
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
        assert result.completed_procedure_ids == ["TTDN-001"]

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
