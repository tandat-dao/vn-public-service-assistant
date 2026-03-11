"""Ingestion script — parse Vietnamese legal PDFs and upsert chunks to Qdrant."""


def ingest(pdf_path: str, procedure_tags: list[str]) -> None:
    """
    Chunk a legal PDF at article boundaries, embed each chunk, and upsert to Qdrant.
    Chunks must include article number and decree reference as payload.
    procedure_tags must be resolved before uploading — never ingest without tags.
    """
    raise NotImplementedError
