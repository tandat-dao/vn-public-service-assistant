"""Diagnostic script: Issue A (Điều 14 adoption retrieval) + Issue C (Điều 20 khoản citation).

Run from backend/ directory:
    python scripts/run_fix_ac_diagnostic.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure backend/ is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings


# ===========================================================================
# TEST A1 — Điều 14 chunk existence in Qdrant
# ===========================================================================

async def test_a1_dieu14_existence():
    from app.services.qdrant_service import QdrantService

    qs = QdrantService()
    print("=== TEST A1: Điều 14 Chunk Existence ===\n")

    results, _ = await qs._client.scroll(
        collection_name=settings.QDRANT_COLLECTION,
        scroll_filter={
            "must": [
                {"key": "document_number", "match": {"value": "52/2010/QH12"}}
            ]
        },
        limit=300,
        with_payload=True,
        with_vectors=False,
    )

    chunks = results
    print(f"Total chunks from 52/2010/QH12: {len(chunks)}")

    # Find Điều 14 specifically — match on article_number
    dieu14_chunks = []
    for c in chunks:
        art = str(c.payload.get("article_number", ""))
        # Match plain "14", "Điều 14", "Điều 14 Khoản X"
        base = art.lstrip("Điều ").strip()
        # base now looks like "14", "14 Khoản 1", etc.
        if base == "14" or base.startswith("14 ") or base.startswith("14.") or art == "Điều 14":
            dieu14_chunks.append(c)

    print(f"Chunks with Điều 14 in article_number: {len(dieu14_chunks)}")

    if dieu14_chunks:
        for c in dieu14_chunks[:3]:
            print(f"\n  article_number: {c.payload.get('article_number')!r}")
            print(f"  content preview: {c.payload.get('content', '')[:200]!r}")
    else:
        print("\n  ⚠️  Điều 14 NOT FOUND in 52/2010/QH12 corpus")

    all_articles = sorted(set(c.payload.get("article_number", "") for c in chunks))
    print(f"\nAll article_numbers in 52/2010/QH12 ({len(all_articles)} unique):")
    print(f"  {all_articles}")

    return dieu14_chunks, all_articles, len(chunks)


# ===========================================================================
# TEST A2 — Direct Qdrant search for Điều 14
# ===========================================================================

async def test_a2_dieu14_retrieval():
    from app.services.qdrant_service import QdrantService

    qs = QdrantService()
    print("\n=== TEST A2: Direct Qdrant Search for Điều 14 ===\n")

    queries = [
        "điều kiện để nhận con nuôi trong nước",
        "điều kiện nhận con nuôi",
        "người nhận con nuôi phải đáp ứng",
    ]

    results_summary = []

    for query in queries:
        print(f"Query: '{query}'")
        chunks = await qs.search(
            query=query,
            procedure_id="TTHC-AD-001",
            scope="VN",
        )

        print(f"  Chunks returned: {len(chunks)}")

        dieu14_present = any(
            str(c.article_number).lstrip("Điều ").strip().split()[0] == "14"
            for c in chunks
        )
        print(f"  Điều 14 in results: {'YES ✓' if dieu14_present else 'NO ✗'}")

        if chunks:
            top3_articles = [c.article_number for c in chunks[:3]]
            top3_scores = [round(c.rrf_score, 6) for c in chunks[:3]]
            print(f"  Top 3 articles: {top3_articles}")
            print(f"  Top 3 RRF scores: {top3_scores}")
            # Print top 5 article numbers for full picture
            top5 = [(c.article_number, round(c.rrf_score, 6)) for c in chunks[:5]]
            print(f"  Top 5 (article, score): {top5}")
        else:
            print("  (no chunks returned)")
        print()

        results_summary.append((query, dieu14_present, [c.article_number for c in chunks[:5]]))

    return results_summary


# ===========================================================================
# TEST A3 — Router output for adoption query
# ===========================================================================

async def test_a3_router_adoption():
    from app.agents.nodes.router import router_node

    print("=== TEST A3: Router Output for Adoption Query ===\n")

    state = {
        "user_message": "Điều kiện để nhận con nuôi trong nước là gì?",
        "session_id": "diag-ad-001",
        "iteration_count": 0,
        "uploaded_image_path": None,
        "conversation_history": [],
        "execution_plan": [],
        "plan_cursor": 0,
        "entities": {},
        "retrieved_chunks": [],
        "citations": [],
        "personal_data": None,
        "document_type": None,
        "target_procedure_id": None,
        "procedure_execution_plan": [],
        "completed_procedures": [],
        "form_id": None,
        "filled_fields": {},
        "unfilled_required_fields": [],
        "final_response": "",
        "response_metadata": {},
        "errors": [],
        "domain": None,
        "filing_jurisdiction": None,
        "location_scope": None,
        "scope_used": None,
        "rag_returned_empty": False,
        "out_of_scope": False,
    }

    try:
        result = await router_node(state)

        print(f"intent: {result.get('intent')!r}")
        print(f"procedure_id: {result.get('procedure_id')!r}")
        print(f"target_procedure_id: {result.get('target_procedure_id')!r}")
        print(f"execution_plan: {result.get('execution_plan')!r}")
        print(f"domain: {result.get('domain')!r}")
        print(f"location_scope: {result.get('location_scope')!r}")
        print(f"out_of_scope: {result.get('out_of_scope')!r}")

        # Check if procedure_id is set correctly to TTHC-AD-001
        actual_procedure = result.get("target_procedure_id") or result.get("procedure_id")
        procedure_ok = actual_procedure == "TTHC-AD-001"
        print(f"\n{'✓' if procedure_ok else '✗'} procedure_id == TTHC-AD-001: {actual_procedure!r}")

        if not procedure_ok:
            print(
                f"  ⚠️  Router not setting TTHC-AD-001 — rag_fn will not filter by procedure"
            )

        return result, procedure_ok

    except Exception as exc:
        print(f"ERROR calling router_node: {exc}")
        import traceback; traceback.print_exc()
        return {}, False


# ===========================================================================
# TEST C1 — Điều 20 khoản citation verification (post-v3.56)
# ===========================================================================

async def test_c1_dieu20_citation():
    from app.services.qdrant_service import QdrantService
    from app.core.citation_formatter import verify_citations

    qs = QdrantService()
    print("=== TEST C1: Điều 20 Khoản Citation Verification (post-v3.56) ===\n")

    results, _ = await qs._client.scroll(
        collection_name=settings.QDRANT_COLLECTION,
        scroll_filter={
            "must": [
                {"key": "document_number", "match": {"value": "68/2020/QH14"}}
            ]
        },
        limit=300,
        with_payload=True,
        with_vectors=False,
    )

    chunks = results
    print(f"Total chunks from 68/2020/QH14: {len(chunks)}")

    # Find chunks whose article_number contains "20"
    dieu20_chunks = []
    for c in chunks:
        art = str(c.payload.get("article_number", ""))
        base = art.lstrip("Điều ").strip()
        # Match "20", "20 Khoản X", "Điều 20", "Điều 20 Khoản X"
        if base == "20" or base.startswith("20 ") or base.startswith("20.") or art == "Điều 20":
            dieu20_chunks.append(c)

    print(f"Điều 20 chunks found: {len(dieu20_chunks)}")

    article_number_formats = []
    for c in dieu20_chunks:
        art = c.payload.get("article_number", "")
        article_number_formats.append(art)
        print(f"\n  article_number: {art!r}")
        print(f"  content preview: {c.payload.get('content', '')[:150]!r}")

    print()

    # Build DocumentChunk-like objects from the raw Qdrant payloads for verify_citations
    class FakeChunk:
        def __init__(self, p):
            self.article_number = p.get("article_number", "")
            self.document_number = p.get("document_number", "")
            self.content = p.get("content", "")

    all_68_chunks = [FakeChunk(c.payload) for c in chunks]

    # Test citation strings against all Điều 20 chunks from 68/2020/QH14
    test_cases = [
        "[Điều 20, 68/2020/QH14]",
        "[Điều 20 Khoản 1, 68/2020/QH14]",
        "[Khoản 1, Điều 20, 68/2020/QH14]",
        "[Điều 20 Khoản 2, 68/2020/QH14]",
        "[Điều 20 Khoản 4, 68/2020/QH14]",
        "[Điều 20 Khoản 5, 68/2020/QH14]",
    ]

    print("Citation verification tests against all 68/2020/QH14 chunks in Qdrant:")
    citation_results = {}
    for citation_str in test_cases:
        test_response = f"Người đăng ký thường trú phải đáp ứng điều kiện theo {citation_str}"
        verified = verify_citations(test_response, all_68_chunks)
        passed = "[unverified:" not in verified
        status = "PASS ✓" if passed else "FAIL (unverified) ✗"
        print(f"  {citation_str}  →  {status}")
        citation_results[citation_str] = passed

    # Also try with only Điều 20 chunks
    print("\nCitation verification against ONLY Điều 20 chunks:")
    only_dieu20 = [FakeChunk(c.payload) for c in dieu20_chunks]
    for citation_str in test_cases:
        test_response = f"Người đăng ký thường trú phải đáp ứng điều kiện theo {citation_str}"
        verified = verify_citations(test_response, only_dieu20)
        passed = "[unverified:" not in verified
        status = "PASS ✓" if passed else "FAIL (unverified) ✗"
        print(f"  {citation_str}  →  {status}")

    return article_number_formats, citation_results


# ===========================================================================
# Main — run all tests + produce report
# ===========================================================================

async def main():
    print("=" * 60)
    print("DIAGNOSTIC: Fix A (Điều 14) + Fix C (Điều 20 Khoản)")
    print("=" * 60)
    print()

    # Run all 4 tests
    a1_dieu14_chunks, a1_all_articles, a1_total = await test_a1_dieu14_existence()
    a2_results = await test_a2_dieu14_retrieval()
    a3_result, a3_procedure_ok = await test_a3_router_adoption()
    c1_article_formats, c1_citation_results = await test_c1_dieu20_citation()

    # ===========================================================================
    # Report generation
    # ===========================================================================
    report_lines = []
    report_lines.append("=== DIAGNOSTIC REPORT: Fix A + Fix C ===\n")
    report_lines.append("--- ISSUE A: Điều 14 Retrieval ---\n")

    report_lines.append("Test A1: Chunk Existence")
    dieu14_exists = len(a1_dieu14_chunks) > 0
    report_lines.append(f"  Điều 14 exists in Qdrant: {'YES' if dieu14_exists else 'NO'}")
    report_lines.append(f"  Total chunks from 52/2010/QH12: {a1_total}")
    report_lines.append(f"  All article_numbers present: {a1_all_articles}")
    if a1_dieu14_chunks:
        report_lines.append(f"  Điều 14 chunk article_number format(s): {[str(c.payload.get('article_number')) for c in a1_dieu14_chunks]}")
    report_lines.append("")

    report_lines.append("Test A2: Direct Search")
    for query, found, top5 in a2_results:
        report_lines.append(f"  Query '{query}' returns Điều 14: {'YES' if found else 'NO'} — top articles: {top5}")
    report_lines.append("")

    report_lines.append("Test A3: Router Output")
    actual_proc = a3_result.get("target_procedure_id") or a3_result.get("procedure_id")
    report_lines.append(f"  procedure_id set correctly (TTHC-AD-001): {'YES' if a3_procedure_ok else 'NO'}")
    report_lines.append(f"  Actual value: {actual_proc!r}")
    report_lines.append(f"  intent: {a3_result.get('intent')!r}")
    report_lines.append(f"  execution_plan: {a3_result.get('execution_plan')!r}")
    report_lines.append("")

    # Root cause analysis for A
    report_lines.append("ROOT CAUSE A:")
    if a1_total == 0:
        root_cause_a = "1. 52/2010/QH12 not ingested at all — zero chunks in Qdrant"
    elif not dieu14_exists:
        root_cause_a = "1. Điều 14 chunk does not exist — 52/2010/QH12 produced no chunk for article 14"
    elif not any(found for _, found, _ in a2_results) and dieu14_exists:
        root_cause_a = "2. Điều 14 exists but is never ranked in top-16 (same flat-score problem as Hanoi / procedure filter issue)"
    elif not a3_procedure_ok:
        root_cause_a = "3. Router not setting TTHC-AD-001 — rag_fn retrieves wrong procedure's chunks"
    else:
        root_cause_a = "0. No root cause found — Điều 14 exists AND is retrieved AND router is correct"
    report_lines.append(f"  {root_cause_a}")
    report_lines.append("")

    # Additional diagnostic details for A
    report_lines.append("  Additional A details:")
    report_lines.append(f"  52/2010/QH12 total chunks: {a1_total}")
    if a1_total > 0:
        report_lines.append(f"  Article numbers in corpus: {a1_all_articles}")
    report_lines.append("")

    report_lines.append("--- ISSUE C: Điều 20 Khoản Citation Hover ---\n")

    report_lines.append("Test C1: Post-v3.56 State")
    report_lines.append(f"  Chunks with '20' in article_number: {len([f for f in c1_article_formats])}")
    report_lines.append(f"  article_number formats found: {c1_article_formats}")
    for citation_str, passed in c1_citation_results.items():
        report_lines.append(f"  {citation_str!r} verifies: {'PASS' if passed else 'FAIL'}")
    report_lines.append("")

    # Root cause analysis for C
    report_lines.append("ROOT CAUSE C:")

    # Determine which case applies
    dieu20_only_citation = c1_citation_results.get("[Điều 20, 68/2020/QH14]", False)
    dieu20_khoan1_citation = c1_citation_results.get("[Điều 20 Khoản 1, 68/2020/QH14]", False)
    khoan1_dieu20_citation = c1_citation_results.get("[Khoản 1, Điều 20, 68/2020/QH14]", False)
    khoan2_pass = c1_citation_results.get("[Điều 20 Khoản 2, 68/2020/QH14]", False)
    khoan4_pass = c1_citation_results.get("[Điều 20 Khoản 4, 68/2020/QH14]", False)
    khoan5_pass = c1_citation_results.get("[Điều 20 Khoản 5, 68/2020/QH14]", False)

    if not c1_article_formats:
        root_cause_c = "3. No Điều 20 chunks found in 68/2020/QH14 — document not ingested or Điều 20 not chunked"
    elif all(c1_citation_results.values()):
        root_cause_c = "1. ALREADY FIXED by v3.56 — all citation formats verify correctly"
    elif dieu20_only_citation and not dieu20_khoan1_citation:
        # Article-level works, khoản-level doesn't
        # Check if article_numbers are plain "20" vs "Điều 20 Khoản X"
        has_khoan_format = any("Khoản" in f for f in c1_article_formats)
        if has_khoan_format:
            root_cause_c = (
                "2. Citation format mismatch — v3.56 stored chunks as 'Điều X Khoản Y' format "
                "but khoản content check in verify_citations fails to find 'Khoản N' verbatim in content. "
                "Check whether content contains 'Khoản 1' literally or just '1. ...' numbered list."
            )
        else:
            root_cause_c = (
                "3. Chunk article_number still plain '20' — v3.56 khoản extraction didn't fire for Điều 20. "
                "Article-level citation passes but khoản-level verification fails due to missing khoản text in content."
            )
    elif not dieu20_only_citation:
        root_cause_c = (
            "4. Even Điều-only citation fails — article_number mismatch or document_number not found. "
            "Check chunk article_number format vs verifier normalisation."
        )
    else:
        # Some pass, some fail
        root_cause_c = (
            f"2. Partial khoản verification failure — Điều 20 base citation PASS, "
            f"Khoản 1: {'PASS' if dieu20_khoan1_citation else 'FAIL'}, "
            f"Khoản 2: {'PASS' if khoan2_pass else 'FAIL'}, "
            f"Khoản 4: {'PASS' if khoan4_pass else 'FAIL'}, "
            f"Khoản 5: {'PASS' if khoan5_pass else 'FAIL'}. "
            "Some khoản content not found verbatim in retrieved chunks."
        )

    report_lines.append(f"  {root_cause_c}")
    report_lines.append("")

    report_text = "\n".join(report_lines)
    print("\n" + "=" * 60)
    print(report_text)

    # Save to file
    out_path = Path("/home/claude/fix_ac_diagnostic.txt")
    # Windows fallback path
    win_out_path = Path(__file__).parent.parent / "scripts" / "fix_ac_diagnostic.txt"
    try:
        out_path.write_text(report_text, encoding="utf-8")
        print(f"Report saved to: {out_path}")
    except Exception:
        win_out_path.write_text(report_text, encoding="utf-8")
        print(f"Report saved to: {win_out_path}")

    return report_text


if __name__ == "__main__":
    asyncio.run(main())
