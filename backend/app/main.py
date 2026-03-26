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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
