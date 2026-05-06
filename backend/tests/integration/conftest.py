"""Integration test fixtures.

All integration tests require live Docker services (Qdrant, PostgreSQL).
If a required service is not reachable, all tests in the session are skipped
cleanly — they never fail with a connection error.

Guard pattern
-------------
  - ``require_qdrant`` (session-scoped, autouse) — skips if Qdrant at
    localhost:6333 is not reachable.
  - ``require_postgres`` (session-scoped) — skips if PostgreSQL is not reachable.
  - Individual test fixtures skip themselves on first use when the parent
    session-scoped guard would already have skipped.

LLM calls
---------
Never made in integration tests. Always mock LLMService.async_invoke()
at the patch target that matches the importing module's import statement.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Service guards — session-scoped so the reachability check runs once
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def require_qdrant():
    """Skip the entire session if Qdrant is not reachable at localhost:6333.

    autouse=True means every integration test in this directory inherits the
    skip automatically — no need to declare the fixture explicitly.
    """
    import httpx

    try:
        response = httpx.get("http://localhost:6333/healthz", timeout=3.0)
        if response.status_code != 200:
            pytest.skip("Qdrant not healthy — skipping integration tests")
    except Exception:
        pytest.skip(
            "Qdrant not reachable at localhost:6333 — skipping integration tests. "
            "Start Docker services with: docker compose up -d"
        )


@pytest.fixture(scope="session")
def require_postgres():
    """Skip if PostgreSQL is not reachable.

    Not autouse — only tests that need PostgreSQL declare this fixture.
    """
    import psycopg2

    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            dbname="dichvucong",
            user="dichvucong",
            password="dichvucong",
            connect_timeout=3,
        )
        conn.close()
    except Exception:
        pytest.skip(
            "PostgreSQL not reachable at localhost:5432 — skipping test. "
            "Start Docker services with: docker compose up -d"
        )


# ---------------------------------------------------------------------------
# Real service fixtures — session-scoped to avoid teardown/startup overhead
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def qdrant_service(require_qdrant):
    """Real QdrantService against localhost:6333.

    Session-scoped: constructed once for the entire test session.
    Depends on ``require_qdrant`` so it is only created when Qdrant is up.
    """
    from app.services.qdrant_service import QdrantService

    return QdrantService()


@pytest.fixture(scope="session")
def embedder_service(require_qdrant):
    """Real EmbedderService — loads the embedding model once per session."""
    from app.services.embedder import EmbedderService

    return EmbedderService()


# ---------------------------------------------------------------------------
# TTHC-001 UUID fixture — fetches from live PostgreSQL
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def tthc001_uuid(require_postgres):
    """Fetch the real TTHC-001 UUID from PostgreSQL.

    Skips if the procedures table has no row with procedure_id = 'TTHC-001'.
    The UUID is fetched once per session.
    """
    import psycopg2

    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            dbname="dichvucong",
            user="dichvucong",
            password="dichvucong",
            connect_timeout=3,
        )
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM procedures WHERE procedure_id = %s LIMIT 1",
            ("TTHC-001",),
        )
        row = cur.fetchone()
        conn.close()
    except Exception as exc:
        pytest.skip(f"Could not query procedures table: {exc}")

    if row is None:
        pytest.skip(
            "No procedure with procedure_id='TTHC-001' found in database. "
            "Run: cd backend && PYTHONPATH=. .venv/Scripts/python ingestion/ingest_procedures.py"
        )

    return str(row[0])


# ---------------------------------------------------------------------------
# Base AgentState fixture — minimal valid dict for graph tests
# ---------------------------------------------------------------------------

@pytest.fixture
def base_agent_state() -> dict:
    """Return a minimal valid AgentState dict for agent graph integration tests.

    All optional fields are either absent or set to their zero/None value.
    Override specific fields in individual tests via dict.update() or unpacking.
    """
    return {
        # Required fields
        "user_message": "Điều kiện đăng ký thường trú là gì?",
        "session_id": "integ-test-session-001",
        "iteration_count": 0,
        # Input
        "uploaded_image_path": None,
        # Routing
        "execution_plan": ["rag_fn"],
        "plan_cursor": 0,
        "entities": {},
        "domain": "housing",
        "filing_jurisdiction": None,
        # Conversation history — empty on first turn
        "conversation_history": [],
        # RAG
        "retrieved_chunks": [],
        "citations": [],
        "scope_used": None,
        # OCR
        "personal_data": None,
        "extracted_personal_data": None,
        "document_type": None,
        # Procedure
        "target_procedure_id": None,
        "procedure_execution_plan": [],
        "completed_procedures": [],
        # Form
        "form_id": None,
        "filled_fields": {},
        "unfilled_required_fields": [],
        "filled_form_path": None,
        "form_fill_complete": False,
        # Output
        "final_response": "",
        "response_metadata": {},
        # Control
        "errors": [],
    }


# ---------------------------------------------------------------------------
# Fixtures for test_api_endpoints.py and test_session_persistence.py
# ---------------------------------------------------------------------------

@pytest.fixture
def session_id() -> str:
    """Fresh unique session_id for each test."""
    import uuid
    return f"test-{uuid.uuid4().hex[:8]}"


@pytest.fixture
async def http_client():
    """AsyncClient connected to the real FastAPI app via ASGI transport.

    The get_db dependency is overridden with a no-op mock so tests do not
    require a running PostgreSQL instance. MinIO lifespan is not triggered
    (ASGITransport does not run lifespan events).
    """
    from unittest.mock import AsyncMock
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.dependencies import get_db

    async def _mock_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = _mock_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="session")
def require_redis():
    """Skip if Redis is not reachable at localhost:6379."""
    import socket
    try:
        s = socket.create_connection(("localhost", 6379), timeout=1)
        s.close()
    except OSError:
        pytest.skip(
            "Redis not reachable at localhost:6379 — skipping test. "
            "Start Docker services with: docker compose up -d"
        )


@pytest.fixture
async def redis_service(require_redis):
    """Real RedisService connected to running Redis.

    Skips if REDIS_ENCRYPTION_KEY is not configured.
    """
    from app.services.redis_service import RedisService
    try:
        svc = RedisService()
        yield svc
    except RuntimeError as exc:
        pytest.skip(f"RedisService unavailable: {exc}")

