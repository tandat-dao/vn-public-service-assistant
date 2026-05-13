#!/usr/bin/env python3
"""DichVuCong AI Benchmark Evaluation.

Measures four metrics against a live running system:

  1. Router Accuracy       — intent, domain, procedure_id, location_scope
                             Dataset: datasets/router_accuracy.json (81 cases)
                             LLM calls: 1 per case (router only)

  2. Document Retrieval    — Recall@5 / Recall@10 / Recall@24
     Recall@k               Dataset: datasets/retrieval_recall.json (52 cases:
                             42 filtered + 10 unfiltered)
                             LLM calls: 0 (pure Qdrant hybrid search)

  3. Citation Faithfulness — verified_citations / total_citations in LLM response
                             Dataset: datasets/retrieval_recall.json (52 cases)
                             LLM calls: 2 per case (router + RAG generation)
                             Tip: set ROUTER_LLM_BACKEND=local in .env to use
                             Ollama for the router and save Anthropic API calls.
                             Only RAG generation then uses the cloud LLM.

  4. Latency Baseline      — end-to-end p50/p95 by query type
                             LLM calls: 2 per query (router + RAG)

Requirements:
  - Backend running:  uvicorn app.main:app --host 0.0.0.0 --port 8000
  - Docker services:  docker compose up -d  (Postgres, Redis, Qdrant, MinIO)
  - API key set:      ANTHROPIC_API_KEY in .env  (or GEMINI_API_KEY)
  - For local router: Ollama running + ROUTER_LLM_BACKEND=local in .env

Usage (from backend/ directory):
    # Run all four metrics
    python scripts/benchmark/run_benchmark.py

    # Run a single metric
    python scripts/benchmark/run_benchmark.py --metric router
    python scripts/benchmark/run_benchmark.py --metric citations
    python scripts/benchmark/run_benchmark.py --metric faithfulness
    python scripts/benchmark/run_benchmark.py --metric latency

    # Target a non-default backend
    python scripts/benchmark/run_benchmark.py --backend http://localhost:8000

    # Label a comparison run (appended to report filename)
    python scripts/benchmark/run_benchmark.py --metric router --backend-label anthropic
    python scripts/benchmark/run_benchmark.py --metric router --backend-label local

Output:
    scripts/benchmark/reports/benchmark_YYYYMMDD_HHMMSS.json
    scripts/benchmark/reports/benchmark_YYYYMMDD_HHMMSS.md
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
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

# Citation patterns for faithfulness parsing.
# verify_citations() in citation_formatter.py rewrites hallucinated citations to
# [unverified: ...] in the final_response before it reaches the SSE stream.
_CITATION_RE = re.compile(r'\[[^\]]+(?:/QH|/NĐ-|/NQ-|/TT-|/VBHN)[^\]]+\]')
_UNVERIFIED_RE = re.compile(r'\[unverified:[^\]]+\]')


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

async def call_rag_direct(
    client: httpx.AsyncClient,
    message: str,
    session_id: str,
    procedure_id: str | None = None,
    domain: str | None = None,
    location_scope: str | None = None,
) -> dict:
    """POST /api/v1/chat/rag_direct — bypasses router, single RAG LLM call, returns JSON.

    Used by the faithfulness benchmark to avoid paying for a router LLM call on
    every case.  procedure_id and domain come directly from the dataset so
    retrieval scope is correct without inference.

    Returns:
        {
            "response":    full generated text (verify_citations already applied),
            "scope_used":  scope code that produced results,
            "chunk_count": number of retrieved chunks,
            "elapsed_ms":  wall-clock time,
            "error":       error string if request failed,
        }
    """
    start = time.perf_counter()
    try:
        response = await client.post(
            f"{BASE_URL}/api/v1/chat/rag_direct",
            json={
                "message": message,
                "session_id": session_id,
                "procedure_id": procedure_id,
                "domain": domain,
                "location_scope": location_scope,
            },
            timeout=300.0,  # 5 min — covers both Anthropic API and Ollama on CPU
        )
        elapsed_ms = round((time.perf_counter() - start) * 1000)

        if response.status_code != 200:
            return {
                "response": "", "scope_used": None, "chunk_count": 0,
                "elapsed_ms": elapsed_ms,
                "error": f"HTTP {response.status_code}: {response.text[:200]}",
            }

        data = response.json()
        if data.get("error"):
            return {
                "response": "", "scope_used": None, "chunk_count": 0,
                "elapsed_ms": elapsed_ms,
                "error": data["error"],
            }

        return {
            "response": data.get("response", ""),
            "scope_used": data.get("scope_used"),
            "chunk_count": data.get("chunk_count", 0),
            "elapsed_ms": elapsed_ms,
            "error": None,
        }

    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000)
        return {
            "response": "", "scope_used": None, "chunk_count": 0,
            "elapsed_ms": elapsed_ms,
            "error": repr(exc) or type(exc).__name__,
        }


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
    top_k: int = 24,
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
    params: dict = {"q": query, "top_k": top_k}
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


_RECALL_K_VALUES = [5, 10, 24]


async def run_retrieval_recall(client: httpx.AsyncClient) -> dict:
    """Measure Document Retrieval Recall@k against ground truth (verified pairs only, Tier 2).

    Calls GET /api/v1/legal/search once per case at top_k=24, then computes
    Recall@5, Recall@10, and Recall@24 from the ordered result list — single
    API call per case, zero LLM calls.

    Filtered cases supply a procedure_id; unfiltered cases (procedure_id=null)
    search the full corpus. Both are reported separately.
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

    filtered_cases   = [c for c in verified_cases if c.get("procedure_id")]
    unfiltered_cases = [c for c in verified_cases if not c.get("procedure_id")]

    print(f"  Running {len(verified_cases)} verified cases "
          f"({len(filtered_cases)} filtered, {len(unfiltered_cases)} unfiltered) "
          f"— {len(all_cases) - len(verified_cases)} unverified skipped")

    # Accumulators: total[k] and found[k] across all cases, filtered, unfiltered
    total: dict[int, int] = {k: 0 for k in _RECALL_K_VALUES}
    found: dict[int, int] = {k: 0 for k in _RECALL_K_VALUES}
    total_f: dict[int, int] = {k: 0 for k in _RECALL_K_VALUES}
    found_f: dict[int, int] = {k: 0 for k in _RECALL_K_VALUES}
    total_u: dict[int, int] = {k: 0 for k in _RECALL_K_VALUES}
    found_u: dict[int, int] = {k: 0 for k in _RECALL_K_VALUES}

    results = []
    max_k = max(_RECALL_K_VALUES)

    for case in verified_cases:
        is_filtered = bool(case.get("procedure_id"))
        tag = "" if is_filtered else " [unfiltered]"
        print(f"  [{case['id']}]{tag} {case['query'][:50]}...", end=" ", flush=True)

        result = await call_search(
            client,
            case["query"],
            procedure_id=case.get("procedure_id"),
            top_k=max_k,
        )

        if result.get("error"):
            print(f"ERR: {result['error'][:60]}")
            results.append({"id": case["id"], "error": result["error"]})
            continue

        chunks: list[dict] = result["chunks"]
        case_found_at: dict[int, list[str]] = {k: [] for k in _RECALL_K_VALUES}
        case_missing_at_24: list[str] = []

        for expected_art, expected_doc in case["expected_citations"]:
            doc_lower = expected_doc.lower()
            for k in _RECALL_K_VALUES:
                docs_at_k = {c["document_number"].lower() for c in chunks[:k]}
                total[k] += 1
                if is_filtered:
                    total_f[k] += 1
                else:
                    total_u[k] += 1
                if doc_lower in docs_at_k:
                    found[k] += 1
                    case_found_at[k].append(f"{expected_art}, {expected_doc}")
                    if is_filtered:
                        found_f[k] += 1
                    else:
                        found_u[k] += 1
                elif k == max_k:
                    case_missing_at_24.append(f"{expected_art}, {expected_doc}")

        # Per-case status line: show result at each k
        k_badges = " ".join(
            f"@{k}:{'ok' if not [c for _, c in case['expected_citations'] if c.lower() not in {ch['document_number'].lower() for ch in chunks[:k]}] else 'X'}"
            for k in _RECALL_K_VALUES
        )
        status_24 = "ok" not in k_badges.split("@24:")[1][:2]  # True = fail at 24
        marker = "✗" if case_missing_at_24 else "✓"
        print(f"{marker} ({result['elapsed_ms']}ms)  {k_badges}"
              f"{'' if not case_missing_at_24 else f'  missing@24: {case_missing_at_24[:1]}'}")

        results.append({
            "id": case["id"],
            "query": case["query"],
            "found_at_24": case_found_at[max_k],
            "missing_at_24": case_missing_at_24,
            "retrieved_count": len(chunks),
        })

    def _recall(f: dict, t: dict, k: int) -> float:
        return f[k] / t[k] if t[k] > 0 else 0.0

    r24 = _recall(found, total, 24)
    r10 = _recall(found, total, 10)
    r5  = _recall(found, total, 5)

    metrics = {
        "retrieval_recall":    round(r24, 3),
        "recall_at_5":         round(r5, 3),
        "recall_at_10":        round(r10, 3),
        "recall_at_24":        round(r24, 3),
        "total_expected_citations": total[24],
        "total_found_citations":    found[24],
        "verified_cases_run":  len(verified_cases),
        "threshold":           threshold,
        "recall_pass":         r24 >= threshold,
        "llm_calls":           0,
    }

    print(f"\n  Recall@5:  {r5:.1%}  ({found[5]}/{total[5]})")
    print(f"  Recall@10: {r10:.1%}  ({found[10]}/{total[10]})")
    print(f"  Recall@24: {r24:.1%}  ({found[24]}/{total[24]})  "
          f"{'PASS' if metrics['recall_pass'] else 'FAIL'} (threshold {threshold:.0%})")

    if unfiltered_cases:
        r24_f = _recall(found_f, total_f, 24)
        r10_f = _recall(found_f, total_f, 10)
        r5_f  = _recall(found_f, total_f, 5)
        r24_u = _recall(found_u, total_u, 24)
        r10_u = _recall(found_u, total_u, 10)
        r5_u  = _recall(found_u, total_u, 5)
        print(f"\n  Filtered   ({len(filtered_cases)} cases):   "
              f"@5={r5_f:.1%}  @10={r10_f:.1%}  @24={r24_f:.1%}")
        print(f"  Unfiltered ({len(unfiltered_cases)} cases):  "
              f"@5={r5_u:.1%}  @10={r10_u:.1%}  @24={r24_u:.1%}")

    print(f"  LLM calls: 0  (pure Qdrant retrieval)")

    return {"metrics": metrics, "results": results}


