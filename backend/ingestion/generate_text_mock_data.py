"""Generate mock PersonalData JSON objects for non-CCCD procedures.

These objects simulate what the system would hold after a user provides
their personal information by text input (not OCR). They are used for
testing the civil_registration and adoption pipeline paths.

Outputs are written to:
    backend/data/mock_text_data/{procedure_id}/mock_{n:03d}.json

Run from the backend/ directory:
    PYTHONPATH=. .venv/Scripts/python ingestion/generate_text_mock_data.py

All names, ID numbers, and addresses in this file are synthetic.
No real citizen data is used.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Add backend/ to sys.path so we can import app schemas
# ---------------------------------------------------------------------------

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.schemas.personal_data import Address, PersonalData  # noqa: E402

# ---------------------------------------------------------------------------
# Output directory
# ---------------------------------------------------------------------------

OUTPUT_DIR = _BACKEND_DIR / "data" / "mock_text_data"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EXTRACTED_AT = datetime(2026, 4, 12, 9, 0, 0, tzinfo=timezone.utc)

_HCM_ADDRESSES = [
    Address(
        street="123 Nguyễn Thị Minh Khai",
        ward="Phường 06",
        district="Quận 3",
        province="Thành phố Hồ Chí Minh",
        city="Thành phố Hồ Chí Minh",
    ),
    Address(
        street="45 Lê Văn Việt",
        ward="Phường Hiệp Phú",
        district="Quận 9",
        province="Thành phố Hồ Chí Minh",
        city="Thành phố Hồ Chí Minh",
    ),
    Address(
        street="88 Điện Biên Phủ",
        ward="Phường 15",
        district="Quận Bình Thạnh",
        province="Thành phố Hồ Chí Minh",
        city="Thành phố Hồ Chí Minh",
    ),
    Address(
        street="200 Cách Mạng Tháng Tám",
        ward="Phường 10",
        district="Quận 3",
        province="Thành phố Hồ Chí Minh",
        city="Thành phố Hồ Chí Minh",
    ),
    Address(
        street="77 Trần Hưng Đạo",
        ward="Phường Cầu Kho",
        district="Quận 1",
        province="Thành phố Hồ Chí Minh",
        city="Thành phố Hồ Chí Minh",
    ),
]

# Fake ID numbers (12 digits, province code 079 = Ho Chi Minh City)
# Format: 079 + gender_century + YY + seq (000001-999999)
# 0 = male born 1900s, 1 = female born 1900s, 2 = male 2000s, 3 = female 2000s
_FAKE_IDS_MALE = [
    "079087001234",  # male, born 1987
    "079092002345",  # male, born 1992
    "079085003456",  # male, born 1985
    "079090004567",  # male, born 1990
    "079078005678",  # male, born 1978
]

_FAKE_IDS_FEMALE = [
    "079193001234",  # female, born 1993
    "079188002345",  # female, born 1988
    "079195003456",  # female, born 1995
    "079182004567",  # female, born 1982
    "079176005678",  # female, born 1976
]

# ---------------------------------------------------------------------------
# TTHC-CR-001: Đăng ký khai sinh (parent registering child's birth)
# PersonalData here is the PARENT (father or mother), not the child.
# Child information goes directly into form fields at fill time.
# extraction_confidence = 0.8 (text-based input, lower than QR decode's 1.0)
# ---------------------------------------------------------------------------

_CR_001_RECORDS: list[PersonalData] = [
    PersonalData(
        full_name="Nguyễn Văn An",
        full_name_latin="Nguyen Van An",
        date_of_birth=date(1987, 5, 20),
        gender="Nam",
        nationality="Việt Nam",
        id_number="079087001234",
        id_issue_date=date(2021, 6, 15),
        id_issue_place="Cục Cảnh sát QLHC về TTXH",
        permanent_address=_HCM_ADDRESSES[0],
        raw_address="123 Nguyễn Thị Minh Khai, Phường 06, Quận 3, Thành phố Hồ Chí Minh",
        source_document_type="text_input",
        source_image_path="data/mock_text_data/TTHC-CR-001/mock_001.json",
        extraction_confidence=0.8,
        field_confidences={
            "full_name": 0.8,
            "date_of_birth": 0.8,
            "gender": 0.8,
            "id_number": 0.8,
            "permanent_address": 0.8,
        },
        extracted_at=_EXTRACTED_AT,
    ),
    PersonalData(
        full_name="Trần Thị Bích",
        full_name_latin="Tran Thi Bich",
        date_of_birth=date(1993, 8, 12),
        gender="Nữ",
        nationality="Việt Nam",
        id_number="079193001234",
        id_issue_date=date(2022, 3, 10),
        id_issue_place="Cục Cảnh sát QLHC về TTXH",
        permanent_address=_HCM_ADDRESSES[1],
        raw_address="45 Lê Văn Việt, Phường Hiệp Phú, Quận 9, Thành phố Hồ Chí Minh",
        source_document_type="text_input",
        source_image_path="data/mock_text_data/TTHC-CR-001/mock_002.json",
        extraction_confidence=0.8,
        field_confidences={
            "full_name": 0.8,
            "date_of_birth": 0.8,
            "gender": 0.8,
            "id_number": 0.8,
            "permanent_address": 0.8,
        },
        extracted_at=_EXTRACTED_AT,
    ),
    PersonalData(
        full_name="Lê Minh Tuấn",
        full_name_latin="Le Minh Tuan",
        date_of_birth=date(1985, 11, 30),
        gender="Nam",
        nationality="Việt Nam",
        id_number="079085003456",
        id_issue_date=date(2020, 9, 5),
        id_issue_place="Cục Cảnh sát QLHC về TTXH",
        permanent_address=_HCM_ADDRESSES[2],
        raw_address="88 Điện Biên Phủ, Phường 15, Quận Bình Thạnh, Thành phố Hồ Chí Minh",
        source_document_type="text_input",
        source_image_path="data/mock_text_data/TTHC-CR-001/mock_003.json",
        extraction_confidence=0.8,
        field_confidences={
            "full_name": 0.8,
            "date_of_birth": 0.8,
            "gender": 0.8,
            "id_number": 0.8,
            "permanent_address": 0.8,
        },
        extracted_at=_EXTRACTED_AT,
    ),
    PersonalData(
        full_name="Phạm Thị Hoa",
        full_name_latin="Pham Thi Hoa",
        date_of_birth=date(1988, 2, 14),
        gender="Nữ",
        nationality="Việt Nam",
        id_number="079188002345",
        id_issue_date=date(2021, 11, 20),
        id_issue_place="Cục Cảnh sát QLHC về TTXH",
        permanent_address=_HCM_ADDRESSES[3],
        raw_address="200 Cách Mạng Tháng Tám, Phường 10, Quận 3, Thành phố Hồ Chí Minh",
        source_document_type="text_input",
        source_image_path="data/mock_text_data/TTHC-CR-001/mock_004.json",
        extraction_confidence=0.8,
        field_confidences={
            "full_name": 0.8,
            "date_of_birth": 0.8,
            "gender": 0.8,
            "id_number": 0.8,
            "permanent_address": 0.8,
        },
        extracted_at=_EXTRACTED_AT,
    ),
    PersonalData(
        full_name="Hoàng Đức Thắng",
        full_name_latin="Hoang Duc Thang",
        date_of_birth=date(1990, 7, 4),
        gender="Nam",
        nationality="Việt Nam",
        id_number="079090004567",
        id_issue_date=date(2023, 1, 7),
        id_issue_place="Cục Cảnh sát QLHC về TTXH",
        permanent_address=_HCM_ADDRESSES[4],
        raw_address="77 Trần Hưng Đạo, Phường Cầu Kho, Quận 1, Thành phố Hồ Chí Minh",
        source_document_type="text_input",
        source_image_path="data/mock_text_data/TTHC-CR-001/mock_005.json",
        extraction_confidence=0.8,
        field_confidences={
            "full_name": 0.8,
            "date_of_birth": 0.8,
            "gender": 0.8,
            "id_number": 0.8,
            "permanent_address": 0.8,
        },
        extracted_at=_EXTRACTED_AT,
    ),
]

# ---------------------------------------------------------------------------
# TTHC-CR-002: Cấp bản sao Trích lục hộ tịch (requester's personal data)
# This is the person requesting a certified copy of the birth record.
# extraction_confidence = 0.8 (text-based input)
# ---------------------------------------------------------------------------

_CR_002_RECORDS: list[PersonalData] = [
    PersonalData(
        full_name="Võ Thị Lan",
        full_name_latin="Vo Thi Lan",
        date_of_birth=date(1995, 3, 22),
        gender="Nữ",
        nationality="Việt Nam",
        id_number="079195003456",
        id_issue_date=date(2022, 8, 18),
        id_issue_place="Cục Cảnh sát QLHC về TTXH",
        permanent_address=_HCM_ADDRESSES[0],
        raw_address="123 Nguyễn Thị Minh Khai, Phường 06, Quận 3, Thành phố Hồ Chí Minh",
        source_document_type="text_input",
        source_image_path="data/mock_text_data/TTHC-CR-002/mock_001.json",
        extraction_confidence=0.8,
        field_confidences={
            "full_name": 0.8,
            "date_of_birth": 0.8,
            "gender": 0.8,
            "id_number": 0.8,
            "permanent_address": 0.8,
        },
        extracted_at=_EXTRACTED_AT,
    ),
    PersonalData(
        full_name="Đặng Văn Hùng",
        full_name_latin="Dang Van Hung",
        date_of_birth=date(1992, 10, 8),
        gender="Nam",
        nationality="Việt Nam",
        id_number="079092002345",
        id_issue_date=date(2021, 4, 25),
        id_issue_place="Cục Cảnh sát QLHC về TTXH",
        permanent_address=_HCM_ADDRESSES[1],
        raw_address="45 Lê Văn Việt, Phường Hiệp Phú, Quận 9, Thành phố Hồ Chí Minh",
        source_document_type="text_input",
        source_image_path="data/mock_text_data/TTHC-CR-002/mock_002.json",
        extraction_confidence=0.8,
        field_confidences={
            "full_name": 0.8,
            "date_of_birth": 0.8,
            "gender": 0.8,
            "id_number": 0.8,
            "permanent_address": 0.8,
        },
        extracted_at=_EXTRACTED_AT,
    ),
    PersonalData(
        full_name="Nguyễn Thị Thanh",
        full_name_latin="Nguyen Thi Thanh",
        date_of_birth=date(1982, 12, 15),
        gender="Nữ",
        nationality="Việt Nam",
        id_number="079182004567",
        id_issue_date=date(2020, 7, 30),
        id_issue_place="Cục Cảnh sát QLHC về TTXH",
        permanent_address=_HCM_ADDRESSES[2],
        raw_address="88 Điện Biên Phủ, Phường 15, Quận Bình Thạnh, Thành phố Hồ Chí Minh",
        source_document_type="text_input",
        source_image_path="data/mock_text_data/TTHC-CR-002/mock_003.json",
        extraction_confidence=0.8,
        field_confidences={
            "full_name": 0.8,
            "date_of_birth": 0.8,
            "gender": 0.8,
            "id_number": 0.8,
            "permanent_address": 0.8,
        },
        extracted_at=_EXTRACTED_AT,
    ),
    PersonalData(
        full_name="Trần Quốc Bảo",
        full_name_latin="Tran Quoc Bao",
        date_of_birth=date(1978, 6, 3),
        gender="Nam",
        nationality="Việt Nam",
        id_number="079078005678",
        id_issue_date=date(2021, 2, 12),
        id_issue_place="Cục Cảnh sát QLHC về TTXH",
        permanent_address=_HCM_ADDRESSES[3],
        raw_address="200 Cách Mạng Tháng Tám, Phường 10, Quận 3, Thành phố Hồ Chí Minh",
        source_document_type="text_input",
        source_image_path="data/mock_text_data/TTHC-CR-002/mock_004.json",
        extraction_confidence=0.8,
        field_confidences={
            "full_name": 0.8,
            "date_of_birth": 0.8,
            "gender": 0.8,
            "id_number": 0.8,
            "permanent_address": 0.8,
        },
        extracted_at=_EXTRACTED_AT,
    ),
    PersonalData(
        full_name="Lý Thị Ngọc",
        full_name_latin="Ly Thi Ngoc",
        date_of_birth=date(1976, 9, 27),
        gender="Nữ",
        nationality="Việt Nam",
        id_number="079176005678",
        id_issue_date=date(2022, 5, 9),
        id_issue_place="Cục Cảnh sát QLHC về TTXH",
        permanent_address=_HCM_ADDRESSES[4],
        raw_address="77 Trần Hưng Đạo, Phường Cầu Kho, Quận 1, Thành phố Hồ Chí Minh",
        source_document_type="text_input",
        source_image_path="data/mock_text_data/TTHC-CR-002/mock_005.json",
        extraction_confidence=0.8,
        field_confidences={
            "full_name": 0.8,
            "date_of_birth": 0.8,
            "gender": 0.8,
            "id_number": 0.8,
            "permanent_address": 0.8,
        },
        extracted_at=_EXTRACTED_AT,
    ),
]

# ---------------------------------------------------------------------------
# TTHC-AD-001: Đăng ký việc nuôi con nuôi trong nước (adoptive parent)
# These are the adoptive parents. CCCD identity fields are standard.
# Fields beyond CCCD (marital status, health, economic conditions) are
# captured as additional notes in the context of a future form fill step.
# extraction_confidence = 0.75 (text input; additional declared fields)
# ---------------------------------------------------------------------------

_AD_001_RECORDS: list[PersonalData] = [
    PersonalData(
        full_name="Bùi Văn Phúc",
        full_name_latin="Bui Van Phuc",
        date_of_birth=date(1980, 4, 10),
        gender="Nam",
        nationality="Việt Nam",
        id_number="079080001234",
        id_issue_date=date(2021, 7, 20),
        id_issue_place="Cục Cảnh sát QLHC về TTXH",
        permanent_address=_HCM_ADDRESSES[0],
        raw_address="123 Nguyễn Thị Minh Khai, Phường 06, Quận 3, Thành phố Hồ Chí Minh",
        source_document_type="text_input",
        source_image_path="data/mock_text_data/TTHC-AD-001/mock_001.json",
        extraction_confidence=0.75,
        field_confidences={
            "full_name": 0.8,
            "date_of_birth": 0.8,
            "gender": 0.8,
            "id_number": 0.8,
            "permanent_address": 0.75,
        },
        extracted_at=_EXTRACTED_AT,
    ),
    PersonalData(
        full_name="Nguyễn Thị Thu Hà",
        full_name_latin="Nguyen Thi Thu Ha",
        date_of_birth=date(1983, 1, 25),
        gender="Nữ",
        nationality="Việt Nam",
        id_number="079183001234",
        id_issue_date=date(2022, 3, 15),
        id_issue_place="Cục Cảnh sát QLHC về TTXH",
        permanent_address=_HCM_ADDRESSES[1],
        raw_address="45 Lê Văn Việt, Phường Hiệp Phú, Quận 9, Thành phố Hồ Chí Minh",
        source_document_type="text_input",
        source_image_path="data/mock_text_data/TTHC-AD-001/mock_002.json",
        extraction_confidence=0.75,
        field_confidences={
            "full_name": 0.8,
            "date_of_birth": 0.8,
            "gender": 0.8,
            "id_number": 0.8,
            "permanent_address": 0.75,
        },
        extracted_at=_EXTRACTED_AT,
    ),
    PersonalData(
        full_name="Đinh Công Sơn",
        full_name_latin="Dinh Cong Son",
        date_of_birth=date(1975, 8, 17),
        gender="Nam",
        nationality="Việt Nam",
        id_number="079075003456",
        id_issue_date=date(2020, 11, 3),
        id_issue_place="Cục Cảnh sát QLHC về TTXH",
        permanent_address=_HCM_ADDRESSES[2],
        raw_address="88 Điện Biên Phủ, Phường 15, Quận Bình Thạnh, Thành phố Hồ Chí Minh",
        source_document_type="text_input",
        source_image_path="data/mock_text_data/TTHC-AD-001/mock_003.json",
        extraction_confidence=0.75,
        field_confidences={
            "full_name": 0.8,
            "date_of_birth": 0.8,
            "gender": 0.8,
            "id_number": 0.8,
            "permanent_address": 0.75,
        },
        extracted_at=_EXTRACTED_AT,
    ),
    PersonalData(
        full_name="Phan Thị Mỹ Dung",
        full_name_latin="Phan Thi My Dung",
        date_of_birth=date(1979, 3, 6),
        gender="Nữ",
        nationality="Việt Nam",
        id_number="079179004567",
        id_issue_date=date(2021, 9, 28),
        id_issue_place="Cục Cảnh sát QLHC về TTXH",
        permanent_address=_HCM_ADDRESSES[3],
        raw_address="200 Cách Mạng Tháng Tám, Phường 10, Quận 3, Thành phố Hồ Chí Minh",
        source_document_type="text_input",
        source_image_path="data/mock_text_data/TTHC-AD-001/mock_004.json",
        extraction_confidence=0.75,
        field_confidences={
            "full_name": 0.8,
            "date_of_birth": 0.8,
            "gender": 0.8,
            "id_number": 0.8,
            "permanent_address": 0.75,
        },
        extracted_at=_EXTRACTED_AT,
    ),
    PersonalData(
        full_name="Trương Văn Khoa",
        full_name_latin="Truong Van Khoa",
        date_of_birth=date(1977, 12, 19),
        gender="Nam",
        nationality="Việt Nam",
        id_number="079077005678",
        id_issue_date=date(2022, 6, 14),
        id_issue_place="Cục Cảnh sát QLHC về TTXH",
        permanent_address=_HCM_ADDRESSES[4],
        raw_address="77 Trần Hưng Đạo, Phường Cầu Kho, Quận 1, Thành phố Hồ Chí Minh",
        source_document_type="text_input",
        source_image_path="data/mock_text_data/TTHC-AD-001/mock_005.json",
        extraction_confidence=0.75,
        field_confidences={
            "full_name": 0.8,
            "date_of_birth": 0.8,
            "gender": 0.8,
            "id_number": 0.8,
            "permanent_address": 0.75,
        },
        extracted_at=_EXTRACTED_AT,
    ),
]

# ---------------------------------------------------------------------------
# TTHC-AD-002: Đăng ký lại việc nuôi con nuôi trong nước
# Same identity fields as TTHC-AD-001. The original registration date
# is captured as a note — it is a form field, not a PersonalData field.
# extraction_confidence = 0.75
# ---------------------------------------------------------------------------

_AD_002_RECORDS: list[PersonalData] = [
    PersonalData(
        full_name="Mai Thị Thanh Bình",
        full_name_latin="Mai Thi Thanh Binh",
        date_of_birth=date(1972, 5, 30),
        gender="Nữ",
        nationality="Việt Nam",
        id_number="079172001234",
        id_issue_date=date(2020, 10, 11),
        id_issue_place="Cục Cảnh sát QLHC về TTXH",
        permanent_address=_HCM_ADDRESSES[0],
        raw_address="123 Nguyễn Thị Minh Khai, Phường 06, Quận 3, Thành phố Hồ Chí Minh",
        source_document_type="text_input",
        source_image_path="data/mock_text_data/TTHC-AD-002/mock_001.json",
        extraction_confidence=0.75,
        field_confidences={
            "full_name": 0.8,
            "date_of_birth": 0.8,
            "gender": 0.8,
            "id_number": 0.8,
            "permanent_address": 0.75,
        },
        extracted_at=_EXTRACTED_AT,
    ),
    PersonalData(
        full_name="Ngô Quang Vinh",
        full_name_latin="Ngo Quang Vinh",
        date_of_birth=date(1968, 2, 8),
        gender="Nam",
        nationality="Việt Nam",
        id_number="079068002345",
        id_issue_date=date(2021, 5, 22),
        id_issue_place="Cục Cảnh sát QLHC về TTXH",
        permanent_address=_HCM_ADDRESSES[1],
        raw_address="45 Lê Văn Việt, Phường Hiệp Phú, Quận 9, Thành phố Hồ Chí Minh",
        source_document_type="text_input",
        source_image_path="data/mock_text_data/TTHC-AD-002/mock_002.json",
        extraction_confidence=0.75,
        field_confidences={
            "full_name": 0.8,
            "date_of_birth": 0.8,
            "gender": 0.8,
            "id_number": 0.8,
            "permanent_address": 0.75,
        },
        extracted_at=_EXTRACTED_AT,
    ),
    PersonalData(
        full_name="Lưu Thị Kim Oanh",
        full_name_latin="Luu Thi Kim Oanh",
        date_of_birth=date(1970, 11, 14),
        gender="Nữ",
        nationality="Việt Nam",
        id_number="079170003456",
        id_issue_date=date(2020, 8, 17),
        id_issue_place="Cục Cảnh sát QLHC về TTXH",
        permanent_address=_HCM_ADDRESSES[2],
        raw_address="88 Điện Biên Phủ, Phường 15, Quận Bình Thạnh, Thành phố Hồ Chí Minh",
        source_document_type="text_input",
        source_image_path="data/mock_text_data/TTHC-AD-002/mock_003.json",
        extraction_confidence=0.75,
        field_confidences={
            "full_name": 0.8,
            "date_of_birth": 0.8,
            "gender": 0.8,
            "id_number": 0.8,
            "permanent_address": 0.75,
        },
        extracted_at=_EXTRACTED_AT,
    ),
    PersonalData(
        full_name="Chu Văn Đạt",
        full_name_latin="Chu Van Dat",
        date_of_birth=date(1965, 7, 21),
        gender="Nam",
        nationality="Việt Nam",
        id_number="079065004567",
        id_issue_date=date(2022, 1, 6),
        id_issue_place="Cục Cảnh sát QLHC về TTXH",
        permanent_address=_HCM_ADDRESSES[3],
        raw_address="200 Cách Mạng Tháng Tám, Phường 10, Quận 3, Thành phố Hồ Chí Minh",
        source_document_type="text_input",
        source_image_path="data/mock_text_data/TTHC-AD-002/mock_004.json",
        extraction_confidence=0.75,
        field_confidences={
            "full_name": 0.8,
            "date_of_birth": 0.8,
            "gender": 0.8,
            "id_number": 0.8,
            "permanent_address": 0.75,
        },
        extracted_at=_EXTRACTED_AT,
    ),
    PersonalData(
        full_name="Hồ Thị Xuân",
        full_name_latin="Ho Thi Xuan",
        date_of_birth=date(1973, 4, 5),
        gender="Nữ",
        nationality="Việt Nam",
        id_number="079173005678",
        id_issue_date=date(2023, 3, 19),
        id_issue_place="Cục Cảnh sát QLHC về TTXH",
        permanent_address=_HCM_ADDRESSES[4],
        raw_address="77 Trần Hưng Đạo, Phường Cầu Kho, Quận 1, Thành phố Hồ Chí Minh",
        source_document_type="text_input",
        source_image_path="data/mock_text_data/TTHC-AD-002/mock_005.json",
        extraction_confidence=0.75,
        field_confidences={
            "full_name": 0.8,
            "date_of_birth": 0.8,
            "gender": 0.8,
            "id_number": 0.8,
            "permanent_address": 0.75,
        },
        extracted_at=_EXTRACTED_AT,
    ),
]

# ---------------------------------------------------------------------------
# Dataset manifest
# ---------------------------------------------------------------------------

DATASETS: list[tuple[str, list[PersonalData]]] = [
    ("TTHC-CR-001", _CR_001_RECORDS),
    ("TTHC-CR-002", _CR_002_RECORDS),
    ("TTHC-AD-001", _AD_001_RECORDS),
    ("TTHC-AD-002", _AD_002_RECORDS),
]


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------

def _serialize(obj: object) -> str:
    """JSON serializer for date/datetime objects."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def generate() -> None:
    total = 0
    rows = []
    for proc_id, records in DATASETS:
        out_dir = OUTPUT_DIR / proc_id
        out_dir.mkdir(parents=True, exist_ok=True)
        for n, record in enumerate(records, start=1):
            path = out_dir / f"mock_{n:03d}.json"
            payload = record.model_dump(mode="json")
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=_serialize), encoding="utf-8")
            total += 1

        rows.append((proc_id, len(records), str(out_dir.relative_to(_BACKEND_DIR))))
        print(f"  [{proc_id}] {len(records)} records -> {out_dir.relative_to(_BACKEND_DIR)}")

    print()
    print(f"Total: {total} mock PersonalData files written.")
    print()
    print(f"{'Procedure':<16}  {'Count':>5}  {'Output path'}")
    print("-" * 60)
    for proc_id, count, path in rows:
        print(f"{proc_id:<16}  {count:>5}  {path}")


if __name__ == "__main__":
    print("Generating text-based mock PersonalData for non-CCCD procedures...")
    generate()
