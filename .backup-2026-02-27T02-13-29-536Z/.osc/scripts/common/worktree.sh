#!/usr/bin/env bash
set -euo pipefail

_COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$_COMMON_DIR/paths.sh"

WORKTREE_CONFIG_REL="$DIR_OSC/worktree.yaml"

osc_worktree_config() {
  local root="${1:-$(osc_repo_root)}"
  echo "$root/$WORKTREE_CONFIG_REL"
}

_osc_yaml_value() {
  local key="$1"
  local cfg="${2:-$(osc_worktree_config)}"
  grep -E "^${key}:" "$cfg" 2>/dev/null | sed -E "s/^${key}:[[:space:]]*//" | tr -d '"' | tr -d "'"
}

_osc_yaml_list() {
  local section="$1"
  local cfg="${2:-$(osc_worktree_config)}"
  local in=0
  while IFS= read -r line; do
    if [[ "$line" =~ ^${section}: ]]; then
      in=1
      continue
    fi
    if [[ $in -eq 1 ]]; then
      if [[ "$line" =~ ^[a-zA-Z0-9_]+: ]] && [[ ! "$line" =~ ^[[:space:]] ]]; then
        break
      fi
      if [[ "$line" =~ ^[[:space:]]*-[[:space:]](.+)$ ]]; then
        echo "${BASH_REMATCH[1]}" | tr -d '"' | tr -d "'"
      fi
    fi
  done <"$cfg"
}

osc_worktree_base_dir() {
  local root="${1:-$(osc_repo_root)}"
  local cfg
  cfg="$(osc_worktree_config "$root")"
  local dir
  dir="$(_osc_yaml_value worktree_dir "$cfg")"
  [[ -n "${dir:-}" ]] || dir="../osc-worktrees"
  if [[ "$dir" == /* ]]; then
    echo "$dir"
  else
    echo "$root/$dir"
  fi
}

osc_worktree_copy_files() {
  local root="${1:-$(osc_repo_root)}"
  _osc_yaml_list copy "$(osc_worktree_config "$root")"
}

osc_worktree_post_create() {
  local root="${1:-$(osc_repo_root)}"
  _osc_yaml_list post_create "$(osc_worktree_config "$root")"
}

osc_worktree_verify() {
  local root="${1:-$(osc_repo_root)}"
  _osc_yaml_list verify "$(osc_worktree_config "$root")"
}

