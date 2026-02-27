#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common/paths.sh"
source "$SCRIPT_DIR/../common/registry.sh"

usage() {
  echo "Usage: $0 <worktree-path>" >&2
}

WT="${1:-}"
if [[ -z "$WT" ]]; then
  usage
  exit 1
fi

ROOT="$(osc_repo_root)"
echo "cleanup worktree: $WT"
git -C "$ROOT" worktree remove --force "$WT"

# Prune stale entries from the agent registry
osc_registry_prune "$ROOT"
