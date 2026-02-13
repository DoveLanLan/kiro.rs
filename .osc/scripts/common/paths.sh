#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------------------------
# Path constants (rename here)
# -----------------------------------------------------------------------------

DIR_OSC=".osc"
DIR_SCRIPTS="scripts"
DIR_SPEC="spec"
DIR_TASKS="tasks"
DIR_WORKSPACE="workspace"
DIR_ARCHIVE="archive"

FILE_DEVELOPER=".developer"
FILE_CURRENT_TASK=".current-task"
FILE_TASK_JSON="task.json"
FILE_JOURNAL_PREFIX="journal-"

osc_repo_root() {
  # Prefer nearest directory that contains .osc/
  local current="$PWD"
  while [[ "$current" != "/" ]]; do
    if [[ -d "$current/$DIR_OSC" ]]; then
      echo "$current"
      return
    fi
    current="$(dirname "$current")"
  done

  # Fallback to git root if available
  if git rev-parse --show-toplevel >/dev/null 2>&1; then
    git rev-parse --show-toplevel
    return
  fi

  echo "$PWD"
}

osc_dir() {
  local root="${1:-$(osc_repo_root)}"
  echo "$root/$DIR_OSC"
}

osc_tasks_dir() {
  local root="${1:-$(osc_repo_root)}"
  echo "$(osc_dir "$root")/$DIR_TASKS"
}

osc_workspace_root() {
  local root="${1:-$(osc_repo_root)}"
  echo "$(osc_dir "$root")/$DIR_WORKSPACE"
}

osc_developer_name() {
  local root="${1:-$(osc_repo_root)}"
  local f="$(osc_dir "$root")/$FILE_DEVELOPER"
  [[ -f "$f" ]] || return 0
  sed -n 's/^name=//p' "$f" 2>/dev/null | head -n 1 || true
}

osc_workspace_dir() {
  local root="${1:-$(osc_repo_root)}"
  local dev
  dev="$(osc_developer_name "$root")"
  [[ -n "${dev:-}" ]] || return 0
  echo "$(osc_workspace_root "$root")/$dev"
}

osc_current_task_file() {
  local root="${1:-$(osc_repo_root)}"
  echo "$(osc_dir "$root")/$FILE_CURRENT_TASK"
}

osc_current_task_rel() {
  local root="${1:-$(osc_repo_root)}"
  local f
  f="$(osc_current_task_file "$root")"
  [[ -f "$f" ]] || return 0
  cat "$f" 2>/dev/null || true
}

osc_current_task_abs() {
  local root="${1:-$(osc_repo_root)}"
  local rel
  rel="$(osc_current_task_rel "$root")"
  [[ -n "${rel:-}" ]] || return 0
  echo "$root/$rel"
}

osc_set_current_task() {
  local task_rel="$1"
  local root="${2:-$(osc_repo_root)}"
  local abs="$root/$task_rel"
  [[ -d "$abs" ]] || { echo "error: task dir not found: $task_rel" >&2; return 1; }
  echo "$task_rel" >"$(osc_current_task_file "$root")"
}

osc_clear_current_task() {
  local root="${1:-$(osc_repo_root)}"
  rm -f "$(osc_current_task_file "$root")" 2>/dev/null || true
}

osc_date_prefix() {
  date +%m-%d
}

