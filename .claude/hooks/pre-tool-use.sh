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
