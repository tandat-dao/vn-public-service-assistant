"""FastAPI application factory."""

import json
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from minio import Minio
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import router as v1_router
from app.config import settings
from app.rate_limit import limiter

logger = structlog.get_logger(__name__)


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"error": "rate_limit_exceeded", "detail": "Too many requests"},
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # MinIO bucket initialisation — private policy (empty Statement list)
    try:
        client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False,
        )
        if not client.bucket_exists(settings.MINIO_BUCKET):
            client.make_bucket(settings.MINIO_BUCKET)
            client.set_bucket_policy(
                settings.MINIO_BUCKET,
                json.dumps({"Version": "2012-10-17", "Statement": []}),
            )
        logger.info("MinIO bucket ready", bucket=settings.MINIO_BUCKET)
    except Exception as exc:
        logger.warning("MinIO not reachable at startup", error=str(exc))

    # Eagerly load the embedding model so the first chat request does not
    # incur a 2-5 minute cold start.  Import inside lifespan to avoid
    # running model load when unit tests import main.py.
    try:
        from app.services.embedder import _get_embedder
        _get_embedder()
    except Exception as exc:
        # bge-m3 load failure is non-fatal — OpenAI fallback handles live
        # requests.  Log a warning and continue startup.
        logger.warning(
            "Embedding model failed to load at startup — OpenAI fallback active",
            error=str(exc),
        )

    logger.info("DichVuCong API starting up", environment=settings.ENVIRONMENT)
    yield
    logger.info("DichVuCong API shutting down")


app = FastAPI(
    title="DichVuCong AI Assistant",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS — locked to configured origins, never wildcard
_cors_base = [o.strip() for o in settings.CORS_ALLOW_ORIGINS.split(",") if o.strip()]
_cors_extra = [o.strip() for o in settings.CORS_EXTRA_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_base + _cors_extra,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")


@app.get("/health")
async def health():
    """Startup verification endpoint.

    Returns HTTP 200 with per-service status booleans.
    Returns HTTP 503 only when the embedding model singleton is not yet loaded.
    All service checks are wrapped in try/except — a failed check never crashes
    this endpoint.
    """
    import app.services.embedder as _embedder_mod

    # Embedding model check — the only condition that causes 503
    model_loaded = _embedder_mod._embedder_svc is not None
    embedding_status = "loaded" if model_loaded else "not_loaded"

    # --- Qdrant ---
    qdrant_ok = False
    try:
        from qdrant_client import AsyncQdrantClient
        _qclient = AsyncQdrantClient(url=settings.QDRANT_URL)
        await _qclient.get_collections()
        qdrant_ok = True
    except Exception:
        pass

    # --- Redis ---
    redis_ok = False
    try:
        import redis.asyncio as aioredis
        _rclient = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await _rclient.ping()
        await _rclient.aclose()
        redis_ok = True
    except Exception:
        pass

    # --- PostgreSQL ---
    postgres_ok = False
    try:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine
        _pg_engine = create_async_engine(settings.POSTGRES_URL)
        async with _pg_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await _pg_engine.dispose()
        postgres_ok = True
    except Exception:
        pass

    import torch

    body = {
        "status": "ready" if model_loaded else "warming_up",
        "embedding_model": embedding_status,
        "services": {
            "qdrant": qdrant_ok,
            "redis": redis_ok,
            "postgres": postgres_ok,
        },
        "gpu": {
            "cuda_available": torch.cuda.is_available(),
            "device_name": (
                torch.cuda.get_device_name(0)
                if torch.cuda.is_available() else None
            ),
            "vram_total_mb": (
                round(
                    torch.cuda.get_device_properties(0).total_memory
                    / 1024 / 1024
                )
                if torch.cuda.is_available() else None
            ),
        },
    }
    status_code = 200 if model_loaded else 503
    return JSONResponse(content=body, status_code=status_code)
