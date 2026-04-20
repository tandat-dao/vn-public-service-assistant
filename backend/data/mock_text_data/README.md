# Mock Text-Based Personal Data

## What these files are

These JSON files are synthetic `PersonalData` objects that simulate what
the system holds after a user provides personal information by **text
input** — not via OCR of an uploaded document.

They are used to test the civil registration (`TTHC-CR-001`,
`TTHC-CR-002`) and adoption (`TTHC-AD-001`, `TTHC-AD-002`) pipeline
paths where no identity document image is uploaded.

Each file is a valid serialization of the `PersonalData` Pydantic model
defined in `app/schemas/personal_data.py`.

All names, ID numbers, and addresses are **synthetic**. No real citizen
data was used.

## Directory structure

```
mock_text_data/
├── TTHC-CR-001/   # Đăng ký khai sinh — parent's data (5 records)
├── TTHC-CR-002/   # Cấp bản sao Trích lục hộ tịch — requester's data (5 records)
├── TTHC-AD-001/   # Đăng ký nuôi con nuôi — adoptive parent's data (5 records)
└── TTHC-AD-002/   # Đăng ký lại nuôi con nuôi — adoptive parent's data (5 records)
```

## Fields explained

### Fields that come from CCCD (would be OCR-extracted in production)

These fields mirror what OCR extraction from a Căn cước công dân card
would produce. In production they arrive via `ocr_fn` with
`extraction_confidence ≈ 1.0` (QR path) or `≈ 0.85` (full OCR path).
In these mock files they are text-entered with `extraction_confidence =
0.75–0.80`.

| Field | Source |
|---|---|
| `full_name` | CCCD front — printed name |
| `full_name_latin` | CCCD front — Latin transcription |
| `date_of_birth` | CCCD front |
| `gender` | CCCD front (`"Nam"` or `"Nữ"`) |
| `nationality` | CCCD front (always `"Việt Nam"` for these mocks) |
| `id_number` | CCCD chip / QR code |
| `id_issue_date` | CCCD back |
| `id_issue_place` | CCCD back |
| `permanent_address` | CCCD chip / QR code |
| `raw_address` | CCCD QR — full single-line address string |

### Fields that require additional user input beyond CCCD

These fields are **not on a CCCD** and must be provided by the user
explicitly (via chat or form input) for the adoption procedures:

| Information | Where it goes | Why not in PersonalData |
|---|---|---|
| Marital status | PDF form field (`tinh_trang_hon_nhan`) | PersonalData has no marital status field |
| Health/medical status | PDF form field (`tinh_trang_suc_khoe`) | Declared at procedure time, not on CCCD |
| Economic / living conditions | PDF form field (`dieu_kien_kinh_te`) | Self-declared, not on CCCD |
| Original adoption registration date (AD-002) | PDF form field (`ngay_dang_ky_goc`) | Historical event, not personal identity data |

For khai sinh (`TTHC-CR-001`), the **child's** information (name, date
of birth, place of birth, hospital/midwife name) also does not come from
PersonalData — it goes directly into the form fields at fill time.

## How to load one file into the pipeline for testing

```python
import json
from pathlib import Path
from app.schemas.personal_data import PersonalData

path = Path("data/mock_text_data/TTHC-CR-001/mock_001.json")
data = json.loads(path.read_text(encoding="utf-8"))
personal_data = PersonalData.model_validate(data)
```

To inject into an `AgentState` for graph testing:

```python
from app.agents.state import AgentState

state: AgentState = {
    "user_message": "Tôi muốn đăng ký khai sinh cho con",
    "session_id": "test-session-001",
    "iteration_count": 0,
    "personal_data": personal_data,
    "uploaded_image_path": None,
    "execution_plan": ["rag_fn"],
    "plan_cursor": 0,
    "entities": {"procedure": "đăng ký khai sinh"},
    "domain": "civil_registration",
    "filing_jurisdiction": "VN-HCM",
    ...
}
```

## Regenerating these files

```bash
cd backend
PYTHONPATH=. .venv/Scripts/python ingestion/generate_text_mock_data.py
```

The generator is deterministic — re-running it produces identical output.
