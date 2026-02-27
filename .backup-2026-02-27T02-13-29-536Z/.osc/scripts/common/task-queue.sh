#!/usr/bin/env bash
set -euo pipefail

_COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$_COMMON_DIR/paths.sh"

osc_list_task_dirs() {
  local root="${1:-$(osc_repo_root)}"
  local tasks
  tasks="$(osc_tasks_dir "$root")"
  [[ -d "$tasks" ]] || return 0
  find "$tasks" -maxdepth 1 -mindepth 1 -type d -print | sort
}

osc_archive_dir() {
  local root="${1:-$(osc_repo_root)}"
  echo "$(osc_tasks_dir "$root")/$DIR_ARCHIVE/$(date +%Y-%m)"
}

