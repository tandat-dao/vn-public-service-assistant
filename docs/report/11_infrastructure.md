# Section 11 — Infrastructure

## 11.1 Docker Compose Services

4 services, all on `dichvucong-net` bridge network:

| Service | Image | Ports | Purpose | Persistence |
|---|---|---|---|---|
| `postgres` | `postgres:16-alpine` | 5432:5432 | PostgreSQL database — procedures, legal docs, sessions schema | Named volume `postgres_data` |
| `redis` | `redis:7-alpine` | 6379:6379 | Encrypted session storage, response cache, citizen carry-forward | Named volume `redis_data` (appendonly) |
| `qdrant` | `qdrant/qdrant:latest` | 6333:6333 (HTTP), 6334:6334 (gRPC) | Vector database for legal document chunks | Named volume `qdrant_data` |
| `minio` | `minio/minio:latest` | 9000:9000 (API), 9001:9001 (console) | Object storage for uploaded files and filled PDFs | Named volume `minio_data` |

**Health checks**: PostgreSQL (`pg_isready -U dichvucong`) and MinIO (`curl /minio/health/live`) have health checks configured. Redis and Qdrant do not.

**Redis command**: `redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}` — requires the `REDIS_PASSWORD` env var from the host `.env` file; AOF persistence enabled.

**MinIO credentials**: Hardcoded dev defaults (`minioadmin`/`minioadmin`) in `docker-compose.yml`. These match the defaults in `.env.example`.

## 11.2 Redis Session Model

### Key Structure

| Key Pattern | Content | TTL | Encryption |
|---|---|---|---|
| `session:{session_id}` | Fernet-encrypted `SessionData` JSON | 3600s (1 hour) | Yes — Fernet symmetric |
| `cache:{cache_key}` | Fernet-encrypted response string | 300s (5 min) | Yes — Fernet symmetric |
| `citizen:{citizen_id}:personal_data` | Fernet-encrypted `PersonalData` JSON | 86400s (24 hours) | Yes — Fernet symmetric |

### Encryption

All Redis values are encrypted with Fernet (symmetric key encryption from the `cryptography` library). The key is a URL-safe base64-encoded 32-byte value set in `REDIS_ENCRYPTION_KEY`. Empty key → `RuntimeError` at `RedisService.__init__()` — the service refuses to start without a key. No plaintext values are ever written to Redis.

**Custom JSON encoding**: `_DatetimeEncoder` handles `datetime`, `date`, `UUID`, `Decimal` objects (encoded as tagged dicts). `_datetime_decoder` reconstructs them on load.

### Session Lifecycle

1. **Load**: `get_session(session_id)` → decrypt → `model_validate(SessionData)`. Returns `None` on miss, decrypt failure, or parse error — never returns empty `SessionData`.
2. **Build AgentState**: caller slices history to last 6 turns (`[-6:]`) before constructing `AgentState`.
3. **Run**: LangGraph pipeline reads/writes `AgentState` (in-memory only, no Redis during graph execution).
4. **Save**: `save_session(session_id, updated)` → compact history → encrypt → write with TTL=3600.

### History Compaction (v3.45)

`_compact_history()` is called in `save_session()`. Activates when `len(conversation_history) > 6`. Compaction strategy:

- **LLM path** (opt-in, not currently used in default pipeline): Summarizes oldest turns in Vietnamese via `LLMService.async_invoke()`, adds 1-3s latency.
- **Default fallback path** (used in production): Concatenates up to 3 oldest user messages into a single `"Tóm tắt trước đó: ..."` synthetic assistant message. Fast (< 1ms).

Result: most-recent 5 turns are kept verbatim; older turns are replaced by the synthetic summary entry.

### Citizen Carry-Forward (v3.76)

When a user uploads a CCCD, the `PersonalData` result is saved to `citizen:{citizenId}:personal_data` (24h TTL). On subsequent sessions from the same browser, the frontend sends `citizen_id` (from localStorage) in the chat request and upload. The backend loads the citizen key at session hydration time if no `extracted_personal_data` is in the current session. This persists OCR results across browser tabs and sessions without requiring a new CCCD upload.

