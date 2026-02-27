#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common/paths.sh"
source "$SCRIPT_DIR/../common/registry.sh"

ROOT="$(osc_repo_root)"
osc_registry_init "$ROOT" || true
REG="$(osc_registry_file "$ROOT")"

echo "osc multi-agent status"
if [[ -z "${REG:-}" || ! -f "$REG" ]]; then
  echo "(no registry)"
  exit 0
fi

command -v jq >/dev/null 2>&1 || { cat "$REG"; exit 0; }

entries="$(jq -c '.[]' "$REG" 2>/dev/null)" || true

while IFS= read -r entry; do
  [[ -n "$entry" ]] || continue
  name="$(echo "$entry" | jq -r '.name')"
  pid="$(echo "$entry" | jq -r '.pid')"
  wt="$(echo "$entry" | jq -r '.worktree')"
  task="$(echo "$entry" | jq -r '.task')"
  started="$(echo "$entry" | jq -r '.started_at')"
  if kill -0 "$pid" 2>/dev/null; then
    state="alive"
  else
    state="dead"
  fi
  printf '%s\tpid=%s\t[%s]\tworktree=%s\ttask=%s\tstarted_at=%s\n' \
    "$name" "$pid" "$state" "$wt" "$task" "$started"
done <<< "$entries"

# --prune support: automatically remove dead entries
if [[ "${1:-}" == "--prune" ]]; then
  osc_registry_prune "$ROOT"
fi
