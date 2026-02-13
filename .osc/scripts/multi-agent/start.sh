#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common/paths.sh"
source "$SCRIPT_DIR/../common/worktree.sh"
source "$SCRIPT_DIR/../common/registry.sh"

usage() {
  echo "Usage: $0 <task-dir>" >&2
  echo "Example: $0 .osc/tasks/01-31-my-task" >&2
}

TASK_DIR="${1:-}"
if [[ -z "$TASK_DIR" ]]; then
  usage
  exit 1
fi

ROOT="$(osc_repo_root)"

# Normalize to abs + rel
if [[ "$TASK_DIR" = /* ]]; then
  TASK_ABS="$TASK_DIR"
  TASK_REL="${TASK_DIR#$ROOT/}"
else
  TASK_REL="$TASK_DIR"
  TASK_ABS="$ROOT/$TASK_DIR"
fi

TASK_JSON="$TASK_ABS/$FILE_TASK_JSON"
if [[ ! -f "$TASK_JSON" ]]; then
  echo "error: task.json not found: $TASK_JSON" >&2
  exit 1
fi

command -v jq >/dev/null 2>&1 || { echo "error: jq is required" >&2; exit 1; }

BRANCH="$(jq -r '.branch' "$TASK_JSON")"
NAME="$(jq -r '.name' "$TASK_JSON")"
[[ -n "${BRANCH:-}" && "$BRANCH" != "null" ]] || { echo "error: task.json missing branch" >&2; exit 1; }

echo "osc multi-agent start"
echo "- task: $TASK_REL"
echo "- branch: $BRANCH"
echo "- name: $NAME"

BASE_BRANCH="$(git -C "$ROOT" branch --show-current 2>/dev/null || echo main)"

WT_BASE="$(osc_worktree_base_dir "$ROOT")"
mkdir -p "$WT_BASE"
WT_BASE="$(cd "$WT_BASE" && pwd)"
WT_PATH="$WT_BASE/$BRANCH"

if [[ ! -d "$WT_PATH" ]]; then
  mkdir -p "$(dirname "$WT_PATH")"
  if git -C "$ROOT" show-ref --verify --quiet "refs/heads/$BRANCH"; then
    git -C "$ROOT" worktree add "$WT_PATH" "$BRANCH"
  else
    git -C "$ROOT" worktree add -b "$BRANCH" "$WT_PATH"
  fi
fi

# Copy configured files
osc_worktree_copy_files "$ROOT" | while IFS= read -r rel; do
  [[ -n "${rel:-}" ]] || continue
  src="$ROOT/$rel"
  dst="$WT_PATH/$rel"
  if [[ -f "$src" ]]; then
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
  fi
done

# Post-create hooks
osc_worktree_post_create "$ROOT" | while IFS= read -r cmd; do
  [[ -n "${cmd:-}" ]] || continue
  (cd "$WT_PATH" && bash -lc "$cmd")
done

# Update task.json with worktree info
tmp="$TASK_JSON.tmp"
jq --arg wt "$WT_PATH" --arg base "$BASE_BRANCH" '.worktree_path=$wt | .base_branch=$base' "$TASK_JSON" >"$tmp"
mv "$tmp" "$TASK_JSON"

echo "- worktree: $WT_PATH"
echo "- base_branch: $BASE_BRANCH"

# Optional: start claude in background if available
if command -v claude >/dev/null 2>&1; then
  export CLAUDE_NON_INTERACTIVE=1
  (cd "$WT_PATH" && nohup claude >/dev/null 2>&1 & echo $! >"$WT_PATH/.osc/.session-id" ) || true
  pid="$(cat "$WT_PATH/.osc/.session-id" 2>/dev/null || true)"
  if [[ -n "${pid:-}" ]]; then
    osc_registry_add "$ROOT" "claude" "$pid" "$WT_PATH" "$TASK_REL" || true
    echo "- started claude pid: $pid"
  fi
else
  echo "- note: 'claude' binary not found; open the worktree and start Claude Code manually."
fi

