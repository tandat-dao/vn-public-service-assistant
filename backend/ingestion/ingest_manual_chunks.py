"""Ingest manually prepared chunk YAML files directly into Qdrant.

Bypasses Docling entirely — article text is pre-prepared by the project owner
and stored in backend/ingestion/manual_chunks/{domain}.yaml.

Re-ingestion / versioning flow
-------------------------------
Same soft-deprecation contract as ingest_legal_docs.py:
  1. Load manual_chunks/{domain}.yaml.
  2. Skip entries where content == "PASTE_ARTICLE_TEXT_HERE".
  3. For each valid chunk, build hierarchy prefix WITHOUT chapter heading.
  4. Soft-deprecate existing active chunks per document_number before upserting.
  5. Upsert active chunks to Qdrant.
  6. Upsert scope_coverage rows in PostgreSQL.

Usage:
    cd backend
    python ingestion/ingest_manual_chunks.py --domain civil_registration
    python ingestion/ingest_manual_chunks.py --domain civil_registration --dry-run
    python ingestion/ingest_manual_chunks.py --domain civil_registration --generate-summaries
    python ingestion/ingest_manual_chunks.py --domain civil_registration --dry-run --generate-summaries
"""

from __future__ import annotations

import argparse
import asyncio
import uuid
from pathlib import Path
from typing import Any

import structlog
import yaml
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.services.embedder import EmbedderService  # noqa: F401 — ensure singleton warms up
from app.services.qdrant_service import QdrantService
from ingestion.ingest_legal_docs import (
    DOCUMENT_FILE_MAP,
    DOCUMENT_NAME_MAP,
    deprecate_existing_chunks,
    generate_structured_summary,
    upsert_scope_coverage,
    validate_document_numbers_only,
)

log = structlog.get_logger(__name__)

MANUAL_CHUNKS_DIR = Path(__file__).parent / "manual_chunks"

_PLACEHOLDER = "PASTE_ARTICLE_TEXT_HERE"


# ---------------------------------------------------------------------------
# Core ingestion logic
# ---------------------------------------------------------------------------


