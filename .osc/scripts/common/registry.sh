#!/usr/bin/env bash
set -euo pipefail

_COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$_COMMON_DIR/paths.sh"

osc_agents_dir() {
  local root="${1:-$(osc_repo_root)}"
  local ws
  ws="$(osc_workspace_dir "$root")"
  [[ -n "${ws:-}" ]] || return 0
  echo "$ws/.agents"
}

osc_registry_file() {
  local root="${1:-$(osc_repo_root)}"
  local d
  d="$(osc_agents_dir "$root")"
  [[ -n "${d:-}" ]] || return 0
  echo "$d/registry.json"
}

osc_registry_init() {
  local root="${1:-$(osc_repo_root)}"
  local d
  d="$(osc_agents_dir "$root")"
  [[ -n "${d:-}" ]] || return 0
  mkdir -p "$d"
  local f
  f="$(osc_registry_file "$root")"
  if [[ ! -f "$f" ]]; then
    echo "[]" >"$f"
  fi
}

osc_registry_add() {
  command -v jq >/dev/null 2>&1 || return 0
  local root="$1" name="$2" pid="$3" worktree="$4" task="$5"
  osc_registry_init "$root"
  local f
  f="$(osc_registry_file "$root")"
  [[ -n "${f:-}" ]] || return 0
  tmp="${f}.tmp"
  jq --arg name "$name" --arg pid "$pid" --arg worktree "$worktree" --arg task "$task" \
    '. + [{name:$name,pid:($pid|tonumber),worktree:$worktree,task:$task,started_at:(now|todate)}]' \
    "$f" >"$tmp" && mv "$tmp" "$f"
}

osc_registry_remove() {
  command -v jq >/dev/null 2>&1 || return 0
  local root="$1" pid="$2"
  local f
  f="$(osc_registry_file "$root")"
  [[ -n "${f:-}" && -f "$f" ]] || return 0
  local tmp="${f}.tmp"
  jq --arg pid "$pid" '[.[] | select(.pid != ($pid|tonumber))]' "$f" >"$tmp" && mv "$tmp" "$f"
}

osc_registry_prune() {
  command -v jq >/dev/null 2>&1 || return 0
  local root="$1"
  local f
  f="$(osc_registry_file "$root")"
  [[ -n "${f:-}" && -f "$f" ]] || return 0
  local tmp="${f}.tmp"
  local pids
  pids="$(jq -r '.[].pid' "$f" 2>/dev/null)" || return 0
  local dead=()
  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    if ! kill -0 "$pid" 2>/dev/null; then
      dead+=("$pid")
    fi
  done <<< "$pids"
  if [[ ${#dead[@]} -gt 0 ]]; then
    local filter
    filter="$(printf '%s\n' "${dead[@]}" | jq -R 'tonumber' | jq -s '.')"
    jq --argjson dead "$filter" '[.[] | select(.pid as $p | $dead | index($p) | not)]' "$f" >"$tmp" && mv "$tmp" "$f"
    echo "pruned ${#dead[@]} stale entries"
  fi
}

