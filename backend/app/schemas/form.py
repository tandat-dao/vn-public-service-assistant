"""Pydantic schemas for form fill operations."""

from typing import Literal

from pydantic import BaseModel


class FormFieldDefinition(BaseModel):
    field_name: str
    field_type: Literal["text", "date", "checkbox", "signature"]
    label: str
    is_required: bool
    source: Literal["ocr_extraction", "user_input", "derived", "carry_forward"]


class FormFillRequest(BaseModel):
    form_id: str
    session_id: str
    manual_overrides: dict[str, str] = {}


class FormFillResponse(BaseModel):
    filled_pdf_path: str
    filled_fields: dict[str, str]
    unfilled_required_fields: list[str]
