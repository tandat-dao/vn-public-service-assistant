"""Shared rate-limiter instance — imported by main.py and route handlers.

Kept in a separate module to avoid circular imports:
  main.py → router → chat.py → (needs limiter) → main.py  ← circular
  main.py → router → chat.py → rate_limit.py            ← fine
"""

from slowapi import Limiter


def _get_session_id_key(request) -> str:
    """Rate-limit key: session_id from cached request body, falls back to client IP.

    FastAPI caches the request body in request._body after the first read.
    For JSON endpoints this is always populated before the route handler runs.
    Falls back to client IP so requests without a session_id are still limited.
    """
    try:
        import json as _json

        raw = getattr(request, "_body", None)
        if raw:
            data = _json.loads(raw)
            sid = data.get("session_id")
            if sid:
                return str(sid)
    except Exception:
        pass
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=_get_session_id_key)
