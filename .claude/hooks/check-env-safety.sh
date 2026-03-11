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
