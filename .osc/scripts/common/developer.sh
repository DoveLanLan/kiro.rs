#!/usr/bin/env bash
set -euo pipefail

_COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$_COMMON_DIR/paths.sh"

osc_init_developer() {
  local name="$1"
  local root="${2:-$(osc_repo_root)}"
  [[ -n "${name:-}" ]] || { echo "error: name required" >&2; return 1; }

  local osc
  osc="$(osc_dir "$root")"
  mkdir -p "$osc"
  echo "name=$name" >"$osc/$FILE_DEVELOPER"

  mkdir -p "$(osc_workspace_root "$root")/$name"
  local ws="$(osc_workspace_root "$root")/$name"

  if [[ ! -f "$ws/index.md" ]]; then
    cat >"$ws/index.md" <<EOF
# ${name} workspace

## Journals

- ${FILE_JOURNAL_PREFIX}1.md
EOF
  fi

  if [[ ! -f "$ws/${FILE_JOURNAL_PREFIX}1.md" ]]; then
    cat >"$ws/${FILE_JOURNAL_PREFIX}1.md" <<EOF
# ${name} journal 1

- Date: $(date -u +%Y-%m-%d)

## Notes
EOF
  fi
}

