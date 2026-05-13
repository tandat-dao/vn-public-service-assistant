"""Full document ingestion pipeline — Điều/Khoản-aware chunker.

HOW TO RUN:
1. Ensure all legal documents are placed at:
   backend/data/legal_documents/adoption/
   backend/data/legal_documents/civil_registration/
   backend/data/legal_documents/housing/

2. Ensure Docker services are running:
   docker compose up -d

3. Ensure the FastAPI backend is NOT running
   (the script connects to services directly)

4. From the backend directory, run:
   python ingestion/ingest_full_documents.py

5. After completion, verify chunk counts:
   Check Qdrant dashboard at http://localhost:6333/dashboard

WARNING: This script WIPES the entire Qdrant collection
and scope_coverage table before re-ingesting.
All existing chunks will be permanently deleted.
"""

from __future__ import annotations

import asyncio
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.services.embedder import _get_embedder  # noqa: F401 — warms up singleton
from app.services.qdrant_service import QdrantService
from ingestion.ingest_legal_docs import upsert_scope_coverage

# ---------------------------------------------------------------------------
# Document metadata registry
# ---------------------------------------------------------------------------

DOCUMENT_REGISTRY: dict[str, dict] = {

    # ── civil_registration ──────────────────────────────────────────────────
    "civil_registration/60.2014.QH13.doc": {
        "document_number": "60/2014/QH13",
        "document_name": "Luật Hộ tịch 2014",
        "domain": "civil_registration",
        "location_scope": "VN",
        "procedure_ids": ["TTHC-CR-001", "TTHC-CR-002"],
    },
    "civil_registration/01.2022.TT.BTP.docx": {
        "document_number": "01/2022/TT-BTP",
        "document_name": "Thông tư 01/2022/TT-BTP",
        "domain": "civil_registration",
        "location_scope": "VN",
        "procedure_ids": ["TTHC-CR-001", "TTHC-CR-002"],
    },
    "civil_registration/1069.VBHN.BTP.pdf": {
        "document_number": "1069/VBHN-BTP",
        "document_name": "VBHN NĐ hộ tịch",
        "domain": "civil_registration",
        "location_scope": "VN",
        "procedure_ids": ["TTHC-CR-001", "TTHC-CR-002"],
    },
    "civil_registration/3884.VBHN.BTP.doc": {
        "document_number": "3884/VBHN-BTP",
        "document_name": "VBHN TT hộ tịch",
        "domain": "civil_registration",
        "location_scope": "VN",
        "procedure_ids": ["TTHC-CR-001", "TTHC-CR-002"],
    },
    "civil_registration/18.2026.NĐ.CP.docx": {
        "document_number": "18/2026/NĐ-CP",
        "document_name": "NĐ 18/2026/NĐ-CP",
        "domain": "civil_registration",
        "location_scope": "VN",
        "procedure_ids": ["TTHC-CR-001", "TTHC-CR-002"],
    },
    "civil_registration/281.2016.TT.BTC.pdf": {
        "document_number": "281/2016/TT-BTC",
        "document_name": "Thông tư 281/2016/TT-BTC",
        "domain": "civil_registration",
        "location_scope": "VN",
        "procedure_ids": ["TTHC-CR-001", "TTHC-CR-002"],
    },
    "civil_registration/124.2016.NQ.HDND.doc": {
        "document_number": "124/2016/NQ-HĐND",
        "document_name": "NQ phí hộ tịch TP.HCM",
        "domain": "civil_registration",
        "location_scope": "VN-HCM",
        "procedure_ids": ["TTHC-CR-001", "TTHC-CR-002"],
    },
    "civil_registration/06.2020.NQ.HDND.doc": {
        "document_number": "06/2020/NQ-HĐND",
        "document_name": "NQ phí hộ tịch Hà Nội",
        "domain": "civil_registration",
        "location_scope": "VN-HN",
        "procedure_ids": ["TTHC-CR-001", "TTHC-CR-002"],
    },
    "civil_registration/05.2025.NQ.HDND.doc": {
        "document_number": "05/2025/NQ-HĐND",
        "document_name": "NQ phí hộ tịch Đà Nẵng",
        "domain": "civil_registration",
        "location_scope": "VN-DN",
        "procedure_ids": ["TTHC-CR-001", "TTHC-CR-002"],
    },

    # ── adoption ────────────────────────────────────────────────────────────
    "adoption/52.2010.QH12.doc": {
        "document_number": "52/2010/QH12",
        "document_name": "Luật Nuôi con nuôi 2010",
        "domain": "adoption",
        "location_scope": "VN",
        "procedure_ids": ["TTHC-AD-001", "TTHC-AD-002"],
    },
    "adoption/275.VBHN.BTP.doc": {
        "document_number": "275/VBHN-BTP",
        "document_name": "VBHN NĐ nuôi con nuôi (19/2011, 06/2025)",
        "domain": "adoption",
        "location_scope": "VN",
        "procedure_ids": ["TTHC-AD-001", "TTHC-AD-002"],
    },
    "adoption/951.VBHN.BTP.pdf": {
        "document_number": "951/VBHN-BTP",
        "document_name": "VBHN NĐ nuôi con nuôi + lệ phí",
        "domain": "adoption",
        "location_scope": "VN",
        "procedure_ids": ["TTHC-AD-001", "TTHC-AD-002"],
    },
    "adoption/3845.VBHN.BTP.doc": {
        "document_number": "3845/VBHN-BTP",
        "document_name": "VBHN TT hồ sơ nuôi con nuôi",
        "domain": "adoption",
        "location_scope": "VN",
        "procedure_ids": ["TTHC-AD-001", "TTHC-AD-002"],
    },

    # ── housing ─────────────────────────────────────────────────────────────
    "housing/68.2020.QH14.doc": {
        "document_number": "68/2020/QH14",
        "document_name": "Luật Cư trú 2020",
        "domain": "housing",
        "location_scope": "VN",
        "procedure_ids": ["TTHC-001", "TTHC-002", "TTHC-003"],
    },
    "housing/154.2024.NĐ.CP.doc": {
        "document_number": "154/2024/NĐ-CP",
        "document_name": "NĐ 154/2024/NĐ-CP về cư trú",
        "domain": "housing",
        "location_scope": "VN",
        "procedure_ids": ["TTHC-001", "TTHC-002", "TTHC-003"],
    },
    "housing/53.2025.TT.BCA.doc": {
        "document_number": "53/2025/TT-BCA",
        "document_name": "Thông tư 53/2025/TT-BCA",
        "domain": "housing",
        "location_scope": "VN",
        "procedure_ids": ["TTHC-002", "TTHC-003"],
    },
    "housing/55.2021.TT.BCA.doc": {
        "document_number": "55/2021/TT-BCA",
        "document_name": "Thông tư 55/2021/TT-BCA",
        "domain": "housing",
        "location_scope": "VN",
        "procedure_ids": ["TTHC-001", "TTHC-002", "TTHC-003"],
    },
    "housing/66.2023.TT.BCA.doc": {
        "document_number": "66/2023/TT-BCA",
        "document_name": "Thông tư 66/2023/TT-BCA",
        "domain": "housing",
        "location_scope": "VN",
        "procedure_ids": ["TTHC-001", "TTHC-002", "TTHC-003"],
    },
    "housing/75.2022.TT.BTC.doc": {
        "document_number": "75/2022/TT-BTC",
        "document_name": "Thông tư 75/2022/TT-BTC",
        "domain": "housing",
        "location_scope": "VN",
        "procedure_ids": ["TTHC-001", "TTHC-002", "TTHC-003"],
    },
}

