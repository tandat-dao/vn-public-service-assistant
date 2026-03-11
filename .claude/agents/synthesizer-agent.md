# Synthesizer Agent — Behavioural Specification

## Node: `synthesizer_node`
## File: `app/agents/nodes/synthesizer.py`
## Prompt: `app/agents/prompts/synthesis_prompt.py`

## Responsibility
Assemble the final user-facing response from all upstream node outputs.
This is the terminal node — it always runs last and always produces `final_response`.

## Inputs (reads but does not modify)
- `retrieved_chunks`, `citations` — from rag_node
- `personal_data`, `document_type` — from ocr_node
- `procedure_execution_plan` — from procedure_planner_node
- `filled_fields`, `unfilled_required_fields` — from form_filler_node
- `errors` — accumulated list from all nodes
- `intent` — to shape response format

## Outputs (partial AgentState dict)
- `final_response: str` — complete user-facing message
- `response_metadata: dict` — structured data for frontend rendering (citations, plan, pdf_path)

## Response Format by Intent

**procedure_inquiry / dependency_check:**
Lead with plain-language summary → numbered execution plan steps →
blocked steps with reason → "Documents needed:" section if missing_documents is non-empty.

**legal_question:**
Direct answer first → inline citations as [Điều X, Decree YYY] for every factual claim →
confidence note if rag_confidence is "low".

**document_ocr:**
Confirm detected document type → list extracted fields with confidence levels →
explicitly flag fields with confidence < 0.7.

**form_fill:**
Confirm which form → list auto-filled fields → list each item in unfilled_required_fields
with a specific instruction → include MinIO download path.

## Error Transparency
If `state["errors"]` is non-empty, include a "Note:" section at the end listing what failed.
Never suppress errors — transparency is more important than clean output.

## Streaming Note
`final_response` is streamed token-by-token by the FastAPI route handler via SSE.
The synthesizer produces the full string — it does not stream internally.
`response_metadata` is sent as a final SSE event after the text stream completes.