# ---------------------------------------------------------------------------
# Metric 3: Citation Faithfulness
# ---------------------------------------------------------------------------

async def run_citation_faithfulness(client: httpx.AsyncClient) -> dict:
    """Measure LLM citation faithfulness — did the LLM cite only what it retrieved?

    Calls POST /api/v1/chat/rag_direct for each verified case in retrieval_recall.json.
    This bypasses the router entirely — procedure_id and domain are passed directly
    from the dataset so retrieval is correctly scoped without any router LLM call.

    verify_citations() runs server-side inside rag_fn and rewrites any citation not
    backed by a retrieved chunk to [unverified: ...].  This function counts those markers.

        faithfulness = verified_citations / (verified + unverified)

    Run twice with different RAG_LLM_BACKEND env values (anthropic vs local) to
    compare citation discipline between the cloud and local LLM paths.
    No router LLM calls — 1 RAG LLM call per case only.
    """
    print("\n=== METRIC 3: Citation Faithfulness  [1 RAG LLM call per case, no router] ===")

    dataset_path = DATASET_DIR / "retrieval_recall.json"
    if not dataset_path.exists():
        print(f"  ERROR: dataset not found at {dataset_path}")
        return {"metrics": {}, "results": []}

    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    all_cases = dataset["test_cases"]
    verified_cases = [c for c in all_cases if c.get("verified", False)]
    threshold = 0.80

    print(f"  Running {len(verified_cases)} verified cases (router bypassed — 1 RAG LLM call each)")

    total_verified_cit = 0
    total_unverified_cit = 0
    cases_with_citations = 0
    cases_no_citations = 0
    results = []

    for case in verified_cases:
        print(f"  [{case['id']}] {case['query'][:55]}...", end=" ", flush=True)

        result = await call_rag_direct(
            client,
            case["query"],
            f"bench-faith-{uuid.uuid4().hex[:8]}",
            procedure_id=case.get("procedure_id"),
            domain=case.get("domain"),
            location_scope=case.get("location_scope"),
        )

        if result.get("error"):
            print(f"ERR: {result['error'][:60]}")
            results.append({"id": case["id"], "error": result["error"]})
            await asyncio.sleep(0.3)
            continue

        response_text: str = result["response"]

        # _CITATION_RE matches all brackets containing a Vietnamese doc identifier.
        # _UNVERIFIED_RE matches the subset rewritten by verify_citations().
        all_cit = _CITATION_RE.findall(response_text)
        unverified_cit = _UNVERIFIED_RE.findall(response_text)

        n_total = len(all_cit)
        n_unverified = len(unverified_cit)
        n_verified = n_total - n_unverified

        if n_total == 0:
            cases_no_citations += 1
            case_faithfulness = None
            print(f"– no citations ({result['elapsed_ms']}ms, {result['chunk_count']} chunks)")
        else:
            cases_with_citations += 1
            total_verified_cit += n_verified
            total_unverified_cit += n_unverified
            case_faithfulness = round(n_verified / n_total, 3)
            status = "✓" if n_unverified == 0 else "✗"
            print(
                f"{status} {case_faithfulness:.0%} "
                f"({n_verified}/{n_total} verified, {result['elapsed_ms']}ms)"
            )

        results.append({
            "id": case["id"],
            "query": case["query"],
            "total_citations": n_total,
            "verified_citations": n_verified,
            "unverified_citations": n_unverified,
            "faithfulness": case_faithfulness,
            "scope_used": result.get("scope_used"),
            "chunk_count": result.get("chunk_count", 0),
        })

        await asyncio.sleep(0.3)

    total_cit = total_verified_cit + total_unverified_cit
    aggregate = total_verified_cit / total_cit if total_cit > 0 else 0.0

    metrics = {
        "citation_faithfulness": round(aggregate, 3),
        "total_verified_citations": total_verified_cit,
        "total_unverified_citations": total_unverified_cit,
        "total_citations_seen": total_cit,
        "cases_with_citations": cases_with_citations,
        "cases_no_citations": cases_no_citations,
        "verified_cases_run": len(verified_cases),
        "threshold": threshold,
        "faithfulness_pass": aggregate >= threshold,
        "llm_calls": len(verified_cases),
    }

    print(
        f"\n  Citation faithfulness: {metrics['citation_faithfulness']:.1%}"
        f" ({'PASS' if metrics['faithfulness_pass'] else 'FAIL'},"
        f" threshold {threshold:.0%})"
    )
    print(
        f"  {cases_with_citations} cases produced citations, "
        f"{cases_no_citations} had none (excluded from aggregate)"
    )
    print(f"  RAG LLM calls: {len(verified_cases)}  (router calls: 0)")

    return {"metrics": metrics, "results": results}


