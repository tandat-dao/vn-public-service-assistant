"""Redis service — session persistence across agent invocations."""


class RedisService:
    """Session store backed by Redis."""

    async def get_session(self, session_id: str) -> dict:
        """Load session data. Returns empty dict if session does not exist."""
        raise NotImplementedError

    async def save_session(self, session_id: str, data: dict) -> None:
        raise NotImplementedError

    async def delete_session(self, session_id: str) -> None:
        raise NotImplementedError
