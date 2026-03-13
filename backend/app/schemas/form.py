"""Pydantic schemas for form fill operations."""

from datetime import datetime
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


# ── Residence form submission (Phase 1: manual input; Phase 2: AI fill) ──────

class ResidenceFormData(BaseModel):
    """Flat payload for all three residence form types.
    Field names mirror PersonalData keys where the field is shared — this is
    the contract the AI form-filler node will depend on in Phase 2."""

    # Shared — map to PersonalData
    ho_ten: str | None = None                           # → full_name
    ngay_sinh: str | None = None                        # → date_of_birth (DD/MM/YYYY)
    gioi_tinh: Literal["Nam", "Nữ"] | None = None      # → gender
    so_cccd: str | None = None                          # → id_number

    # Đăng ký thường trú
    noi_thuong_tru_cu: str | None = None
    dia_chi_thuong_tru_moi: str | None = None
    quan_he_chu_ho: str | None = None
    ten_chu_ho: str | None = None
    cccd_chu_ho: str | None = None

    # Đăng ký tạm trú
    dia_chi_thuong_tru: str | None = None               # → permanent_address
    dia_chi_tam_tru: str | None = None                  # → temporary_address
    tu_ngay: str | None = None
    den_ngay: str | None = None
    muc_dich: str | None = None

    # Xác nhận cư trú
    dia_chi_can_xac_nhan: str | None = None
    loai_xac_nhan: Literal["Thường trú", "Tạm trú"] | None = None
    muc_dich_xac_nhan: str | None = None


class FormSubmissionRequest(BaseModel):
    form_type: Literal["thuong-tru", "tam-tru", "xac-nhan"]
    session_id: str
    submission_mode: Literal["manual", "ai"] = "manual"
    form_data: ResidenceFormData


class FormSubmissionResponse(BaseModel):
    ma_ho_so: str
    form_type: str
    submitted_at: datetime
    status: Literal["received", "processing", "completed"] = "received"
    message: str
