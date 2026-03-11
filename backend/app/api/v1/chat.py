"""Chat API routes."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest

router = APIRouter()


@router.post("", response_class=StreamingResponse)
async def chat(request: ChatRequest) -> StreamingResponse:
    """Stream agent response as Server-Sent Events."""
    raise NotImplementedError
