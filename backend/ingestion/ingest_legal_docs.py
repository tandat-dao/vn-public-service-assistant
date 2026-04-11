"""Ingestion script — parse Vietnamese legal PDFs and upsert chunks to Qdrant.

Re-ingestion / versioning flow
-------------------------------
When a document that has previously been ingested is re-ingested (e.g. an
updated decree), the old chunks must be marked as ``"superseded"`` BEFORE the
new chunks are upserted.  This ensures that searches always return the latest
version of each chunk.

Flow:
    1. Load domain config (domain_configs/<domain>.yaml).
    2. Soft-deprecate existing chunks for each document_number being ingested.
    3. Parse article-boundary chunks via Docling.
    4. Filter chunks to only those whose article_number is in the domain config;
       skip (with WARNING) any chunk that has no matching procedure_tags.
    5. Apply boilerplate removal, hierarchy prefix, and structured summary.
    6. Embed and upsert active chunks to Qdrant.
    7. Upsert scope_coverage rows in PostgreSQL.

Usage:
    cd backend
    python ingestion/ingest_legal_docs.py
    python ingestion/ingest_legal_docs.py --domain housing
    python ingestion/ingest_legal_docs.py --dry-run
    python ingestion/ingest_legal_docs.py --dry-run --verbose
    python ingestion/ingest_legal_docs.py --dry-run --verbose --generate-summaries
    python ingestion/ingest_legal_docs.py --doc "68/2020/QH14"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
import yaml
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.services.embedder import EmbedderService
from app.services.qdrant_service import QdrantService

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LEGAL_DOCS_DIR = Path(__file__).parent.parent / "data" / "legal_documents"
DOMAIN_CONFIGS_DIR = Path(__file__).parent / "domain_configs"

# Explicit mapping: document_number string → filename on disk.
# Do not infer from filenames — Vietnamese filenames use romanised encodings.
DOCUMENT_FILE_MAP: dict[str, str] = {
    "68/2020/QH14":   "68_2020_QH14_435315.pdf",
    "62/2021/NĐ-CP":  "62_2021_ND-CP_473325.pdf",
    "104/2022/NĐ-CP": "104_2022_ND-CP_544177.pdf",
    "55/2021/TT-BCA": "55_2021_TT-BCA_466836.pdf",
}

# Human-readable document names for hierarchy prefix.
DOCUMENT_NAME_MAP: dict[str, str] = {
    "68/2020/QH14":   "Luật Cư trú 2020",
    "62/2021/NĐ-CP":  "Nghị định 62/2021/NĐ-CP",
    "104/2022/NĐ-CP": "Nghị định 104/2022/NĐ-CP",
    "55/2021/TT-BCA": "Thông tư 55/2021/TT-BCA",
}

# Regex to detect Vietnamese article headings: "Điều 1", "Điều 20", etc.
_DIEU_PATTERN = re.compile(r"Điều\s+(\d+)", re.UNICODE)

# Regex to detect Vietnamese chapter headings: "Chương I", "Chương III: ...", etc.
_CHUONG_PATTERN = re.compile(
    r"^(?:#{1,4}\s+)?(Chương\s+(?:[IVXivxLCDM]+|\d+)(?:[:.]\s*.+)?)\s*$",
    re.UNICODE,
)

# Chunk token warning threshold — warn but do not reject
_CHUNK_TOKEN_WARNING = 500

# ---------------------------------------------------------------------------
# Boilerplate removal patterns
# ---------------------------------------------------------------------------

# Each pattern is applied line-by-line. Matching lines are removed entirely.
_BOILERPLATE_LINE_PATTERNS: list[re.Pattern] = [
    # National preamble header
    re.compile(r"^CỘNG\s+HÒA\s+XÃ\s+HỘI\s+CHỦ\s+NGHĨA\s+VIỆT\s+NAM\s*$", re.UNICODE),
    re.compile(r"^Độc\s+lập\s*[-–]\s*Tự\s+do\s*[-–]\s*Hạnh\s+phúc\s*$", re.UNICODE),
    # Page number patterns: standalone digits or "Trang X" / "Trang X/Y"
    re.compile(r"^\d+\s*$"),
    re.compile(r"^Trang\s+\d+(?:/\d+)?\s*$", re.UNICODE),
    # Signing authority lines
    re.compile(r"^TM\.\s*CHÍNH\s+PHỦ\s*$", re.UNICODE),
    re.compile(r"^THỦ\s+TƯỚNG\s*$", re.UNICODE),
    re.compile(r"^KT\.\s*THỦ\s+TƯỚNG\s*$", re.UNICODE),
    re.compile(r"^PHÓ\s+THỦ\s+TƯỚNG\s*$", re.UNICODE),
    re.compile(r"^BỘ\s+TRƯỞNG\s*$", re.UNICODE),
    re.compile(r"^TỔNG\s+CỤC\s+TRƯỞNG\s*$", re.UNICODE),
    re.compile(r"^CỤC\s+TRƯỞNG\s*$", re.UNICODE),
    re.compile(r"^GIÁM\s+ĐỐC\s*$", re.UNICODE),
    # Repeated section dividers (3+ dashes, underscores, or asterisks)
    re.compile(r"^[-_*]{3,}\s*$"),
]


def clean_pdf_text(text: str, verbose: bool = False) -> str:
    """Strip predictable Vietnamese government document boilerplate from chunk text.

    Patterns removed:
    - National preamble lines (CỘNG HÒA..., Độc lập - Tự do...)
    - Page number patterns (standalone digits, Trang X/Y)
    - Signing authority lines (TM. CHÍNH PHỦ, THỦ TƯỚNG, etc.)
    - Repeated section dividers (--- or ___ lines)

    Args:
        text:    Raw chunk content string.
        verbose: If True, logs each stripped line at DEBUG level.

    Returns:
        Cleaned content string with boilerplate lines removed.
    """
    lines = text.splitlines()
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()
        matched_pattern = None
        for pattern in _BOILERPLATE_LINE_PATTERNS:
            if pattern.match(stripped):
                matched_pattern = pattern.pattern
                break
        if matched_pattern is not None:
            if verbose:
                log.debug(
                    "boilerplate_line_stripped",
                    line=stripped,
                    pattern=matched_pattern,
                )
        else:
            cleaned.append(line)

    # Collapse runs of blank lines to a single blank line
    result_lines: list[str] = []
    prev_blank = False
    for line in cleaned:
        is_blank = not line.strip()
        if is_blank and prev_blank:
            continue
        result_lines.append(line)
        prev_blank = is_blank

    return "\n".join(result_lines).strip()


# ---------------------------------------------------------------------------
# Structured summary generation
# ---------------------------------------------------------------------------

_SUMMARY_SYSTEM_PROMPT = (
    "Given this Vietnamese legal article text, extract the core legal "
    "content as JSON with exactly these fields:\n"
    "- \"obligation\": what the regulation requires (1 sentence, Vietnamese)\n"
    "- \"condition\": when or under what circumstances it applies "
    "(1 sentence, Vietnamese, null if not applicable)\n"
    "- \"consequence\": what happens if followed or violated "
    "(1 sentence, Vietnamese, null if not applicable)\n\n"
    "Return only valid JSON. No explanation."
)


async def generate_structured_summary(
    llm: Any,
    content: str,
) -> dict | None:
    """Generate a structured summary dict for a chunk via LLM.

    Args:
        llm:     LLMService instance.
        content: Chunk content (after boilerplate removal and hierarchy prefix).

    Returns:
        Dict with keys obligation/condition/consequence, or None on failure.
    """
    messages = [{"role": "user", "content": f"Article text:\n{content}"}]
    try:
        raw = await llm.async_invoke(
            system=_SUMMARY_SYSTEM_PROMPT,
            messages=messages,
            max_tokens=300,
        )
        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        log.warning(
            "structured_summary_invalid_json",
            error=str(exc),
            raw_response=raw[:200] if "raw" in dir() else "",
        )
        return None
    except Exception as exc:
        log.warning(
            "structured_summary_llm_failed",
            error=str(exc),
        )
        return None


# ---------------------------------------------------------------------------
# Domain config loading
# ---------------------------------------------------------------------------


def load_domain_config(domain: str) -> dict[str, Any]:
    """Load and validate the domain YAML config.

    Returns a dict with:
        domain: str
        procedures: list[dict]  (each has id, name, relevant_documents)
    Raises FileNotFoundError if the config file is missing.
    """
    config_path = DOMAIN_CONFIGS_DIR / f"{domain}.yaml"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Domain config not found: {config_path}. "
            f"Create ingestion/domain_configs/{domain}.yaml before running."
        )
    with config_path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def build_article_lookup(
    config: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Build a nested lookup from the domain config.

    Returns:
        {
          document_number: {
            article_number: {
              "procedure_ids": [str, ...],
              "location_scope": str,
            }
          }
        }

    An article_number may appear under multiple procedures — the lookup merges
    all procedure_ids for that article.
    """
    lookup: dict[str, dict[str, Any]] = {}

    for proc in config.get("procedures", []):
        proc_id = proc["id"]
        for doc_entry in proc.get("relevant_documents", []):
            doc_num = doc_entry["document_number"]
            scope = doc_entry.get("location_scope", "VN")

            if doc_num not in lookup:
                lookup[doc_num] = {}

            for article in doc_entry.get("relevant_articles", []):
                if article not in lookup[doc_num]:
                    lookup[doc_num][article] = {
                        "procedure_ids": [],
                        "location_scope": scope,
                    }
                if proc_id not in lookup[doc_num][article]["procedure_ids"]:
                    lookup[doc_num][article]["procedure_ids"].append(proc_id)

    return lookup


