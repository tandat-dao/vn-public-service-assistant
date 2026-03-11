"""FastAPI application factory."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.config import settings

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("DichVuCong API starting up", environment=settings.ENVIRONMENT)
    yield
    logger.info("DichVuCong API shutting down")


app = FastAPI(
    title="DichVuCong AI Assistant",
    version="0.1.0",
    lifespan=lifespan,
)

if settings.is_development:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(v1_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
