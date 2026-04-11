"""Unit tests for app/core/jurisdiction.py.

expand_scope_hierarchy is pure Python with no infrastructure dependencies.
validate_scope_code is async and requires a DB session — tested with an AsyncMock.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from app.core.jurisdiction import expand_scope_hierarchy, validate_scope_code


# ---------------------------------------------------------------------------
# expand_scope_hierarchy — pure function tests
# ---------------------------------------------------------------------------

def test_expand_single_level():
    assert expand_scope_hierarchy("VN") == ["VN"]


def test_expand_two_levels():
    assert expand_scope_hierarchy("VN-HCM") == ["VN", "VN-HCM"]


def test_expand_three_levels():
    assert expand_scope_hierarchy("VN-HCM-070") == ["VN", "VN-HCM", "VN-HCM-070"]


def test_expand_ward_code():
    assert expand_scope_hierarchy("VN-HCM-26968") == [
        "VN",
        "VN-HCM",
        "VN-HCM-26968",
    ]


def test_expand_preserves_order_most_general_first():
    result = expand_scope_hierarchy("VN-HCM-26968")
    assert result[0] == "VN"
    assert result[-1] == "VN-HCM-26968"


def test_expand_returns_list_not_generator():
    result = expand_scope_hierarchy("VN-HCM-070")
    assert isinstance(result, list)


def test_expand_single_code_no_hyphen():
    result = expand_scope_hierarchy("VN")
    assert len(result) == 1


# ---------------------------------------------------------------------------
# validate_scope_code — async, uses DB mock
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validate_scope_code_returns_false_on_db_error():
    """validate_scope_code must return False on any exception — never raises."""
    mock_db = AsyncMock()
    mock_db.execute.side_effect = Exception("DB down")
    result = await validate_scope_code("VN-HCM-26968", mock_db)
    assert result is False


# ---------------------------------------------------------------------------
# Infrastructure-independence assertion
# ---------------------------------------------------------------------------

def test_expand_scope_hierarchy_has_no_infrastructure_imports():
    """expand_scope_hierarchy must be callable with zero setup.

    If this import works and the function call works, there are no hidden
    infrastructure dependencies in the function body.
    """
    # Already imported at module level — just call it
    result = expand_scope_hierarchy("VN-HCM-26968")
    assert len(result) == 3
