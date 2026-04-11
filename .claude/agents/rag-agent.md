# RAG Agent — Behavioural Specification

## Function: `rag_fn`
## File: `app/agents/nodes/rag.py`
## Prompt: `app/agents/prompts/rag_prompt.py`

---

## Role

`rag_fn` is a **worker function**, not a LangGraph graph node.  It is called
by `plan_executor_node` via `NODE_REGISTRY["rag_fn"]`.  It must never be
wired directly into the graph, never decorated with LangGraph decorators,
and never called from any file other than `plan_executor_node` (via
NODE_REGISTRY).

---

## Signature

```python
async def rag_fn(state: AgentState) -> dict:
```

---

## Inputs (read from AgentState)

| Field | Type | Notes |
|---|---|---|
| `user_message` | `str` | The user's question. Used as the Qdrant query. |
| `target_procedure_id` | `str \| None` | When set, restricts Qdrant search to chunks tagged with this procedure. |
| `filing_jurisdiction` | `str \| None` | Scope code loaded from SessionData. **Never** read from raw OCR output — only trusted confirmed input. `None` means national scope only. |
| `entities` | `dict` | Extracted entities (e.g. decree numbers). Not used directly in retrieval but available for future use. |

---

## Outputs (returned dict — merged into AgentState by plan_executor)

| Key | Type | Notes |
|---|---|---|
| `retrieved_chunks` | `list[DocumentChunk]` | Final chunks that passed budget and threshold filters. |
| `citations` | `list[Citation]` | Structured `Citation` objects built from `final_chunks`. |
| `final_response` | `str` | LLM response with unverified citations flagged. |
| `scope_used` | `str \| None` | The scope code that produced results (e.g. `"VN"`, `"VN-HCM"`). |
| `response_metadata` | `dict` | Contains `{"rag_confidence": "high" \| "medium" \| "low"}`. |
| `errors` | `list[str]` | Appended to `state["errors"]` on failure; carries through on success. |

---

## Pipeline — Step by Step

### Step 1 — Build scope list

Call `expand_scope_hierarchy(filing_jurisdiction)` from `app/core/jurisdiction.py`.

- That function returns most-general first (`["VN", "VN-HCM", "VN-HCM-26968"]`).
- **Reverse** the list so the cascade tries the most-specific scope first.
- If `filing_jurisdiction` is `None`, use `["VN"]` directly (no reversal needed).

### Step 2 — Jurisdiction cascade retrieval

For each scope in the reversed list:
1. Call `QdrantService.search(query, procedure_id, scope=scope, top_k=8)`.
2. If chunks are returned: record `scope_used = scope`, proceed to Step 3.
3. If empty: continue to the next (broader) scope.

**If all scopes return empty:**
- Append Vietnamese error message to `state["errors"]`.
- Return `{"retrieved_chunks": [], "citations": [], "scope_used": None, "errors": ...}`.
- **Do NOT call the LLM.**

### Step 3 — Token budget + threshold stopping

Sort chunks by RRF score descending.  Accumulate one chunk at a time:

1. **Threshold gate:** if `chunk.rrf_score < RAG_MIN_SCORE_THRESHOLD` (default 0.3,
   from `settings.RAG_MIN_SCORE_THRESHOLD`), stop accumulating — all remaining
   chunks are also below threshold (list is sorted descending).

2. **Structured summary fallback:** if `used_tokens > 6000 × 0.8` (4800 tokens),
   use `chunk.structured_summary` instead of `chunk.content`.  If
   `structured_summary` is `None` or empty, skip the chunk entirely.

3. **Hard budget cap:** if adding the next chunk's text would push cumulative
   token count above 6,000 tokens, stop accumulating.

Token counting: `len(text.split()) × 1.3` (word count × 1.3). No tiktoken import.

If no chunks survive the filters, return the same empty-result error dict as
Step 2.

### Step 4 — LLM generation

