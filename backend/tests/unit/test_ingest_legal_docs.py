"""Unit tests for ingestion/ingest_legal_docs.py.

All Qdrant, EmbedderService, Docling, and DB calls are mocked.
No real API calls are made.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------

SAMPLE_CONFIG = {
    "domain": "housing",
    "procedures": [
        {
            "id": "TTHC-001",
            "name": "Đăng ký thường trú",
            "relevant_documents": [
                {
                    "document_number": "68/2020/QH14",
                    "location_scope": "VN",
                    "relevant_articles": ["Điều 20", "Điều 21"],
                }
            ],
        },
        {
            "id": "TTHC-002",
            "name": "Đăng ký tạm trú",
            "relevant_documents": [
                {
                    "document_number": "68/2020/QH14",
                    "location_scope": "VN",
                    "relevant_articles": ["Điều 27"],
                }
            ],
        },
    ],
}


def _make_chunk(article: str, doc: str, content: str = "text") -> dict:
    return {
        "article_number": article,
        "document_number": doc,
        "content": content,
        "char_count": len(content),
    }


# ---------------------------------------------------------------------------
# Test 1 — Article-boundary chunking never spans two articles
# ---------------------------------------------------------------------------

class TestArticleBoundaryChunking:
    def test_each_chunk_contains_only_one_dieu(self):
        """_extract_article_chunks must produce one chunk per Điều heading."""
        from ingestion.ingest_legal_docs import _extract_article_chunks

        mock_doc = MagicMock()
        mock_doc.export_to_markdown.return_value = (
            "Điều 20. Đăng ký thường trú\n"
            "Công dân có quyền đăng ký.\n\n"
            "Điều 21. Điều kiện đăng ký\n"
            "Phải có chỗ ở hợp pháp.\n"
        )

        chunks = _extract_article_chunks(mock_doc, "68/2020/QH14")

        assert len(chunks) == 2
        assert chunks[0]["article_number"] == "Điều 20"
        assert chunks[1]["article_number"] == "Điều 21"

        # Confirm no chunk contains text from a different article
        assert "Điều 21" not in chunks[0]["content"] or chunks[0]["content"].startswith("Điều 20")
        assert "Điều 20" not in chunks[1]["content"] or chunks[1]["content"].startswith("Điều 21")

    def test_chunk_content_includes_heading(self):
        """Each chunk must include its Điều heading line."""
        from ingestion.ingest_legal_docs import _extract_article_chunks

        mock_doc = MagicMock()
        mock_doc.export_to_markdown.return_value = (
            "Điều 5. Hồ sơ đăng ký\n"
            "Gồm các giấy tờ sau đây.\n"
        )

        chunks = _extract_article_chunks(mock_doc, "62/2021/NĐ-CP")

        assert len(chunks) == 1
        assert "Điều 5" in chunks[0]["content"]


# ---------------------------------------------------------------------------
# Test 2 — Unmatched article_number is skipped with WARNING
# ---------------------------------------------------------------------------

class TestUnmatchedArticleSkipped:
    @pytest.mark.asyncio
    async def test_chunk_not_in_yaml_is_skipped_not_upserted(self):
        """Chunks whose article_number is absent from the domain config are skipped."""
        from ingestion.ingest_legal_docs import build_article_lookup, ingest_document

        article_lookup = build_article_lookup(SAMPLE_CONFIG)

        # Raw chunks include Điều 99 which is NOT in the YAML
        raw_chunks = [
            _make_chunk("Điều 20", "68/2020/QH14", "text for dieu 20"),
            _make_chunk("Điều 99", "68/2020/QH14", "text for dieu 99 — no tags"),
        ]

        mock_qdrant = AsyncMock()
        mock_qdrant.scroll_by_document_number = AsyncMock(return_value=[])
        mock_qdrant.batch_set_status = AsyncMock()
        mock_qdrant.upsert = AsyncMock()

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(fetchone=MagicMock(return_value=("uuid-001",))))
        mock_db.commit = AsyncMock()

        with patch(
            "ingestion.ingest_legal_docs.parse_chunks_from_pdf",
            return_value=raw_chunks,
        ):
            summary = await ingest_document(
                document_number="68/2020/QH14",
                article_lookup=article_lookup,
                domain="housing",
                qdrant=mock_qdrant,
                db=mock_db,
                dry_run=False,
                verbose=False,
            )

        # Điều 99 must be skipped
        assert summary["chunks_skipped"] == 1
        assert summary["chunks_ingested"] == 1

        # Only Điều 20 should reach qdrant.upsert
        assert mock_qdrant.upsert.called
        upserted = mock_qdrant.upsert.call_args[0][0]
        article_numbers = [c["article_number"] for c in upserted]
        assert "Điều 99" not in article_numbers
        assert "Điều 20" in article_numbers


# ---------------------------------------------------------------------------
# Test 3 — Soft-deprecation runs BEFORE upsert
# ---------------------------------------------------------------------------

class TestSoftDeprecationOrder:
    @pytest.mark.asyncio
    async def test_batch_set_status_called_before_upsert(self):
        """batch_set_status('superseded') must be called before upsert()."""
        from ingestion.ingest_legal_docs import build_article_lookup, ingest_document

        article_lookup = build_article_lookup(SAMPLE_CONFIG)
        raw_chunks = [_make_chunk("Điều 20", "68/2020/QH14", "content")]

        call_order: list[str] = []

        mock_qdrant = AsyncMock()
        mock_qdrant.scroll_by_document_number = AsyncMock(return_value=["old-id-1"])

        async def fake_batch_set_status(*args, **kwargs):
            call_order.append("batch_set_status")

        async def fake_upsert(*args, **kwargs):
            call_order.append("upsert")

        mock_qdrant.batch_set_status = fake_batch_set_status
        mock_qdrant.upsert = fake_upsert

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(fetchone=MagicMock(return_value=("uuid-001",)))
        )
        mock_db.commit = AsyncMock()

        with patch(
            "ingestion.ingest_legal_docs.parse_chunks_from_pdf",
            return_value=raw_chunks,
        ):
            await ingest_document(
                document_number="68/2020/QH14",
                article_lookup=article_lookup,
                domain="housing",
                qdrant=mock_qdrant,
                db=mock_db,
                dry_run=False,
            )

        assert call_order == ["batch_set_status", "upsert"], (
            f"Expected batch_set_status before upsert, got: {call_order}"
        )


# ---------------------------------------------------------------------------
# Test 4 — scope_coverage upserted once per (scope, procedure_id) pair
# ---------------------------------------------------------------------------

class TestScopeCoverageUpsert:
    @pytest.mark.asyncio
    async def test_scope_coverage_called_per_combination(self):
        """upsert_scope_coverage must be called once per (scope, proc_id) pair."""
        from ingestion.ingest_legal_docs import build_article_lookup, ingest_document

        article_lookup = build_article_lookup(SAMPLE_CONFIG)

        # Two chunks — Điều 20 (TTHC-001) and Điều 27 (TTHC-002)
        raw_chunks = [
            _make_chunk("Điều 20", "68/2020/QH14", "thường trú content"),
            _make_chunk("Điều 27", "68/2020/QH14", "tạm trú content"),
        ]

        mock_qdrant = AsyncMock()
        mock_qdrant.scroll_by_document_number = AsyncMock(return_value=[])
        mock_qdrant.batch_set_status = AsyncMock()
        mock_qdrant.upsert = AsyncMock()

        upsert_calls: list[tuple] = []

        async def fake_upsert_coverage(db, scope, proc_id, domain, count):
            upsert_calls.append((scope, proc_id))

        mock_db = AsyncMock()

        with patch(
            "ingestion.ingest_legal_docs.parse_chunks_from_pdf",
            return_value=raw_chunks,
        ), patch(
            "ingestion.ingest_legal_docs.upsert_scope_coverage",
            side_effect=fake_upsert_coverage,
        ):
            await ingest_document(
                document_number="68/2020/QH14",
                article_lookup=article_lookup,
                domain="housing",
                qdrant=mock_qdrant,
                db=mock_db,
                dry_run=False,
            )

        # Expect one call per (VN, TTHC-001) and (VN, TTHC-002)
        assert ("VN", "TTHC-001") in upsert_calls
        assert ("VN", "TTHC-002") in upsert_calls
        assert len(upsert_calls) == 2


# ---------------------------------------------------------------------------
# Test 5 — dry-run produces zero Qdrant writes and zero DB writes
# ---------------------------------------------------------------------------

class TestDryRun:
    @pytest.mark.asyncio
    async def test_dry_run_no_qdrant_writes(self):
        """In dry-run mode, qdrant.upsert and qdrant.batch_set_status are never called."""
        from ingestion.ingest_legal_docs import build_article_lookup, ingest_document

        article_lookup = build_article_lookup(SAMPLE_CONFIG)
        raw_chunks = [_make_chunk("Điều 20", "68/2020/QH14", "some content")]

        mock_qdrant = AsyncMock()
        mock_qdrant.scroll_by_document_number = AsyncMock(return_value=[])
        mock_qdrant.batch_set_status = AsyncMock()
        mock_qdrant.upsert = AsyncMock()

        mock_db = AsyncMock()

        with patch(
            "ingestion.ingest_legal_docs.parse_chunks_from_pdf",
            return_value=raw_chunks,
        ), patch(
            "ingestion.ingest_legal_docs.upsert_scope_coverage",
            new_callable=AsyncMock,
        ) as mock_cov:
            summary = await ingest_document(
                document_number="68/2020/QH14",
                article_lookup=article_lookup,
                domain="housing",
                qdrant=mock_qdrant,
                db=mock_db,
                dry_run=True,
            )

        mock_qdrant.upsert.assert_not_called()
        mock_qdrant.batch_set_status.assert_not_called()
        mock_cov.assert_not_called()

        # Chunks are still counted correctly even in dry-run
        assert summary["chunks_ingested"] == 1
        assert summary["chunks_deprecated"] == 0


# ---------------------------------------------------------------------------
# Test 6 — document_number absent from DOCUMENT_FILE_MAP raises before processing
# ---------------------------------------------------------------------------

class TestDocumentFileMappingValidation:
    def test_missing_doc_map_entry_raises_key_error(self):
        """validate_document_file_map must raise KeyError if document_number is unknown."""
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

    def test_valid_config_passes_without_error(self):
        """validate_document_file_map must pass silently for a valid config."""
        from ingestion.ingest_legal_docs import validate_document_file_map

        # Patch the file existence check so it doesn't require real PDFs on disk
        with patch("ingestion.ingest_legal_docs.LEGAL_DOCS_DIR") as mock_dir:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_dir.__truediv__ = MagicMock(return_value=mock_path)
            validate_document_file_map(SAMPLE_CONFIG)


# ---------------------------------------------------------------------------
# Test 7 — Re-run produces no duplicate chunks (idempotency)
# ---------------------------------------------------------------------------

class TestIdempotency:
    @pytest.mark.asyncio
    async def test_rerun_supersedes_old_chunks_then_upserts_new(self):
        """Second run must supersede old IDs and upsert fresh chunks — no duplicates."""
        from ingestion.ingest_legal_docs import build_article_lookup, ingest_document

        article_lookup = build_article_lookup(SAMPLE_CONFIG)
        raw_chunks = [_make_chunk("Điều 20", "68/2020/QH14", "updated content")]

        existing_ids = ["old-point-1", "old-point-2"]

        mock_qdrant = AsyncMock()
        mock_qdrant.scroll_by_document_number = AsyncMock(return_value=existing_ids)
        mock_qdrant.batch_set_status = AsyncMock()
        mock_qdrant.upsert = AsyncMock()

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(fetchone=MagicMock(return_value=("uuid-001",)))
        )
        mock_db.commit = AsyncMock()

        with patch(
            "ingestion.ingest_legal_docs.parse_chunks_from_pdf",
            return_value=raw_chunks,
        ):
            summary = await ingest_document(
                document_number="68/2020/QH14",
                article_lookup=article_lookup,
                domain="housing",
                qdrant=mock_qdrant,
                db=mock_db,
                dry_run=False,
            )

        # Old IDs must be marked superseded
        mock_qdrant.batch_set_status.assert_called_once_with(existing_ids, "superseded")

        # New chunk is upserted
        assert mock_qdrant.upsert.called
        upserted = mock_qdrant.upsert.call_args[0][0]
        assert len(upserted) == 1
        assert upserted[0]["status"] == "active"
        # Content now includes hierarchy prefix followed by the original text
        assert "updated content" in upserted[0]["content"]
        assert upserted[0]["content"].startswith("[Luật Cư trú 2020")

        # Summary reflects correct counts
        assert summary["chunks_deprecated"] == 2
        assert summary["chunks_ingested"] == 1


# ---------------------------------------------------------------------------
# Test 8 — Boilerplate removal strips preamble lines
# ---------------------------------------------------------------------------

class TestBoilerplateRemoval:
    def test_strips_cong_hoa_preamble(self):
        """clean_pdf_text must remove CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM lines."""
        from ingestion.ingest_legal_docs import clean_pdf_text

        text = (
            "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n"
            "Độc lập - Tự do - Hạnh phúc\n"
            "Điều 20. Đăng ký thường trú\n"
            "Công dân có quyền đăng ký."
        )

        result = clean_pdf_text(text)

        assert "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" not in result
        assert "Độc lập - Tự do - Hạnh phúc" not in result
        assert "Điều 20. Đăng ký thường trú" in result
        assert "Công dân có quyền đăng ký." in result

    def test_strips_standalone_page_numbers(self):
        """clean_pdf_text must remove standalone page number lines."""
        from ingestion.ingest_legal_docs import clean_pdf_text

        text = (
            "Điều 5. Hồ sơ đăng ký\n"
            "3\n"
            "Gồm các giấy tờ.\n"
            "Trang 2/10\n"
            "Tiếp theo.\n"
        )

        result = clean_pdf_text(text)

        assert "Điều 5" in result
        assert "Gồm các giấy tờ." in result
        assert "Tiếp theo." in result
        # Standalone page number and Trang X/Y must be stripped
        lines = [l.strip() for l in result.splitlines() if l.strip()]
        assert "3" not in lines
        assert "Trang 2/10" not in lines

    def test_strips_section_dividers(self):
        """clean_pdf_text must remove lines consisting only of dashes or underscores."""
        from ingestion.ingest_legal_docs import clean_pdf_text

        text = "Điều 7. Quy định\n---\nNội dung quy định.\n___\nKết thúc."

        result = clean_pdf_text(text)

        assert "Điều 7" in result
        assert "Nội dung quy định." in result
        assert "---" not in result
        assert "___" not in result


# ---------------------------------------------------------------------------
# Test 9 — Hierarchy prefix format
# ---------------------------------------------------------------------------

class TestHierarchyPrefix:
    def test_prefix_with_chapter_and_article(self):
        """build_hierarchy_prefix must produce [doc > chapter > article] format."""
        from ingestion.ingest_legal_docs import build_hierarchy_prefix

        prefix = build_hierarchy_prefix(
            "68/2020/QH14",
            "Chương III: Đăng ký thường trú",
            "Điều 20",
        )

        assert prefix == "[Luật Cư trú 2020 > Chương III: Đăng ký thường trú > Điều 20]"

    def test_prefix_without_chapter_falls_back_to_two_part(self):
        """build_hierarchy_prefix must produce [doc > article] when chapter is None."""
        from ingestion.ingest_legal_docs import build_hierarchy_prefix

        prefix = build_hierarchy_prefix(
            "62/2021/NĐ-CP",
            None,
            "Điều 5",
        )

        assert prefix == "[Nghị định 62/2021/NĐ-CP > Điều 5]"

    def test_hierarchy_prefix_prepended_to_chunk_content(self):
        """ingest_document must prepend hierarchy prefix to chunk content in Qdrant payload."""
        from ingestion.ingest_legal_docs import build_article_lookup, ingest_document

        article_lookup = build_article_lookup(SAMPLE_CONFIG)
        # Chunk includes chapter_heading in the dict (as returned by _extract_article_chunks)
        raw_chunks = [
            {
                "article_number": "Điều 20",
                "document_number": "68/2020/QH14",
                "content": "Công dân có quyền đăng ký thường trú.",
                "char_count": 40,
                "chapter_heading": "Chương III: Đăng ký thường trú",
            }
        ]

        mock_qdrant = AsyncMock()
        mock_qdrant.scroll_by_document_number = AsyncMock(return_value=[])
        mock_qdrant.batch_set_status = AsyncMock()
        mock_qdrant.upsert = AsyncMock()

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(fetchone=MagicMock(return_value=("uuid-001",)))
        )
        mock_db.commit = AsyncMock()

        with patch(
            "ingestion.ingest_legal_docs.parse_chunks_from_pdf",
            return_value=raw_chunks,
        ):
            summary = asyncio.get_event_loop().run_until_complete(
                ingest_document(
                    document_number="68/2020/QH14",
                    article_lookup=article_lookup,
                    domain="housing",
                    qdrant=mock_qdrant,
                    db=mock_db,
                    dry_run=False,
                    generate_summaries=False,
                )
            )

        upserted = mock_qdrant.upsert.call_args[0][0]
        assert len(upserted) == 1
        content = upserted[0]["content"]
        assert content.startswith(
            "[Luật Cư trú 2020 > Chương III: Đăng ký thường trú > Điều 20]"
        )
        assert "Công dân có quyền đăng ký thường trú." in content

    def test_hierarchy_payload_stored_separately(self):
        """ingest_document must store hierarchy as a separate payload field."""
        from ingestion.ingest_legal_docs import build_article_lookup, ingest_document

        article_lookup = build_article_lookup(SAMPLE_CONFIG)
        raw_chunks = [
            {
                "article_number": "Điều 20",
                "document_number": "68/2020/QH14",
                "content": "Nội dung.",
                "char_count": 9,
                "chapter_heading": "Chương III",
            }
        ]

        mock_qdrant = AsyncMock()
        mock_qdrant.scroll_by_document_number = AsyncMock(return_value=[])
        mock_qdrant.batch_set_status = AsyncMock()
        mock_qdrant.upsert = AsyncMock()

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(fetchone=MagicMock(return_value=("uuid-001",)))
        )
        mock_db.commit = AsyncMock()

        with patch(
            "ingestion.ingest_legal_docs.parse_chunks_from_pdf",
            return_value=raw_chunks,
        ):
            asyncio.get_event_loop().run_until_complete(
                ingest_document(
                    document_number="68/2020/QH14",
                    article_lookup=article_lookup,
                    domain="housing",
                    qdrant=mock_qdrant,
                    db=mock_db,
                    dry_run=False,
                    generate_summaries=False,
                )
            )

        upserted = mock_qdrant.upsert.call_args[0][0]
        hierarchy = upserted[0]["hierarchy"]
        assert hierarchy["document_name"] == "Luật Cư trú 2020"
        assert hierarchy["chapter"] == "Chương III"
        assert hierarchy["article"] == "Điều 20"


# ---------------------------------------------------------------------------
# Test 10 — Structured summary field in payload
# ---------------------------------------------------------------------------

class TestStructuredSummary:
    @pytest.mark.asyncio
    async def test_structured_summary_present_when_llm_returns_valid_json(self):
        """structured_summary must be populated in payload when LLM returns valid JSON."""
        from ingestion.ingest_legal_docs import build_article_lookup, ingest_document

        article_lookup = build_article_lookup(SAMPLE_CONFIG)
        raw_chunks = [
            {
                "article_number": "Điều 20",
                "document_number": "68/2020/QH14",
                "content": "Công dân có quyền đăng ký.",
                "char_count": 26,
                "chapter_heading": None,
            }
        ]

        expected_summary = {
            "obligation": "Công dân phải đăng ký thường trú.",
            "condition": "Khi có chỗ ở hợp pháp.",
            "consequence": None,
        }

        mock_llm = AsyncMock()
        mock_llm.async_invoke = AsyncMock(
            return_value=json.dumps(expected_summary)
        )

        mock_qdrant = AsyncMock()
        mock_qdrant.scroll_by_document_number = AsyncMock(return_value=[])
        mock_qdrant.batch_set_status = AsyncMock()
        mock_qdrant.upsert = AsyncMock()

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(fetchone=MagicMock(return_value=("uuid-001",)))
        )
        mock_db.commit = AsyncMock()

        with patch(
            "ingestion.ingest_legal_docs.parse_chunks_from_pdf",
            return_value=raw_chunks,
        ), patch("asyncio.sleep", new_callable=AsyncMock):
            summary = await ingest_document(
                document_number="68/2020/QH14",
                article_lookup=article_lookup,
                domain="housing",
                qdrant=mock_qdrant,
                db=mock_db,
                dry_run=False,
                generate_summaries=True,
                llm=mock_llm,
            )

        upserted = mock_qdrant.upsert.call_args[0][0]
        assert upserted[0]["structured_summary"] == expected_summary

    @pytest.mark.asyncio
    async def test_structured_summary_none_when_llm_returns_invalid_json(self):
        """structured_summary must be None when LLM returns invalid JSON — chunk still ingested."""
        from ingestion.ingest_legal_docs import build_article_lookup, ingest_document

        article_lookup = build_article_lookup(SAMPLE_CONFIG)
        raw_chunks = [
            {
                "article_number": "Điều 20",
                "document_number": "68/2020/QH14",
                "content": "Công dân có quyền đăng ký.",
                "char_count": 26,
                "chapter_heading": None,
            }
        ]

        mock_llm = AsyncMock()
        # LLM returns invalid JSON
        mock_llm.async_invoke = AsyncMock(return_value="not valid json {{{")

        mock_qdrant = AsyncMock()
        mock_qdrant.scroll_by_document_number = AsyncMock(return_value=[])
        mock_qdrant.batch_set_status = AsyncMock()
        mock_qdrant.upsert = AsyncMock()

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(fetchone=MagicMock(return_value=("uuid-001",)))
        )
        mock_db.commit = AsyncMock()

        with patch(
            "ingestion.ingest_legal_docs.parse_chunks_from_pdf",
            return_value=raw_chunks,
        ), patch("asyncio.sleep", new_callable=AsyncMock):
            summary = await ingest_document(
                document_number="68/2020/QH14",
                article_lookup=article_lookup,
                domain="housing",
                qdrant=mock_qdrant,
                db=mock_db,
                dry_run=False,
                generate_summaries=True,
                llm=mock_llm,
            )

        # Chunk must still be ingested despite bad JSON
        assert summary["chunks_ingested"] == 1
        upserted = mock_qdrant.upsert.call_args[0][0]
        assert upserted[0]["structured_summary"] is None

    @pytest.mark.asyncio
    async def test_llm_not_called_in_dry_run_without_generate_summaries(self):
        """In dry-run without --generate-summaries, LLMService.async_invoke must not be called."""
        from ingestion.ingest_legal_docs import build_article_lookup, ingest_document

        article_lookup = build_article_lookup(SAMPLE_CONFIG)
        raw_chunks = [
            {
                "article_number": "Điều 20",
                "document_number": "68/2020/QH14",
                "content": "Công dân có quyền đăng ký.",
                "char_count": 26,
                "chapter_heading": None,
            }
        ]

        mock_llm = AsyncMock()
        mock_llm.async_invoke = AsyncMock(return_value="{}")

        with patch(
            "ingestion.ingest_legal_docs.parse_chunks_from_pdf",
            return_value=raw_chunks,
        ):
            await ingest_document(
                document_number="68/2020/QH14",
                article_lookup=article_lookup,
                domain="housing",
                qdrant=None,
                db=None,
                dry_run=True,
                generate_summaries=False,
                llm=mock_llm,
            )

        mock_llm.async_invoke.assert_not_called()
