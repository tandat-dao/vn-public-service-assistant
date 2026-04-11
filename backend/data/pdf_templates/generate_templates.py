"""Generate synthetic AcroForm PDF templates for three residence procedures.

Produces TTHC-001.pdf, TTHC-002.pdf, TTHC-003.pdf in the same directory as
this script.  All three mirror the real CT01 form structure (Tờ khai thay
đổi thông tin cư trú, Mẫu CT01, Thông tư 66/2023/TT-BCA).

Usage (standalone — does NOT import from app/):
    cd backend
    PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python data/pdf_templates/generate_templates.py

Requirements already in requirements.txt:
    reportlab>=4.0
    pdfrw>=0.4

Font:
    DejaVuSans.ttf must be present alongside this script at:
        data/pdf_templates/DejaVuSans.ttf
    Download once with:
        curl -L -o data/pdf_templates/dejavu-fonts.zip \
          https://github.com/dejavu-fonts/dejavu-fonts/releases/download/version_2_37/dejavu-fonts-ttf-2.37.zip
        unzip -p data/pdf_templates/dejavu-fonts.zip \
          dejavu-fonts-ttf-2.37/ttf/DejaVuSans.ttf > data/pdf_templates/DejaVuSans.ttf
        rm data/pdf_templates/dejavu-fonts.zip

Notes:
  - AcroForm field names are ASCII-safe (no Vietnamese diacritics in names).
  - Visual labels use full Vietnamese text rendered with DejaVuSans.
  - All fields are single-line text (/Tx) widgets compatible with
    PDFService._fill_acroform().
"""

from __future__ import annotations

import os
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# ---------------------------------------------------------------------------
# Output directory — same folder as this script
# ---------------------------------------------------------------------------
OUTPUT_DIR: Path = Path(__file__).parent

# ---------------------------------------------------------------------------
# Register DejaVuSans for Vietnamese diacritic support
# ---------------------------------------------------------------------------
_FONT_PATH = str(OUTPUT_DIR / "DejaVuSans.ttf")

if not os.path.exists(_FONT_PATH):
    raise FileNotFoundError(
        f"DejaVuSans.ttf not found at {_FONT_PATH}.\n"
        "Download it:\n"
        "  curl -L -o data/pdf_templates/dejavu-fonts.zip "
        "https://github.com/dejavu-fonts/dejavu-fonts/releases/download/version_2_37/dejavu-fonts-ttf-2.37.zip\n"
        "  unzip -p data/pdf_templates/dejavu-fonts.zip "
        "dejavu-fonts-ttf-2.37/ttf/DejaVuSans.ttf > data/pdf_templates/DejaVuSans.ttf"
    )

pdfmetrics.registerFont(TTFont("DejaVuSans", _FONT_PATH))
pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", _FONT_PATH))  # bold alias uses same file

# ---------------------------------------------------------------------------
# Field definitions
# Each entry is (acroform_field_name, vietnamese_label)
# Field names must be ASCII-safe — they are used as dict keys by PDFService.
# Labels are full Vietnamese text rendered with DejaVuSans.
# ---------------------------------------------------------------------------
SHARED_FIELDS: list[tuple[str, str]] = [
    ("ho_chu_dem_va_ten",    "Họ, chữ đệm và tên"),
    ("ngay_thang_nam_sinh",  "Ngày, tháng, năm sinh"),
    ("gioi_tinh",            "Giới tính"),
    ("dan_toc",              "Dân tộc"),
    ("so_dinh_danh_ca_nhan", "Số định danh cá nhân / CCCD"),
    ("que_quan",             "Quê quán"),
    ("noi_thuong_tru",       "Nơi thường trú"),
    ("noi_o_hien_tai",       "Nơi ở hiện tại"),
    ("nghe_nghiep",          "Nghề nghiệp"),
    ("noi_lam_viec",         "Nơi làm việc"),
    ("ho_ten_chu_ho",        "Họ tên chủ hộ"),
    ("quan_he_voi_chu_ho",   "Quan hệ với chủ hộ"),
    ("so_dinh_danh_chu_ho",  "Số định danh cá nhân chủ hộ"),
    ("noi_dung_de_nghi",     "Nội dung đề nghị"),
]

