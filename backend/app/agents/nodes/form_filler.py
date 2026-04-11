"""Form filler worker function — maps personal data to PDF form fields and fills the form.

Called by plan_executor_node via NODE_REGISTRY["form_filler_fn"].
This is a plain async function, NOT a LangGraph graph node — never add decorators.

Pipeline:
  1. Merge extracted_personal_data (latest OCR) into personal_data (accumulated)
     via SessionDataAccumulator.
  2. Look up the PDF template path for the target procedure.
  3. Get the form's fillable field names (hardcoded placeholder until TASK-15).
  4. Map PersonalData values to form fields via FormFieldMapper (LLM + cache).
  5. Fill the PDF via PDFService and write to tmp/ in MinIO.
  6. If all required fields are filled, promote to forms/{session_id}/{proc}.pdf.
     Otherwise leave in tmp/ and surface unfilled fields to the Synthesizer.
"""

from __future__ import annotations

import structlog

from app.agents.state import AgentState
from app.core.form_field_mapper import FormFieldMapper
from app.core.session_accumulator import SessionDataAccumulator

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Lazy service singletons
# Instantiated on first use so that import-time side effects are avoided and
# tests can patch these getters before form_filler_fn is called.
# ---------------------------------------------------------------------------

_llm_svc = None
_storage_svc = None
_pdf_svc = None


def _get_llm_svc():
    global _llm_svc
    if _llm_svc is None:
        from app.services.llm import LLMService
        _llm_svc = LLMService()
    return _llm_svc


def _get_storage_svc():
    global _storage_svc
    if _storage_svc is None:
        from app.services.storage_service import StorageService
        _storage_svc = StorageService()
    return _storage_svc


def _get_pdf_svc():
    global _pdf_svc
    if _pdf_svc is None:
        from app.services.pdf_service import PDFService
        _pdf_svc = PDFService(storage_service=_get_storage_svc())
    return _pdf_svc


# ---------------------------------------------------------------------------
# Form field and template definitions
# These are placeholder stubs until TASK-15 delivers real PDF templates.
# TODO: Replace PROCEDURE_TEMPLATE_PATHS with a DB lookup once form_templates
#       table is populated (TASK-15).
# TODO: Replace PROCEDURE_FORM_FIELDS with PDFService.get_form_fields(template_path)
#       once real PDF templates are available (TASK-15).
# ---------------------------------------------------------------------------

PROCEDURE_TEMPLATE_PATHS: dict[str, str] = {
    "TTHC-001": "templates/dang-ky-thuong-tru.pdf",
    "TTHC-002": "templates/dang-ky-tam-tru.pdf",
    "TTHC-003": "templates/xac-nhan-cu-tru.pdf",
}

PROCEDURE_FORM_FIELDS: dict[str, list[str]] = {
    # Đăng ký thường trú
    "TTHC-001": [
        "ho_ten",
        "ngay_sinh",
        "so_cccd",
        "noi_thuong_tru_cu",
        "dia_chi_thuong_tru_moi",
        "quan_he_chu_ho",
        "ten_chu_ho",
    ],
    # Đăng ký tạm trú
    "TTHC-002": [
        "ho_ten",
        "ngay_sinh",
        "so_cccd",
        "dia_chi_thuong_tru",
        "dia_chi_tam_tru",
        "tu_ngay",
        "den_ngay",
    ],
    # Xác nhận thông tin cư trú
    "TTHC-003": [
        "ho_ten",
        "ngay_sinh",
        "so_cccd",
        "dia_chi_can_xac_nhan",
        "loai_xac_nhan",
        "muc_dich_xac_nhan",
    ],
}


# ---------------------------------------------------------------------------
# Worker function
# ---------------------------------------------------------------------------

