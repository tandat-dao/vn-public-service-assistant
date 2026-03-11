"""Forms API routes."""

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.schemas.form import FormFillRequest, FormFillResponse

router = APIRouter()


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
