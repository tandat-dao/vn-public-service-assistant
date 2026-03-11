# Implementation Prompt: .claude/ Directory — Hooks, Skills, and Agents

You are extending the **DichVuCong AI Assistant** project. Read `CLAUDE.md` before touching anything. This prompt has one goal: create the `.claude/` directory with its three subsystems (hooks, skills, agents), wire the hooks into Claude Code's settings, and update `CLAUDE.md` to document all of it.

Do not touch any file outside of `.claude/` and `CLAUDE.md`.

---

## What You Are Building

```
.claude/
├── settings.json              # Claude Code configuration — registers all hooks
├── hooks/
│   ├── pre-bash.sh            # Runs before every bash command — destructive op guard
│   ├── pre-tool-use.sh        # Runs before Edit/Write — structural architecture guard
│   ├── post-tool-use.sh       # Runs after every bash command — failure surfacing
│   ├── check-env-safety.sh    # Blocks operations touching real .env files
│   ├── check-migration.sh     # Guards against modifying committed Alembic migrations
│   └── check-test-imports.sh  # Blocks real API calls in unit test files
├── skills/
│   └── code-review/
│       ├── README.md
│       ├── review-agent-node.md
│       ├── review-schema.md
│       ├── review-migration.md
│       └── review-api-route.md
└── agents/
    ├── README.md
    ├── router-agent.md
    ├── rag-agent.md
    ├── ocr-agent.md
    ├── procedure-planner-agent.md
    ├── form-filler-agent.md
    └── synthesizer-agent.md
```

---

## Step 1: `settings.json`

Create `.claude/settings.json`. This file registers all hooks with Claude Code and sets project-level behaviour.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/pre-bash.sh"
          },
          {
            "type": "command",
            "command": "bash .claude/hooks/check-env-safety.sh"
          }
        ]
      },
      {
        "matcher": "Edit|Write|Create",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/pre-tool-use.sh"
          },
          {
            "type": "command",
            "command": "bash .claude/hooks/check-migration.sh"
          },
          {
            "type": "command",
            "command": "bash .claude/hooks/check-test-imports.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/post-tool-use.sh"
          }
        ]
      }
    ]
  },
  "permissions": {
    "allow": [
      "Bash(git status)",
      "Bash(git diff*)",
      "Bash(git log*)",
      "Bash(git add*)",
      "Bash(git commit*)",
      "Bash(pytest*)",
      "Bash(alembic*)",
      "Bash(uvicorn*)",
      "Bash(docker compose*)",
      "Bash(pip install*)",
      "Bash(npm*)",
      "Bash(python -m*)"
    ],
    "deny": [
      "Bash(git push --force*)",
      "Bash(git push -f*)"
    ]
  }
}
```

---

## Step 2: Hook Scripts

Every hook script must follow these rules:
- First line: `#!/usr/bin/env bash`
- Second line: `set -euo pipefail`
- All output goes to `stderr` — stdout is reserved for hook pass/fail signalling
- Exit `0` to allow the operation to proceed
- Exit `1` to block the operation with a clear message to stderr
- Each script must be self-contained — no sourcing other scripts

### `.claude/hooks/pre-bash.sh`

Purpose: Block destructive shell commands before they execute. Reads `$CLAUDE_TOOL_INPUT` which Claude Code sets to the full command string.

Blocked patterns and messages:

| Pattern (case-insensitive regex) | Blocked Message |
|---|---|
| `rm\s+-rf\s+/` | Will not delete root filesystem |
| `rm\s+-rf\s+~` | Will not delete home directory |
| `rm\s+-rf\s+\.` | Will not recursively delete working directory |
| `DROP\s+DATABASE` | Database drop requires manual execution |
| `DROP\s+TABLE` | Table drop requires manual execution — use Alembic migrations instead |
| `TRUNCATE\s+\w` | Truncation requires manual execution |
| `git\s+push\s+(--force\|-f)` | Force push is not permitted |
| `git\s+rebase` | Rebase requires manual execution |
| `chmod\s+-R\s+777` | Will not set world-writable permissions |
| `(curl\|wget).+\|\s*(ba)?sh` | Will not pipe remote scripts to shell |
| `(pkill\|killall)\s` | Process termination requires manual confirmation |

