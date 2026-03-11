"""Top-level v1 API router — aggregates all sub-routers."""

from fastapi import APIRouter

from app.api.v1 import chat, documents, forms, legal, procedures

router = APIRouter()
router.include_router(chat.router, prefix="/chat", tags=["Chat"])
router.include_router(procedures.router, prefix="/procedures", tags=["Procedures"])
router.include_router(documents.router, prefix="/documents", tags=["Documents"])
router.include_router(forms.router, prefix="/forms", tags=["Forms"])
router.include_router(legal.router, prefix="/legal", tags=["Legal"])
