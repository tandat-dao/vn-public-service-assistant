# Router Agent — Behavioural Specification

## Node: `router_node`
## File: `app/agents/nodes/router.py`
## Prompt: `app/agents/prompts/router_prompt.py`

## Responsibility
Classify user intent and extract named entities. Route to the correct downstream node.
This node must never perform retrieval, generation, or any side effect.

## Inputs (read from AgentState)
- `user_message: str` — always present
- `uploaded_image_path: str | None` — presence changes routing

## Outputs (partial AgentState dict)
- `intent` — one of: `procedure_inquiry`, `document_ocr`, `form_fill`, `legal_question`, `dependency_check`
- `entities: dict` — extracted named entities (procedure names, document types, dates)
- `target_procedure_id: str | None` — UUID if a procedure was identified, else None

## Routing Table (implemented in `route_after_classification`)
This function is pure — no LLM calls, no state modification, no side effects.

| Condition | Route To |
|---|---|
| image present AND intent in (document_ocr, form_fill) | ocr_node |
| intent in (procedure_inquiry, dependency_check) | procedure_planner_node |
| intent == legal_question | rag_node |
| intent == form_fill AND no image | form_filler_node |
| fallback / unrecognised | rag_node |

## Constraints
- Must use `llm.with_structured_output(IntentClassification)` — not free-text parsing
- `route_after_classification` must be a named function — never a lambda
- If classification fails, default to `intent = "legal_question"` and append to `state["errors"]`
- Iteration guard: if `state["iteration_count"] > 5`, route to synthesizer_node with error
- Never route directly to synthesizer_node under normal operation
