# Skill: Review API Route Handler

You are reviewing a FastAPI route handler file for the DichVuCong project.
Apply every check. Report each as PASS, WARN, or FAIL.

## Checks

### Thinness (most important)
- FAIL if the handler body contains any SQL query
- FAIL if the handler body contains any LLM call
- FAIL if the handler body contains more than 5 lines of business logic
- FAIL if the handler imports from `app.core` directly
- PASS if the handler does exactly: receive → validate → delegate → return

### Response Types
- FAIL if a streaming route uses `return` instead of `StreamingResponse`
- FAIL if any route returns a raw dict instead of a typed Pydantic schema
- WARN if error responses do not use `HTTPException` with a meaningful `detail`

### Dependencies
- FAIL if a DB session or Redis connection is created inside the handler body
- WARN if the same `Depends(...)` appears more than once in the signature

### Naming
- WARN if route paths use camelCase instead of kebab-case
- FAIL if a mutating operation uses GET method

## Output Format
`[PASS|WARN|FAIL] <check>: <one line reason>`
End with: PASS / WARN / FAIL counts + one recommended action.