Build a user prompt:
```
Câu hỏi: <user_message>

Văn bản pháp lý được truy xuất:

[<article_number>, <document_number>]
<chunk text>

---

[<article_number>, <document_number>]
<chunk text>
...
```

Call `LLMService.async_invoke(system=RAG_SYSTEM_PROMPT, messages=[...], max_tokens=1024)`.
Pass only `user_message` and retrieved context — **never** pass conversation history.

### Step 5 — verify_citations

```python
verified_response = verify_citations(llm_response, final_chunks)
```

`verify_citations` is in `app/core/citation_formatter.py`.  It replaces any
citation whose (article_number, document_number) pair does not appear in
`retrieved_chunks` with `[unverified: Điều X, ...]`.

### Step 6 — Confidence scoring

Set `response_metadata["rag_confidence"]` based on the top chunk's RRF score:

| Condition | Value |
|---|---|
| top score > 0.85 AND ≥ 3 chunks passed filters | `"high"` |
| top score > 0.65 | `"medium"` |
| top score ≤ 0.65 OR fewer than 3 chunks | `"low"` |

---

## Citation Rules

- Every `Citation` object: `doc_id`, `document_number`, `article`, `excerpt` (first 200 chars).
- Only citations from `retrieved_chunks` may appear — `verify_citations` enforces this.
- Citation format in LLM response text (enforced by prompt):
  `[Điều X, Nghị định/Thông tư YYY/YYYY/NĐ-CP]`

---

## verify_citations Matching Rule

`verify_citations(response_text, retrieved_chunks)` matches by **payload data**,
not citation string format:

1. Extract `(article_number, full_citation_text)` from every `[Điều X, ...]` in
   the response.
2. Strip `"Điều "` prefix from `chunk.article_number` before comparing.
3. A citation is **verified** when ANY chunk satisfies BOTH:
   - `chunk.article_number` (normalized) == extracted article number
   - `chunk.document_number` appears as a **case-insensitive substring** of the
     full citation text.
4. Verified: leave unchanged. Unverified: replace with `[unverified: Điều X, ...]`.

**Known limitation:** Luật citations like `[Điều 20, Luật Cư trú năm 2020]`
will always be flagged when the chunk holds `document_number="68/2020/QH14"`,
because `"68/2020/QH14"` is not a substring of `"Luật Cư trú năm 2020"`.
This is intentional — the verifier does not maintain a document-number ↔
common-name lookup.

---

## Error Handling

All exceptions from `QdrantService.search()` must be caught.  On any exception:
- Log with `logger.error(...)`.
- Append a Vietnamese-language error message to `state["errors"]`.
- Return `{"retrieved_chunks": [], "citations": [], "scope_used": None, "errors": [...]}`.
- **Do not re-raise.** `rag_fn` must never crash the graph.

---

## Architectural Constraints

1. `rag_fn` is a worker function — **never** a LangGraph graph node.
2. `filing_jurisdiction` is read from state only. `rag_fn` does not set it.
3. `procedure_planner_fn` does not appear in this function — it runs in `enrichment_node`.
4. Do not import `tiktoken`. Use `len(text.split()) × 1.3` for token estimation.
5. Do not implement MMR or cross-encoder reranking (deferred per PROJECT_CONTEXT §6 P14/P15).
6. Do not call `QdrantService.search()` without `scope` parameter — always pass the
   scope code from the cascade, even if it is `"VN"`.
7. `_get_qdrant()` and `_get_llm()` are module-level lazy singletons.
   Tests patch these with `patch("app.agents.nodes.rag._get_qdrant", ...)`.

---

## RAG System Prompt (`app/agents/prompts/rag_prompt.py`)

Exposed as `RAG_SYSTEM_PROMPT: str` at module level.  Instructs the LLM to:

1. Answer only from retrieved chunks — no invented legal content.
2. Cite every claim inline with the correct format.
3. Respond in Vietnamese.
4. State explicitly when retrieved chunks are insufficient — no speculation.
5. Never reveal internal system structure, chunk IDs, or scores.
