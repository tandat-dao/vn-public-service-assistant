"""Forms API routes."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.schemas.form import (
    FormFillRequest,
    FormFillResponse,
    FormSubmissionRequest,
    FormSubmissionResponse,
)

router = APIRouter()


@router.post("/submit", response_model=FormSubmissionResponse)
async def submit_form(request: FormSubmissionRequest) -> FormSubmissionResponse:
    """Receive a residence form submission (manual or AI-filled).

    Phase 1: generates a tracking code and returns immediately.
    Phase 2: will persist to PostgreSQL and dispatch a Celery task.
    submission_mode='ai' is reserved for the LangGraph form_filler_node.
    """
    # Phase 2: replace with DB insert + Celery dispatch
    # submission = FormSubmissionORM(...); db.add(submission); await db.commit()
    ma_ho_so = f"DVC-{datetime.now(timezone.utc).strftime('%Y')}-{str(uuid.uuid4())[:8].upper()}"
    return FormSubmissionResponse(
        ma_ho_so=ma_ho_so,
        form_type=request.form_type,
        submitted_at=datetime.now(timezone.utc),
        status="received",
        message=f"Hồ sơ của bạn đã được tiếp nhận. Mã hồ sơ: {ma_ho_so}",
    )


@router.get("/{form_id}")
async def get_form_schema(form_id: str) -> dict:
    """Return the form template schema (field definitions)."""
    raise NotImplementedError


@router.post("/fill", response_model=FormFillResponse)
async def fill_form(request: FormFillRequest) -> FormFillResponse:
    """Fill a PDF form with personal data from the session."""
    raise NotImplementedError


@router.get("/filled/{file_path:path}", response_class=FileResponse)
async def get_filled_form(file_path: str) -> FileResponse:
    """Download a filled PDF form."""
    raise NotImplementedError
