"""Forms API routes."""

import json
import random
import string
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
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


# ---------------------------------------------------------------------------
# Fill request schema
# ---------------------------------------------------------------------------

class FillFormRequest(BaseModel):
    procedure_id: str
    form_file: str
    field_values: dict[str, str] = {}


# ---------------------------------------------------------------------------
# POST /fill — fill a .doc form and return it as a file download
# ---------------------------------------------------------------------------

@router.post("/fill")
async def fill_form(request: FillFormRequest) -> Response:
    """Fill a .doc form template with the supplied field values.

    Validates that form_file is a valid choice for procedure_id, then calls
    doc_filler.fill_doc() and returns the filled document as a file download.

    Returns:
        200 — .doc file bytes with correct Content-Type and Content-Disposition.
        422 — form_file is not valid for the given procedure_id.
        404 — form source file not found on disk.
    """
    from app.core.form_field_configs import PROCEDURE_FORM_FILES
    from app.services.doc_filler import fill_doc

    # ── Validate procedure_id ───────────────────────────────────────────────
    if request.procedure_id not in PROCEDURE_FORM_FILES:
        raise HTTPException(
            status_code=422,
            detail="form_file not valid for procedure_id",
        )

    # ── Validate form_file belongs to this procedure ───────────────────────
    allowed_files = PROCEDURE_FORM_FILES[request.procedure_id]
    if request.form_file not in allowed_files:
        raise HTTPException(
            status_code=422,
            detail="form_file not valid for procedure_id",
        )

    # ── Fill the document ─────────────────────────────────────────────────
    try:
        doc_bytes = await fill_doc(request.form_file, request.field_values)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Form source file not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return Response(
        content=doc_bytes,
        media_type=(
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{request.form_file}"',
        },
    )


# ---------------------------------------------------------------------------
# GET /configs/{procedure_id} — return field configs for a procedure
# ---------------------------------------------------------------------------

@router.get("/configs/{procedure_id}")
async def get_form_configs(procedure_id: str) -> dict:
    """Return the ordered list of form files and their field definitions for a procedure.

    Used by the frontend to know which tabs and input fields to render.

    Returns:
        200 — { procedure_id, forms: [ { form_file, tab_label, fields } ] }
        404 — procedure_id not found in PROCEDURE_FORM_FILES.
    """
    from app.core.form_field_configs import FORM_FILE_CONFIGS, PROCEDURE_FORM_FILES

    if procedure_id not in PROCEDURE_FORM_FILES:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy thủ tục: {procedure_id}",
        )

    form_files = PROCEDURE_FORM_FILES[procedure_id]

    forms = []
    for form_file in form_files:
        cfg = FORM_FILE_CONFIGS.get(form_file)
        if cfg is None:
            continue
        forms.append(
            {
                "form_file": cfg["form_file"],
                "tab_label": cfg["tab_label"],
                "fields": cfg["fields"],
            }
        )

    return {
        "procedure_id": procedure_id,
        "forms": forms,
    }


# ---------------------------------------------------------------------------
# GET /{form_id} — schema stub (not yet implemented)
# ---------------------------------------------------------------------------

@router.get("/{form_id}")
async def get_form_schema(form_id: str) -> dict:
    """Return the form template schema (field definitions)."""
    raise NotImplementedError
