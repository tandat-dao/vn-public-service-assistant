"""Targeted ingestion for a specific subset of documents.

Use this script to re-ingest individual documents WITHOUT wiping the entire
Qdrant collection.  It:
  1. Soft-deprecates any existing chunks for each target document (sets
     status="superseded", domain-scoped to avoid cross-domain collisions).
  2. Extracts text from the new .doc file (LibreOffice fallback for binary .doc).
  3. Chunks and upserts new points (QdrantService.upsert always forces status="active").
  4. Upserts scope_coverage rows.

HOW TO RUN (from backend/ directory):
    python ingestion/ingest_targeted.py

Add or remove document keys from TARGET_KEYS to control which documents are
re-ingested.  Keys must match entries in DOCUMENT_REGISTRY exactly.
"""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.services.qdrant_service import QdrantService
from ingestion.ingest_full_documents import (
    DOCUMENT_REGISTRY,
    LEGAL_DOCS_DIR,
    chunk_document,
    extract_text,
    update_scope_coverage,
    upsert_chunk,
)
from ingestion.ingest_legal_docs import upsert_scope_coverage  # noqa: F401 — re-exported

# ---------------------------------------------------------------------------
# Documents to re-ingest — edit this list as needed
# ---------------------------------------------------------------------------

TARGET_KEYS = [
    "housing/53.2025.TT.BCA.doc",
    "housing/75.2022.TT.BTC.doc",
    "civil_registration/3884.VBHN.BTP.doc",
    "adoption/275.VBHN.BTP.doc",
    "adoption/3845.VBHN.BTP.doc",
]


# ---------------------------------------------------------------------------
# Main targeted ingestion flow
# ---------------------------------------------------------------------------


async def ingest_targeted() -> None:
    qdrant = QdrantService()
    engine = create_async_engine(settings.POSTGRES_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    total_chunks = 0

    for rel_path in TARGET_KEYS:
        meta = DOCUMENT_REGISTRY.get(rel_path)
        if meta is None:
            print(f"ERROR: '{rel_path}' not found in DOCUMENT_REGISTRY — skipping")
            continue

        file_path = LEGAL_DOCS_DIR / rel_path
        if not file_path.exists():
            print(f"ERROR: file not found on disk: {file_path} — skipping")
            continue

        doc_number = meta["document_number"]
        domain = meta["domain"]

        print(f"\n{'='*60}")
        print(f"Processing: {rel_path}")
        print(f"  document_number: {doc_number}  domain: {domain}")

        # Step 1 — Soft-deprecate existing chunks for this document
        existing_ids = await qdrant.scroll_by_document_number(doc_number, domain=domain)
        if existing_ids:
            print(f"  Superseding {len(existing_ids)} existing point(s)...")
            await qdrant.batch_set_status(existing_ids, "superseded")
        else:
            print(f"  No existing points found — clean insert.")

        # Step 2 — Extract text
        print(f"  Extracting text...")
        try:
            raw_text = extract_text(file_path)
        except Exception as exc:
            print(f"  ERROR extracting text: {exc} — skipping")
            continue

        char_count = len(raw_text)
        print(f"  Extracted {char_count} chars.")
        if char_count < 100:
            print(f"  WARNING: very short extraction — file may be scanned or empty.")

        # Step 3 — Chunk
        chunks = chunk_document(raw_text, rel_path)
        print(f"  chunks: {len(chunks)}")

        # Step 4 — Upsert (QdrantService.upsert forces status="active")
        for chunk in chunks:
            await upsert_chunk(chunk, meta, qdrant)
            total_chunks += 1

        # Step 5 — scope_coverage
        await update_scope_coverage(meta, session_factory)
        print(f"  scope_coverage updated.")

    await engine.dispose()
    print(f"\n{'='*60}")
    print(f"Done. Chunks upserted this run: {total_chunks}")


if __name__ == "__main__":
    asyncio.run(ingest_targeted())
