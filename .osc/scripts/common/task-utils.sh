#!/usr/bin/env bash
set -euo pipefail

_COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$_COMMON_DIR/paths.sh"

osc_slugify() {
  # ASCII-only slugify (good enough for branch/dir names)
  echo "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g' | sed -E 's/^-+//; s/-+$//; s/-+/-/g'
}

osc_next_journal_number() {
  local root="${1:-$(osc_repo_root)}"
  local ws
  ws="$(osc_workspace_dir "$root")"
  [[ -n "${ws:-}" ]] || { echo "1"; return; }
  local n=0
  for f in "$ws"/${FILE_JOURNAL_PREFIX}*.md; do
    [[ -f "$f" ]] || continue
    local base num
    base="$(basename "$f")"
    num="${base#${FILE_JOURNAL_PREFIX}}"
    num="${num%.md}"
    [[ "$num" =~ ^[0-9]+$ ]] || continue
    if [[ "$num" -gt "$n" ]]; then n="$num"; fi
  done
  echo $((n + 1))
}

