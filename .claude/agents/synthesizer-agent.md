# Synthesizer Agent — Behavioural Specification

## Node: `synthesizer_node`
## File: `app/agents/nodes/synthesizer.py`
## Prompt: `app/agents/prompts/synthesis_prompt.py`

---

## Role

`synthesizer_node` is a **true LangGraph graph node** — the last node before END.
It is NOT a worker function and is NOT in `NODE_REGISTRY`.
It is NOT called by `plan_executor`.

It receives the fully accumulated `AgentState` after all worker functions have run
and produces the `final_response` string that streams to the frontend.

It is the **only node** in the pipeline that makes an LLM call for response generation.
It is the **only node** whose output goes to the frontend via SSE.

---

## Inputs (reads, never mutates)

| Key | Source |
|-----|--------|
| `errors` | Accumulated from all nodes |
| `plan_cursor` | Set by `plan_executor_node` |
| `form_fill_complete` | Set by `form_filler_fn` |
| `unfilled_required_fields` | Set by `form_filler_fn` |
| `filled_form_path` | Set by `form_filler_fn` |
| `retrieved_chunks` | Set by `rag_fn` |
| `final_response` | Set by `rag_fn` (contains inline-cited legal answer) |
| `response_metadata` | Partial dict from `rag_fn` |
| `scope_used` | Set by `rag_fn` (scope code that produced results) |
| `filing_jurisdiction` | Loaded from Redis `SessionData` at graph entry |
| `procedure_execution_plan` | Set by `procedure_planner_fn` via `enrichment_node` |
| `conversation_history` | Trimmed to 6 turns — loaded from Redis |
| `user_message` | Set at graph entry |
| `domain` | Set by `router_node` |

---

## Outputs (partial AgentState dict)

Only two keys are returned. Nothing else is written to state.

```python
{
    "final_response": str,          # complete user-facing message
    "response_metadata": {
        "mode": str,                # one of the six mode name strings
        "scope_used": str | None,   # scope code that produced RAG results
        "scope_notice_included": bool,
        "rag_confidence": str | None,  # "high" | "medium" | "low" | None
    },
}
```

Raw state fields, chunk lists, error internals, MinIO paths, and internal score
values are **never** returned directly — they are summarised in the LLM response
or omitted entirely.

---

## Six Response Modes

Modes are evaluated in **priority order**. The first matching condition wins.

### Priority 1 — error
**Condition:** `state["errors"]` is non-empty.

Always evaluated first regardless of what else is in state. Even if chunks were
retrieved successfully, a non-empty errors list means something failed upstream.

LLM call: **yes** (to produce a polite Vietnamese apology).
Prompt task: summarise what went wrong in plain language; never expose raw error
strings or Python tracebacks; suggest retry or support contact.

### Priority 2 — circuit_breaker
**Condition:** `state["plan_cursor"] >= MAX_PLAN_STEPS` AND `errors` is empty.

In practice `plan_executor` appends to `errors` when the circuit-breaker fires,
so this mode handles the edge case where the plan stalled with no explicit error.

LLM call: **yes**.
Prompt task: polite apology; suggest simpler question or support contact.
Do NOT expose `MAX_PLAN_STEPS` or internal step counts to the user.

### Priority 3 — form_fill_complete
**Condition:** `state["form_fill_complete"]` is `True`.

LLM call: **yes**.
Prompt task: confirm form is ready; mention procedure name if available;
do NOT expose MinIO path.
Scope notice: included if applicable.

### Priority 4 — form_fill_partial
**Condition:** `state["unfilled_required_fields"]` is non-empty.

LLM call: **yes**.
Prompt task: list each missing field by name in Vietnamese; ask user to provide;
do NOT ask for fields already filled.
Scope notice: included if applicable.

### Priority 5 — rag_only
**Condition:** `state["retrieved_chunks"]` is non-empty AND `form_fill_complete`
is False AND `unfilled_required_fields` is empty.

**LLM call optimisation:** when no scope notice is needed
(`scope_used == filing_jurisdiction` or either is `None`), the LLM call is
**skipped entirely** and `state["final_response"]` (already produced by `rag_fn`)
is returned directly. This saves a full token round-trip for the common case.