If none match, print `[pre-bash] OK` to stderr and exit 0.

```bash
#!/usr/bin/env bash
set -euo pipefail

CMD="${CLAUDE_TOOL_INPUT:-}"

block_if_matches() {
  local pattern="$1"
  local reason="$2"
  if echo "$CMD" | grep -qiE "$pattern"; then
    echo "[pre-bash] BLOCKED: $reason" >&2
    echo "[pre-bash] Command was: $CMD" >&2
    exit 1
  fi
}

block_if_matches 'rm\s+-rf\s+/'             'Will not delete root filesystem'
block_if_matches 'rm\s+-rf\s+~'             'Will not delete home directory'
block_if_matches 'rm\s+-rf\s+\.'            'Will not recursively delete working directory'
block_if_matches 'DROP\s+DATABASE'          'Database drop requires manual execution'
block_if_matches 'DROP\s+TABLE'             'Table drop requires manual execution — use Alembic migrations instead'
block_if_matches 'TRUNCATE\s+\w'            'Truncation requires manual execution'
block_if_matches 'git\s+push\s+(--force|-f)' 'Force push is not permitted'
block_if_matches 'git\s+rebase'             'Rebase requires manual execution'
block_if_matches 'chmod\s+-R\s+777'         'Will not set world-writable permissions'
block_if_matches '(curl|wget).+\|\s*(ba)?sh' 'Will not pipe remote scripts to shell'
block_if_matches '(pkill|killall)\s'        'Process termination requires manual confirmation'

echo "[pre-bash] OK" >&2
exit 0
```

### `.claude/hooks/check-env-safety.sh`

Purpose: Prevent reading or writing `.env` files that may contain real secrets. Reads `$CLAUDE_TOOL_INPUT` (command string) and `$CLAUDE_TOOL_FILE_PATH` (file being written, if applicable).

Allow `.env.example` and `.env.local.example` explicitly. Block everything else that touches a real `.env` or attempts to print secret variable values.

```bash
#!/usr/bin/env bash
set -euo pipefail

CMD="${CLAUDE_TOOL_INPUT:-}"
FILE="${CLAUDE_TOOL_FILE_PATH:-}"

# Allow example files explicitly
if echo "$FILE" | grep -qE '\.env\.(example|local\.example)$'; then
  echo "[check-env-safety] Allowing example env file: $FILE" >&2
  exit 0
fi

# Block writes to real .env files
if echo "$FILE" | grep -qE '(^|/)\.env$'; then
  echo "[check-env-safety] BLOCKED: Will not write to .env — edit .env.example instead" >&2
  exit 1
fi

block_if_matches() {
  local pattern="$1"
  local reason="$2"
  if echo "$CMD" | grep -qiE "$pattern"; then
    echo "[check-env-safety] BLOCKED: $reason" >&2
    exit 1
  fi
}

block_if_matches 'printenv'                                           'Will not print all environment variables'
block_if_matches 'env\s+\|'                                          'Will not pipe env output'
block_if_matches 'cat\s+\.env(\s|$)'                                 'Will not cat .env file'
block_if_matches '(ANTHROPIC_API_KEY|OPENAI_API_KEY|MINIO_SECRET_KEY)' 'Will not echo secret environment variable values'

echo "[check-env-safety] OK" >&2
exit 0
```

### `.claude/hooks/check-migration.sh`

Purpose: Prevent modifying any Alembic migration that has already been committed to git. New (untracked) migration files are always allowed.

```bash
#!/usr/bin/env bash
set -euo pipefail

FILE="${CLAUDE_TOOL_FILE_PATH:-}"

# Only applies to files inside alembic/versions/
if ! echo "$FILE" | grep -qE 'alembic/versions/.+\.py$'; then
  echo "[check-migration] Not a migration file, skipping" >&2
  exit 0
fi

# Allow if the file does not exist yet (new migration being created)
if [ ! -f "$FILE" ]; then
  echo "[check-migration] New migration file, allowing" >&2
  exit 0
fi

# Block if already tracked by git
if git ls-files --error-unmatch "$FILE" 2>/dev/null; then
  echo "[check-migration] BLOCKED: Migration '$FILE' is already committed." >&2
  echo "[check-migration] Never modify a committed migration — create a new one:" >&2
  echo "[check-migration]   alembic revision --autogenerate -m 'describe_your_change'" >&2
  exit 1
fi

echo "[check-migration] Untracked migration file, allowing" >&2
exit 0
```

