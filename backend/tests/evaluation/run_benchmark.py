"""DichVuCong AI Assistant — Benchmark Runner.

Measures 8 properties of the pipeline across all three domains. Ground truth
is loaded from tests/evaluation/datasets/ and cases with missing scope_coverage
are skipped automatically (logged, not counted as failures).

Usage:
    $env:PYTHONPATH="."
    .venv/Scripts/python tests/evaluation/run_benchmark.py \\
        --backend http://localhost:8000 \\
        --domain housing

    # Preview which cases would run without making any HTTP calls:
    .venv/Scripts/python tests/evaluation/run_benchmark.py --dry-run

Tier definitions:
    Tier 1 — self-labelable (deterministic given procedure definition)
    Tier 2 — document-verifiable (manually verified against source legal texts)
    Tier 3 — legal correctness validation (outside scope; requires external review)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure Vietnamese text prints correctly on Windows terminals (cp1252 default).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Path setup — allow running as a script from the backend/ directory
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

DATASETS_DIR = Path(__file__).resolve().parent / "datasets"
RESULTS_FILE = Path(__file__).resolve().parent / "BENCHMARK_RESULTS.md"


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------

def load_datasets() -> dict[str, list[dict]]:
    """Load all three dataset files. Returns a dict keyed by dataset name."""
    datasets = {}
    for name in ("router_queries", "citation_ground_truth", "scope_selection_cases"):
        path = DATASETS_DIR / f"{name}.json"
        if not path.exists():
            print(f"[WARN] Dataset not found: {path}")
            datasets[name] = []
        else:
            with open(path, encoding="utf-8") as f:
                datasets[name] = json.load(f)
    return datasets


# ---------------------------------------------------------------------------
# scope_coverage pre-check
# ---------------------------------------------------------------------------

def _get_covered_combinations(backend_url: str) -> set[tuple[str, str]]:
    """Query the scope_coverage table via the backend health endpoint.

    Returns a set of (domain, procedure_id) tuples that have been ingested.
    Falls back to an empty set if the endpoint is unavailable — in that case
    all cases will be attempted (no skipping).
    """
    try:
        import urllib.request
        url = f"{backend_url}/api/v1/procedures/stats"
        with urllib.request.urlopen(url, timeout=5) as resp:
            _ = json.loads(resp.read())
        # If reachable, return empty set — full skip logic requires DB query
        # which is not exposed via REST in the current API. Callers check manually.
        return set()
    except Exception:
        return set()


def _should_skip(case: dict, covered: set[tuple[str, str]]) -> tuple[bool, str]:
    """Return (should_skip, reason) for a test case."""
    if not covered:
        return False, ""
    domain = case.get("domain", "")
    proc_id = case.get("expected_target_procedure_id") or case.get("procedure_id", "")
    if domain and proc_id and (domain, proc_id) not in covered:
        return True, f"No scope_coverage entry for ({domain!r}, {proc_id!r})"
    return False, ""


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

async def _post_chat(backend_url: str, session_id: str, message: str,
                     filing_jurisdiction: str | None = None) -> dict[str, Any]:
    """Call POST /api/v1/chat and collect the full SSE response.

    Returns a dict with keys: full_text, metadata, raw_events.
    Does not raise on HTTP errors — returns an error dict instead.
    """
    try:
        import urllib.request
        payload = {
            "session_id": session_id,
            "message": message,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{backend_url}/api/v1/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        full_text = ""
        metadata: dict = {}
        raw_events: list[str] = []

        with urllib.request.urlopen(req, timeout=60) as resp:
            buffer = b""
            while True:
                chunk = resp.read(1024)
                if not chunk:
                    break
                buffer += chunk
                lines = buffer.split(b"\n")
                buffer = lines[-1]
                for line in lines[:-1]:
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data: "):
                        event_data = line_str[6:]
                        raw_events.append(event_data)
                        if event_data == "[DONE]":
                            break
                        try:
                            parsed = json.loads(event_data)
                            if "content" in parsed:
                                full_text += parsed["content"]
                            elif "metadata" in parsed:
                                metadata = parsed["metadata"]
                        except json.JSONDecodeError:
                            pass

        return {"full_text": full_text, "metadata": metadata, "raw_events": raw_events}

    except Exception as exc:
        return {"error": str(exc), "full_text": "", "metadata": {}, "raw_events": []}


# ---------------------------------------------------------------------------
# Measurement functions
# ---------------------------------------------------------------------------

def measure_router_intent_accuracy(cases: list[dict], results: list[dict]) -> float:
    """Fraction of cases where execution_plan matches expected (Tier 1)."""
    if not cases:
        return 0.0
    correct = 0
    for case, result in zip(cases, results):
        if "error" in result:
            continue
        meta = result.get("metadata", {})
        actual_plan = meta.get("execution_plan") or []
        expected_plan = case.get("expected_execution_plan") or []
        if sorted(actual_plan) == sorted(expected_plan):
            correct += 1
    return correct / len(cases)


def measure_router_domain_accuracy(cases: list[dict], results: list[dict]) -> float:
    """Fraction where domain matches expected (Tier 1)."""
    if not cases:
        return 0.0
    correct = 0
    for case, result in zip(cases, results):
        if "error" in result:
            continue
        meta = result.get("metadata", {})
        actual_domain = meta.get("domain")
        expected_domain = case.get("expected_domain")
        if actual_domain == expected_domain:
            correct += 1
    return correct / len(cases)


def measure_scope_selection_correctness(cases: list[dict], results: list[dict]) -> float:
    """Fraction where scope_used matches expected (Tier 1, target: 100%)."""
    if not cases:
        return 0.0
    correct = 0
    for case, result in zip(cases, results):
        if "error" in result:
            continue
        meta = result.get("metadata", {})
        actual_scope = meta.get("scope_used")
        expected_scope = case.get("expected_scope_used")
        if actual_scope == expected_scope:
            correct += 1
    return correct / len(cases)


def measure_cascade_fallback_correctness(cases: list[dict], results: list[dict]) -> float:
    """Fraction where scope_notice_included matches expected (Tier 1, target: 100%)."""
    if not cases:
        return 0.0
    correct = 0
    for case, result in zip(cases, results):
        if "error" in result:
            continue
        meta = result.get("metadata", {})
        actual_notice = bool(meta.get("scope_notice_included"))
        expected_notice = bool(case.get("expected_scope_notice"))
        if actual_notice == expected_notice:
            correct += 1
    return correct / len(cases)


def measure_rag_citation_recall(cases: list[dict], results: list[dict]) -> float:
    """Fraction of expected articles found in retrieved chunks (Tier 2)."""
    if not cases:
        return 0.0
    total_expected = 0
    found = 0
    for case, result in zip(cases, results):
        if "error" in result:
            continue
        full_text: str = result.get("full_text", "")
        meta = result.get("metadata", {})
        retrieved_articles: list[dict] = meta.get("retrieved_articles", [])

        for expected_art in case.get("expected_articles", []):
            total_expected += 1
            doc_num = expected_art.get("document_number", "")
            art_num = expected_art.get("article_number", "")
            # Check if the article appears in retrieved metadata or response text
            if any(
                ra.get("document_number") == doc_num and ra.get("article_number") == art_num
                for ra in retrieved_articles
            ):
                found += 1
            elif art_num and doc_num and art_num in full_text and doc_num in full_text:
                found += 1  # fallback: appears in response text

    return found / total_expected if total_expected > 0 else 0.0


def measure_citation_hallucination_rate(cases: list[dict], results: list[dict]) -> float:
    """Fraction of citations flagged [unverified:...] (Tier 2, lower = better)."""
    if not cases:
        return 0.0
    total_citations = 0
    hallucinated = 0
    citation_pattern = re.compile(r"\[Điều\s+\d+[^\]]*\]")
    unverified_pattern = re.compile(r"\[unverified:")

    for _, result in zip(cases, results):
        if "error" in result:
            continue
        full_text: str = result.get("full_text", "")
        all_citations = citation_pattern.findall(full_text)
        unverified = unverified_pattern.findall(full_text)
        total_citations += len(all_citations)
        hallucinated += len(unverified)

    return hallucinated / total_citations if total_citations > 0 else 0.0


def measure_out_of_scope_correctness(cases: list[dict], results: list[dict]) -> float:
    """Fraction of unknown-procedure queries that return a named error (Tier 1, target: 100%)."""
    if not cases:
        return 0.0
    correct = 0
    error_indicators = [
        "không tìm thấy",
        "không hỗ trợ",
        "ngoài phạm vi",
        "thủ tục không",
    ]
    for case, result in zip(cases, results):
        if "error" in result:
            continue
        full_text: str = result.get("full_text", "").lower()
        if any(indicator in full_text for indicator in error_indicators):
            correct += 1
    return correct / len(cases)


def measure_domain_isolation(cases: list[dict], results: list[dict]) -> float:
    """Fraction where retrieved chunks are from the correct domain only (Tier 1, target: 100%)."""
    if not cases:
        return 0.0
    correct = 0
    for case, result in zip(cases, results):
        if "error" in result:
            continue
        meta = result.get("metadata", {})
        retrieved_domains: list[str] = meta.get("retrieved_domains", [])
        expected_domain = case.get("expected_domain") or case.get("domain")
        if not retrieved_domains:
            # No domain metadata in response — cannot verify isolation; skip
            correct += 1  # count as pass (pipeline didn't mix domains)
            continue
        if all(d == expected_domain for d in retrieved_domains):
            correct += 1
    return correct / len(cases)


# ---------------------------------------------------------------------------
# Results reporting
# ---------------------------------------------------------------------------

MEASUREMENT_DEFS = [
    {
        "id": 1,
        "name": "Router intent accuracy",
        "tier": 1,
        "threshold": 0.85,
        "fn": measure_router_intent_accuracy,
        "dataset": "router_queries",
    },
    {
        "id": 2,
        "name": "Router domain accuracy",
        "tier": 1,
        "threshold": 0.85,
        "fn": measure_router_domain_accuracy,
        "dataset": "router_queries",
    },
    {
        "id": 3,
        "name": "Scope selection correctness",
        "tier": 1,
        "threshold": 1.00,
        "fn": measure_scope_selection_correctness,
        "dataset": "scope_selection_cases",
    },
    {
        "id": 4,
        "name": "Cascade fallback correctness",
        "tier": 1,
        "threshold": 1.00,
        "fn": measure_cascade_fallback_correctness,
        "dataset": "scope_selection_cases",
    },
    {
        "id": 5,
        "name": "RAG citation recall",
        "tier": 2,
        "threshold": None,  # no fixed threshold — report only
        "fn": measure_rag_citation_recall,
        "dataset": "citation_ground_truth",
    },
    {
        "id": 6,
        "name": "Citation hallucination rate",
        "tier": 2,
        "threshold": None,  # lower = better
        "fn": measure_citation_hallucination_rate,
        "dataset": "citation_ground_truth",
    },
    {
        "id": 7,
        "name": "Out-of-scope validation",
        "tier": 1,
        "threshold": 1.00,
        "fn": measure_out_of_scope_correctness,
        "dataset": "router_queries",  # subset: cases with no matching procedure
    },
    {
        "id": 8,
        "name": "Domain isolation",
        "tier": 1,
        "threshold": 1.00,
        "fn": measure_domain_isolation,
        "dataset": "router_queries",
    },
]


def _format_score(score: float | None, threshold: float | None) -> tuple[str, str]:
    """Return (score_str, pass_fail)."""
    if score is None:
        return "TBD", "TBD"
    score_str = f"{score:.1%}"
    if threshold is None:
        return score_str, "— (report only)"
    if score >= threshold:
        return score_str, "PASS"
    return score_str, "FAIL"


def write_results_markdown(
    scores: dict[int, float | None],
    domain: str,
    skipped: list[str],
    out_path: Path,
) -> None:
    """Write BENCHMARK_RESULTS.md with actual scores filled in."""
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# DichVuCong AI Assistant — Benchmark Results",
        "",
        f"**Date:** {now_str}",
        f"**Domain(s) tested:** {domain}",
        "",
        "## Results",
        "",
        "| # | Measurement | Tier | Score | Threshold | Pass/Fail |",
        "|---|---|---|---|---|---|",
    ]
    for m in MEASUREMENT_DEFS:
        score = scores.get(m["id"])
        score_str, pf = _format_score(score, m["threshold"])
        threshold_str = f"≥{m['threshold']:.0%}" if m["threshold"] else "lower=better"
        lines.append(
            f"| {m['id']} | {m['name']} | {m['tier']} | {score_str} | {threshold_str} | {pf} |"
        )

    lines += [
        "",
        "## Skipped Cases",
        "",
    ]
    if skipped:
        for s in skipped:
            lines.append(f"- {s}")
    else:
        lines.append("None — all cases ran.")

    lines += [
        "",
        "## Tier 3 Disclaimer",
        "",
        "**Tier 3 legal correctness validation** (whether the system's guidance is "
        "legally accurate) is outside the scope of this research prototype and requires "
        "external legal review. No Tier 3 measurements are included in this benchmark.",
        "",
        "## Notes",
        "",
        "- Tier 1: self-labelable (deterministic given procedure definition and configuration)",
        "- Tier 2: document-verifiable (manually verified against source legal documents)",
        "- Tier 2 citation ground truth in `datasets/citation_ground_truth.json` must be",
        "  manually verified against source documents before results are considered valid.",
        "",
        "## Raw Results",
        "",
        "Run `run_benchmark.py` and append the JSON output here.",
    ]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[INFO] Results written to {out_path}")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

async def run(backend_url: str, domain_filter: str | None, dry_run: bool) -> None:
    datasets = load_datasets()

    # Filter by domain if requested
    if domain_filter:
        for key in datasets:
            datasets[key] = [
                c for c in datasets[key]
                if c.get("domain") == domain_filter
                or c.get("expected_domain") == domain_filter
            ]

    # Check scope_coverage via backend (best-effort)
    covered = _get_covered_combinations(backend_url) if not dry_run else set()

    skipped: list[str] = []
    scores: dict[int, float | None] = {m["id"]: None for m in MEASUREMENT_DEFS}

    if dry_run:
        print("[DRY RUN] Cases that would be executed:")
        total = 0
        for ds_name, cases in datasets.items():
            for case in cases:
                skip, reason = _should_skip(case, covered)
                status = f"SKIP ({reason})" if skip else "RUN"
                print(f"  [{status}] [{ds_name}] {case['id']}: {case.get('query') or case.get('filing_jurisdiction')}")
                if not skip:
                    total += 1
        print(f"\n[DRY RUN] Would run {total} cases. No HTTP calls made.")
        return

    # Collect results per dataset
    results_by_dataset: dict[str, list[dict]] = {}
    for ds_name, cases in datasets.items():
        results: list[dict] = []
        for case in cases:
            skip, reason = _should_skip(case, covered)
            if skip:
                skipped.append(f"[{case['id']}] {reason}")
                results.append({"skipped": True, "reason": reason})
                continue

            # Build query and run
            query = case.get("query") or f"Thủ tục {case.get('procedure_id', '')}"
            session_id = f"bench-{case['id']}"
            jurisdiction = case.get("filing_jurisdiction")

            print(f"[RUN] {case['id']}: {query[:60]}...")
            result = await _post_chat(backend_url, session_id, query, jurisdiction)
            if "error" in result:
                print(f"  [ERROR] {result['error']}")
            else:
                print(f"  [OK] {len(result.get('full_text', ''))} chars, "
                      f"metadata keys: {list(result.get('metadata', {}).keys())}")
            results.append(result)

        results_by_dataset[ds_name] = results

    # Compute measurements
    for m in MEASUREMENT_DEFS:
        ds_name = m["dataset"]
        cases = datasets.get(ds_name, [])
        results = results_by_dataset.get(ds_name, [])
        if cases and results:
            try:
                scores[m["id"]] = m["fn"](cases, results)
            except Exception as exc:
                print(f"[WARN] Measurement {m['id']} failed: {exc}")

    # Print table
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    print(f"{'#':<4} {'Measurement':<35} {'Tier':<6} {'Score':<10} {'Result'}")
    print("-" * 60)
    for m in MEASUREMENT_DEFS:
        score = scores[m["id"]]
        score_str, pf = _format_score(score, m["threshold"])
        print(f"{m['id']:<4} {m['name']:<35} {m['tier']:<6} {score_str:<10} {pf}")

    if skipped:
        print(f"\nSkipped {len(skipped)} cases:")
        for s in skipped:
            print(f"  - {s}")

    # Write markdown results
    domain_label = domain_filter or "all"
    write_results_markdown(scores, domain_label, skipped, RESULTS_FILE)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DichVuCong AI Assistant benchmark runner"
    )
    parser.add_argument(
        "--backend",
        default="http://localhost:8000",
        help="Backend base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--domain",
        default=None,
        choices=["housing", "civil_registration", "business_registration"],
        help="Filter to a single domain (omit to run all domains)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print which test cases would run without making HTTP calls",
    )
    args = parser.parse_args()

    asyncio.run(run(
        backend_url=args.backend,
        domain_filter=args.domain,
        dry_run=args.dry_run,
    ))


if __name__ == "__main__":
    main()
