# Form Filler Agent — Behavioural Specification

## Node: `form_filler_node`
## File: `app/agents/nodes/form_filler.py`
## Prompt: `app/agents/prompts/form_mapping_prompt.py`

## Responsibility
Map PersonalData fields to a PDF form's field names, populate the PDF, upload to MinIO.
This node calls `form_field_mapper` (core), `pdf_service`, and `storage_service`.

## Inputs (read from AgentState)
- `form_id: str` — the FormTemplate UUID
- `personal_data: PersonalData | None`
- `session_id: str`

## Outputs (partial AgentState dict)
- `filled_fields: dict[str, str]` — field_name → filled value
- `unfilled_required_fields: list[str]` — required fields that could not be filled
- `response_metadata["filled_pdf_path"]: str` — MinIO path to the generated PDF

## Processing Pipeline
1. Load FormTemplate from DB (fields + pdf_template_path)
2. Download PDF template from MinIO
3. Call `form_field_mapper.map_fields(personal_data, form_template.fields)` — LLM-driven
4. Apply `manual_overrides` from state (user corrections always win)
5. Call `pdf_service.fill(template_path, field_values)` — auto-detects AcroForm vs overlay
6. Upload filled PDF to MinIO at `filled/{session_id}/{form_id}.pdf`
7. Populate `unfilled_required_fields` with any required field that has no mapped value

## Critical Constraints
- NEVER hard-code a mapping from PersonalData fields to form field names
- If `personal_data` is None, ALL required fields go to `unfilled_required_fields`
  and a blank PDF is still generated — this is not an error state
- `manual_overrides` always override LLM-mapped values
- Filled PDF MUST be uploaded to MinIO — never return a local file path
- A form that silently leaves required fields empty is worse than explicit `unfilled_required_fields`

## Error Handling
On PDF fill failure: append to `state["errors"]`, return empty `filled_fields`. Do not crash.