### `.claude/hooks/check-test-imports.sh`

Purpose: Prevent direct infrastructure instantiation in unit test files. Reads `$CLAUDE_TOOL_FILE_PATH` and `$CLAUDE_TOOL_CONTENT`.

```bash
#!/usr/bin/env bash
set -euo pipefail

FILE="${CLAUDE_TOOL_FILE_PATH:-}"
CONTENT="${CLAUDE_TOOL_CONTENT:-}"

# Only applies to tests/unit/
if ! echo "$FILE" | grep -qE 'tests/unit/.+\.py$'; then
  echo "[check-test-imports] Not a unit test file, skipping" >&2
  exit 0
fi

block_pattern() {
  local pattern="$1"
  local reason="$2"
  if echo "$CONTENT" | grep -qE "$pattern"; then
    echo "[check-test-imports] BLOCKED in $FILE: $reason" >&2
    echo "[check-test-imports] Unit tests must mock all external services." >&2
    echo "[check-test-imports] Use pytest fixtures from tests/conftest.py" >&2
    exit 1
  fi
}

block_pattern 'Anthropic\(\)'           'Direct Anthropic client — use mock_llm fixture'
block_pattern 'QdrantClient\(\)'        'Direct QdrantClient — use mock_qdrant fixture'
block_pattern 'AsyncSession\(\)'        'Direct AsyncSession — use mock_db fixture'
block_pattern 'redis\.asyncio\.from_url' 'Direct Redis connection — use mock_redis fixture'
block_pattern 'requests\.(get|post)\('  'Real HTTP request in unit test — use respx or httpx mock'

echo "[check-test-imports] OK" >&2
exit 0
```

### `.claude/hooks/pre-tool-use.sh`

Purpose: General pre-write guardrail. Enforces two structural architecture rules from `CLAUDE.md` at the file-write level: `app/core/` cannot import from `app/services/`, and `app/api/v1/` route handlers cannot import `anthropic` directly.

```bash
#!/usr/bin/env bash
set -euo pipefail

FILE="${CLAUDE_TOOL_FILE_PATH:-}"
CONTENT="${CLAUDE_TOOL_CONTENT:-}"

echo "[pre-tool-use] About to write: ${FILE:-unknown}" >&2

# Guard: app/core/ must not import from app/services/
if echo "$FILE" | grep -qE 'app/core/.+\.py$'; then
  if echo "$CONTENT" | grep -qE 'from app\.services'; then
    echo "[pre-tool-use] BLOCKED: app/core/ must not import from app/services/" >&2
    echo "[pre-tool-use] See CLAUDE.md Rule 5: Core Domain Logic Has Zero Infrastructure Dependencies" >&2
    exit 1
  fi
fi

# Guard: route handlers must not import anthropic directly
if echo "$FILE" | grep -qE 'app/api/v1/.+\.py$'; then
  if echo "$CONTENT" | grep -qE '^(import anthropic|from anthropic)'; then
    echo "[pre-tool-use] BLOCKED: Route handlers must not import anthropic directly" >&2
    echo "[pre-tool-use] LLM calls belong in agent nodes, not route handlers." >&2
    echo "[pre-tool-use] See CLAUDE.md Rule 2: API Routes are Thin" >&2
    exit 1
  fi
fi

echo "[pre-tool-use] OK" >&2
exit 0
```

### `.claude/hooks/post-tool-use.sh`

Purpose: After a bash command runs, surface common failure signals so they are not silently swallowed. Reads `$CLAUDE_TOOL_EXIT_CODE` and `$CLAUDE_TOOL_OUTPUT`.

