"""Chat API routes."""

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.config import settings
from app.rate_limit import limiter
from app.schemas.chat import ChatRequest

router = APIRouter()


@router.post("", response_class=StreamingResponse)
@limiter.limit(settings.CHAT_RATE_LIMIT)
async def chat(request: Request, body: ChatRequest) -> StreamingResponse:
    """Stream agent response as Server-Sent Events."""
    raise NotImplementedError
