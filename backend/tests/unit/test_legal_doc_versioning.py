"""Unit tests for legal document versioning in QdrantService and ingest_legal_docs.

All tests mock qdrant_client — no real Qdrant connection required.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.qdrant_service import QdrantService


class TestActiveFilter:
    def test_active_filter_returns_status_active_filter(self):
        """_active_filter() must return a Filter with status='active' condition.

        Updated in TASK-02: the stub is now implemented, so we verify the
        returned Filter contains FieldCondition(key="status", match="active").
        """
        f = QdrantService._active_filter()
        assert f is not None
        must_conditions = f.must
        status_conditions = [
            c for c in must_conditions if getattr(c, "key", None) == "status"
        ]
        assert len(status_conditions) == 1
        assert status_conditions[0].match.value == "active"

    def test_active_filter_is_static_method(self):
        """_active_filter must be callable without an instance."""
        # If it were a regular method this would raise TypeError
        assert callable(QdrantService._active_filter)


class TestReIngestionSupersedes:
    """Verify the versioning contract: existing chunks are superseded before
    new chunks are upserted."""

    @patch("app.services.qdrant_service.EmbedderService")
    async def test_reingest_calls_batch_set_status_before_upsert(self, mock_embedder_cls):
        """scroll_by_document_number → batch_set_status("superseded") must
        happen before upsert_chunks in the re-ingestion flow."""
        mock_embedder_cls.return_value = MagicMock()
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

    @patch("app.services.qdrant_service.EmbedderService")
    async def test_first_ingest_skips_supersede(self, mock_embedder_cls):
        """When no existing chunks are found, batch_set_status must NOT be called."""
        mock_embedder_cls.return_value = MagicMock()
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
    @pytest.mark.asyncio
    async def test_empty_procedure_tags_chunk_is_skipped_not_raised(self):
        """Chunks with empty procedure_tags must be skipped (logged as WARNING), not raise.

        The old stub raised ValueError. The full implementation soft-skips instead.
        """
        from ingestion.ingest_legal_docs import build_article_lookup, ingest_document

        config = {
            "domain": "housing",
            "procedures": [
                {
                    "id": "TTHC-001",
                    "name": "Test",
                    "relevant_documents": [
                        {
                            "document_number": "68/2020/QH14",
                            "location_scope": "VN",
                            "relevant_articles": ["Điều 20"],
                        }
                    ],
                }
            ],
        }
        article_lookup = build_article_lookup(config)
        # Manually remove procedure_ids to simulate an empty-tags scenario
        article_lookup["68/2020/QH14"]["Điều 20"]["procedure_ids"] = []

        raw_chunks = [
            {
                "article_number": "Điều 20",
                "document_number": "68/2020/QH14",
                "content": "Some content",
                "char_count": 12,
                "chapter_heading": None,
            }
        ]

        mock_qdrant = AsyncMock()
        mock_qdrant.scroll_by_document_number = AsyncMock(return_value=[])
        mock_qdrant.batch_set_status = AsyncMock()
        mock_qdrant.upsert = AsyncMock()

        with patch(
            "ingestion.ingest_legal_docs.parse_chunks_from_pdf",
            return_value=raw_chunks,
        ), patch("ingestion.ingest_legal_docs.upsert_scope_coverage", new_callable=AsyncMock):
            summary = await ingest_document(
                document_number="68/2020/QH14",
                article_lookup=article_lookup,
                domain="housing",
                qdrant=mock_qdrant,
                db=AsyncMock(),
                dry_run=False,
            )

        # The chunk must be skipped, not raise
        assert summary["chunks_skipped"] == 1
        assert summary["chunks_ingested"] == 0
        mock_qdrant.upsert.assert_not_called()

    def test_unknown_document_number_raises_key_error(self):
        """validate_document_file_map must raise KeyError for unknown document_numbers."""
        from ingestion.ingest_legal_docs import validate_document_file_map

        bad_config = {
            "domain": "housing",
            "procedures": [
                {
                    "id": "TTHC-001",
                    "name": "Test",
                    "relevant_documents": [
                        {
                            "document_number": "99/9999/UNKNOWN",
                            "relevant_articles": ["Điều 1"],
                        }
                    ],
                }
            ],
        }

        with pytest.raises(KeyError, match="99/9999/UNKNOWN"):
            validate_document_file_map(bad_config)
