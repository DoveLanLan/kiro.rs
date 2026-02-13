#!/usr/bin/env bash
set -euo pipefail

_COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$_COMMON_DIR/paths.sh"

_json_escape() {
  python3 - <<'PY'
import json,sys
print(json.dumps(sys.stdin.read().rstrip('\n')))
PY
}

emit_text() {
  local root="$1"
  local dev task_rel
  dev="$(osc_developer_name "$root")"
  task_rel="$(osc_current_task_rel "$root")"

  echo "osc:"
  echo "  repo_root: $root"
  echo "  developer: ${dev:-<unset>}"
  echo "  current_task: ${task_rel:-<none>}"
  echo ""
  echo "git:"
  (cd "$root" && git status --porcelain 2>/dev/null) || true
  echo ""
  echo "recent_commits:"
  (cd "$root" && git log --oneline -n 10 2>/dev/null) || true
}

emit_json() {
  local root="$1"
  local dev task_rel status log
  dev="$(osc_developer_name "$root")"
  task_rel="$(osc_current_task_rel "$root")"
  status="$(cd "$root" && git status --porcelain 2>/dev/null || true)"
  log="$(cd "$root" && git log --oneline -n 10 2>/dev/null || true)"

  python3 - <<PY
import json
print(json.dumps({
  "repo_root": $(_json_escape <<<"$root"),
  "developer": $(_json_escape <<<"${dev:-}"),
  "current_task": $(_json_escape <<<"${task_rel:-}"),
  "git_status": $(_json_escape <<<"$status"),
  "recent_commits": $(_json_escape <<<"$log"),
}, ensure_ascii=False, indent=2))
PY
}

main() {
  local root
  root="$(osc_repo_root)"
  if [[ "${1:-}" == "--json" ]]; then
    emit_json "$root"
  else
    emit_text "$root"
  fi
}

main "$@"