def validate_document_file_map(config: dict[str, Any]) -> None:
    """Raise if any document_number in the config is not in DOCUMENT_FILE_MAP."""
    for proc in config.get("procedures", []):
        for doc_entry in proc.get("relevant_documents", []):
            doc_num = doc_entry["document_number"]
            if doc_num not in DOCUMENT_FILE_MAP:
                raise KeyError(
                    f"document_number '{doc_num}' in domain config has no entry in "
                    f"DOCUMENT_FILE_MAP. Add it to DOCUMENT_FILE_MAP before ingesting."
                )
            pdf_path = LEGAL_DOCS_DIR / DOCUMENT_FILE_MAP[doc_num]
            if not pdf_path.exists():
                raise FileNotFoundError(
                    f"PDF file not found: {pdf_path}. "
                    f"Check that '{DOCUMENT_FILE_MAP[doc_num]}' exists in "
                    f"backend/data/legal_documents/."
                )


# ---------------------------------------------------------------------------
# Docling article-boundary chunking
# ---------------------------------------------------------------------------


def parse_chunks_from_pdf(
    pdf_path: Path,
    document_number: str,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    """Parse a PDF and return article-boundary chunks.

    Uses Docling to extract document structure. Identifies Điều headings and
    groups all text under each heading into a single chunk. Falls back to
    paragraph-level chunking (max 1,500 chars) if no Điều headings are found.

    Boilerplate removal is applied to each chunk's content before it is
    added to the prepared list.

    Args:
        pdf_path:        Path to the PDF file.
        document_number: Document number string for chunk metadata.
        verbose:         If True, logs stripped boilerplate lines at DEBUG.

    Returns:
        List of chunk dicts, each with keys:
            article_number, document_number, content, char_count, chapter_heading
    """
    import torch  # must be imported before docling on Windows — avoids c10.dll DLL init failure
    from docling.document_converter import DocumentConverter

    log.info("parsing_pdf", path=str(pdf_path), document_number=document_number)

    try:
        converter = DocumentConverter()
        result = converter.convert(str(pdf_path))
        doc = result.document
    except Exception as exc:
        log.error(
            "docling_parse_failed",
            path=str(pdf_path),
            document_number=document_number,
            error=str(exc),
        )
        raise

    chunks = _extract_article_chunks(doc, document_number, verbose=verbose)

    if not chunks:
        log.warning(
            "no_article_headings_found_fallback_to_paragraphs",
            document_number=document_number,
            path=str(pdf_path),
        )
        chunks = _fallback_paragraph_chunks(doc, document_number, verbose=verbose)

    log.info(
        "pdf_parsed",
        document_number=document_number,
        chunk_count=len(chunks),
    )
    return chunks


def _extract_article_chunks(
    doc: Any,
    document_number: str,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    """Extract chunks at Điều-heading boundaries from a Docling document.

    Scans all text elements in document order. When a line containing
    "Điều N" is detected as a heading (or the first occurrence in a paragraph),
    a new chunk begins. All text until the next Điều heading is accumulated
    into that chunk.

    Also tracks Chương headings to populate chapter_heading in each chunk.
    Applies boilerplate removal to each chunk's content before flushing.
    """
    chunks: list[dict[str, Any]] = []
    current_article: str | None = None
    current_lines: list[str] = []
    current_chapter: str | None = None

    def _flush() -> None:
        if current_article and current_lines:
            raw_content = "\n".join(current_lines).strip()
            cleaned_content = clean_pdf_text(raw_content, verbose=verbose)
            if cleaned_content:
                chunks.append(
                    {
                        "article_number": current_article,
                        "document_number": document_number,
                        "content": cleaned_content,
                        "char_count": len(cleaned_content),
                        "chapter_heading": current_chapter,
                    }
                )

    # Docling exposes text via doc.export_to_markdown() or iterating elements.
    # We use export_to_markdown and parse the resulting text line-by-line.
    try:
        full_text = doc.export_to_markdown()
    except Exception:
        # Fallback: try iterating text items
        try:
            items = list(doc.iterate_items())
            full_text = "\n".join(
                str(item.text) for item in items if hasattr(item, "text") and item.text
            )
        except Exception:
            full_text = str(doc)

    for line in full_text.splitlines():
        stripped = line.strip()
        if not stripped:
            if current_article:
                current_lines.append("")
            continue

        # Detect chapter heading BEFORE article heading check
        chuong_match = _CHUONG_PATTERN.match(stripped)
        if chuong_match:
            current_chapter = chuong_match.group(1).strip()
            if current_article:
                current_lines.append(stripped)
            continue

        match = _DIEU_PATTERN.search(stripped)
        if match and _is_article_heading(stripped, match.group(0)):
            # New article boundary found
            _flush()
            article_num = match.group(0).strip()
            current_article = article_num
            current_lines = [stripped]
        else:
            if current_article is not None:
                current_lines.append(stripped)
            # Text before first Điều heading is preamble — skip

    _flush()
    return chunks


def _is_article_heading(line: str, dieu_text: str) -> bool:
    """Heuristic: determine if this line is an article heading vs body text.

    A heading line is short (< 150 chars) and starts with or early contains
    the Điều marker. Prevents matching "theo Điều 20" inside a paragraph.
    """
    stripped = line.strip()
    # Must start with Điều or have it very early (within first 10 chars)
    dieu_pos = stripped.find(dieu_text)
    return dieu_pos <= 10 and len(stripped) < 200


def _fallback_paragraph_chunks(
    doc: Any,
    document_number: str,
    max_chars: int = 1500,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    """Fallback: split document text into fixed-size paragraph chunks."""
    try:
        full_text = doc.export_to_markdown()
    except Exception:
        full_text = str(doc)

    paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]
    chunks: list[dict[str, Any]] = []
    idx = 1

    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 > max_chars and current:
            cleaned = clean_pdf_text(current.strip(), verbose=verbose)
            chunks.append(
                {
                    "article_number": f"Đoạn {idx}",
                    "document_number": document_number,
                    "content": cleaned,
                    "char_count": len(cleaned),
                    "chapter_heading": None,
                }
            )
            idx += 1
            current = para
        else:
            current = (current + "\n\n" + para).strip() if current else para

    if current.strip():
        cleaned = clean_pdf_text(current.strip(), verbose=verbose)
        chunks.append(
            {
                "article_number": f"Đoạn {idx}",
                "document_number": document_number,
                "content": cleaned,
                "char_count": len(cleaned),
                "chapter_heading": None,
            }
        )

    return chunks


# ---------------------------------------------------------------------------
# Hierarchy prefix
# ---------------------------------------------------------------------------


def build_hierarchy_prefix(
    document_number: str,
    chapter_heading: str | None,
    article_number: str,
) -> str:
    """Build the structured hierarchy prefix for a chunk.

    Format:
        [{document_name} > {chapter_heading} > {article_number}]
    or, if chapter_heading is None:
        [{document_name} > {article_number}]
    """
    doc_name = DOCUMENT_NAME_MAP.get(document_number, document_number)
    if chapter_heading:
        return f"[{doc_name} > {chapter_heading} > {article_number}]"
    return f"[{doc_name} > {article_number}]"


# ---------------------------------------------------------------------------
# Soft-deprecation
# ---------------------------------------------------------------------------


async def deprecate_existing_chunks(
    qdrant: QdrantService,
    document_number: str,
) -> int:
    """Mark all existing active chunks for document_number as superseded.

    Returns count of deprecated chunks.
    """
    existing_ids = await qdrant.scroll_by_document_number(document_number)
    if existing_ids:
        await qdrant.batch_set_status(existing_ids, "superseded")
        log.info(
            "deprecated_existing_chunks",
            document_number=document_number,
            count=len(existing_ids),
        )
    return len(existing_ids)


# ---------------------------------------------------------------------------
# scope_coverage upsert
# ---------------------------------------------------------------------------


async def upsert_scope_coverage(
    db: AsyncSession,
    location_scope: str,
    procedure_id_str: str,
    domain: str,
    chunk_count: int,
) -> None:
    """Upsert a scope_coverage row for a (location_scope, procedure_id) pair.

    Looks up the procedure UUID from the procedures table by external code.
    Skips (with WARNING) if the procedure code is not found in the DB.
    """
    # Look up the UUID by code
    result = await db.execute(
        text("SELECT id FROM procedures WHERE code = :code"),
        {"code": procedure_id_str},
    )
    row = result.fetchone()
    if row is None:
        log.warning(
            "procedure_not_found_in_db_skipping_scope_coverage",
            procedure_id=procedure_id_str,
        )
        return

    proc_uuid = str(row[0])

    # Roll back any aborted transaction before attempting the upsert.
    # This is a no-op when the session is clean.
    try:
        await db.rollback()
    except Exception:
        pass

    stmt = text("""
        INSERT INTO scope_coverage
            (location_scope, procedure_id, domain, chunk_count, last_ingested_at)
        VALUES
            (:scope, CAST(:proc_id AS UUID), :domain, :count, :now)
        ON CONFLICT (location_scope, procedure_id)
        DO UPDATE SET
            chunk_count = EXCLUDED.chunk_count,
            last_ingested_at = EXCLUDED.last_ingested_at
    """)
    await db.execute(
        stmt,
        {
            "scope": location_scope,
            "proc_id": proc_uuid,
            "domain": domain,
            "count": chunk_count,
            "now": datetime.now(timezone.utc),
        },
    )
    await db.commit()
    log.info(
        "scope_coverage_upserted",
        location_scope=location_scope,
        procedure_id=procedure_id_str,
        domain=domain,
        chunk_count=chunk_count,
    )


# ---------------------------------------------------------------------------
# Core ingestion logic
# ---------------------------------------------------------------------------


async def ingest_document(
    document_number: str,
    article_lookup: dict[str, Any],
    domain: str,
    qdrant: QdrantService | None,
    db: AsyncSession | None,
    dry_run: bool = False,
    verbose: bool = False,
    generate_summaries: bool = False,
    llm: Any = None,
) -> dict[str, Any]:
    """Ingest a single document end-to-end.

    Args:
        document_number:    e.g. "68/2020/QH14"
        article_lookup:     Output of build_article_lookup()
        domain:             Domain name string
        qdrant:             QdrantService instance (None in dry-run)
        db:                 AsyncSession (None in dry-run)
        dry_run:            If True, parse and prepare but skip all writes
        verbose:            If True, log per-chunk details
        generate_summaries: If True, call LLM for structured_summary per chunk
        llm:                LLMService instance (required if generate_summaries=True)

    Returns a summary dict:
        {
            "document_number": str,
            "chunks_ingested": int,
            "chunks_skipped": int,
            "chunks_deprecated": int,
            "procedure_chunk_counts": {proc_id: int},
            "scope_coverage_pairs": [(location_scope, proc_id)],
        }
    """
    pdf_file = DOCUMENT_FILE_MAP[document_number]
    pdf_path = LEGAL_DOCS_DIR / pdf_file

    # Stage 2: Soft-deprecate existing chunks
    deprecated_count = 0
    if not dry_run:
        deprecated_count = await deprecate_existing_chunks(qdrant, document_number)
    else:
        log.info("dry_run_skip_deprecation", document_number=document_number)

    # Stage 3: Parse PDF
    try:
        raw_chunks = parse_chunks_from_pdf(pdf_path, document_number, verbose=verbose)
    except Exception as exc:
        log.error(
            "parse_failed_skipping_document",
            document_number=document_number,
            error=str(exc),
        )
        return {
            "document_number": document_number,
            "chunks_ingested": 0,
            "chunks_skipped": 0,
            "chunks_deprecated": deprecated_count,
            "procedure_chunk_counts": {},
            "scope_coverage_pairs": [],
        }

    # Stage 4: Filter, enrich, embed, upsert
    doc_article_lookup = article_lookup.get(document_number, {})
    active_chunks: list[dict[str, Any]] = []
    skipped = 0

    for chunk in raw_chunks:
        article = chunk["article_number"]
        article_info = doc_article_lookup.get(article)

        if article_info is None:
            log.warning(
                "article_not_in_domain_config_skipping",
                article_number=article,
                document_number=document_number,
            )
            skipped += 1
            continue

        procedure_tags = article_info["procedure_ids"]
        location_scope = article_info["location_scope"]

        if not procedure_tags:
            log.warning(
                "empty_procedure_tags_skipping",
                article_number=article,
                document_number=document_number,
            )
            skipped += 1
            continue

        # Build hierarchy prefix and prepend to content
        chapter_heading = chunk.get("chapter_heading")
        prefix = build_hierarchy_prefix(document_number, chapter_heading, article)
        prefixed_content = f"{prefix}\n{chunk['content']}"

        # Token budget warning (not rejection)
        estimated_tokens = len(prefixed_content) // 4
        if estimated_tokens > _CHUNK_TOKEN_WARNING:
            log.warning(
                "chunk_exceeds_token_warning",
                article=article,
                doc=document_number,
                estimated_tokens=estimated_tokens,
            )

        # Structured summary generation
        structured_summary: dict | None = None
        if generate_summaries and llm is not None:
            structured_summary = await generate_structured_summary(llm, prefixed_content)
            await asyncio.sleep(0.5)  # rate-limit between LLM calls
        elif dry_run and not generate_summaries:
            # Show the prompt that would be sent without calling LLM
            log.info(
                "structured_summary_skipped_dry_run",
                article=article,
                document_number=document_number,
                note="(LLM call — will incur cost in live run)",
                prompt_preview=_SUMMARY_SYSTEM_PROMPT[:100] + "...",
            )

        hierarchy_payload = {
            "document_name": DOCUMENT_NAME_MAP.get(document_number, document_number),
            "chapter": chapter_heading,
            "article": article,
        }

        enriched = {
            "point_id": str(uuid.uuid4()),
            "document_number": document_number,
            "article_number": article,
            "procedure_tags": procedure_tags,
            "content": prefixed_content,
            "status": "active",
            "location_scope": location_scope,
            "domain": domain,
            "effective_date": None,
            "char_count": len(prefixed_content),
            "hierarchy": hierarchy_payload,
            "structured_summary": structured_summary,
        }
        active_chunks.append(enriched)

        if verbose:
            log.info(
                "chunk_prepared",
                article=article,
                chapter=chapter_heading,
                procedure_tags=procedure_tags,
                location_scope=location_scope,
                has_summary=structured_summary is not None,
            )

    if not dry_run and active_chunks:
        try:
            await qdrant.upsert(active_chunks)
        except Exception as exc:
            log.error(
                "qdrant_upsert_failed",
                document_number=document_number,
                error=str(exc),
            )
            log.warning(
                "document_partially_superseded_must_reingest",
                document_number=document_number,
            )
            return {
                "document_number": document_number,
                "chunks_ingested": 0,
                "chunks_skipped": skipped,
                "chunks_deprecated": deprecated_count,
                "procedure_chunk_counts": {},
                "scope_coverage_pairs": [],
            }

    # Stage 5: Upsert scope_coverage
    # Collect (location_scope, proc_id) → chunk_count
    scope_proc_counts: dict[tuple[str, str], int] = {}
    for chunk in active_chunks:
        scope = chunk["location_scope"]
        for proc_id in chunk["procedure_tags"]:
            key = (scope, proc_id)
            scope_proc_counts[key] = scope_proc_counts.get(key, 0) + 1

    if not dry_run:
        for (scope, proc_id), count in scope_proc_counts.items():
            try:
                await upsert_scope_coverage(db, scope, proc_id, domain, count)
            except Exception as exc:
                log.error(
                    "scope_coverage_upsert_failed",
                    location_scope=scope,
                    procedure_id=proc_id,
                    error=str(exc),
                )

    # Build per-procedure chunk counts for summary
    proc_counts: dict[str, int] = {}
    for chunk in active_chunks:
        for proc_id in chunk["procedure_tags"]:
            proc_counts[proc_id] = proc_counts.get(proc_id, 0) + 1

    return {
        "document_number": document_number,
        "chunks_ingested": len(active_chunks),
        "chunks_skipped": skipped,
        "chunks_deprecated": deprecated_count,
        "procedure_chunk_counts": proc_counts,
        "scope_coverage_pairs": list(scope_proc_counts.keys()),
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def run_ingestion(
    domain: str = "housing",
    dry_run: bool = False,
    verbose: bool = False,
    doc_filter: str | None = None,
    generate_summaries: bool = False,
) -> None:
    """Orchestrate the full ingestion pipeline for a domain."""
    log.info(
        "ingestion_start",
        domain=domain,
        dry_run=dry_run,
        doc_filter=doc_filter,
        generate_summaries=generate_summaries,
    )

    # Load domain config
    config = load_domain_config(domain)

    # Validate all document_numbers have a file mapping before processing begins
    validate_document_file_map(config)

    article_lookup = build_article_lookup(config)

    # Determine which documents to process
    all_doc_numbers = list(article_lookup.keys())
    if doc_filter:
        if doc_filter not in all_doc_numbers:
            raise ValueError(
                f"--doc '{doc_filter}' not found in domain config. "
                f"Available: {all_doc_numbers}"
            )
        doc_numbers_to_process = [doc_filter]
    else:
        doc_numbers_to_process = all_doc_numbers

    log.info(
        "documents_to_process",
        count=len(doc_numbers_to_process),
        documents=doc_numbers_to_process,
    )

    # Initialise services — skip in dry-run to avoid requiring embeddings credentials
    qdrant: QdrantService | None = None
    if not dry_run:
        qdrant = QdrantService()
        await qdrant.create_collection()

    # Set up DB session (only needed for live runs)
    engine = None
    session_factory = None
    if not dry_run:
        engine = create_async_engine(settings.POSTGRES_URL, echo=False)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Set up LLMService for structured summaries.
    # - In dry-run without --generate-summaries: no LLM calls.
    # - In dry-run with --generate-summaries: create LLM, call for summaries.
    # - In live mode: always create LLM, always generate summaries.
    llm = None
    _should_generate = generate_summaries or (not dry_run)
    if _should_generate:
        from app.services.llm import LLMService
        llm = LLMService()
        log.info("llm_service_initialised", generate_summaries=True)

    # Process each document
    summaries: list[dict[str, Any]] = []

    for doc_num in doc_numbers_to_process:
        log.info("processing_document", document_number=doc_num)
        if dry_run:
            summary = await ingest_document(
                document_number=doc_num,
                article_lookup=article_lookup,
                domain=domain,
                qdrant=None,
                db=None,
                dry_run=True,
                verbose=verbose,
                generate_summaries=generate_summaries,
                llm=llm,
            )
            summaries.append(summary)
        else:
            async with session_factory() as db:
                summary = await ingest_document(
                    document_number=doc_num,
                    article_lookup=article_lookup,
                    domain=domain,
                    qdrant=qdrant,
                    db=db,
                    dry_run=False,
                    verbose=verbose,
                    generate_summaries=True,
                    llm=llm,
                )
            summaries.append(summary)

    if engine:
        await engine.dispose()

    # ---- Final summary ----
    total_ingested = sum(s["chunks_ingested"] for s in summaries)
    total_deprecated = sum(s["chunks_deprecated"] for s in summaries)
    total_skipped = sum(s["chunks_skipped"] for s in summaries)

    # Aggregate per-procedure chunk counts
    global_proc_counts: dict[str, int] = {}
    total_coverage_pairs = 0
    for s in summaries:
        total_coverage_pairs += len(s["scope_coverage_pairs"])
        for proc_id, count in s["procedure_chunk_counts"].items():
            global_proc_counts[proc_id] = global_proc_counts.get(proc_id, 0) + count

    proc_summary = ", ".join(
        f"{pid} ({cnt} chunks)" for pid, cnt in sorted(global_proc_counts.items())
    )

    mode = "[DRY-RUN] " if dry_run else ""
    print(f"\n{mode}Ingestion complete.")
    print(f"  Documents processed: {len(summaries)}")
    print(f"  Chunks ingested: {total_ingested}")
    print(f"  Chunks deprecated: {total_deprecated}")
    print(f"  Chunks skipped (no procedure_tags match): {total_skipped}")
    print(f"  Procedures covered: {proc_summary or '(none)'}")
    print(f"  scope_coverage rows upserted: {total_coverage_pairs}")

    # Per-document table
    print(f"\n{'Document':<20} {'Ingested':>9} {'Skipped':>8} {'Deprecated':>11}")
    print("-" * 52)
    for s in summaries:
        print(
            f"{s['document_number']:<20} "
            f"{s['chunks_ingested']:>9} "
            f"{s['chunks_skipped']:>8} "
            f"{s['chunks_deprecated']:>11}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest Vietnamese legal PDFs into Qdrant."
    )
    parser.add_argument(
        "--domain",
        default="housing",
        help="Domain to ingest (default: housing)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and chunk but do not write to Qdrant or DB.",
    )
    parser.add_argument(
        "--doc",
        metavar="DOCUMENT_NUM",
        default=None,
        help='Ingest only one document, e.g. "68/2020/QH14".',
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print each chunk article_number and procedure_tags as it is processed.",
    )
    parser.add_argument(
        "--generate-summaries",
        action="store_true",
        help=(
            "Generate structured_summary via LLM during dry-run. "
            "Default: skip in dry-run, always run in live mode."
        ),
    )
    args = parser.parse_args()

    asyncio.run(
        run_ingestion(
            domain=args.domain,
            dry_run=args.dry_run,
            verbose=args.verbose,
            doc_filter=args.doc,
            generate_summaries=args.generate_summaries,
        )
    )


if __name__ == "__main__":
    main()
