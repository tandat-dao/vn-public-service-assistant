"""DOC form filling service.

Opens a .doc (OOXML-based) file from FORM_SOURCES_DIR, applies field value
substitutions using four rules, and returns the filled document as bytes.

Fill rules applied in order:
  Rule 1 — Dot sequence replacement in paragraphs and table cells.
             Signing sections are skipped entirely.
  Rule 2 — CCCD character grid fill (1-row, 9+ cell tables).
  Rule 3 — Family member table row 1 pre-fill.
  Rule 4 — Signing sections are never modified under any circumstance.

All operations are best-effort: missing field values leave the document
unchanged for that position. Never raises on missing field values.
"""

from __future__ import annotations

import asyncio
import io
import os
import re
import subprocess
import tempfile
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

from app.core.form_field_configs import FORM_FILE_CONFIGS, FormField

FORM_SOURCES_DIR = Path(__file__).parent.parent.parent / "data" / "form_sources"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Matches 3+ consecutive dots, middle dots (·), horizontal ellipsis (…),
# or mathematical ellipsis (⋯).
_DOT_RE = re.compile(r"[.·…⋯]{3,}")

# Phrases that mark a signing section — never modify paragraphs/cells
# containing any of these.
_SIGNING_PHRASES: tuple[str, ...] = (
    "Ký, ghi rõ họ tên",
    "Xác nhận của",
    "ngày....tháng",
    "CHỮ KÝ",
    "NGƯỜI KÝ",
)

# Column header keywords that indicate a family-member table row.
_FAMILY_COL_KEYWORDS: tuple[str, ...] = (
    "họ",
    "tên",
    "sinh",
    "giới",
    "tính",
    "định danh",
    "quốc tịch",
    "dân tộc",
    "quan hệ",
)


# ---------------------------------------------------------------------------
# Helpers — signing-section detection
# ---------------------------------------------------------------------------

def _is_signing_section(text: str) -> bool:
    """Return True when *text* contains any signing-section phrase."""
    return any(phrase in text for phrase in _SIGNING_PHRASES)


# ---------------------------------------------------------------------------
# Helpers — label-to-field matching
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Lowercase, strip dots/colons/parens for label comparison."""
    text = _DOT_RE.sub("", text)
    text = re.sub(r"[,:()\[\]/\\]+", " ", text)
    return text.strip().lower()


def _find_field_id(label: str, fields: list[FormField]) -> str | None:
    """Return the field ID whose label best matches *label*, or None.

    Matching priority:
      1. Substring: either label is a substring of the other (exact).
      2. Word-subset: all words in the shorter token set appear in the longer
         (handles labels like "Họ tên" matching "Họ, chữ đệm và tên cha nuôi").
    """
    norm = _normalize(label)
    if not norm:
        return None

    # Pass 1 — substring match
    for field in fields:
        norm_field = _normalize(field["label"])
        if norm_field and (norm_field in norm or norm in norm_field):
            return field["id"]

    # Pass 2 — word-subset match (all words of the shorter must appear in the longer)
    query_words = set(norm.split())
    if not query_words:
        return None
    for field in fields:
        norm_field = _normalize(field["label"])
        if not norm_field:
            continue
        field_words = set(norm_field.split())
        shorter, longer = (
            (query_words, field_words)
            if len(query_words) <= len(field_words)
            else (field_words, query_words)
        )
        if shorter and shorter.issubset(longer):
            return field["id"]

    return None


# ---------------------------------------------------------------------------
# Helpers — cell text writing
# ---------------------------------------------------------------------------

def _set_cell_char(cell, char: str) -> None:
    """Write a single character into the first run of the cell's first paragraph."""
    if not cell.paragraphs:
        return
    para = cell.paragraphs[0]
    if para.runs:
        para.runs[0].text = char
    else:
        para.add_run(char)


def _set_cell_value(cell, value: str) -> None:
    """Replace the text content of the first paragraph in *cell* with *value*."""
    if not cell.paragraphs:
        return
    para = cell.paragraphs[0]
    # Clear all existing runs
    for run in para.runs:
        run.text = ""
    # Write value into the first run (or add one if none exist)
    if para.runs:
        para.runs[0].text = value
    else:
        para.add_run(value)


