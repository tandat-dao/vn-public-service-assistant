# Skill: Review Pydantic Schema

You are reviewing a Pydantic v2 schema file for the DichVuCong project.
Apply every check below. Report each as PASS, WARN, or FAIL.

## Checks

### Field Definitions
- FAIL if any field representing extracted/OCR data is not `X | None`
- FAIL if `PersonalData` or any subclass omits `field_confidences: dict[str, float]`
- WARN if a date field uses `str` instead of `date`
- FAIL if `datetime` is used without timezone — use `datetime` with `timezone=True` validator

### Validation
- WARN if a schema with a confidence field has no `@model_validator` checking 0.0–1.0 range
- FAIL if a response schema mapping to a SQLAlchemy model omits `model_config = ConfigDict(from_attributes=True)`

### Naming
- FAIL if request schemas do not end in `Request`
- FAIL if response schemas do not end in `Response` or `Read`
- WARN if a schema is defined in the wrong file (e.g., procedure schema in chat.py)

### Separation of Concerns
- FAIL if a schema imports from `app.models`
- FAIL if a schema imports from `app.services` or `app.agents`

## Output Format
`[PASS|WARN|FAIL] <check>: <one line reason>`
End with: PASS / WARN / FAIL counts + one recommended action.
