"""Unit tests for app.core.text_utils.strip_markdown."""

import pytest

from app.core.text_utils import strip_markdown


def test_strip_markdown_removes_headers():
    assert strip_markdown("## Tiêu đề") == "Tiêu đề"
    assert strip_markdown("# H1") == "H1"
    assert strip_markdown("### H3 text") == "H3 text"
    assert strip_markdown("## Điều kiện\nNội dung") == "Điều kiện\nNội dung"


def test_strip_markdown_removes_bold():
    assert strip_markdown("**text**") == "text"
    assert strip_markdown("Đây là **thông tin quan trọng** nhé.") == "Đây là thông tin quan trọng nhé."
    assert strip_markdown("__bold__") == "bold"


def test_strip_markdown_removes_bullets():
    result = strip_markdown("- item một\n- item hai")
    assert result == "item một\nitem hai"

    result = strip_markdown("* mục A\n* mục B")
    assert result == "mục A\nmục B"


def test_strip_markdown_preserves_numbered_lists():
    text = "1. Điều kiện thứ nhất\n2. Điều kiện thứ hai"
    assert strip_markdown(text) == text


def test_strip_markdown_preserves_citations():
    text = "Theo quy định [Điều 3, 06/2020/NQ-HĐND] thì lệ phí là 50.000 đồng."
    assert strip_markdown(text) == text

    text2 = "[Điều 15 Khoản 1, 60/2014/QH13] áp dụng cho trường hợp này."
    assert strip_markdown(text2) == text2


def test_strip_markdown_idempotent():
    text = "**bold** và ## header\n- bullet"
    once = strip_markdown(text)
    twice = strip_markdown(once)
    assert once == twice