# ---------------------------------------------------------------------------
# Rule 1 — Dot sequence replacement in a paragraph
# ---------------------------------------------------------------------------

def _apply_dot_rule_to_paragraph(
    para,
    label_hint: str,
    fields: list[FormField],
    field_values: dict[str, str],
) -> None:
    """Replace dot sequences in *para*'s runs with the matching field value.

    *label_hint* is the text to use when no non-dot text exists in the
    paragraph itself (e.g., the preceding paragraph's text).
    """
    para_text = para.text
    if _is_signing_section(para_text):
        return

    has_dots = any(_DOT_RE.search(run.text) for run in para.runs)
    if not has_dots:
        return

    # Prefer text in the same paragraph (label before the dots);
    # fall back to the hint from the previous paragraph.
    same_para_label = _normalize(_DOT_RE.sub("", para_text))
    label = same_para_label if same_para_label else _normalize(label_hint)

    field_id = _find_field_id(label, fields)
    if not field_id:
        return
    value = field_values.get(field_id)
    if not value:
        return

    for run in para.runs:
        if _DOT_RE.search(run.text):
            run.text = _DOT_RE.sub(value, run.text)


# ---------------------------------------------------------------------------
# Rule 2 — CCCD character grid detection and fill
# ---------------------------------------------------------------------------

def _is_cccd_grid(table) -> bool:
    """True when the table looks like a 12-cell CCCD character grid."""
    rows = table.rows
    if len(rows) != 1:
        return False
    cells = rows[0].cells
    if len(cells) < 9:
        return False
    for cell in cells:
        text = cell.text.strip()
        if len(text) > 1:
            return False
    return True


def _find_id_number(field_values: dict[str, str]) -> str | None:
    """Return the first value in *field_values* that looks like a CCCD number."""
    _ID_RE = re.compile(r"^\d{9,12}$")
    for value in field_values.values():
        if value and _ID_RE.match(value.strip()):
            return value.strip()
    return None


def _apply_cccd_grid_rule(table, field_values: dict[str, str]) -> None:
    """Fill the CCCD character grid one digit per cell."""
    id_number = _find_id_number(field_values)
    if not id_number:
        return
    cells = table.rows[0].cells
    for i, char in enumerate(id_number):
        if i >= len(cells):
            break
        _set_cell_char(cells[i], char)


# ---------------------------------------------------------------------------
# Rule 3 — Family member table row 1 pre-fill
# ---------------------------------------------------------------------------

def _is_header_row(row) -> bool:
    """True when the row looks like a table header (bold text or all-caps labels)."""
    row_text = " ".join(c.text.strip() for c in row.cells)
    if not row_text.strip():
        return False

    # All-caps check with family-relevant keywords
    lower = row_text.lower()
    keyword_hits = sum(1 for kw in _FAMILY_COL_KEYWORDS if kw in lower)
    if keyword_hits >= 2:
        return True

    # Bold text in any cell
    for cell in row.cells:
        for para in cell.paragraphs:
            for run in para.runs:
                if run.bold and run.text.strip():
                    return True

    return False


def _is_family_table(table) -> bool:
    """True when the table has 2+ rows and a recognisable header row."""
    rows = table.rows
    if len(rows) < 2:
        return False
    return _is_header_row(rows[0])


def _apply_family_table_rule(
    table,
    fields: list[FormField],
    field_values: dict[str, str],
) -> None:
    """Pre-fill row 1 of a family-member table using column header matching."""
    rows = table.rows
    if len(rows) < 2:
        return

    header_cells = rows[0].cells
    data_cells = rows[1].cells

    for i, header_cell in enumerate(header_cells):
        if i >= len(data_cells):
            break
        header_text = header_cell.text.strip()
        if not header_text or _is_signing_section(header_text):
            continue
        field_id = _find_field_id(header_text, fields)
        if not field_id:
            continue
        value = field_values.get(field_id)
        if not value:
            continue
        if not _is_signing_section(data_cells[i].text):
            _set_cell_value(data_cells[i], value)


# ---------------------------------------------------------------------------
# Rule 1 applied to a table (cell-level dot replacement)
# ---------------------------------------------------------------------------

