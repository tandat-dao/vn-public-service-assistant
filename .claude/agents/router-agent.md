# Router Agent — Behavioural Specification

## Node: `router_node`
## File: `app/agents/nodes/router.py`
## Prompt: `app/agents/prompts/router_prompt.py`

---

## Responsibility

Decompose every user message into an ordered `execution_plan: list[str]` and extract named entities. The Router is a **pure LLM classification step** — it must never call a database, Redis, Qdrant, or any other service. It must never perform retrieval or generation. Its sole output is a routing decision.

---

## Architecture Context

This node runs in the `plan_executor` loop topology:

```
Entry → router_node → enrichment_node → plan_executor (loop) → synthesizer_node → END
```

The Router produces `execution_plan` and `plan_cursor = 0`. `enrichment_node` runs unconditionally after the Router (handling procedure DAG resolution, with no LLM call). `plan_executor` then executes the plan.

---

## Inputs (read from AgentState)

| Field | Type | Notes |
|---|---|---|
| `user_message` | `str` | Always present — the raw user input |
| `uploaded_image_path` | `str \| None` | Presence changes routing — signals that an identity document image was uploaded |

---

## Output Contract

The node returns a **partial `AgentState` dict** with exactly these three keys:

```python
{
    "execution_plan": list[str],  # ordered list of worker function names
    "entities": dict[str, Any],   # extracted named entities (may be empty dict)
    "plan_cursor": int,           # always 0 — reset by Router on every invocation
}
```

### `execution_plan` — Valid Values

Valid entries are defined in `NODE_REGISTRY` (imported from `node_registry.py`):

| Value | Meaning |
|---|---|
| `"rag_fn"` | Retrieve relevant legal document chunks and generate a cited answer |
| `"ocr_fn"` | Extract `PersonalData` from the uploaded identity document image |
| `"form_filler_fn"` | Fill government PDF form fields using extracted `PersonalData` |

**`"procedure_planner_fn"` is explicitly NOT a valid `execution_plan` entry.** Procedure DAG resolution runs in `enrichment_node`, which is a separate unconditional graph node that runs before `plan_executor`. The Router never needs to schedule it.

### Ordering Rules

1. `ocr_fn` **must always precede** `form_filler_fn` when both are present. `form_filler_fn` depends on `PersonalData` produced by `ocr_fn`.
2. `rag_fn` may appear in any position relative to `ocr_fn`.
3. `router_node` post-processes the LLM output to enforce rule 1 before returning.

### Empty Plan Rule

`execution_plan = []` is **only valid** for messages that require none of: legal retrieval, OCR, or form filling. Examples: bare greetings ("Xin chào"), completely unclassifiable input. Any message expressing procedural intent, legal inquiry, or form fill intent must produce a non-empty plan.

---

## Classification Cases

| Message Type | `uploaded_image_path` | Expected `execution_plan` | Reasoning |
|---|---|---|---|
| Pure legal question ("Điều 20 Luật Cư trú quy định gì?") | None | `["rag_fn"]` | Needs legal retrieval + cited answer |
| Procedure inquiry ("Tôi muốn đăng ký thường trú") | None | `["rag_fn"]` | `enrichment_node` resolves the DAG; Router schedules `rag_fn` for the legal explanation |
| Procedure inquiry ("Đăng ký tạm trú cần giấy tờ gì?") | None | `["rag_fn"]` | Legal retrieval explains documentary requirements |
| Image uploaded, form fill intent | Set | `["ocr_fn", "form_filler_fn"]` | Extract data then fill form |
| Image uploaded, legal question | Set | `["ocr_fn", "rag_fn"]` | Extract data (for context) + answer legal question |
| Image uploaded, form fill + legal question | Set | `["ocr_fn", "rag_fn", "form_filler_fn"]` | Extract, answer, fill |
| Form fill intent, **no image** | None | `["rag_fn"]` | Cannot fill without OCR data; explain requirements instead |
| Greeting / unclassifiable ("Xin chào") | None | `[]` | No actionable intent |

---

## Prompt Contract (`router_prompt.py`)

- Defines `RouterOutput` Pydantic model: `execution_plan: list[str]`, `entities: dict[str, Any]`
- System prompt **imports and embeds** `VALID_PLAN_STEPS` from `node_registry.py` — never hardcodes step names as string literals in the prompt body
- Includes at least 6 few-shot examples covering the classification cases above
- Instructs the model to output **only valid JSON** matching `RouterOutput` with no preamble or explanation
- Defines `build_router_messages(user_message: str, has_image: bool) -> list[dict]`

---

## Error Handling

| Failure | Behaviour |
|---|---|
| LLM returns malformed JSON | Log the raw response at WARNING level; return fallback `{"execution_plan": ["rag_fn"], "entities": {}, "plan_cursor": 0}` — never raise to caller |
| LLM returns invalid step name | `router_node` raises `ValueError` immediately — this is a prompt drift bug, not a user error, and must be caught during development |
| LLM call network error | Propagate the exception — do not swallow infrastructure failures |

---

## Constraints

- **No service calls.** Router must not import or call `QdrantService`, `RedisService`, `OCRService`, or any DB session.
- **No retrieval, no generation.** The Router only classifies. The LLM call is purely for structured JSON extraction.
- `plan_cursor` is always `0` in the returned dict — it is reset on every Router invocation.
- Worker functions in `NODE_REGISTRY` must never appear in the Router's own logic — only in `VALID_PLAN_STEPS` for validation.
- `route_after_classification` from the old architecture is **removed** — routing is now determined entirely by `execution_plan` content, not by a separate routing function.
- All LLM calls in unit tests must be mocked — no real Anthropic API calls in `tests/unit/`.