LEGAL_DOCS_DIR = Path(__file__).parent.parent / "data" / "legal_documents"

# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

LIBREOFFICE_EXE = Path(r"C:\Program Files\LibreOffice\program\soffice.exe")


def convert_doc_to_pdf(path: Path) -> Path:
    """Convert a binary .doc file to PDF via LibreOffice headless.

    Uses a temp directory so the original file is never modified.
    Returns the path to the converted PDF inside the temp dir.
    The caller is responsible for cleaning up the temp dir.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="dichvucong_doc_"))
    print(f"  [LibreOffice converting...] {path.name}")
    try:
        subprocess.run(
            [
                str(LIBREOFFICE_EXE),
                "--headless",
                "--convert-to", "pdf",
                "--outdir", str(tmp_dir),
                str(path),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        pdf_path = tmp_dir / (path.stem + ".pdf")
        if not pdf_path.exists():
            raise RuntimeError(f"LibreOffice did not produce {pdf_path}")
        return pdf_path
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise


def cleanup_tmp(pdf_path: Path) -> None:
    """Remove the temp directory created by convert_doc_to_pdf."""
    shutil.rmtree(pdf_path.parent, ignore_errors=True)


def extract_text_from_docx(path: Path) -> str:
    """Extract full text from .docx using python-docx."""
    from docx import Document
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_text_from_pdf(path: Path) -> str:
    """Extract full text from text-based PDF using pdfplumber."""
    import pdfplumber
    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                pages.append(page_text)
    return "\n".join(pages)


def extract_text(path: Path) -> str:
    """Auto-detect format and extract text.

    For .doc files: try python-docx first (works when the file is internally
    docx format despite .doc extension). Falls back to LibreOffice PDF
    conversion for true binary .doc files.
    For .docx: python-docx directly.
    For .pdf: pdfplumber directly.
    """
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(path)
    elif suffix == ".docx":
        return extract_text_from_docx(path)
    elif suffix == ".doc":
        try:
            return extract_text_from_docx(path)
        except Exception:
            # True binary .doc — convert via LibreOffice then extract PDF text
            pdf_path = convert_doc_to_pdf(path)
            try:
                return extract_text_from_pdf(pdf_path)
            finally:
                cleanup_tmp(pdf_path)
    else:
        raise ValueError(f"Unsupported format: {suffix}")


# ---------------------------------------------------------------------------
# Điều/Khoản chunking
# ---------------------------------------------------------------------------

DIEU_PATTERN = re.compile(
    r"(?=^Điều\s+\d+[\.\:])",
    re.MULTILINE,
)

KHOAN_PATTERN = re.compile(
    r"(?=^\d+\.\s)",
    re.MULTILINE,
)

_PHU_LUC_PATTERN = re.compile(r"\nPHỤ LỤC\b", re.IGNORECASE)

MAX_CHUNK_CHARS = 1200
MIN_CHUNK_CHARS = 80


def _extract_khoan_number(content: str) -> str | None:
    """Extract khoản number from chunk content if present.

    Checks the first 3 lines after the Điều header line for a top-level
    numeric khoản (e.g., "6. Lệ phí hộ tịch"). Letter subdivisions
    ("a.", "b.") and non-numeric lines are ignored.

    Returns:
        Khoản number string (e.g., "6") if found, else None.
    """
    lines = content.strip().split("\n")
    for line in lines[1:4]:  # skip line 0 (Điều header), check next 3
        match = re.match(r"^\s*(\d+)\.\s+", line)
        if match:
            return match.group(1)
    return None


def _split_phu_luc(
    content: str,
    article_num: str,
    base_metadata: dict,
) -> list[dict]:
    """Split a chunk at the PHỤ LỤC boundary if present.

    When a chunk contains a PHỤ LỤC appendix section (e.g. fee tables
    appended after the last Điều), split it off as a separate chunk
    with article_number="Phụ lục" so the appendix gets its own
    semantically coherent embedding.

    Returns:
        A list of 1 chunk (no PHỤ LỤC found) or 2 chunks (pre-appendix
        body + PHỤ LỤC chunk). The PHỤ LỤC chunk is exempt from the
        1,200-char length limit because fee tables must stay together
        to preserve their semantic context.
    """
    match = _PHU_LUC_PATTERN.search(content)
    if not match:
        return []  # Signal: no split needed, caller keeps original chunk

    pre_content = content[: match.start()].strip()
    phu_luc_content = content[match.start() :].strip()

    result = []

    if len(pre_content) >= MIN_CHUNK_CHARS:
        result.append({
            **base_metadata,
            "article_number": article_num,
            "content": pre_content,
        })

    if len(phu_luc_content) >= MIN_CHUNK_CHARS:
        result.append({
            **base_metadata,
            "article_number": "Phụ lục",
            "content": phu_luc_content,
        })

    return result


def split_by_dieu(text: str) -> list[tuple[str, str]]:
    """Split document text into (article_number, content) pairs by Điều boundaries.

    Returns list of (article_number_str, chunk_text).
    article_number_str is the digit(s) after "Điều ", e.g. "15" for "Điều 15."
    """
    parts = DIEU_PATTERN.split(text)
    results = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        match = re.match(r"Điều\s+(\d+)", part)
        if match:
            article_num = match.group(1)
        else:
            article_num = "0"  # preamble content
        results.append((article_num, part))
    return results


def split_by_khoan(article_num: str, content: str) -> list[dict]:
    """Split a single Điều into khoản-level chunks when content exceeds MAX_CHUNK_CHARS.

    Returns list of chunk dicts with keys: article_number, khoan_number, content.
    """
    if len(content) <= MAX_CHUNK_CHARS:
        return [{"article_number": article_num, "khoan_number": None, "content": content}]

    parts = KHOAN_PATTERN.split(content)
    chunks = []

    # First part is the Điều header + any intro text before the first khoản
    header = parts[0].strip()
    khoan_num = 0

    for part in parts[1:]:
        part = part.strip()
        if not part or len(part) < MIN_CHUNK_CHARS:
            continue
        khoan_match = re.match(r"^(\d+)\.\s", part)
        if khoan_match:
            khoan_num = khoan_match.group(1)

        # Prepend Điều header for context
        chunk_content = f"{header}\n{part}" if header else part

        # Include khoản in article_number so BM25 can discriminate chunks
        # within documents where the entire content sits under one Điều
        # (e.g. fee schedule documents).
        extracted_khoan = _extract_khoan_number(chunk_content)
        final_article_number = (
            f"Điều {article_num} Khoản {extracted_khoan}"
            if extracted_khoan
            else article_num
        )

        chunks.append({
            "article_number": final_article_number,
            "khoan_number": str(khoan_num),
            "content": chunk_content,
        })

    # If splitting by khoản produced nothing useful, fall back to full article
    if not chunks:
        return [{"article_number": article_num, "khoan_number": None, "content": content}]

    return chunks


def chunk_by_paragraphs(text: str) -> list[dict]:
    """Fallback chunker for documents with no Điều article headers.

    Splits on blank lines, groups paragraphs into windows of MAX_CHUNK_CHARS,
    and assigns synthetic article_number values ("p1", "p2", ...).
    """
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if len(p.strip()) >= MIN_CHUNK_CHARS]
    chunks = []
    window = []
    window_len = 0
    chunk_idx = 1

    for para in paragraphs:
        if window_len + len(para) > MAX_CHUNK_CHARS and window:
            chunks.append({
                "article_number": f"p{chunk_idx}",
                "khoan_number": None,
                "content": "\n\n".join(window),
            })
            chunk_idx += 1
            window = []
            window_len = 0
        window.append(para)
        window_len += len(para)

    if window:
        chunks.append({
            "article_number": f"p{chunk_idx}",
            "khoan_number": None,
            "content": "\n\n".join(window),
        })

    return chunks


def chunk_document(text: str, rel_path: str = "") -> list[dict]:
    """Main chunking entry point. Returns list of chunk dicts ready for Qdrant upsert.

    Each dict has: article_number, khoan_number, content.
    Falls back to paragraph chunker when no real Điều articles are found.
    """
    articles = split_by_dieu(text)
    # Only count articles with a real Điều number (article_num != "0")
    real_articles = [(n, c) for n, c in articles if n != "0" and len(c) >= MIN_CHUNK_CHARS]

    if not real_articles:
        print(f"  [no Điều headers — using paragraph chunker]")
        return chunk_by_paragraphs(text)

    raw_chunks = []
    for article_num, content in articles:
        if len(content) < MIN_CHUNK_CHARS:
            continue
        chunks = split_by_khoan(article_num, content)
        raw_chunks.extend(chunks)

    # Post-process: split off any PHỤ LỤC appendix sections
    all_chunks = []
    for chunk in raw_chunks:
        base_metadata = {k: v for k, v in chunk.items() if k not in ("article_number", "content")}
        split_result = _split_phu_luc(chunk["content"], chunk["article_number"], base_metadata)
        if split_result:
            all_chunks.extend(split_result)
        else:
            all_chunks.append(chunk)

    return all_chunks


# ---------------------------------------------------------------------------
# Qdrant upsert
# ---------------------------------------------------------------------------


async def upsert_chunk(chunk: dict, meta: dict, qdrant: QdrantService) -> None:
    """Embed and upsert a single chunk into Qdrant with deterministic UUID5 point ID."""
    point_id = str(uuid.uuid5(
        uuid.NAMESPACE_DNS,
        f"{meta['document_number']}::{chunk['article_number']}"
        f"::{chunk['khoan_number']}::{chunk['content'][:50]}",
    ))

    point = {
        "point_id": point_id,
        "document_number": meta["document_number"],
        "document_name": meta["document_name"],
        "domain": meta["domain"],
        "location_scope": meta["location_scope"],
        # Use procedure_tags key to match QdrantService._build_filter() expectations
        "procedure_tags": meta["procedure_ids"],
        "article_number": chunk["article_number"],
        "khoan_number": chunk["khoan_number"],
        "content": chunk["content"],
    }
    await qdrant.upsert([point])


# ---------------------------------------------------------------------------
# scope_coverage update
# ---------------------------------------------------------------------------


async def update_scope_coverage(meta: dict, session_factory) -> None:
    """Upsert one scope_coverage row per (location_scope, procedure_id) for the document."""
    location_scope = meta["location_scope"]
    domain = meta["domain"]

    async with session_factory() as db:
        for proc_id in meta["procedure_ids"]:
            try:
                await upsert_scope_coverage(db, location_scope, proc_id, domain, 1)
            except Exception as exc:
                print(
                    f"  WARNING: scope_coverage upsert failed "
                    f"({location_scope}, {proc_id}): {exc}"
                )


# ---------------------------------------------------------------------------
# Main ingestion flow
# ---------------------------------------------------------------------------


async def ingest_all() -> None:
    # Step 1 — Wipe Qdrant collection
    print("Wiping existing Qdrant collection...")
    qdrant = QdrantService()
    try:
        await qdrant._client.delete_collection(settings.QDRANT_COLLECTION)
        print(f"  Deleted collection '{settings.QDRANT_COLLECTION}'")
    except Exception as exc:
        print(f"  Note: could not delete collection ({exc}) — continuing")
    await qdrant.create_collection()
    print(f"  Collection '{settings.QDRANT_COLLECTION}' ready.")

    # Step 2 — Clear scope_coverage table
    print("Clearing scope_coverage table...")
    engine = create_async_engine(settings.POSTGRES_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        await db.execute(sql_text("DELETE FROM scope_coverage"))
        await db.commit()
    print("  scope_coverage cleared.")

    # Step 3 — Process each document in registry
    total_chunks = 0
    for rel_path, meta in DOCUMENT_REGISTRY.items():
        file_path = LEGAL_DOCS_DIR / rel_path
        if not file_path.exists():
            print(f"SKIP (not found): {rel_path}")
            continue

        print(f"Processing: {rel_path}")
        try:
            raw_text = extract_text(file_path)
        except Exception as exc:
            print(f"ERROR extracting {rel_path}: {exc}")
            continue

        chunks = chunk_document(raw_text, rel_path)
        print(f"  → {len(chunks)} chunks")

        for chunk in chunks:
            await upsert_chunk(chunk, meta, qdrant)
            total_chunks += 1

        await update_scope_coverage(meta, session_factory)

    await engine.dispose()
    print(f"\nDone. Total chunks ingested: {total_chunks}")


if __name__ == "__main__":
    asyncio.run(ingest_all())