# ---------------------------------------------------------------------------
# Metric 4: Latency Baseline
# ---------------------------------------------------------------------------

async def run_latency_baseline(client: httpx.AsyncClient) -> dict:
    """Measure end-to-end latency across representative query types."""
    print("\n=== METRIC 4: Latency Baseline ===")

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
        "",
        "---",
        "",
        "## 3. Citation Faithfulness  *(Tier 3 — LLM citation discipline)*",
        "",
        "| Metric | Value | Threshold | Status |",
        "|---|---|---|---|",
    ]

    faithfulness = all_results.get("citation_faithfulness", {}).get("metrics", {})

    if faithfulness:
        thresh = faithfulness.get("threshold", 0.8)
        lines += [
            f"| Citation faithfulness | {faithfulness.get('citation_faithfulness', 0):.1%} | {thresh:.0%} | "
            f"{'✅ PASS' if faithfulness.get('faithfulness_pass') else '❌ FAIL'} |",
            f"| Verified citations | {faithfulness.get('total_verified_citations', 0)} | | |",
            f"| Unverified (hallucinated) citations | {faithfulness.get('total_unverified_citations', 0)} | | |",
            f"| Cases with citations | {faithfulness.get('cases_with_citations', 0)} | | |",
            f"| Cases with no citations | {faithfulness.get('cases_no_citations', 0)} | | |",
            f"| LLM calls | {faithfulness.get('llm_calls', 0)} | | |",
        ]
    else:
        lines.append("*Not measured*")

    lines += [
        "",
        "> **Note:** Faithfulness = verified_citations / total_citations in LLM response.",
        "> `verify_citations()` runs server-side in `rag_fn` and rewrites hallucinated citations",
        "> to `[unverified: ...]` before the response reaches the SSE stream.",
        "> Run with `RAG_LLM_BACKEND=anthropic` and `RAG_LLM_BACKEND=local` to compare.",
        "",
        "---",
        "",
        "## 4. Latency Baseline",
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
        choices=["router", "citations", "faithfulness", "latency", "all"],
        default="all",
        help="Which metric to measure (default: all)",
    )
    parser.add_argument(
        "--backend",
        default="http://localhost:8000",
        help="Backend base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--backend-label",
        default="",
        help="Label appended to report filename for comparison runs, e.g. 'anthropic' or 'local'",
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

        if args.metric in ("faithfulness", "all"):
            all_results["citation_faithfulness"] = await run_citation_faithfulness(client)

        if args.metric in ("latency", "all"):
            all_results["latency"] = await run_latency_baseline(client)

    label = f"_{args.backend_label}" if args.backend_label else ""
    json_path = REPORTS_DIR / f"benchmark_{timestamp}{label}.json"
    md_path = REPORTS_DIR / f"benchmark_{timestamp}{label}.md"

    json_path.write_text(
        json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md_path.write_text(generate_report(all_results, timestamp), encoding="utf-8")

    print(f"\nReports written:")
    print(f"  {json_path}")
    print(f"  {md_path}")


if __name__ == "__main__":
    asyncio.run(main())