```bash
#!/usr/bin/env bash
set -euo pipefail

EXIT_CODE="${CLAUDE_TOOL_EXIT_CODE:-0}"
OUTPUT="${CLAUDE_TOOL_OUTPUT:-}"

# Surface pytest failures
if echo "$OUTPUT" | grep -qE 'FAILED|ERROR' && echo "$OUTPUT" | grep -q 'pytest'; then
  echo "[post-tool-use] WARNING: pytest reported failures. Fix before proceeding." >&2
fi

# Surface Alembic errors
if echo "$OUTPUT" | grep -qi 'alembic' && echo "$OUTPUT" | grep -qi 'error'; then
  echo "[post-tool-use] WARNING: Alembic reported an error. Check migration state." >&2
fi

# Surface Python import errors
if echo "$OUTPUT" | grep -qE 'ImportError|ModuleNotFoundError'; then
  echo "[post-tool-use] WARNING: Python import error detected." >&2
  echo "[post-tool-use] Run: pip install -r requirements.txt" >&2
fi

echo "[post-tool-use] Done (exit: $EXIT_CODE)" >&2
exit 0
```

---

## Step 3: Skills — `code-review/`

Skills are reusable review prompt templates. When you need to review a piece of code, invoke the relevant skill by saying: "Review this file using `.claude/skills/code-review/<skill>.md`" then paste the code. Skills are not executed automatically.

### `.claude/skills/code-review/README.md`

```markdown
# Code Review Skills

Reusable review prompts. Invoke a skill by saying:
"Review this using .claude/skills/code-review/<skill-name>.md" then paste the code.

| Skill | Use When |
|---|---|
| review-agent-node.md | Any file in app/agents/nodes/ |
| review-schema.md | Any file in app/schemas/ |
| review-migration.md | Any new Alembic migration before committing |
| review-api-route.md | Any file in app/api/v1/ |
```

### `.claude/skills/code-review/review-agent-node.md`

```markdown
# Skill: Review Agent Node

You are reviewing a LangGraph agent node for the DichVuCong project.
Apply every check below in order. Report each as PASS, WARN, or FAIL.

## Checks

### State Contract
- FAIL if the function signature is not `def <name>_node(state: AgentState) -> dict`
- FAIL if the node returns the full AgentState instead of a partial dict
- FAIL if the node mutates `state` in place before returning
- WARN if the node modifies more than 4 state keys — consider splitting

### Infrastructure Isolation
- FAIL if the node imports from `app.core` AND directly calls a service in the same function body
- FAIL if the node instantiates any client (Anthropic, Qdrant, Redis) directly
- WARN if the node body exceeds 60 lines

### Error Handling
- FAIL if the node makes any external call with no try/except
- FAIL if exceptions are silently swallowed (bare `except: pass`)
- WARN if errors are not appended to `state["errors"]` before returning

### Routing Functions
- FAIL if a conditional routing function has any side effects
- FAIL if routing logic is a lambda instead of a named function
- FAIL if a routing function does anything except inspect state and return a node name string

### Prompts
- FAIL if the LLM prompt is a string literal defined inline inside the node
- WARN if the prompt does not instruct the model to return null for missing fields

## Output Format
`[PASS|WARN|FAIL] <check>: <one line reason>`
End with: PASS count / WARN count / FAIL count + one recommended action.
```

### `.claude/skills/code-review/review-schema.md`

```markdown
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
```

### `.claude/skills/code-review/review-migration.md`

```markdown
# Skill: Review Alembic Migration

You are reviewing a new Alembic migration before it is committed.
Apply every check. Report each as PASS, WARN, or FAIL.

## Checks

### Safety
- FAIL if `upgrade()` has `DROP TABLE` or `DROP COLUMN` without a restore in `downgrade()`
- FAIL if `downgrade()` is empty or raises `NotImplementedError`
- WARN if the migration modifies more than 3 tables — consider splitting

### Schema Conventions
- FAIL if any new primary key is not UUID type
- FAIL if any new timestamp column is not `TIMESTAMP(timezone=True)`
- FAIL if a NOT NULL column is added to an existing table without a `server_default`
- WARN if a new index is not named `ix_<table>_<column>`
- WARN if a new FK constraint is not named `fk_<child>_<parent>`

### Completeness
- FAIL if the migration was autogenerated but its models are not imported in `alembic/env.py`
- FAIL if `down_revision` is `None` and this is not the first migration

## Output Format
`[PASS|WARN|FAIL] <check>: <one line reason>`
End with: Safe to commit? YES / NO + reason.
```