LLM call: **only when `include_scope_notice` is True**.
Prompt task (when LLM called): prepend scope notice naturally; pass through the
`rag_fn` response with citations intact; do NOT re-answer the legal question;
do NOT regenerate content that `rag_fn` already produced.
Scope notice: included if applicable.

### Priority 6 — fallback
**Condition:** none of the above matched. Handles greetings, unclassifiable
messages, and empty execution plans.

LLM call: **yes**.
Prompt task: polite greeting; explain three supported procedures (TTHC-001,
TTHC-002, TTHC-003); ask what the user needs help with.

---

## Scope Fallback Notice

Applies to modes 3, 4, and 5 only. Does NOT apply to error or fallback modes.

**Fallback occurred when:**
- `state["scope_used"]` is not `None`
- `state["filing_jurisdiction"]` is not `None`
- `state["scope_used"] != state["filing_jurisdiction"]`

When the fallback occurred, `include_scope_notice = True` and a Vietnamese
notice is woven into the response:
```
"Đang áp dụng quy định [scope_used_level] vì chưa tìm thấy quy định [filing_jurisdiction_level]."
```

### Scope code → Vietnamese level name mapping

```python
def _scope_level_name(scope_code: str) -> str:
    parts = scope_code.split("-")
    n = len(parts)
    if n == 1:
        return "cấp quốc gia"   # e.g. "VN"
    elif n == 2:
        return "cấp thành phố"  # e.g. "VN-HCM"
    else:
        return "cấp phường"     # e.g. "VN-HCM-26968"
```

The notice must be worded naturally in Vietnamese, not like a system alert.

---

## LLM Call Rules

- Always calls `LLMService.async_invoke()`, never `LLMService.stream()`.
  Streaming is handled at the API layer in TASK-11.
- Messages passed to the LLM: `conversation_history` (already trimmed to 6 turns
  by RedisService) + the current `user_message` as the final user turn.
  The full session history is never reconstructed inside this node.
- `MAX_TOKENS = 1024` for the synthesis call.
- The lazy singleton `_llm_svc` is created on first call via `_get_llm()`.
  Tests replace it with `patch("app.agents.nodes.synthesizer._get_llm", return_value=mock)`.

---

## Error Handling

If `LLMService.async_invoke()` raises any exception:
- Return the hardcoded Vietnamese fallback string:
  `"Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại sau."`
- Set `response_metadata["mode"] = "error"`.
- **Do not propagate the exception.** `synthesizer_node` must never raise.

---

## What Is NOT Streamed to the Frontend

- Raw `retrieved_chunks` list
- `errors` list contents (verbatim)
- MinIO paths (`filled_form_path`)
- Internal score values (`rrf_score`, etc.)
- Stack traces or Python exception messages
- LangGraph state keys or internal variable names

---

## Files

| File | Purpose |
|------|---------|
| `app/agents/nodes/synthesizer.py` | Node implementation |
| `app/agents/prompts/synthesis_prompt.py` | `build_synthesis_prompt(mode, context)` + `_scope_level_name()` |
| `tests/unit/test_synthesizer_node.py` | 8 unit tests (all LLM calls mocked) |

---

## Unit Test Inventory

| Test | Covers |
|------|--------|
| `test_synthesizer_error_mode` | Mode 1: errors list non-empty; LLM called |
| `test_synthesizer_form_fill_complete_mode` | Mode 3: form_fill_complete=True |
| `test_synthesizer_form_fill_partial_mode` | Mode 4: unfilled_required_fields non-empty |
| `test_synthesizer_rag_only_mode_no_scope_notice` | Mode 5: direct passthrough; LLM NOT called |
| `test_synthesizer_rag_only_mode_with_scope_notice` | Mode 5 with fallback: LLM IS called |
| `test_synthesizer_fallback_mode` | Mode 6: empty state → fallback |
| `test_synthesizer_scope_level_mapping` | `_scope_level_name()` pure unit test |
| `test_synthesizer_llm_failure_returns_hardcoded_fallback` | LLM exception → hardcoded string |