# TTHC-002 has one extra field
TTHC002_EXTRA: list[tuple[str, str]] = [
    ("thoi_han_tam_tru", "Thời hạn tạm trú"),
]

# ---------------------------------------------------------------------------
# Procedure metadata
# ---------------------------------------------------------------------------
PROCEDURES: dict[str, dict] = {
    "TTHC-001": {
        "title_vn": "Đăng ký thường trú",
        "fields": SHARED_FIELDS,
    },
    "TTHC-002": {
        "title_vn": "Đăng ký tạm trú",
        "fields": SHARED_FIELDS + TTHC002_EXTRA,
    },
    "TTHC-003": {
        "title_vn": "Xác nhận thông tin về cư trú",
        "fields": SHARED_FIELDS,
    },
}

# ---------------------------------------------------------------------------
# Layout constants (A4 dimensions: 595 x 842 pt)
# ---------------------------------------------------------------------------
PAGE_W, PAGE_H = A4
MARGIN_LEFT: float = 50.0
LABEL_COL_W: float = 200.0          # label column width
FIELD_X: float = MARGIN_LEFT + LABEL_COL_W + 8.0
FIELD_W: float = PAGE_W - FIELD_X - MARGIN_LEFT
FIELD_H: float = 16.0
ROW_H: float = 28.0                 # vertical spacing between rows
HEADER_BOTTOM: float = PAGE_H - 155.0  # y of first field row
MIN_Y: float = 60.0                 # bottom margin


def _draw_header(c: canvas.Canvas, procedure_id: str, title_vn: str) -> None:
    """Draw the form header centred at the top of the current page."""
    c.setFont("DejaVuSans-Bold", 11)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 48, "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM")
    c.setFont("DejaVuSans", 10)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 63, "Độc lập – Tự do – Hạnh phúc")
    c.line(MARGIN_LEFT + 80, PAGE_H - 72, PAGE_W - MARGIN_LEFT - 80, PAGE_H - 72)

    c.setFont("DejaVuSans-Bold", 12)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 93, "TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ")
    c.setFont("DejaVuSans", 9)
    c.drawCentredString(
        PAGE_W / 2,
        PAGE_H - 108,
        f"(Mẫu CT01 – {title_vn})",
    )
    c.setFont("DejaVuSans", 9)
    c.drawString(
        MARGIN_LEFT,
        PAGE_H - 128,
        "Kính gửi: Công an phường/xã __________________________________",
    )

    # Column headers
    c.setFont("DejaVuSans-Bold", 8)
    c.drawString(MARGIN_LEFT, PAGE_H - 148, "Thông tin")
    c.drawString(FIELD_X, PAGE_H - 148, "Nội dung điền")


def generate_pdf(procedure_id: str, title_vn: str, fields: list[tuple[str, str]]) -> None:
    """Generate one AcroForm PDF template and write it to OUTPUT_DIR."""
    output_path = OUTPUT_DIR / f"{procedure_id}.pdf"
    c = canvas.Canvas(str(output_path), pagesize=A4)
    acro = c.acroForm

    _draw_header(c, procedure_id, title_vn)

    y = HEADER_BOTTOM
    c.setFont("DejaVuSans", 9)

    for field_name, label in fields:
        # Start a new page if we are about to overflow the bottom margin
        if y - FIELD_H < MIN_Y:
            c.showPage()
            _draw_header(c, procedure_id, title_vn)
            y = HEADER_BOTTOM
            c.setFont("DejaVuSans", 9)

        # Draw the label
        c.drawString(MARGIN_LEFT, y, f"{label}:")

        # Draw the AcroForm text field
        acro.textfield(
            name=field_name,
            tooltip=label,
            x=FIELD_X,
            y=y - 3,
            width=FIELD_W,
            height=FIELD_H,
            fontName="Helvetica",  # AcroForm widget uses standard PDF font; visual labels use DejaVuSans
            fontSize=9,
            borderWidth=0.5,
        )

        y -= ROW_H

    c.save()
    print(f"  Generated: {output_path} ({len(fields)} fields)")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Writing PDF templates to: {OUTPUT_DIR.resolve()}\n")
    for proc_id, info in PROCEDURES.items():
        generate_pdf(proc_id, info["title_vn"], info["fields"])
    print("\nDone.")


if __name__ == "__main__":
    main()