### `.claude/skills/code-review/review-api-route.md`

```markdown
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
```

---

## Step 4: Agents — Behavioural Specification Files

Each file defines the complete behavioural contract for one LangGraph node. Before implementing or modifying any node, read its spec file. If the implementation needs to diverge from the spec, update the spec first.

### `.claude/agents/README.md`

```markdown
# Agent Specification Files

Read the relevant file before implementing or modifying any LangGraph node.

| File | Node | Source Location |
|---|---|---|
| router-agent.md | router_node | app/agents/nodes/router.py |
| rag-agent.md | rag_node | app/agents/nodes/rag.py |
| ocr-agent.md | ocr_node | app/agents/nodes/ocr.py |
| procedure-planner-agent.md | procedure_planner_node | app/agents/nodes/procedure_planner.py |
| form-filler-agent.md | form_filler_node | app/agents/nodes/form_filler.py |
| synthesizer-agent.md | synthesizer_node | app/agents/nodes/synthesizer.py |

## Workflow
1. Read the spec file before writing any code.
2. After implementing, self-review with `.claude/skills/code-review/review-agent-node.md`.
3. If behaviour needs to change, update the spec file first and note why in the commit.
```

### `.claude/agents/router-agent.md`

```markdown
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
```

### `.claude/agents/rag-agent.md`

```markdown
# RAG Agent — Behavioural Specification

## Node: `rag_node`
## File: `app/agents/nodes/rag.py`
## Prompt: `app/agents/prompts/rag_prompt.py`

## Responsibility
Retrieve legal document chunks from Qdrant and generate a cited answer.
Only this node calls `qdrant_service`.

## Inputs (read from AgentState)
- `user_message: str`
- `target_procedure_id: str | None` — used as a Qdrant payload filter
- `entities: dict` — may contain decree numbers for targeted BM25 queries

## Outputs (partial AgentState dict)
- `retrieved_chunks: list[DocumentChunk]`
- `citations: list[Citation]` — structured, ready for the synthesizer

## Retrieval Rules
1. Always use hybrid search (dense + BM25 + RRF). Dense-only is forbidden.
2. Pass `target_procedure_id` as a filter when set — this constrains results to relevant legal docs.
3. Minimum `top_k = 8`. Never fewer.
4. If zero chunks returned: set `citations = []`, append warning to `state["errors"]`, return without calling LLM.

## Citation Rules
- Every `Citation` object must have: `doc_id`, `document_number`, `article`, `excerpt`
- `excerpt` is verbatim text from the retrieved chunk, max 200 characters
- Only citations appearing in `retrieved_chunks` may be included — no invented references
- Citation format in response text: `[Điều X, Nghị định/Thông tư YYY/YYYY/NĐ-CP]`

## Confidence Scoring
Set `state["response_metadata"]["rag_confidence"]`:
- `"high"` — top chunk score > 0.85 AND at least 3 chunks retrieved
- `"medium"` — top chunk score > 0.65
- `"low"` — top chunk score ≤ 0.65 OR fewer than 3 chunks

## Error Handling
On Qdrant failure: append to `state["errors"]`, set empty retrieved_chunks and citations, return.
Do not crash the graph.
```

### `.claude/agents/ocr-agent.md`

