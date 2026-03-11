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