def _apply_dot_rule_to_table(
    table,
    fields: list[FormField],
    field_values: dict[str, str],
) -> None:
    """Apply dot-sequence replacement to every non-signing cell in *table*."""
    prev_cell_text = ""
    for row in table.rows:
        for cell in row.cells:
            cell_text = cell.text
            if _is_signing_section(cell_text):
                prev_cell_text = cell_text
                continue
            prev_para_text = prev_cell_text
            for para in cell.paragraphs:
                _apply_dot_rule_to_paragraph(para, prev_para_text, fields, field_values)
                prev_para_text = para.text
            prev_cell_text = cell_text


# ---------------------------------------------------------------------------
# LibreOffice PDF conversion
# ---------------------------------------------------------------------------

# Matches the path used in ingest_full_documents.py
_LIBREOFFICE_EXE = Path(r"C:\Program Files\LibreOffice\program\soffice.exe")


async def _convert_docx_to_pdf(docx_bytes: bytes) -> bytes:
    """Convert .docx bytes to .pdf bytes via LibreOffice headless.

    Writes docx_bytes to a temp file, invokes LibreOffice to convert
    in a temp directory, reads the resulting .pdf, then cleans up.

    Raises RuntimeError if LibreOffice is not found or conversion fails.
    """
    if not _LIBREOFFICE_EXE.exists():
        raise RuntimeError(
            f"LibreOffice not found at {_LIBREOFFICE_EXE}. "
            "Install LibreOffice or update _LIBREOFFICE_EXE path."
        )

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        docx_path = tmp_dir_path / "input.docx"
        docx_path.write_bytes(docx_bytes)

        result = subprocess.run(
            [
                str(_LIBREOFFICE_EXE),
                "--headless",
                "--convert-to", "pdf",
                "--outdir", str(tmp_dir_path),
                str(docx_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"LibreOffice conversion failed (exit {result.returncode}): "
                f"{result.stderr[:500]}"
            )

        pdf_path = tmp_dir_path / "input.pdf"
        if not pdf_path.exists():
            raise RuntimeError(
                f"LibreOffice ran but produced no PDF. stdout: {result.stdout[:300]}"
            )

        return pdf_path.read_bytes()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def fill_doc(
    form_file: str,
    field_values: dict[str, str],
) -> bytes:
    """Open *form_file* from FORM_SOURCES_DIR, apply *field_values*, return bytes.

    Raises FileNotFoundError when form_file is not present in FORM_SOURCES_DIR.
    Raises ValueError when form_file is not registered in FORM_FILE_CONFIGS.
    Fill operations are best-effort — missing values leave the document unchanged.
    The source file on disk is never modified.
    """
    if form_file not in FORM_FILE_CONFIGS:
        raise ValueError(f"form_file not in FORM_FILE_CONFIGS: {form_file!r}")

    source_path = FORM_SOURCES_DIR / form_file
    if not source_path.exists():
        raise FileNotFoundError(f"Form source file not found: {form_file!r}")

    config = FORM_FILE_CONFIGS[form_file]
    fields: list[FormField] = config["fields"]

    # Load into memory — Document() never modifies the source file on disk.
    with source_path.open("rb") as fh:
        file_bytes = fh.read()

    doc = Document(io.BytesIO(file_bytes))

    # ── Rule 1: paragraphs ──────────────────────────────────────────────────
    prev_para_text = ""
    for para in doc.paragraphs:
        _apply_dot_rule_to_paragraph(para, prev_para_text, fields, field_values)
        prev_para_text = para.text

    # ── Tables: Rules 2, 3, then 1 ────────────────────────────────────────
    for table in doc.tables:
        # Rule 2 — CCCD character grid (takes priority; skip other rules)
        if _is_cccd_grid(table):
            _apply_cccd_grid_rule(table, field_values)
            continue

        # Rule 3 — family member table (pre-fill row 1)
        if _is_family_table(table):
            _apply_family_table_rule(table, fields, field_values)
            # Still apply dot-replacement to other rows after row 1
            _apply_dot_rule_to_table(table, fields, field_values)
            continue

        # Default: dot replacement only (Rule 1)
        _apply_dot_rule_to_table(table, fields, field_values)

    # Save the modified document to bytes, convert to PDF, and return.
    buf = io.BytesIO()
    doc.save(buf)
    docx_bytes = buf.getvalue()
    return await _convert_docx_to_pdf(docx_bytes)