```markdown
# OCR Agent — Behavioural Specification

## Node: `ocr_node`
## File: `app/agents/nodes/ocr.py`
## Prompt: `app/agents/prompts/ocr_extraction_prompt.py`

## Responsibility
Run the full OCR pipeline on an uploaded document image and populate PersonalData.
Only this node calls `ocr_service` and `storage_service`.

## Inputs (read from AgentState)
- `uploaded_image_path: str` — must be present (router only sends here if image exists)
- `session_id: str` — to load existing PersonalData for merging

## Outputs (partial AgentState dict)
- `personal_data: PersonalData`
- `document_type: str` — classified document type

## Processing Pipeline (execute in this exact order — no steps optional)
1. Download image from MinIO via `storage_service`
2. OpenCV pre-processing: deskew → CLAHE → denoise
3. Classify document type via vision LLM
4. Run PaddleOCR (Vietnamese PP-OCRv4)
5. LLM field extraction using `ocr_extraction_prompt`
6. Validation: CCCD checksum if applicable, date normalisation always
7. Load existing PersonalData from session (Redis)
8. Merge with `session_accumulator.merge()` — higher confidence wins
9. Return merged PersonalData

## Field Extraction Rules
- The extraction prompt must instruct the model to return `null` for unrecognised fields — never guess
- Fields with confidence < 0.5 must be set to `None` even if text was extracted
- `extraction_confidence` = mean of all `field_confidences` values

## Fallback
PaddleOCR fails → retry once with Tesseract.
Both fail → set `personal_data = None`, append error, continue — do not crash.
```

### `.claude/agents/procedure-planner-agent.md`

```markdown
# Procedure Planner Agent — Behavioural Specification

## Node: `procedure_planner_node`
## File: `app/agents/nodes/procedure_planner.py`

## Responsibility
Resolve the full dependency chain for a target procedure and produce an ordered execution plan.
Only this node queries the procedures database and calls `procedure_graph` core logic.

## Inputs (read from AgentState)
- `target_procedure_id: str | None` — if None, resolve from `entities`
- `completed_procedures: list[str]` — loaded from Redis at graph entry
- `entities: dict` — may contain procedure name strings to resolve to IDs

## Outputs (partial AgentState dict)
- `procedure_execution_plan: ProcedureExecutionPlan`
- `target_procedure_id: str` — confirmed/resolved ID

## Resolution Logic (in order)
1. If `target_procedure_id` is None, fuzzy-match `entities` against procedure names in DB.
   If no match, append error and return empty plan.
2. Load ALL dependency edges for the subgraph rooted at target from DB in a single JOIN query.
3. Call `procedure_graph.resolve_execution_plan()` — the algorithm lives in core, not here.
4. Mark steps in `completed_procedures` as `"completed"`.
5. Mark steps whose direct prerequisites are not completed as `"blocked"`.
6. Return the full plan including completed steps — do not filter them out.

## Critical Constraints
- The topological sort algorithm MUST live in `app/core/procedure_graph.py` — not in this node
- This node's only job is: fetch data → pass to core → return result
- If a cycle is detected (ValueError), return a single-step plan with the target, status "blocked"
- Conditional dependencies (`is_mandatory = False`) are included but flagged separately
- Do NOT N+1 query — load the entire subgraph in one query

## Error Handling
On DB failure: append to `state["errors"]`, return empty plan. Do not crash.
```

### `.claude/agents/form-filler-agent.md`

```markdown
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
```

### `.claude/agents/synthesizer-agent.md`

```markdown
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
```

---

## Step 5: Make All Hooks Executable

```bash
chmod +x .claude/hooks/pre-bash.sh
chmod +x .claude/hooks/check-env-safety.sh
chmod +x .claude/hooks/check-migration.sh
chmod +x .claude/hooks/check-test-imports.sh
chmod +x .claude/hooks/pre-tool-use.sh
chmod +x .claude/hooks/post-tool-use.sh
```

Validate all scripts are syntactically valid:

```bash
for f in .claude/hooks/*.sh; do
  bash -n "$f" && echo "OK: $f" || echo "SYNTAX ERROR: $f"
done
```

All six must print `OK`. Fix any syntax errors before proceeding to Step 6.

---

## Step 6: Update `CLAUDE.md`

Add two new blocks to the existing `CLAUDE.md`. Insert them between the **LangGraph Node Conventions** section and the **RAG — Implementation Notes** section. Do not modify any existing content.

### Block A — Insert as new section after LangGraph Node Conventions:

````markdown
---

## .claude/ Directory

The `.claude/` directory contains three subsystems that govern how Claude Code behaves on this project. Read the relevant files before implementing any feature.

### Hooks — Automated Guardrails

Hooks in `.claude/hooks/` run automatically before and after every tool use. They cannot be bypassed from within Claude Code. If a hook blocks an operation, its error message will state the exact rule violated and the relevant `CLAUDE.md` section.

