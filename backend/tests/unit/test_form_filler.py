"""Unit tests for app/agents/nodes/form_filler.py.

All LLM, PDF, and storage calls are mocked — no real API calls or file I/O.
Covers all TASK-08 DoD items for form_filler_fn.
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.nodes.form_filler import form_filler_fn
from app.schemas.personal_data import PersonalData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pd(
    full_name: str = "Nguyễn Văn A",
    id_number: str = "012345678",
) -> PersonalData:
    return PersonalData(
        full_name=full_name,
        id_number=id_number,
        source_document_type="cccd",
        source_image_path="path/cccd.jpg",
        extraction_confidence=0.9,
        field_confidences={"full_name": 0.95, "id_number": 0.9},
        extracted_at=datetime(2024, 1, 1),
    )


def _base_state(
    personal_data: PersonalData | None = None,
    extracted_personal_data: PersonalData | None = None,
    procedure_id: str = "TTHC-001",
    session_id: str = "test-session-123",
) -> dict:
    return {
        "user_message": "Tôi muốn đăng ký thường trú",
        "session_id": session_id,
        "iteration_count": 1,
        "personal_data": personal_data,
        "extracted_personal_data": extracted_personal_data,
        "target_procedure_id": procedure_id,
        "errors": [],
    }


def _mock_pdf_svc(tmp_path: str = "tmp/test-session-123/TTHC-001.pdf") -> MagicMock:
    svc = MagicMock()
    svc.fill = AsyncMock(return_value=tmp_path)
    return svc


def _mock_storage_svc() -> MagicMock:
    svc = MagicMock()
    svc.promote_tmp = AsyncMock(return_value=None)
    return svc


def _mock_mapper(field_values: dict[str, str]) -> MagicMock:
    """Return a mock FormFieldMapper whose map() returns field_values."""
    mapper_instance = MagicMock()
    mapper_instance.map = AsyncMock(return_value=field_values)
    mapper_class = MagicMock(return_value=mapper_instance)
    return mapper_class, mapper_instance


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

# 8 — promote called when all fields filled
@pytest.mark.asyncio
async def test_form_filler_fn_promotes_when_all_fields_filled():
    """When all form fields have values, promote_tmp must be called exactly once."""
    state = _base_state(personal_data=_pd())
    mock_storage = _mock_storage_svc()
    mock_pdf = _mock_pdf_svc(tmp_path="tmp/test-session-123/TTHC-001.pdf")
    mapper_class, mapper_instance = _mock_mapper(
        {"ho_ten": "Nguyễn Văn A", "ngay_sinh": "01/01/1990",
         "so_cccd": "012345678", "noi_thuong_tru_cu": "Hà Nội",
         "dia_chi_thuong_tru_moi": "HCM", "quan_he_chu_ho": "Con",
         "ten_chu_ho": "Nguyễn Văn B"}
    )

    with patch("app.agents.nodes.form_filler._get_llm_svc", return_value=MagicMock()), \
         patch("app.agents.nodes.form_filler._get_storage_svc", return_value=mock_storage), \
         patch("app.agents.nodes.form_filler._get_pdf_svc", return_value=mock_pdf), \
         patch("app.agents.nodes.form_filler.FormFieldMapper", mapper_class):

        result = await form_filler_fn(state)

    assert result["form_fill_complete"] is True
    assert result["unfilled_required_fields"] == []
    mock_storage.promote_tmp.assert_called_once()
    assert result["filled_form_path"] == "forms/test-session-123/TTHC-001.pdf"


# 9 — promote NOT called when fields are missing
@pytest.mark.asyncio
async def test_form_filler_fn_does_not_promote_when_fields_missing():
    """When some fields are empty, promote_tmp must NOT be called."""
    state = _base_state(personal_data=_pd())
    mock_storage = _mock_storage_svc()
    mock_pdf = _mock_pdf_svc(tmp_path="tmp/test-session-123/TTHC-001.pdf")
    # Two fields empty → partial fill
    mapper_class, mapper_instance = _mock_mapper(
        {"ho_ten": "Nguyễn Văn A", "ngay_sinh": "",
         "so_cccd": "", "noi_thuong_tru_cu": "",
         "dia_chi_thuong_tru_moi": "", "quan_he_chu_ho": "",
         "ten_chu_ho": ""}
    )

    with patch("app.agents.nodes.form_filler._get_llm_svc", return_value=MagicMock()), \
         patch("app.agents.nodes.form_filler._get_storage_svc", return_value=mock_storage), \
         patch("app.agents.nodes.form_filler._get_pdf_svc", return_value=mock_pdf), \
         patch("app.agents.nodes.form_filler.FormFieldMapper", mapper_class):

        result = await form_filler_fn(state)

    mock_storage.promote_tmp.assert_not_called()
    assert result["form_fill_complete"] is False
    assert len(result["unfilled_required_fields"]) > 0
    assert result["filled_form_path"] == "tmp/test-session-123/TTHC-001.pdf"


# 10 — no personal data returns error without calling PDFService
@pytest.mark.asyncio
async def test_form_filler_fn_no_personal_data_returns_error():
    """Both personal_data and extracted_personal_data None → error, PDF not called."""
    state = _base_state(personal_data=None, extracted_personal_data=None)
    mock_pdf = _mock_pdf_svc()

    with patch("app.agents.nodes.form_filler._get_llm_svc", return_value=MagicMock()), \
         patch("app.agents.nodes.form_filler._get_storage_svc", return_value=_mock_storage_svc()), \
         patch("app.agents.nodes.form_filler._get_pdf_svc", return_value=mock_pdf):

        result = await form_filler_fn(state)

    mock_pdf.fill.assert_not_called()
    assert result["form_fill_complete"] is False
    assert result["filled_form_path"] is None
    assert len(result["errors"]) > 0
    assert "Không có dữ liệu cá nhân" in result["errors"][-1]


# 11 — PDF exception does not crash form_filler_fn
@pytest.mark.asyncio
async def test_form_filler_fn_pdf_exception_does_not_crash():
    """If PDFService.fill() raises, form_filler_fn must return a dict, not raise."""
    state = _base_state(personal_data=_pd())
    mock_storage = _mock_storage_svc()
    mock_pdf = MagicMock()
    mock_pdf.fill = AsyncMock(side_effect=RuntimeError("MinIO connection refused"))
    mapper_class, _ = _mock_mapper({"ho_ten": "Nguyễn Văn A"})

    with patch("app.agents.nodes.form_filler._get_llm_svc", return_value=MagicMock()), \
         patch("app.agents.nodes.form_filler._get_storage_svc", return_value=mock_storage), \
         patch("app.agents.nodes.form_filler._get_pdf_svc", return_value=mock_pdf), \
         patch("app.agents.nodes.form_filler.FormFieldMapper", mapper_class):

        result = await form_filler_fn(state)  # must not raise

    assert isinstance(result, dict)
    assert result["form_fill_complete"] is False
    assert result["filled_form_path"] is None
    assert len(result["errors"]) > 0


# — extracted_personal_data merged before mapping
@pytest.mark.asyncio
async def test_form_filler_fn_merges_extracted_personal_data():
    """extracted_personal_data with higher confidence should override personal_data."""
    from app.schemas.personal_data import PersonalData

    low_conf_pd = PersonalData(
        full_name="Old Name",
        source_document_type="cccd",
        source_image_path="old.jpg",
        extraction_confidence=0.5,
        field_confidences={"full_name": 0.5},
        extracted_at=datetime(2024, 1, 1),
    )
    high_conf_pd = PersonalData(
        full_name="New Correct Name",
        source_document_type="cccd",
        source_image_path="new.jpg",
        extraction_confidence=0.95,
        field_confidences={"full_name": 0.95},
        extracted_at=datetime(2024, 2, 1),
    )

    captured_pd = {}

    class CapturingMapper:
        """Captures the personal_data passed to map()."""
        def __init__(self, **kwargs):
            pass

        async def map(self, personal_data, form_fields, form_id):
            captured_pd["pd"] = personal_data
            return {f: "" for f in form_fields}

    state = _base_state(
        personal_data=low_conf_pd,
        extracted_personal_data=high_conf_pd,
    )

    with patch("app.agents.nodes.form_filler._get_llm_svc", return_value=MagicMock()), \
         patch("app.agents.nodes.form_filler._get_storage_svc", return_value=_mock_storage_svc()), \
         patch("app.agents.nodes.form_filler._get_pdf_svc", return_value=_mock_pdf_svc()), \
         patch("app.agents.nodes.form_filler.FormFieldMapper", CapturingMapper):

        result = await form_filler_fn(state)

    # The merged PersonalData passed to FormFieldMapper should use high-conf value.
    assert captured_pd["pd"].full_name == "New Correct Name"
    # Merged result also returned in state update.
    assert result["personal_data"].full_name == "New Correct Name"


# — TTHC-002 field mapping returns filled_fields for tạm trú
@pytest.mark.asyncio
async def test_form_filler_tthc002_field_mapping():
    """form_filler_fn for TTHC-002 populates ho_chu_dem_va_ten and ngay_thang_nam_sinh."""
    pd = PersonalData(
        full_name="Trần Thị B",
        date_of_birth=None,
        source_document_type="cccd",
        source_image_path="path/cccd.jpg",
        extraction_confidence=0.9,
        field_confidences={"full_name": 0.9},
        extracted_at=datetime(2024, 1, 1),
    )
    state = _base_state(personal_data=pd, procedure_id="TTHC-002")
    mock_storage = _mock_storage_svc()
    mock_pdf = _mock_pdf_svc(tmp_path="tmp/test-session-123/TTHC-002.pdf")

    # Return all 15 TTHC-002 fields with the two key fields populated
    tthc002_fields = {
        "ho_chu_dem_va_ten": "Trần Thị B",
        "ngay_thang_nam_sinh": "01/01/1990",
        "gioi_tinh": "",
        "dan_toc": "",
        "so_dinh_danh_ca_nhan": "",
        "que_quan": "",
        "noi_thuong_tru": "",
        "noi_o_hien_tai": "",
        "nghe_nghiep": "",
        "noi_lam_viec": "",
        "ho_ten_chu_ho": "",
        "quan_he_voi_chu_ho": "",
        "so_dinh_danh_chu_ho": "",
        "noi_dung_de_nghi": "",
        "thoi_han_tam_tru": "",
    }
    mapper_class, _ = _mock_mapper(tthc002_fields)

    with patch("app.agents.nodes.form_filler._get_llm_svc", return_value=MagicMock()), \
         patch("app.agents.nodes.form_filler._get_storage_svc", return_value=mock_storage), \
         patch("app.agents.nodes.form_filler._get_pdf_svc", return_value=mock_pdf), \
         patch("app.agents.nodes.form_filler.FormFieldMapper", mapper_class):

        result = await form_filler_fn(state)

    # Key fields are filled — procedure routed and PDF service called
    assert result["filled_form_path"] is not None
    mock_pdf.fill.assert_called_once()
    # Unfilled fields exist (not all 15 were filled), but no error
    assert "errors" not in result or result.get("errors") == []
    assert result["personal_data"].full_name == "Trần Thị B"


# — TTHC-003 field mapping returns filled_fields for xác nhận cư trú
@pytest.mark.asyncio
async def test_form_filler_tthc003_field_mapping():
    """form_filler_fn for TTHC-003 populates ho_chu_dem_va_ten and ngay_thang_nam_sinh."""
    pd = PersonalData(
        full_name="Lê Văn C",
        date_of_birth=None,
        source_document_type="cccd",
        source_image_path="path/cccd.jpg",
        extraction_confidence=0.88,
        field_confidences={"full_name": 0.88},
        extracted_at=datetime(2024, 3, 15),
    )
    state = _base_state(personal_data=pd, procedure_id="TTHC-003")
    mock_storage = _mock_storage_svc()
    mock_pdf = _mock_pdf_svc(tmp_path="tmp/test-session-123/TTHC-003.pdf")

    # Return all 14 TTHC-003 fields with the two key fields populated
    tthc003_fields = {
        "ho_chu_dem_va_ten": "Lê Văn C",
        "ngay_thang_nam_sinh": "15/03/1985",
        "gioi_tinh": "",
        "dan_toc": "",
        "so_dinh_danh_ca_nhan": "",
        "que_quan": "",
        "noi_thuong_tru": "",
        "noi_o_hien_tai": "",
        "nghe_nghiep": "",
        "noi_lam_viec": "",
        "ho_ten_chu_ho": "",
        "quan_he_voi_chu_ho": "",
        "so_dinh_danh_chu_ho": "",
        "noi_dung_de_nghi": "",
    }
    mapper_class, _ = _mock_mapper(tthc003_fields)

    with patch("app.agents.nodes.form_filler._get_llm_svc", return_value=MagicMock()), \
         patch("app.agents.nodes.form_filler._get_storage_svc", return_value=mock_storage), \
         patch("app.agents.nodes.form_filler._get_pdf_svc", return_value=mock_pdf), \
         patch("app.agents.nodes.form_filler.FormFieldMapper", mapper_class):

        result = await form_filler_fn(state)

    # Key fields are filled — procedure routed and PDF service called
    assert result["filled_form_path"] is not None
    mock_pdf.fill.assert_called_once()
    # Unfilled fields exist (not all 14 were filled), but no error
    assert "errors" not in result or result.get("errors") == []
    assert result["personal_data"].full_name == "Lê Văn C"


# — unknown procedure_id returns error without calling PDFService
@pytest.mark.asyncio
async def test_form_filler_fn_unknown_procedure_returns_error():
    state = _base_state(personal_data=_pd(), procedure_id="UNKNOWN-999")
    mock_pdf = _mock_pdf_svc()

    with patch("app.agents.nodes.form_filler._get_llm_svc", return_value=MagicMock()), \
         patch("app.agents.nodes.form_filler._get_storage_svc", return_value=_mock_storage_svc()), \
         patch("app.agents.nodes.form_filler._get_pdf_svc", return_value=mock_pdf):

        result = await form_filler_fn(state)

    mock_pdf.fill.assert_not_called()
    assert result["filled_form_path"] is None
    assert result["form_fill_complete"] is False
    assert "Không tìm thấy mẫu biểu" in result["errors"][-1]
