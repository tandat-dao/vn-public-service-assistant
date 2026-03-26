"""Redis service — session persistence across agent invocations.

Session data is Fernet-encrypted before storage so that PII values (PersonalData)
are never written as plaintext to Redis.  The encryption key is a URL-safe
base64-encoded 32-byte value stored in the REDIS_ENCRYPTION_KEY env var.
"""

import json
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import structlog
from cryptography.fernet import Fernet, InvalidToken

from app.config import settings
from app.schemas.session import SessionData

logger = structlog.get_logger(__name__)

_SESSION_TTL = 3600  # 1 hour
_MAX_HISTORY_TURNS = 6


class _DatetimeEncoder(json.JSONEncoder):
    """Custom JSON encoder handling types not natively serialisable."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return {"__type__": "datetime", "value": obj.isoformat()}
        if isinstance(obj, date):
            return {"__type__": "date", "value": obj.isoformat()}
        if isinstance(obj, UUID):
            return {"__type__": "uuid", "value": str(obj)}
        if isinstance(obj, Decimal):
            return {"__type__": "decimal", "value": str(obj)}
        return super().default(obj)


def _datetime_decoder(dct: dict) -> Any:
    """Object hook for json.loads — reconstructs typed values from _DatetimeEncoder."""
    if "__type__" not in dct:
        return dct
    t = dct["__type__"]
    v = dct["value"]
    if t == "datetime":
        return datetime.fromisoformat(v)
    if t == "date":
        return date.fromisoformat(v)
    if t == "uuid":
        return UUID(v)
    if t == "decimal":
        return Decimal(v)
    return dct


class RedisService:
    """Session store backed by Redis with Fernet-encrypted values."""

    def __init__(self) -> None:
        import redis.asyncio as aioredis

        if not settings.REDIS_ENCRYPTION_KEY:
            raise RuntimeError(
                "REDIS_ENCRYPTION_KEY is not set. "
                "Generate one with Fernet.generate_key() and add it to .env."
            )
        self._fernet = Fernet(settings.REDIS_ENCRYPTION_KEY.encode())
        self._client = aioredis.from_url(
            settings.REDIS_URL,
            password=settings.REDIS_PASSWORD or None,
            decode_responses=False,  # raw bytes — we handle encoding
        )

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def get_session(self, session_id: str) -> SessionData | None:
        """Load and decrypt session data. Returns None if not found or on decryption failure."""
        raw: bytes | None = await self._client.get(f"session:{session_id}")
        if raw is None:
            return None
        try:
            plaintext = self._fernet.decrypt(raw)
            data = json.loads(plaintext, object_hook=_datetime_decoder)
            return SessionData.model_validate(data)
        except (InvalidToken, json.JSONDecodeError, Exception) as exc:
            logger.warning(
                "Failed to decrypt/parse session — returning None",
                session_id=session_id,
                error=str(exc),
            )
            return None

    async def save_session(self, session_id: str, data: SessionData) -> None:
        """Trim history, update timestamp, encrypt, and persist with TTL of 3600 seconds."""
        # Enforce 6-turn window and update timestamp
        trimmed_history = data.conversation_history[-_MAX_HISTORY_TURNS:]
        data = data.model_copy(
            update={
                "conversation_history": trimmed_history,
                "updated_at": datetime.utcnow(),
            }
        )
        payload = data.model_dump(mode="python")
        plaintext = json.dumps(payload, cls=_DatetimeEncoder).encode()
        ciphertext = self._fernet.encrypt(plaintext)
        await self._client.set(f"session:{session_id}", ciphertext, ex=_SESSION_TTL)

    async def delete_session(self, session_id: str) -> None:
        await self._client.delete(f"session:{session_id}")

    # ------------------------------------------------------------------
    # Response cache (short-lived, not encrypted — no PII)
    # ------------------------------------------------------------------

    async def get_cached_response(self, cache_key: str) -> str | None:
        raw: bytes | None = await self._client.get(f"cache:{cache_key}")
        if raw is None:
            return None
        ciphertext = raw
        try:
            plaintext = self._fernet.decrypt(ciphertext)
            return plaintext.decode()
        except Exception:
            return None

    async def cache_response(self, cache_key: str, value: str, ttl: int = 300) -> None:
        ciphertext = self._fernet.encrypt(value.encode())
        await self._client.set(f"cache:{cache_key}", ciphertext, ex=ttl)