async def form_filler_fn(state: AgentState) -> dict:
    """Fill a PDF form from accumulated PersonalData and return state updates.

    Reads: personal_data, extracted_personal_data, target_procedure_id, session_id
    Writes: personal_data (merged), filled_form_path, unfilled_required_fields,
            form_fill_complete, errors (on failure)
    """
    # ── Step 1: Merge incoming OCR data ──────────────────────────────────────
    accumulator = SessionDataAccumulator()
    effective_pd = accumulator.merge(
        state.get("personal_data"),
        state.get("extracted_personal_data"),
    )

    if effective_pd is None:
        log.warning("form_filler_fn: no personal data available")
        return {
            "personal_data": None,
            "filled_form_path": None,
            "unfilled_required_fields": [],
            "form_fill_complete": False,
            "errors": (state.get("errors") or []) + [
                "Không có dữ liệu cá nhân để điền vào biểu mẫu."
            ],
        }

    try:
        # ── Step 2: Look up template path ─────────────────────────────────────
        procedure_id: str | None = state.get("target_procedure_id")
        template_path = PROCEDURE_TEMPLATE_PATHS.get(procedure_id or "")
        if not template_path:
            log.warning(
                "form_filler_fn: no template for procedure",
                procedure_id=procedure_id,
            )
            return {
                "personal_data": effective_pd,
                "filled_form_path": None,
                "unfilled_required_fields": [],
                "form_fill_complete": False,
                "errors": (state.get("errors") or []) + [
                    "Không tìm thấy mẫu biểu cho thủ tục này."
                ],
            }

        # ── Step 3: Get form field names ──────────────────────────────────────
        # TODO: Replace with PDFService.get_form_fields(template_path)
        #       once TASK-15 delivers the real PDF templates.
        form_field_names: list[str] = PROCEDURE_FORM_FIELDS.get(procedure_id or "", [])

        # ── Step 4: Map PersonalData → form fields ────────────────────────────
        form_mapper = FormFieldMapper(llm_service=_get_llm_svc())
        field_values = await form_mapper.map(
            personal_data=effective_pd,
            form_fields=form_field_names,
            form_id=procedure_id or "",
        )

        # ── Step 5: Identify unfilled required fields ─────────────────────────
        # All fields are treated as required until TASK-15 provides
        # required/optional metadata from real templates.
        unfilled = [f for f, v in field_values.items() if not v]

        # ── Step 6: Fill PDF and write to tmp/ ────────────────────────────────
        # PDFService.fill() is already async (it awaits download/upload via
        # StorageService), so it is awaited directly here.
        # NOTE: The TASK-08 spec described fill() as synchronous and expected
        # run_in_executor wrapping, but the existing implementation is async.
        pdf_svc = _get_pdf_svc()
        session_id: str = state["session_id"]
        tmp_path: str = await pdf_svc.fill(
            template_path,
            field_values,
            session_id,
            procedure_id or "",
        )

        # ── Step 7: Promote or hold ───────────────────────────────────────────
        if unfilled:
            # Partial fill — stay in tmp/ so Synthesizer can ask for missing data.
            filled_form_path = tmp_path
        else:
            # All fields filled — promote to permanent path.
            final_path = f"forms/{session_id}/{procedure_id}.pdf"
            await _get_storage_svc().promote_tmp(tmp_path, final_path)
            filled_form_path = final_path

        log.info(
            "form_filler_fn: complete",
            procedure_id=procedure_id,
            filled=len(field_values) - len(unfilled),
            unfilled=len(unfilled),
            promoted=len(unfilled) == 0,
        )

        return {
            "personal_data": effective_pd,
            "filled_form_path": filled_form_path,
            "unfilled_required_fields": unfilled,
            "form_fill_complete": len(unfilled) == 0,
        }

    except Exception as exc:
        log.warning("form_filler_fn: exception during fill", error=str(exc))
        return {
            "personal_data": effective_pd,
            "filled_form_path": None,
            "unfilled_required_fields": [],
            "form_fill_complete": False,
            "errors": (state.get("errors") or []) + [
                f"Lỗi khi điền biểu mẫu: {exc}"
            ],
        }
