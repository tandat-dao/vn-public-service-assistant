"""Diagnostic script: print Qdrant payload samples and diagnose verify_citations() failures.

Run from the backend/ directory:
    cd backend
    PYTHONPATH=. python scripts/diagnose_citations.py

Reads QDRANT_URL from environment (falls back to http://localhost:6333).
Does NOT require embeddings — only scrolls raw payloads.
"""

from __future__ import annotations

import io
import os
import re
import sys

# Force UTF-8 output on Windows (avoids cp1252 UnicodeEncodeError for Vietnamese chars)
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Qdrant connection (plain client, no app/ imports needed for scroll)
# ---------------------------------------------------------------------------

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import FieldCondition, Filter, MatchValue
except ImportError:
    print("ERROR: qdrant-client not installed. Run: pip install qdrant-client")
    sys.exit(1)

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
COLLECTION = os.environ.get("QDRANT_COLLECTION", "legal_documents")

client = QdrantClient(url=QDRANT_URL)

_COLLECTION_RESOLVED: list[str] = [COLLECTION]  # mutable so main() can override


def scroll_by_domain(domain: str, limit: int = 5) -> list[dict]:
    """Return up to `limit` chunks whose payload.domain == domain."""
    collection = _COLLECTION_RESOLVED[0]
    domain_filter = Filter(
        must=[FieldCondition(key="domain", match=MatchValue(value=domain))]
    )
    results, _ = client.scroll(
        collection_name=collection,
        scroll_filter=domain_filter,
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )
    return [{"id": str(p.id), "payload": p.payload or {}} for p in results]


def print_section_a() -> list[dict]:
    """Print raw payload samples for civil_registration, adoption, housing domains."""
    print("=" * 70)
    print("SECTION A — Raw payload samples")
    print("=" * 70)

    all_chunks: list[dict] = []

    for domain, limit in [
        ("civil_registration", 5),
        ("adoption", 5),
        ("housing", 3),
    ]:
        chunks = scroll_by_domain(domain, limit)
        print(f"\n--- domain={domain!r} ({len(chunks)} chunks fetched) ---")
        for item in chunks:
            payload = item["payload"]
            content = payload.get("content", "")
            print(f"  chunk_id: {item['id']}")
            print(f'  document_number: "{payload.get("document_number", "")}"')
            print(f'  article_number: "{payload.get("article_number", "")}"')
            print(f"  procedure_ids: {payload.get('procedure_tags', [])}")
            print(f"  location_scope: {payload.get('location_scope', '')}")
            print(f'  content_preview: "{content[:120]}"')
            print()
        all_chunks.extend(chunks)

    return all_chunks


# ---------------------------------------------------------------------------
# Inline citation verification — mirrors verify_citations() logic without importing it
# ---------------------------------------------------------------------------

_CITATION_RE = re.compile(
    r"\[(?P<article>"
    r"Điều\s+\d+[a-z]?(?:\s+Khoản\s+\d+[a-z]?)?"
    r"|"
    r"Khoản\s+\d+[a-z]?,\s*Điều\s+\d+[a-z]?"
    r"),\s*(?P<document>[^\]]+)\]",
    re.UNICODE,
)


def _parse_article_ref(article_str: str) -> tuple[str, str | None]:
    s = article_str.strip()
    m = re.match(r"(Điều\s+\d+[a-z]?)\s+(Khoản\s+\d+[a-z]?)\s*$", s)
    if m:
        return m.group(1), m.group(2)
    m = re.match(r"(Khoản\s+\d+[a-z]?),\s*(Điều\s+\d+[a-z]?)\s*$", s)
    if m:
        return m.group(2), m.group(1)
    return s, None


def _parse_citation_string(citation_str: str) -> tuple[str | None, str | None]:
    """Parse '[article, document]' into (article_ref, document_ref). Returns (None, None) on no match."""
    # Remove outer brackets for matching
    inner = citation_str.strip("[]")
    m = _CITATION_RE.match(citation_str)
    if m:
        return m.group("article"), m.group("document")
    return None, None


def verify_citation_against_chunks(citation_str: str, chunks: list[dict]) -> tuple[bool, str]:
    """
    Run inline citation verification against chunk payloads.
    Returns (verified: bool, reason: str).
    """
    m = _CITATION_RE.match(citation_str)
    if not m:
        return False, "Citation string did not match _CITATION_RE regex — cannot parse"

    article_str = m.group("article")
    base_article, khoan_ref = _parse_article_ref(article_str)
    base_article_num = re.sub(r"^Điều\s+", "", base_article).strip()

    full_lower = citation_str.lower()

    matching_chunk = None
    for item in chunks:
        payload = item["payload"]
        raw_article = payload.get("article_number", "")
        chunk_article_num = re.sub(r"^Điều\s+", "", raw_article).strip()
        chunk_doc_num = payload.get("document_number", "")

        article_match = chunk_article_num == base_article_num
        doc_match = chunk_doc_num.lower() in full_lower

        if article_match and doc_match:
            matching_chunk = item
            break

    if matching_chunk is None:
        # Diagnose which part failed
        article_candidates = []
        for item in chunks:
            payload = item["payload"]
            raw_article = payload.get("article_number", "")
            chunk_article_num = re.sub(r"^Điều\s+", "", raw_article).strip()
            if chunk_article_num == base_article_num:
                article_candidates.append(payload.get("document_number", ""))

        if article_candidates:
            reason = (
                f"Article-level match found (article={base_article_num!r}) "
                f"but document_number NOT a substring of citation. "
                f"Qdrant document_number(s) for this article: {article_candidates}. "
                f"Citation document text: {m.group('document')!r}. "
                f"Mismatch confirmed."
            )
        else:
            reason = (
                f"No chunk found with article_number={base_article_num!r} "
                f"in the fetched chunks. Article may be missing from Qdrant "
                f"OR not fetched in this scroll sample."
            )
        return False, reason

    if khoan_ref is None:
        return True, "Article-level match, no khoản in citation"

    content = matching_chunk["payload"].get("content", "")
    _MONEY_PATTERN = re.compile(r"\d[\d.].000\sđồng|đồng/")
    if khoan_ref in content:
        return True, f"Khoản reference {khoan_ref!r} found in chunk content"
    if _MONEY_PATTERN.search(content):
        return True, "Khoản-level: monetary pattern in content (fees table fallback)"

    return False, f"Khoản reference {khoan_ref!r} NOT found in chunk content"


