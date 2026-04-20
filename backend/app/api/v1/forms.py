"""Forms API routes."""

import json
import random
import string
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.form import (
    FormFillRequest,
    FormFillResponse,
    FormSubmissionRequest,
    FormSubmissionResponse,
)

router = APIRouter()


def _generate_tracking_code() -> str:
    """Generate a tracking code: DVC-{YYYYMMDD}-{6 random uppercase alphanumeric chars}.

    Example: DVC-20260412-K7FX3P
    """
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"DVC-{date_str}-{suffix}"


@router.post("/submit", response_model=FormSubmissionResponse)
async def submit_form(
    request: FormSubmissionRequest,
    db: AsyncSession = Depends(get_db),
) -> FormSubmissionResponse:
    """Receive a residence form submission (manual or AI-filled).

    Generates a tracking code, persists submission metadata to DB, and returns
    a confirmation response. submission_mode='ai' is reserved for the LangGraph
    form_filler_fn worker.

    Note: no dedicated form_submissions table exists in the current schema.
    Submission metadata is stored in sessions.form_fill_state (JSONB) as a
    temporary measure. A future migration should add a form_submissions table.
    """
    # ---- Step 1: Validate form_data is not empty ----
    form_dict = request.form_data.model_dump(exclude_none=True)
    if not form_dict:
        raise HTTPException(status_code=422, detail="form_data không được để trống.")

    # ---- Step 2: Generate tracking code ----
    tracking_code = _generate_tracking_code()
    submitted_at = datetime.now(timezone.utc)

    # ---- Step 3: Persist to DB ----
    # Stores in sessions table (form_fill_state JSONB) since no form_submissions
    # table exists in the current migration. The submission_type field
    # distinguishes these rows from regular session records.
    submission_payload = json.dumps(
        {
            "_submission_type": "form_submit",
            "tracking_code": tracking_code,
            "form_type": request.form_type,
            "session_id": request.session_id,
            "submission_mode": request.submission_mode,
            "form_data": form_dict,
            "status": "pending",
            "submitted_at": submitted_at.isoformat(),
        }
    )
    try:
        await db.execute(
            text(
                "INSERT INTO sessions (id, form_fill_state, created_at, updated_at) "
                "VALUES (gen_random_uuid(), cast(:payload AS jsonb), now(), now())"
            ),
            {"payload": submission_payload},
        )
        await db.commit()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Không thể lưu hồ sơ. Vui lòng thử lại.",
        ) from exc

    # ---- Step 4: Return response ----
    return FormSubmissionResponse(
        ma_ho_so=tracking_code,
        form_type=request.form_type,
        submitted_at=submitted_at,
        status="received",
        message=f"Hồ sơ đã được tiếp nhận. Mã hồ sơ của bạn là {tracking_code}.",
    )


@router.get("/{form_id}")
async def get_form_schema(form_id: str) -> dict:
    """Return the form template schema (field definitions)."""
    raise NotImplementedError


@router.post("/fill", response_model=FormFillResponse)
async def fill_form(request: FormFillRequest) -> FormFillResponse:
    """Fill a PDF form with personal data from the session."""
    raise NotImplementedError


