"""Unit tests for _split_phu_luc() in ingestion/ingest_full_documents.py."""

from __future__ import annotations


class TestSplitPhuLuc:
    def test_phu_luc_split_when_present(self):
        """Content with \\nPHỤ LỤC produces 2 chunks; second has article_number='Phụ lục'."""
        from ingestion.ingest_full_documents import _split_phu_luc

        content = (
            "Điều 5 Khoản 2. Hiệu lực thi hành.\n"
            "Nghị quyết này có hiệu lực kể từ ngày 01 tháng 01 năm 2026.\n"
            "\nPHỤ LỤC\n"
            "MỨC THU LỆ PHÍ HỘ TỊCH ÁP DỤNG TẠI ỦY BAN NHÂN DÂN CẤP XÃ\n"
            "STT Nội dung Mức thu\n"
            "1 Khai sinh không đúng hạn 5.000\n"
            "2 Đăng ký kết hôn 30.000\n"
        )
        base_metadata = {"khoan_number": "2"}

        result = _split_phu_luc(content, "5", base_metadata)

        assert len(result) == 2, f"Expected 2 chunks, got {len(result)}"

        pre_chunk = result[0]
        assert pre_chunk["article_number"] == "5"
        assert "PHỤ LỤC" not in pre_chunk["content"]
        assert pre_chunk["khoan_number"] == "2"

        phu_luc_chunk = result[1]
        assert phu_luc_chunk["article_number"] == "Phụ lục"
        assert "5.000" in phu_luc_chunk["content"]
        assert phu_luc_chunk["khoan_number"] == "2"

    def test_phu_luc_not_split_when_absent(self):
        """Content without PHỤ LỤC returns empty list (original chunk preserved by caller)."""
        from ingestion.ingest_full_documents import _split_phu_luc

        content = (
            "Điều 3 Khoản 3. Mức thu lệ phí hộ tịch.\n"
            "Mức thu lệ phí hộ tịch theo Phụ lục đính kèm nghị quyết này.\n"
        )
        base_metadata = {"khoan_number": "3"}

        result = _split_phu_luc(content, "3", base_metadata)

        assert result == [], f"Expected empty list when no PHỤ LỤC boundary, got {result}"

    def test_phu_luc_short_pre_content_discarded(self):
        """Pre-PHỤ LỤC portion under MIN_CHUNK_CHARS (80 chars) is not included in result."""
        from ingestion.ingest_full_documents import _split_phu_luc

        # Pre-content is only 30 chars — below the 80-char minimum
        content = (
            "Điều 5. Ngắn.\n"
            "\nPHỤ LỤC\n"
            "MỨC THU LỆ PHÍ HỘ TỊCH\n"
            "STT Nội dung Mức thu\n"
            "1 Khai sinh không đúng hạn 5.000\n"
            "2 Đăng ký kết hôn 30.000\n"
            "3 Nhận cha mẹ con 15.000\n"
        )
        base_metadata = {"khoan_number": None}

        result = _split_phu_luc(content, "5", base_metadata)

        # Should return exactly 1 chunk — just the Phụ lục chunk
        assert len(result) == 1, f"Expected 1 chunk (only Phụ lục), got {len(result)}"
        assert result[0]["article_number"] == "Phụ lục"
        assert "5.000" in result[0]["content"]
