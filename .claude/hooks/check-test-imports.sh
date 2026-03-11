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
