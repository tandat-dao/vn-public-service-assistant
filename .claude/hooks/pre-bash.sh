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
