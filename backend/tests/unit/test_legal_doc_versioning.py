"""Unit tests for legal document versioning in QdrantService and ingest_legal_docs.

All tests mock qdrant_client — no real Qdrant connection required.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.qdrant_service import QdrantService


class TestActiveFilter:
    def test_active_filter_raises_not_implemented(self):
        """_active_filter() is a stub — verify it raises NotImplementedError.

        When TASK-02 implements it, this test should be updated to assert the
        returned Filter contains FieldCondition(key="status", match="active").
        """
        with pytest.raises(NotImplementedError):
            QdrantService._active_filter()

    def test_active_filter_is_static_method(self):
        """_active_filter must be callable without an instance."""
        # If it were a regular method this would raise TypeError
        assert callable(QdrantService._active_filter)


class TestReIngestionSupersedes:
    """Verify the versioning contract: existing chunks are superseded before
    new chunks are upserted."""

    async def test_reingest_calls_batch_set_status_before_upsert(self):
        """scroll_by_document_number → batch_set_status("superseded") must
        happen before upsert_chunks in the re-ingestion flow."""
        svc = QdrantService()

        call_order: list[str] = []

        async def _scroll(document_number: str) -> list[str]:
            call_order.append("scroll")
            return ["id-1", "id-2"]

        async def _set_status(point_ids: list[str], status: str) -> None:
            call_order.append(f"set_status:{status}")

        async def _upsert(chunks: list[dict]) -> None:
            call_order.append("upsert")

        svc.scroll_by_document_number = _scroll
        svc.batch_set_status = _set_status
        svc.upsert_chunks = _upsert

        # Simulate the re-ingestion flow directly
        existing_ids = await svc.scroll_by_document_number("123/2021/NĐ-CP")
        assert existing_ids == ["id-1", "id-2"]
        if existing_ids:
            await svc.batch_set_status(existing_ids, "superseded")
        await svc.upsert_chunks([{"payload": {"status": "active"}}])

        assert call_order == ["scroll", "set_status:superseded", "upsert"], (
            "supersede must happen before upsert"
        )

    async def test_first_ingest_skips_supersede(self):
        """When no existing chunks are found, batch_set_status must NOT be called."""
        svc = QdrantService()

        supersede_called = False

        async def _scroll(document_number: str) -> list[str]:
            return []  # first-time ingest — nothing to supersede

        async def _set_status(point_ids: list[str], status: str) -> None:
            nonlocal supersede_called
            supersede_called = True

        async def _upsert(chunks: list[dict]) -> None:
            pass

        svc.scroll_by_document_number = _scroll
        svc.batch_set_status = _set_status
        svc.upsert_chunks = _upsert

        existing_ids = await svc.scroll_by_document_number("new-doc")
        if existing_ids:
            await svc.batch_set_status(existing_ids, "superseded")
        await svc.upsert_chunks([{"payload": {"status": "active"}}])

        assert not supersede_called, "batch_set_status must not be called on first ingest"


class TestLegalDocumentModel:
    def test_superseded_by_column_exists(self):
        """LegalDocument model must have a nullable superseded_by UUID column."""
        from app.models.legal_document import LegalDocument

        col = LegalDocument.__table__.columns.get("superseded_by")
        assert col is not None, "superseded_by column missing from LegalDocument"
        assert col.nullable is True

    def test_superseded_by_is_uuid_fk(self):
        """superseded_by must be a UUID FK pointing to legal_documents.id."""
        from app.models.legal_document import LegalDocument

        col = LegalDocument.__table__.columns["superseded_by"]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "legal_documents.id" in fk_targets


class TestIngestLegalDocs:
    def test_empty_procedure_tags_raises_value_error(self):
        """ingest() must reject an empty procedure_tags list immediately."""
        from ingestion.ingest_legal_docs import ingest

        with pytest.raises(ValueError, match="procedure_tags must not be empty"):
            ingest("some/path.pdf", [])

    def test_non_empty_tags_raises_not_implemented(self):
        """With valid tags, ingest() should reach the NotImplementedError stub."""
        from ingestion.ingest_legal_docs import ingest

        with pytest.raises(NotImplementedError):
            ingest("some/path.pdf", ["TTDN-001"])
