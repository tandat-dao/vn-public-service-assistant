"""Ingestion script — parse Vietnamese legal PDFs and upsert chunks to Qdrant.

Re-ingestion / versioning flow
-------------------------------
When a document that has previously been ingested is re-ingested (e.g. an
updated decree), the old chunks must be marked as ``"superseded"`` BEFORE the
new chunks are upserted.  This ensures that searches always return the latest
version of each chunk.

Flow:
    1. Parse document_number from PDF metadata or filename.
    2. Retrieve existing point IDs for that document_number from Qdrant.
    3. If any exist, call batch_set_status(existing_ids, "superseded").
    4. Parse article-boundary chunks via Docling.
    5. Attach ``"status": "active"`` to every new chunk payload.
    6. Embed chunks with bge-m3.
    7. Upsert to Qdrant.
"""


def ingest(pdf_path: str, procedure_tags: list[str]) -> None:
    """Ingest a legal PDF into Qdrant with versioning support.

    Args:
        pdf_path:       Absolute path to the PDF file to ingest.
        procedure_tags: List of procedure IDs this document is tagged to.
                        Must be non-empty — never ingest without tags so that
                        filtered search can find the chunks.

    Raises:
        ValueError: If procedure_tags is empty.
        NotImplementedError: Always — real implementation deferred to TASK-05.
    """
    if not procedure_tags:
        raise ValueError("procedure_tags must not be empty — resolve tags before ingesting")

    # Step 1: Parse document_number from PDF metadata / filename
    # document_number = _parse_document_number(pdf_path)

    # Step 2: SUPERSEDE existing chunks for this document_number
    # qdrant = QdrantService()
    # existing_ids = await qdrant.scroll_by_document_number(document_number)
    # if existing_ids:
    #     await qdrant.batch_set_status(existing_ids, "superseded")

    # Step 3: Parse article-boundary chunks via Docling
    # chunks = _parse_chunks(pdf_path)

    # Step 4: Add "status": "active" to every chunk payload
    # for chunk in chunks:
    #     chunk["payload"]["status"] = "active"
    #     chunk["payload"]["procedure_tags"] = procedure_tags
    #     chunk["payload"]["document_number"] = document_number

    # Step 5: Embed chunks with bge-m3
    # embeddings = _embed_chunks(chunks)

    # Step 6: Upsert to Qdrant
    # await qdrant.upsert_chunks(chunks)

    raise NotImplementedError  # real implementation in TASK-05
