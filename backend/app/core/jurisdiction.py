"""Jurisdiction utilities — pure Python, zero infrastructure dependencies.

These functions are in app/core/ (Rule 5: no imports from services/, no DB
session, no HTTP calls). They must be importable and testable without any
running infrastructure.

Scope code format: "VN" | "VN-HCM" | "VN-HCM-26968"
  - Level 0 (national):  "VN"
  - Level 1 (province):  "VN-HCM"  (Thành phố Hồ Chí Minh)
  - Level 2 (ward/dist): "VN-HCM-{ward_code}"

The narrower geographic scope always takes precedence (Luật BHVBQPPL 2015,
Điều 156). expand_scope_hierarchy() returns the full ancestor chain so the
RAG retrieval layer can build an OR-filter covering all applicable scopes.
"""

from __future__ import annotations


def expand_scope_hierarchy(scope: str) -> list[str]:
    """Expand a scope code into its full ancestor chain, most-general first.

    Examples:
        "VN"           → ["VN"]
        "VN-HCM"       → ["VN", "VN-HCM"]
        "VN-HCM-070"   → ["VN", "VN-HCM", "VN-HCM-070"]
        "VN-HCM-26968" → ["VN", "VN-HCM", "VN-HCM-26968"]

    Pure Python. No DB call. No validation against administrative_units table.
    Called at query time by rag_fn before building the Qdrant jurisdiction filter.

    Args:
        scope: A hyphen-separated geographic scope code.

    Returns:
        A list of scope codes from the most-general ancestor to the given scope.
    """
    parts = scope.split("-")
    return ["-".join(parts[: i + 1]) for i in range(len(parts))]


async def validate_scope_code(scope: str, db) -> bool:
    """Check whether the leaf code of a scope string exists in administrative_units.

    This is an optional validation used at query time only. It is never called
    during ingestion (ingestion creates codes, not validates them).

    Args:
        scope: A scope code such as "VN-HCM-26968".
        db:    An active AsyncSession.

    Returns:
        True if the leaf administrative unit code exists, False otherwise.
        Never raises — returns False on any DB error.
    """
    try:
        from sqlalchemy import text

        leaf_code = scope.split("-")[-1]
        result = await db.execute(
            text("SELECT 1 FROM administrative_units WHERE code = :code"),
            {"code": leaf_code},
        )
        return result.scalar() is not None
    except Exception:
        return False
