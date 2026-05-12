#!/usr/bin/env python3
"""DichVuCong AI Benchmark Evaluation.

Measures three metrics against a live running system:

  1. Router Accuracy  — intent, domain, procedure_id, location_scope
  2. Citation Recall  — expected articles appear in retrieved_sources
  3. Latency Baseline — end-to-end response time distribution

Requirements:
  - Backend running: cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
  - Docker Compose services running: docker compose up -d
  - Real LLM configured (ANTHROPIC_API_KEY or GEMINI_API_KEY in .env)

Usage (from backend/ directory):
    python scripts/benchmark/run_benchmark.py
    python scripts/benchmark/run_benchmark.py --metric router
    python scripts/benchmark/run_benchmark.py --metric citations
    python scripts/benchmark/run_benchmark.py --metric latency
    python scripts/benchmark/run_benchmark.py --backend http://localhost:8000

Output:
    scripts/benchmark/reports/benchmark_YYYYMMDD_HHMMSS.json
    scripts/benchmark/reports/benchmark_YYYYMMDD_HHMMSS.md
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

# Ensure Vietnamese text prints correctly on Windows terminals (cp1252 default).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: pip install httpx")
    sys.exit(1)

BASE_URL = "http://localhost:8000"
DATASET_DIR = Path(__file__).parent / "datasets"
REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

async def call_chat(
    client: httpx.AsyncClient,
    message: str,
    session_id: str,
    filing_jurisdiction: str | None = None,
) -> dict:
    """POST /api/v1/chat and parse the full SSE response.

    Returns:
        {
            "response":      full text (concatenated content chunks),
            "metadata":      metadata dict from the SSE metadata event,
            "elapsed_ms":    total wall-clock time in milliseconds,
            "error":         error string if request failed,
        }
    """
    start = time.perf_counter()
    payload: dict = {
        "message": message,
        "session_id": session_id,
        "citizen_id": session_id,
    }

    try:
        response = await client.post(
            f"{BASE_URL}/api/v1/chat",
            json=payload,
            headers={"Accept": "text/event-stream"},
            timeout=90.0,
        )
        elapsed_ms = round((time.perf_counter() - start) * 1000)

        if response.status_code != 200:
            return {
                "response": "",
                "metadata": {},
                "elapsed_ms": elapsed_ms,
                "error": f"HTTP {response.status_code}: {response.text[:200]}",
            }

        full_response = ""
        metadata: dict = {}

        for line in response.text.split("\n"):
            if not line.startswith("data: "):
                continue
            payload_str = line[6:]
            if payload_str == "[DONE]":
                break
            try:
                data = json.loads(payload_str)
                if "content" in data:
                    full_response += data["content"]
                if "metadata" in data:
                    metadata = data["metadata"]
            except json.JSONDecodeError:
                pass

        return {
            "response": full_response,
            "metadata": metadata,
            "elapsed_ms": elapsed_ms,
            "error": None,
        }

    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000)
        return {
            "response": "",
            "metadata": {},
            "elapsed_ms": elapsed_ms,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Metric 1: Router Accuracy
# ---------------------------------------------------------------------------

async def call_classify(
    client: httpx.AsyncClient,
    message: str,
    session_id: str,
) -> dict:
    """POST /api/v1/chat/classify — router only, zero downstream LLM calls.

    Returns:
        {
            "metadata":   dict with mode/domain/procedure_id/location_scope,
            "elapsed_ms": wall-clock time in milliseconds,
            "error":      error string if request failed,
        }
    """
    start = time.perf_counter()
    try:
        response = await client.post(
            f"{BASE_URL}/api/v1/chat/classify",
            json={"message": message, "session_id": session_id},
            timeout=120.0,  # Qwen on CPU can take 30-60s per inference for the long router prompt
        )
        elapsed_ms = round((time.perf_counter() - start) * 1000)

        if response.status_code != 200:
            return {
                "metadata": {},
                "elapsed_ms": elapsed_ms,
                "error": f"HTTP {response.status_code}: {response.text[:200]}",
            }

        data = response.json()
        metadata = {
            "mode": data.get("mode"),
            "domain": data.get("domain"),
            "target_procedure_id": data.get("procedure_id"),
            "location_scope": data.get("location_scope"),
        }
        return {"metadata": metadata, "elapsed_ms": elapsed_ms, "error": None}

    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000)
        # Use repr() — str(httpx.ReadTimeout) can be empty string (falsy), masking the error
        return {"metadata": {}, "elapsed_ms": elapsed_ms, "error": repr(exc) or type(exc).__name__}


async def run_router_accuracy(client: httpx.AsyncClient) -> dict:
    """Measure router classification accuracy against labeled test cases (Tier 1).

    Calls POST /api/v1/chat/classify instead of /api/v1/chat — zero RAG or
    generation LLM calls, ~10x faster per case.
    """
    print("\n=== METRIC 1: Router Accuracy  [0 generation LLM calls — router only] ===")

    dataset_path = DATASET_DIR / "router_accuracy.json"
    if not dataset_path.exists():
        print(f"  ERROR: dataset not found at {dataset_path}")
        return {"metrics": {}, "results": []}

    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = dataset["test_cases"]
    threshold = dataset.get("threshold", 0.80)

    correct_mode = correct_domain = correct_procedure = correct_scope = 0
    total = len(cases)
    results = []

    for case in cases:
        qid = case["id"]
        query = case["query"]
        expected = case["expected"]
        print(f"  [{qid}] {query[:55]}...", end=" ", flush=True)

        result = await call_classify(client, query, f"bench-{uuid.uuid4().hex[:8]}")

        if result.get("error") is not None:
            print(f"ERR: {result['error'][:80]}")
            results.append({"id": qid, "error": result["error"]})
            await asyncio.sleep(0.2)
            continue

        meta = result.get("metadata", {})
        actual = {
            "mode": meta.get("mode"),
            "domain": meta.get("domain"),
            "procedure_id": meta.get("target_procedure_id"),
            "location_scope": meta.get("location_scope"),
        }

        mode_ok = actual.get("mode") == expected.get("mode")
        domain_ok = actual.get("domain") == expected.get("domain")
        proc_ok = actual.get("procedure_id") == expected.get("procedure_id")
        scope_ok = actual.get("location_scope") == expected.get("location_scope")

        if mode_ok:
            correct_mode += 1
        if domain_ok:
            correct_domain += 1
        if proc_ok:
            correct_procedure += 1
        if scope_ok:
            correct_scope += 1

        status = "✓" if mode_ok else "✗"
        print(f"{status} mode={actual.get('mode')} ({result['elapsed_ms']}ms)")

        results.append({
            "id": qid,
            "query": query,
            "expected": expected,
            "actual": actual,
            "mode_correct": mode_ok,
            "domain_correct": domain_ok,
            "procedure_correct": proc_ok,
            "scope_correct": scope_ok,
        })

        await asyncio.sleep(0.1)

    metrics = {
        "mode_accuracy": round(correct_mode / total, 3),
        "domain_accuracy": round(correct_domain / total, 3),
        "procedure_accuracy": round(correct_procedure / total, 3),
        "location_scope_accuracy": round(correct_scope / total, 3),
        "total_cases": total,
        "threshold": threshold,
        "mode_pass": correct_mode / total >= threshold,
        "domain_pass": correct_domain / total >= threshold,
    }

    print(f"\n  Mode accuracy:      {metrics['mode_accuracy']:.1%}"
          f" ({'PASS' if metrics['mode_pass'] else 'FAIL'},"
          f" threshold {threshold:.0%})")
    print(f"  Domain accuracy:    {metrics['domain_accuracy']:.1%}"
          f" ({'PASS' if metrics['domain_pass'] else 'FAIL'})")
    print(f"  Procedure accuracy: {metrics['procedure_accuracy']:.1%}")
    print(f"  Scope accuracy:     {metrics['location_scope_accuracy']:.1%}")

    return {"metrics": metrics, "results": results}


# ---------------------------------------------------------------------------
# Metric 2: Citation Recall
# ---------------------------------------------------------------------------

async def call_search(
    client: httpx.AsyncClient,
    query: str,
    procedure_id: str | None = None,
) -> dict:
    """GET /api/v1/legal/search — pure Qdrant retrieval, zero LLM calls.

    Returns:
        {
            "chunks":     list of {article_number, document_number, score},
            "elapsed_ms": wall-clock time in milliseconds,
            "error":      error string if request failed,
        }
    """
    start = time.perf_counter()
    params: dict = {"q": query}
    if procedure_id:
        params["procedure_id"] = procedure_id

    try:
        response = await client.get(
            f"{BASE_URL}/api/v1/legal/search",
            params=params,
            timeout=30.0,
        )
        elapsed_ms = round((time.perf_counter() - start) * 1000)

        if response.status_code != 200:
            return {
                "chunks": [],
                "elapsed_ms": elapsed_ms,
                "error": f"HTTP {response.status_code}: {response.text[:200]}",
            }

        return {
            "chunks": response.json(),
            "elapsed_ms": elapsed_ms,
            "error": None,
        }

    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000)
        return {"chunks": [], "elapsed_ms": elapsed_ms, "error": str(exc)}


async def run_retrieval_recall(client: httpx.AsyncClient) -> dict:
    """Measure Document Retrieval Recall@k against ground truth (verified pairs only, Tier 2).

    Calls GET /api/v1/legal/search instead of POST /api/v1/chat — zero LLM
    calls per case. Evaluates source_found only: the expected document_number
    must appear in the retrieved chunks within top_k results.
    """
    print("\n=== METRIC 2: Document Retrieval Recall@k  [0 LLM calls — pure Qdrant] ===")

    dataset_path = DATASET_DIR / "retrieval_recall.json"
    if not dataset_path.exists():
        print(f"  ERROR: dataset not found at {dataset_path}")
        return {"metrics": {}, "results": []}

    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    all_cases = dataset["test_cases"]
    verified_cases = [c for c in all_cases if c.get("verified", False)]
    threshold = dataset.get("recall_threshold", 0.80)

    print(f"  Running {len(verified_cases)} verified cases "
          f"({len(all_cases) - len(verified_cases)} unverified skipped)")

    total_expected = total_found = 0
    results = []

    for case in verified_cases:
        print(f"  [{case['id']}] {case['query'][:55]}...", end=" ", flush=True)

        result = await call_search(
            client,
            case["query"],
            procedure_id=case.get("procedure_id"),
        )

        if result.get("error"):
            print(f"ERR: {result['error'][:60]}")
            results.append({"id": case["id"], "error": result["error"]})
            continue

        chunks: list[dict] = result["chunks"]
        retrieved_docs = {c["document_number"].lower() for c in chunks}

        found: list[str] = []
        missing: list[str] = []

        for expected_art, expected_doc in case["expected_citations"]:
            total_expected += 1
            if expected_doc.lower() in retrieved_docs:
                total_found += 1
                found.append(f"{expected_art}, {expected_doc}")
            else:
                missing.append(f"{expected_art}, {expected_doc}")

        status = "✓" if not missing else "✗"
        print(f"{status} ({result['elapsed_ms']}ms) "
              f"{'OK' if not missing else f'missing: {missing[:1]}'}")

        results.append({
            "id": case["id"],
            "query": case["query"],
            "found": found,
            "missing": missing,
            "retrieved_count": len(chunks),
        })

    recall = total_found / total_expected if total_expected > 0 else 0.0

    metrics = {
        "retrieval_recall": round(recall, 3),
        "total_expected_citations": total_expected,
        "total_found_citations": total_found,
        "verified_cases_run": len(verified_cases),
        "threshold": threshold,
        "recall_pass": recall >= threshold,
        "llm_calls": 0,
    }

    print(f"\n  Retrieval Recall@k: {metrics['retrieval_recall']:.1%}"
          f" ({'PASS' if metrics['recall_pass'] else 'FAIL'},"
          f" threshold {threshold:.0%})")
    print(f"  LLM calls: 0  (pure Qdrant retrieval)")

    return {"metrics": metrics, "results": results}


# ---------------------------------------------------------------------------
# Metric 3: Latency Baseline
# ---------------------------------------------------------------------------

async def run_latency_baseline(client: httpx.AsyncClient) -> dict:
    """Measure end-to-end latency across representative query types."""
    print("\n=== METRIC 3: Latency Baseline ===")

    queries = [
        ("housing_rag",  "Điều kiện đăng ký thường trú là gì?"),
        ("housing_rag",  "Hồ sơ đăng ký tạm trú gồm những gì?"),
        ("civil_rag",    "Lệ phí đăng ký khai sinh tại Hà Nội?"),
        ("civil_rag",    "Điều kiện cấp bản sao trích lục hộ tịch?"),
        ("adoption_rag", "Điều kiện nhận con nuôi trong nước?"),
        ("adoption_rag", "Hành vi bị cấm trong nuôi con nuôi?"),
        ("city_fee",     "Lệ phí đăng ký hộ tịch tại TP.HCM?"),
        ("city_fee",     "Lệ phí đăng ký khai sinh tại Đà Nẵng?"),
        ("out_of_scope", "Thời tiết hôm nay thế nào?"),
        ("housing_rag",  "Xác nhận thông tin cư trú cần gì?"),
    ] * 2  # 20 total queries

    print(f"  Running {len(queries)} queries...")

    latencies: list[int] = []
    by_type: dict[str, list[int]] = {}

    for query_type, query in queries:
        result = await call_chat(client, query, f"bench-lat-{uuid.uuid4().hex[:8]}")
        ms = result["elapsed_ms"]
        latencies.append(ms)
        by_type.setdefault(query_type, []).append(ms)

        status = "ERR" if result.get("error") else f"{ms}ms"
        print(f"  {query_type}: {status}")
        await asyncio.sleep(1.0)

    if not latencies:
        return {"metrics": {}}

    latencies_sorted = sorted(latencies)
    n = len(latencies_sorted)

    metrics = {
        "total_queries": n,
        "p50_ms":  latencies_sorted[n // 2],
        "p90_ms":  latencies_sorted[int(n * 0.9)],
        "p95_ms":  latencies_sorted[min(int(n * 0.95), n - 1)],
        "mean_ms": round(sum(latencies_sorted) / n),
        "min_ms":  min(latencies_sorted),
        "max_ms":  max(latencies_sorted),
        "by_type": {
            k: {"mean_ms": round(sum(v) / len(v)), "samples": len(v)}
            for k, v in by_type.items()
        },
    }

    print(f"\n  p50: {metrics['p50_ms']}ms  "
          f"p90: {metrics['p90_ms']}ms  "
          f"p95: {metrics['p95_ms']}ms")
    print(f"  mean: {metrics['mean_ms']}ms  "
          f"min: {metrics['min_ms']}ms  "
          f"max: {metrics['max_ms']}ms")

    return {"metrics": metrics}


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(all_results: dict, timestamp: str) -> str:
    """Generate a human-readable Markdown benchmark report."""
    router = all_results.get("router_accuracy", {}).get("metrics", {})
    citations = all_results.get("retrieval_recall", {}).get("metrics", {})
    latency = all_results.get("latency", {}).get("metrics", {})

    lines = [
        "# DichVuCong Benchmark Report",
        "",
        f"**Generated:** {timestamp}",
        "",
        "---",
        "",
        "## 1. Router Accuracy  *(Tier 1 — self-labelable)*",
        "",
        "| Metric | Value | Threshold | Status |",
        "|---|---|---|---|",
    ]

    if router:
        thresh = router.get("threshold", 0.8)
        lines += [
            f"| Mode accuracy | {router.get('mode_accuracy', 0):.1%} | {thresh:.0%} | "
            f"{'✅ PASS' if router.get('mode_pass') else '❌ FAIL'} |",
            f"| Domain accuracy | {router.get('domain_accuracy', 0):.1%} | {thresh:.0%} | "
            f"{'✅ PASS' if router.get('domain_pass') else '❌ FAIL'} |",
            f"| Procedure ID accuracy | {router.get('procedure_accuracy', 0):.1%} | — | — |",
            f"| Location scope accuracy | {router.get('location_scope_accuracy', 0):.1%} | — | — |",
            f"| Total test cases | {router.get('total_cases', 0)} | | |",
        ]
    else:
        lines.append("*Not measured*")

    lines += [
        "",
        "---",
        "",
        "## 2. Document Retrieval Recall@k  *(Tier 2 — document-verifiable, 0 LLM calls)*",
        "",
        "| Metric | Value | Threshold | Status |",
        "|---|---|---|---|",
    ]

    if citations:
        thresh = citations.get("threshold", 0.8)
        lines += [
            f"| Retrieval Recall@k | {citations.get('retrieval_recall', 0):.1%} | {thresh:.0%} | "
            f"{'✅ PASS' if citations.get('recall_pass') else '❌ FAIL'} |",
            f"| Expected citations | {citations.get('total_expected_citations', 0)} | | |",
            f"| Found citations | {citations.get('total_found_citations', 0)} | | |",
            f"| Verified cases run | {citations.get('verified_cases_run', 0)} | | |",
            f"| LLM calls | {citations.get('llm_calls', 0)} | | |",
        ]
    else:
        lines.append("*Not measured*")

    lines += [
        "",
        "> **Note:** Retrieval Recall@k checks whether the expected source document appears in top-k",
        "> Qdrant results. Covers only Tier 2 (document-verified) ground truth pairs.",
        "> LLM faithfulness (Tier 3) is outside research prototype scope.",
        "",
        "---",
        "",
        "## 3. Latency Baseline",
        "",
        "| Metric | Value |",
        "|---|---|",
    ]

    if latency:
        lines += [
            f"| p50 | {latency.get('p50_ms', 0)}ms |",
            f"| p90 | {latency.get('p90_ms', 0)}ms |",
            f"| p95 | {latency.get('p95_ms', 0)}ms |",
            f"| Mean | {latency.get('mean_ms', 0)}ms |",
            f"| Min | {latency.get('min_ms', 0)}ms |",
            f"| Max | {latency.get('max_ms', 0)}ms |",
            f"| Total queries | {latency.get('total_queries', 0)} |",
            "",
            "**By query type:**",
            "",
        ]
        for qt, stats in latency.get("by_type", {}).items():
            lines.append(f"- `{qt}`: {stats['mean_ms']}ms avg ({stats['samples']} samples)")
    else:
        lines.append("*Not measured*")

    lines += [
        "",
        "---",
        "",
        "*End of report*",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    parser = argparse.ArgumentParser(description="DichVuCong benchmark evaluation")
    parser.add_argument(
        "--metric",
        choices=["router", "citations", "latency", "all"],
        default="all",
        help="Which metric to measure (default: all)",
    )
    parser.add_argument(
        "--backend",
        default="http://localhost:8000",
        help="Backend base URL (default: http://localhost:8000)",
    )
    args = parser.parse_args()

    global BASE_URL
    BASE_URL = args.backend.rstrip("/")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"DichVuCong Benchmark — {timestamp}")
    print(f"Backend: {BASE_URL}")
    print(f"Datasets: {DATASET_DIR}")

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Health check
        try:
            r = await client.get(f"{BASE_URL}/health")
            print(f"Backend status: HTTP {r.status_code}")
        except Exception as exc:
            print(f"ERROR: Cannot reach backend at {BASE_URL}: {exc}")
            print("Start backend with: uvicorn app.main:app --host 0.0.0.0 --port 8000")
            return

        all_results: dict = {}

        if args.metric in ("router", "all"):
            all_results["router_accuracy"] = await run_router_accuracy(client)

        if args.metric in ("citations", "all"):
            all_results["retrieval_recall"] = await run_retrieval_recall(client)

        if args.metric in ("latency", "all"):
            all_results["latency"] = await run_latency_baseline(client)

    json_path = REPORTS_DIR / f"benchmark_{timestamp}.json"
    md_path = REPORTS_DIR / f"benchmark_{timestamp}.md"

    json_path.write_text(
        json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md_path.write_text(generate_report(all_results, timestamp), encoding="utf-8")

    print(f"\nReports written:")
    print(f"  {json_path}")
    print(f"  {md_path}")


if __name__ == "__main__":
    asyncio.run(main())
