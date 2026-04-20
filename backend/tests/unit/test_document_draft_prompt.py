"""Unit tests for document_draft_prompt module.

Tests cover:
  1. assemble_document() structural correctness (quốc hiệu, tiêu ngữ, closing)
  2. assemble_document() personal data injection
  3. assemble_document() placeholder when personal data absent
  4. build_document_draft_prompt() raises ValueError for unknown document_type
  5. All 5 document types have required config keys
"""

from __future__ import annotations

import pytest

from app.agents.prompts.document_draft_prompt import (
    DOCUMENT_TYPE_CONFIGS,
    assemble_document,
    build_document_draft_prompt,
)


# ---------------------------------------------------------------------------
# Test 1 — assembled document contains all mandatory structural sections
# ---------------------------------------------------------------------------

def test_assemble_document_contains_required_sections():
    """assemble_document() always includes quốc hiệu, tiêu ngữ, and closing."""
    result = assemble_document("don_xac_nhan_cu_tru", {}, "")

    assert "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" in result
    assert "Độc lập – Tự do – Hạnh phúc" in result
    assert "ĐƠN XIN XÁC NHẬN THÔNG TIN CƯ TRÚ" in result
    assert "Trân trọng kính trình" in result
    assert "Kính gửi:" in result
    assert "Người làm đơn" in result


# ---------------------------------------------------------------------------
# Test 2 — personal data is injected when provided
# ---------------------------------------------------------------------------

def test_assemble_document_injects_personal_data():
    """Personal data fields (full_name, id_number) appear in the assembled document."""
    result = assemble_document(
        "don_dang_ky_thuong_tru",
        {"full_name": "Trần Thị B", "id_number": "098765432109"},
        "body text here",
    )

    assert "Trần Thị B" in result
    assert "098765432109" in result
    # Signature line uses the same full_name
    assert result.count("Trần Thị B") >= 2


# ---------------------------------------------------------------------------
# Test 3 — placeholders appear when personal data is absent
# ---------------------------------------------------------------------------

def test_assemble_document_placeholder_when_no_personal_data():
    """When personal data dict is empty, [bracket] placeholders are used."""
    result = assemble_document("giay_cam_ket", {}, "body")

    assert "[Họ và tên]" in result
    assert "[Số CCCD/CMND]" in result
    assert "[Ngày sinh]" in result
    assert "[Địa chỉ thường trú]" in result


# ---------------------------------------------------------------------------
# Test 4 — build_document_draft_prompt raises ValueError for unknown type
# ---------------------------------------------------------------------------

def test_build_document_draft_prompt_raises_for_unknown_type():
    """build_document_draft_prompt raises ValueError for unrecognised document types."""
    with pytest.raises(ValueError, match="Unsupported document type"):
        build_document_draft_prompt("don_khong_ton_tai", {})


# ---------------------------------------------------------------------------
# Test 5 — all 5 document type configs have required keys
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("doc_type", list(DOCUMENT_TYPE_CONFIGS.keys()))
def test_all_document_types_have_required_config_keys(doc_type: str):
    """Every entry in DOCUMENT_TYPE_CONFIGS has ten_van_ban, kinh_gui, body_instruction, max_words."""
    cfg = DOCUMENT_TYPE_CONFIGS[doc_type]
    assert "ten_van_ban" in cfg, f"{doc_type} missing ten_van_ban"
    assert "kinh_gui" in cfg, f"{doc_type} missing kinh_gui"
    assert "body_instruction" in cfg, f"{doc_type} missing body_instruction"
    assert "max_words" in cfg, f"{doc_type} missing max_words"
    # ten_van_ban must be ALL-CAPS Vietnamese
    assert cfg["ten_van_ban"] == cfg["ten_van_ban"].upper(), (
        f"{doc_type}: ten_van_ban must be all-caps"
    )


# ---------------------------------------------------------------------------
# Test 6 — assemble_document raises ValueError for unknown type
# ---------------------------------------------------------------------------

def test_assemble_document_raises_for_unknown_type():
    """assemble_document raises ValueError when document_type is not supported."""
    with pytest.raises(ValueError, match="Unsupported document type"):
        assemble_document("khong_ton_tai", {}, "body")


# ---------------------------------------------------------------------------
# Test 7 — filing_jurisdiction mapping
# ---------------------------------------------------------------------------

def test_assemble_document_dia_danh_hcm():
    """VN-HCM-26968 maps to 'TP. Hồ Chí Minh' in the document footer."""
    result = assemble_document(
        "don_xac_nhan_cu_tru", {}, "body", filing_jurisdiction="VN-HCM-26968"
    )
    assert "TP. Hồ Chí Minh" in result


def test_assemble_document_dia_danh_unknown_jurisdiction():
    """Unknown jurisdiction maps to placeholder dots."""
    result = assemble_document(
        "don_xac_nhan_cu_tru", {}, "body", filing_jurisdiction="VN-XX-00000"
    )
    assert ".........." in result


def test_assemble_document_dia_danh_none():
    """None filing_jurisdiction maps to placeholder dots."""
    result = assemble_document("don_xac_nhan_cu_tru", {}, "body", filing_jurisdiction=None)
    assert ".........." in result


# ---------------------------------------------------------------------------
# Test 8 — date_of_birth formatting
# ---------------------------------------------------------------------------

def test_assemble_document_formats_date_iso_string():
    """ISO date string '1990-05-20' is formatted as '20/05/1990' in the document."""
    result = assemble_document(
        "don_dang_ky_tam_tru",
        {"date_of_birth": "1990-05-20"},
        "body",
    )
    assert "20/05/1990" in result


def test_assemble_document_formats_date_object():
    """Python date object is formatted as DD/MM/YYYY."""
    from datetime import date as DateType
    result = assemble_document(
        "don_dang_ky_tam_tru",
        {"date_of_birth": DateType(1985, 3, 7)},
        "body",
    )
    assert "07/03/1985" in result
