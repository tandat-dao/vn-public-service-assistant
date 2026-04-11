# Form Filler Agent — Behavioural Specification

## Function: `form_filler_fn`
## File: `app/agents/nodes/form_filler.py`
## Prompt: `app/agents/prompts/form_mapping_prompt.py`

> **This is a worker function, NOT a LangGraph graph node.**
> It is called by `plan_executor_node` via `NODE_REGISTRY["form_filler_fn"]`.
> Never add LangGraph decorators. Never put it in the graph topology directly.

---

## Responsibility

Merge the latest OCR extraction into the accumulated PersonalData, map fields to
a PDF form template via LLM-driven semantic matching, fill the PDF, and write it
to MinIO.  Returns the MinIO path and a list of any fields that could not be filled
so the Synthesizer can prompt the user for missing information.

---

## Inputs (read from AgentState)

| Field | Type | Description |
|---|---|---|
| `personal_data` | `PersonalData \| None` | Accumulated carry-forward PersonalData from prior turns |
| `extracted_personal_data` | `PersonalData \| None` | Latest OCR output not yet merged |
| `target_procedure_id` | `str \| None` | Procedure code used to look up the form template |
| `session_id` | `str` | Used to construct the MinIO `tmp/` and `forms/` paths |
| `errors` | `list[str]` | Existing errors list (appended to on failure) |

---

## Outputs (partial AgentState dict)

| Key | Type | Description |
|---|---|---|
| `personal_data` | `PersonalData \| None` | Merged effective PersonalData |
| `filled_form_path` | `str \| None` | MinIO path to the filled PDF (tmp or final) |
| `unfilled_required_fields` | `list[str]` | Form field names that could not be filled |
| `form_fill_complete` | `bool` | `True` only when all required fields filled and PDF promoted |
| `errors` | `list[str]` | Populated on failure; absent on success |

---

## Processing Pipeline

### Step 1 — Merge OCR data
Call `SessionDataAccumulator().merge(state["personal_data"], state["extracted_personal_data"])`.
The result is `effective_personal_data`.

- If `effective_personal_data is None` (both inputs were None): append Vietnamese error
  `"Không có dữ liệu cá nhân để điền vào biểu mẫu."` and return immediately — do NOT
  proceed to PDF fill.

### Step 2 — Look up template path
Look up `PROCEDURE_TEMPLATE_PATHS[target_procedure_id]`.

- If no template exists: append `"Không tìm thấy mẫu biểu cho thủ tục này."` and return.

### Step 3 — Get form field names
Look up `PROCEDURE_FORM_FIELDS[target_procedure_id]`.

> **TODO (TASK-15):** Replace with `PDFService.get_form_fields(template_path)` once
> real PDF templates are collected.  Currently hardcoded for TTHC-001/002/003.

### Step 4 — Map PersonalData to form fields
Instantiate `FormFieldMapper(llm_service=_get_llm_svc())` and call `map()`.

`FormFieldMapper` calls the LLM only on the first encounter of a (form_id, field-list)
pair.  All subsequent calls for the same form reuse the cached structural mapping.
The cache stores `{pdf_field_name: personal_data_attr_name | None}` — not values.
Values are resolved from `effective_personal_data` at each call.

### Step 5 — Identify unfilled required fields
Any form field whose mapped value is `""` is added to `unfilled_required_fields`.
All fields are currently treated as required (TASK-15 will introduce proper metadata).

### Step 6 — Fill PDF
```python
tmp_path = await pdf_svc.fill(template_path, field_values, session_id, procedure_id)
```
`PDFService.fill()` is async (it awaits MinIO download and upload internally).
Await it directly — do not wrap in `run_in_executor`.

### Step 7 — Promote or hold
- **All fields filled** (`unfilled_required_fields` is empty): call
  `await storage_svc.promote_tmp(tmp_path, f"forms/{session_id}/{procedure_id}.pdf")`.
  Set `form_fill_complete = True`. Set `filled_form_path` to the final path.

- **Fields missing**: do NOT call `promote_tmp`. The PDF stays in `tmp/`.
  Set `form_fill_complete = False`. Set `filled_form_path` to `tmp_path`.
  The Synthesizer will prompt the user for the missing fields.

**NEVER promote a partially filled form.  This rule is absolute.**

---

## SessionDataAccumulator Merge Rules

`app/core/session_accumulator.py` — `SessionDataAccumulator.merge(existing, incoming)`:

- `existing=None` → return `incoming` (first OCR result wins as baseline)
- `incoming=None` → return `existing` (no new data)
- Both present → merge field by field:
  - Only one side has a value → take that value
  - Both have a value → compare `field_confidences[field]`; higher confidence wins
  - Equal confidence → `existing` wins (stability over freshness)
- Returns a **new** PersonalData — never mutates either input
- Provenance fields: `source_document_type`, `source_image_path`, `extracted_at` from
  `incoming`; `extraction_confidence` = max of both; `field_confidences` = max per key

---

## FormFieldMapper Cache Contract

`app/core/form_field_mapper.py` — `FormFieldMapper.map(personal_data, form_fields, form_id)`:

Cache key: `f"{form_id}:{':'.join(sorted(form_fields))}"`

The cache stores the **structural mapping** (which PersonalData attribute name maps to
which PDF field name), NOT the actual values.  Values change per user; the mapping is
reusable across users for the same PDF template structure.

On bad JSON from LLM: log a warning, store an all-null mapping, return `{}` (all `""`).
Never raise an exception for a parse failure.

---

## Error Handling

Steps 2–7 are wrapped in a single `try/except Exception`.  On any uncaught exception:

```python
return {
    "personal_data": effective_personal_data,
    "filled_form_path": None,
    "unfilled_required_fields": [],
    "form_fill_complete": False,
    "errors": (state.get("errors") or []) + [f"Lỗi khi điền biểu mẫu: {exc}"],
}
```

`form_filler_fn` must never raise — it must always return a dict.

---

## Lazy Singleton Services

`_llm_svc`, `_storage_svc`, `_pdf_svc` are module-level singletons initialised on
first use via `_get_llm_svc()`, `_get_storage_svc()`, `_get_pdf_svc()` getters.
Tests patch these getters before calling `form_filler_fn`.

`PDFService` is constructed with `PDFService(storage_service=_get_storage_svc())` —
never self-instantiates `StorageService` internally.