| Hook | Trigger | Enforces |
|---|---|---|
| `pre-bash.sh` | Before every bash command | Blocks destructive commands (rm -rf, DROP TABLE, force push, remote pipe-to-shell) |
| `check-env-safety.sh` | Before bash + file writes | Prevents accessing real `.env` files or echoing secret variable values |
| `check-migration.sh` | Before any file write | Prevents modifying committed Alembic migrations |
| `check-test-imports.sh` | Before writing to `tests/unit/` | Prevents direct infrastructure instantiation in unit tests |
| `pre-tool-use.sh` | Before Edit/Write/Create | Enforces: `app/core/` has no service imports; route handlers have no direct LLM imports |
| `post-tool-use.sh` | After every bash command | Surfaces pytest failures, Alembic errors, and import errors |

If you need to run a legitimately blocked command (e.g., `DROP TABLE` during a manual environment reset), run it directly in your terminal outside Claude Code. Never modify hooks to permit a one-off operation — add a targeted exemption with a comment if the pattern is genuinely needed.

### Skills — Reusable Review Workflows

Skills in `.claude/skills/code-review/` are review prompt templates. Run the relevant skill on your own output before considering any implementation complete.

To invoke: say "Review this using `.claude/skills/code-review/<skill>.md`" then paste the code.

| Skill | Use For |
|---|---|
| `review-agent-node.md` | Any file in `app/agents/nodes/` |
| `review-schema.md` | Any file in `app/schemas/` |
| `review-migration.md` | Any new Alembic migration before committing |
| `review-api-route.md` | Any file in `app/api/v1/` |

### Agents — Behavioural Specifications

Files in `.claude/agents/` define the complete behavioural contract for each LangGraph node: inputs, outputs, processing rules, error handling, and which prompt file to use.

**Read the spec file before implementing or modifying any node.**
**If the implementation needs to diverge from the spec, update the spec first and explain why in the commit.**

| Spec File | Node |
|---|---|
| `router-agent.md` | `router_node` — intent classification and routing |
| `rag-agent.md` | `rag_node` — hybrid retrieval and citation generation |
| `ocr-agent.md` | `ocr_node` — document image extraction pipeline |
| `procedure-planner-agent.md` | `procedure_planner_node` — dependency resolution |
| `form-filler-agent.md` | `form_filler_node` — semantic field mapping and PDF fill |
| `synthesizer-agent.md` | `synthesizer_node` — final response assembly |
````

### Block B — Append to the existing Common Mistakes section:

````markdown
- **Do not work around hooks** by running blocked commands in a separate terminal and continuing in Claude Code as if they succeeded. Hooks exist because those patterns caused bugs. If a hook incorrectly blocks a legitimate operation, add a targeted exemption to the hook with a comment explaining the exception.
- **Do not implement a node without reading its `.claude/agents/` spec first.** Spec files define the state key contract other nodes depend on. Implementing from memory leads to key mismatches that break the entire graph and are difficult to trace.
- **Do not skip code-review skills before marking a task complete.** Running the relevant skill on your own output takes under a minute and catches structural violations before they propagate into other phases.
````

---

## Verification

After completing all steps, run:

```bash
# 1. Verify file count
find .claude -type f | sort
```

Expected: 19 files total.

```bash
# 2. Verify hooks are executable
ls -la .claude/hooks/*.sh | awk '{print $1, $9}' | grep -v '^-rwx'
```

Expected: no output (all files are executable).

```bash
# 3. Verify CLAUDE.md was updated
grep -n "\.claude/ Directory" CLAUDE.md
grep -n "Hooks — Automated Guardrails" CLAUDE.md
grep -n "Skills — Reusable Review Workflows" CLAUDE.md
grep -n "Agents — Behavioural Specifications" CLAUDE.md
```

Expected: all four return a line number. If any is missing, the `CLAUDE.md` update is incomplete.

```bash
# 4. Verify hook syntax
for f in .claude/hooks/*.sh; do
  bash -n "$f" && echo "OK: $f" || echo "SYNTAX ERROR: $f"
done
```

Expected: six `OK` lines. Fix any syntax error before finishing.
