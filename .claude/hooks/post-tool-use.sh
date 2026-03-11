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