## 11.3 MinIO Storage

**Bucket**: `dichvucong` (single bucket, private policy — empty `Statement` list).

**Bucket initialization**: Handled in FastAPI lifespan at startup — creates the bucket if it doesn't exist, applies the private policy. If MinIO is not reachable at startup, a warning is logged and startup continues.

**Path structure**:

| Path Prefix | Content | Promotion |
|---|---|---|
| `tmp/{session_id}/{uuid}.{ext}` | Uploaded documents (CCCD images) — temporary | Never promoted; stays in `tmp/` |
| `tmp/{session_id}/{form_id}.pdf` | In-progress / unverified filled PDFs | Promoted to `forms/` on successful form fill |
| `forms/{session_id}/{form_id}.pdf` | Completed filled PDFs (all required fields filled) | Final location |

**Promotion**: `StorageService.promote_tmp(src_path, dest_path)` copies `tmp/` to `forms/` then deletes the `tmp/` copy. Delete failure is logged as warning and does not raise — the copy is complete so the user can still download.

**Download security**: `GET /api/v1/documents/download` validates that the `path` query param's session component (`path.split("/")[1]`) matches the `session_id` query param. Mismatched or malformed paths return HTTP 403.

**All blocking MinIO SDK calls** are wrapped in `asyncio.get_event_loop().run_in_executor(None, ...)` inside `StorageService` — they never block the FastAPI event loop.

## 11.4 Alembic Migration History

3 migrations, linear chain:

```
0001 → 0002 → 0003
```

| Migration | Key Changes |
|---|---|
| `0001_initial_schema.py` (2026-03-05) | 7 tables: procedure_categories, procedures, procedure_dependencies, form_templates, legal_documents, procedure_legal_docs, sessions |
| `0002_legal_doc_versioning.py` (2026-03-19) | Adds `superseded_by` self-referential FK on `legal_documents` |
| `0003_jurisdiction_and_domain.py` (2026-03-29) | Adds `domain` column to `procedures`; creates `administrative_units` and `scope_coverage` tables |

Alembic configuration: `backend/alembic.ini` + `backend/alembic/script.py.mako` (migration template). Convention: `NEVER modify a committed migration — add a new one.`

## 11.5 Ngrok Support (v3.74)

`CORS_EXTRA_ORIGINS` env var: comma-separated list of additional CORS origins. Added to allow Ngrok tunnels without modifying `CORS_ALLOW_ORIGINS`. The frontend checks `NEXT_PUBLIC_API_URL_PUBLIC` for the public-facing Ngrok URL; if set, uses it as the API base URL. The `ngrok-skip-browser-warning` header is automatically injected in `client.ts` when the base URL contains `"ngrok"`.

## 11.6 Rate Limiting

Rate limiting uses `slowapi` with the client IP as the key. Limits are configured via env vars:

| Env Var | Default | Applied To |
|---|---|---|
| `CHAT_RATE_LIMIT` | `"10/minute"` | `POST /api/v1/chat` |
| `UPLOAD_RATE_LIMIT` | `"5/minute"` | `POST /api/v1/documents/upload`, `GET /api/v1/documents/download` |

Rate limit exceeded → HTTP 429 with JSON body: `{"error": "rate_limit_exceeded", "detail": "Too many requests"}`.

The `Limiter` instance lives in `app/rate_limit.py` (standalone module to avoid circular imports between `app/main.py` and route handlers).

## 11.7 Startup Sequence

FastAPI lifespan (`@asynccontextmanager` in `main.py`):
1. **MinIO bucket init**: Creates `dichvucong` bucket if absent, applies private policy. Failure is non-fatal (warning logged).
2. **Embedding model eager load**: Calls `_get_embedder()` to warm up the bge-m3 model singleton (~2-5 minutes on first cold start). Failure is non-fatal — OpenAI fallback handles subsequent requests.
3. **API ready**: Application starts serving requests.

The `/health` endpoint returns HTTP 503 until the embedding model is loaded (condition: `_embedder_mod._embedder_svc is not None`). All other conditions (Qdrant connectivity, Redis ping, PostgreSQL connectivity) are informational only — they never cause 503.