def print_section_b(all_fetched_chunks: list[dict]) -> None:
    """Section B: run test citations through verify_citations logic."""
    print("=" * 70)
    print("SECTION B — Citation format test (inline verify_citations replay)")
    print("=" * 70)

    test_citations = [
        "[Điều 15 Khoản 1, Luật Hộ tịch năm 2014]",
        "[Điều 14 Khoản 1, Luật Nuôi con nuôi 2010]",
        "[Điều 14 Khoản 2, Luật Nuôi con nuôi 2010]",
        "[Điều 14 Khoản 3, Luật Nuôi con nuôi 2010]",
    ]

    # Also fetch targeted chunks for exact articles
    civil_chunks = scroll_by_domain("civil_registration", 50)
    adoption_chunks = scroll_by_domain("adoption", 50)
    all_target_chunks = civil_chunks + adoption_chunks

    print(
        f"\n(Fetched {len(civil_chunks)} civil_registration chunks + "
        f"{len(adoption_chunks)} adoption chunks for verification)\n"
    )

    for citation in test_citations:
        m = _CITATION_RE.match(citation)
        if m:
            article_str = m.group("article")
            base_article, khoan_ref = _parse_article_ref(article_str)
            base_article_num = re.sub(r"^Điều\s+", "", base_article).strip()
            print(f'citation: "{citation}"')
            print(f'  parsed: article="{base_article_num}", document="{m.group("document")}", khoan={khoan_ref!r}')
        else:
            print(f'citation: "{citation}"')
            print("  parsed: FAILED — regex did not match")

        verified, reason = verify_citation_against_chunks(citation, all_target_chunks)
        print(f"  verified: {verified}")
        print(f"  reason: {reason}")
        print()


def print_section_c(all_fetched_chunks: list[dict]) -> None:
    """Section C: side-by-side format comparison."""
    print("=" * 70)
    print("SECTION C — Document number format comparison")
    print("=" * 70)

    # Fetch all chunks so we can look up by article
    civil_chunks = scroll_by_domain("civil_registration", 50)
    adoption_chunks = scroll_by_domain("adoption", 50)
    all_chunks = civil_chunks + adoption_chunks

    # Build lookup: (article_num_stripped) -> set of document_numbers
    article_to_doc: dict[str, list[str]] = {}
    for item in all_chunks:
        payload = item["payload"]
        raw = payload.get("article_number", "")
        num = re.sub(r"^Điều\s+", "", raw).strip()
        doc = payload.get("document_number", "")
        if num not in article_to_doc:
            article_to_doc[num] = []
        if doc not in article_to_doc[num]:
            article_to_doc[num].append(doc)

    comparisons = [
        {
            "llm_format": "Luật Hộ tịch năm 2014",
            "article": "15",
            "domain": "civil_registration",
        },
        {
            "llm_format": "Luật Nuôi con nuôi 2010",
            "article": "14",
            "domain": "adoption",
        },
    ]

    for comp in comparisons:
        article_num = comp["article"]
        llm_doc_str = comp["llm_format"]
        qdrant_docs = article_to_doc.get(article_num, ["(not found in fetched chunks)"])

        print(f"\nArticle: Điều {article_num} (domain={comp['domain']})")
        print(f"  LLM format:    {llm_doc_str!r}")
        for qdrant_doc in qdrant_docs:
            is_substring = qdrant_doc.lower() in llm_doc_str.lower()
            print(f"  Qdrant stored: {qdrant_doc!r}")
            print(f"  Match (Qdrant doc_num substring of LLM text): {is_substring}")
            if not is_substring:
                print(
                    f"  → MISMATCH: verify_citations() looks for {qdrant_doc!r} "
                    f"as substring inside [{llm_doc_str}] — not found."
                )

    print()


def main() -> None:
    print(f"\nQdrant URL: {QDRANT_URL}")
    print(f"Collection: {COLLECTION}")

    # Check if collection exists
    try:
        collections = client.get_collections()
        names = [c.name for c in collections.collections]
        if COLLECTION not in names:
            print(f"\nWARNING: Collection '{COLLECTION}' not found.")
            print(f"Available collections: {names}")
            alt = "legal_chunks"
            if alt in names:
                print(f"Found '{alt}' — will use that instead.")
                _COLLECTION_RESOLVED[0] = alt
            else:
                print("No known collection found. Is Qdrant running?")
                sys.exit(1)
        else:
            info = client.get_collection(COLLECTION)
            print(f"Collection '{COLLECTION}': {info.points_count} points total\n")
    except Exception as exc:
        print(f"\nERROR connecting to Qdrant at {QDRANT_URL}: {exc}")
        sys.exit(1)

    all_fetched = print_section_a()
    print()
    print_section_b(all_fetched)
    print()
    print_section_c(all_fetched)

    print("=" * 70)
    print("Diagnostic complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()
