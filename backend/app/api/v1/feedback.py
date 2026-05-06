"""Feedback endpoint — append-only JSONL log of user message ratings."""

import json
from datetime import datetime
from pathlib import Path

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()
logger = structlog.get_logger()

FEEDBACK_FILE = Path(__file__).parent.parent.parent.parent / "data" / "feedback.jsonl"


class FeedbackRequest(BaseModel):
    session_id: str
    message_id: str
    feedback: str  # "helpful" | "unhelpful"
    timestamp: str


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    entry = {
        "session_id": request.session_id,
        "message_id": request.message_id,
        "feedback": request.feedback,
        "timestamp": request.timestamp,
        "received_at": datetime.utcnow().isoformat(),
    }
    logger.info(
        "feedback received",
        feedback=request.feedback,
        session_id=request.session_id[:8] + "...",
    )
    try:
        FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("feedback write failed", error=str(e))
    return {"status": "ok"}