async def run_ingestion(
    domain: str,
    dry_run: bool = False,
    generate_summaries: bool = False,
) -> None:
    """Load a manual chunks YAML file and upsert valid entries to Qdrant."""
    log.info(
        "manual_ingestion_start",
        domain=domain,
        dry_run=dry_run,
        generate_summaries=generate_summaries,
    )

    # Load YAML
    yaml_path = MANUAL_CHUNKS_DIR / f"{domain}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(
            f"Manual chunks file not found: {yaml_path}. "
            f"Create backend/ingestion/manual_chunks/{domain}.yaml before running."
        )
    with yaml_path.open(encoding="utf-8") as fh:
        wrapper = yaml.safe_load(fh)

    raw_chunks: list[dict[str, Any]] = wrapper.get("chunks", [])
    log.info("manual_chunks_loaded", total=len(raw_chunks))

    # Pre-flight: verify every document_number is recognized in DOCUMENT_FILE_MAP.
    # Build a synthetic config so validate_document_numbers_only() can be reused
    # directly — PDF file existence is NOT checked (manual workflow has no PDFs).
    _all_doc_numbers = sorted({c["document_number"] for c in raw_chunks if c.get("document_number")})
    validate_document_numbers_only({
        "procedures": [{
            "id": "manual",
            "relevant_documents": [{"document_number": d} for d in _all_doc_numbers],
        }]
    })

    # ---- Pass 1: validate and filter ----
    valid_chunks: list[dict[str, Any]] = []
    skipped_count = 0

    for chunk in raw_chunks:
        if chunk.get("content") == _PLACEHOLDER:
            log.warning(
                "skipping_placeholder_chunk",
                document_number=chunk.get("document_number"),
                article_number=chunk.get("article_number"),
            )
            skipped_count += 1
            continue

        valid_chunks.append(chunk)

    log.info(
        "chunk_filter_complete",
        valid=len(valid_chunks),
        skipped_placeholder=skipped_count,
    )

    # ---- Initialise services ----
    qdrant: QdrantService | None = None
    if not dry_run:
        qdrant = QdrantService()
        await qdrant.create_collection()

    engine = None
    session_factory = None
    if not dry_run:
        engine = create_async_engine(settings.POSTGRES_URL, echo=False)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Matches ingest_legal_docs.py: always generate summaries in live mode;
    # only generate in dry-run when --generate-summaries flag is explicitly set.
    llm = None
    _should_generate = generate_summaries or (not dry_run)
    if _should_generate and valid_chunks:
        from app.services.llm import LLMService
        llm = LLMService()
        log.info("llm_service_initialised", generate_summaries=True)

    # ---- Pass 2: build Qdrant points ----
    points: list[dict[str, Any]] = []
    scope_proc_counts: dict[tuple[str, str], int] = {}

    for chunk in valid_chunks:
        doc_num = chunk["document_number"]
        article_num = chunk["article_number"]
        location_scope = chunk["location_scope"]
        procedure_tags = chunk["procedure_tags"]

        # Hierarchy prefix WITHOUT chapter heading
        doc_name = DOCUMENT_NAME_MAP.get(doc_num, doc_num)
        prefix = f"[{doc_name} > {article_num}]"
        prefixed_content = f"{prefix}\n{chunk['content']}"

        # Structured summary (LLM call)
        structured_summary: dict | None = None
        if _should_generate and llm is not None:
            structured_summary = await generate_structured_summary(llm, prefixed_content)
            await asyncio.sleep(0.5)  # rate-limit between LLM calls
        elif dry_run and not generate_summaries:
            log.info(
                "structured_summary_skipped_dry_run",
                article=article_num,
                document_number=doc_num,
                note="(LLM call — will incur cost in live run)",
            )

        point: dict[str, Any] = {
            "point_id": str(uuid.uuid4()),
            "document_number": doc_num,
            "article_number": article_num,
            "procedure_tags": procedure_tags,
            "content": prefixed_content,
            "status": "active",
            "location_scope": location_scope,
            "domain": domain,
            "effective_date": None,
            "char_count": len(prefixed_content),
            "hierarchy": {
                "document_name": doc_name,
                "chapter": None,
                "article": article_num,
            },
            "structured_summary": structured_summary,
        }
        points.append(point)

        if dry_run:
            log.info(
                "dry_run_would_upsert",
                article=article_num,
                document_number=doc_num,
                procedure_tags=procedure_tags,
                location_scope=location_scope,
            )

        for proc_id in procedure_tags:
            key = (location_scope, proc_id)
            scope_proc_counts[key] = scope_proc_counts.get(key, 0) + 1

    # ---- Pass 3: deprecate + upsert + scope_coverage ----
    deprecated_total = 0
    scope_coverage_upserted = 0
    doc_numbers_in_batch = {chunk["document_number"] for chunk in valid_chunks}

    if not dry_run:
        # Soft-deprecate per document_number before upserting
        for doc_num in sorted(doc_numbers_in_batch):
            count = await deprecate_existing_chunks(qdrant, doc_num, domain)
            deprecated_total += count

        # Upsert all valid points
        if points:
            await qdrant.upsert(points)
            log.info("qdrant_upsert_complete", count=len(points))

        # Upsert scope_coverage rows
        async with session_factory() as db:
            for (scope, proc_id), count in scope_proc_counts.items():
                try:
                    await upsert_scope_coverage(db, scope, proc_id, domain, count)
                    scope_coverage_upserted += 1
                except Exception as exc:
                    log.error(
                        "scope_coverage_upsert_failed",
                        location_scope=scope,
                        procedure_id=proc_id,
                        error=str(exc),
                    )
    else:
        for doc_num in sorted(doc_numbers_in_batch):
            log.info("dry_run_would_deprecate", document_number=doc_num, domain=domain)
        for (scope, proc_id), count in scope_proc_counts.items():
            log.info(
                "dry_run_would_upsert_scope_coverage",
                location_scope=scope,
                procedure_id=proc_id,
                chunk_count=count,
            )
        scope_coverage_upserted = len(scope_proc_counts)

    if engine:
        await engine.dispose()

    # ---- Final summary ----
    proc_counts: dict[str, int] = {}
    for chunk in valid_chunks:
        for proc_id in chunk["procedure_tags"]:
            proc_counts[proc_id] = proc_counts.get(proc_id, 0) + 1

    proc_summary = ", ".join(
        f"{pid} ({cnt} chunks)" for pid, cnt in sorted(proc_counts.items())
    )

    mode = "[DRY-RUN] " if dry_run else ""
    print(f"\n{mode}Ingestion complete.")
    print(f"  Documents processed: {len(doc_numbers_in_batch)}")
    print(f"  Chunks ingested: {len(points) if not dry_run else 0}")
    print(f"  Chunks deprecated: {deprecated_total}")
    print(f"  Chunks skipped (placeholder content): {skipped_count}")
    print(f"  Procedures covered: {proc_summary or '(none)'}")
    print(f"  scope_coverage rows upserted: {scope_coverage_upserted}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest manually prepared chunk YAML files into Qdrant."
    )
    parser.add_argument(
        "--domain",
        required=True,
        help="Domain to ingest, e.g. civil_registration",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and log what would be upserted without writing to Qdrant or DB.",
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
            generate_summaries=args.generate_summaries,
        )
    )


if __name__ == "__main__":
    main()
