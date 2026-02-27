#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common/paths.sh"
source "$SCRIPT_DIR/common/task-utils.sh"
source "$SCRIPT_DIR/common/task-queue.sh"

usage() {
  cat <<'EOF'
Usage:
  ./.osc/scripts/task.sh list
  ./.osc/scripts/task.sh create "<title>" [--type feature|bugfix|hotfix|refactor|docs] [--slug <slug>] [--branch <branch>] [--priority P0|P1|P2|P3] [--depends <task-dir>]
  ./.osc/scripts/task.sh select <task-dir>
  ./.osc/scripts/task.sh next
  ./.osc/scripts/task.sh clear
  ./.osc/scripts/task.sh archive <task-dir>
  ./.osc/scripts/task.sh status [<task-dir>]
  ./.osc/scripts/task.sh done [<task-dir>]
  ./.osc/scripts/task.sh progress <message> [<task-dir>]
EOF
}

require_jq() {
  command -v jq >/dev/null 2>&1 || { echo "error: jq is required" >&2; exit 1; }
}

ensure_dirs() {
  local root="${1:-$(osc_repo_root)}"
  mkdir -p "$(osc_tasks_dir "$root")" "$(osc_workspace_root "$root")"
}

cmd_list() {
  require_jq
  local root="${1:-$(osc_repo_root)}"
  local current
  current="$(osc_current_task_rel "$root")"
  echo "current: ${current:-<none>}"
  osc_list_task_dirs "$root" | while IFS= read -r d; do
    local rel marker status task_type deps
    rel="${d#$root/}"
    if [[ "$rel" == "$current" ]]; then marker="*"; else marker=" "; fi
    local tj="$d/$FILE_TASK_JSON"
    if [[ -f "$tj" ]]; then
      status="$(jq -r '.status // "?"' "$tj" 2>/dev/null)"
      task_type="$(jq -r '.type // "feature"' "$tj" 2>/dev/null)"
      deps="$(jq -r '.depends_on // [] | if length > 0 then "blocked_by:" + join(",") else "" end' "$tj" 2>/dev/null)"
      printf '%s [%s] (%s) %s %s\n' "$marker" "$status" "$task_type" "$rel" "$deps"
    else
      echo "$marker $rel"
    fi
  done
}

cmd_create() {
  require_jq
  local title="$1"; shift || true
  local slug="" branch="" priority="P2" description="" task_type="feature" depends=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --slug|-s) slug="$2"; shift 2 ;;
      --branch|-b) branch="$2"; shift 2 ;;
      --priority|-p) priority="$2"; shift 2 ;;
      --description|-d) description="$2"; shift 2 ;;
      --type|-t) task_type="$2"; shift 2 ;;
      --depends) depends="$2"; shift 2 ;;
      *) echo "error: unknown arg: $1" >&2; exit 1 ;;
    esac
  done

  # Validate type
  case "$task_type" in
    feature|bugfix|hotfix|refactor|docs) ;;
    *) echo "error: unknown type '$task_type' (feature|bugfix|hotfix|refactor|docs)" >&2; exit 1 ;;
  esac

  [[ -n "$title" ]] || { echo "error: title required" >&2; exit 1; }
  if [[ -z "$slug" ]]; then slug="$(osc_slugify "$title")"; fi
  [[ -n "$slug" ]] || { echo "error: slug empty" >&2; exit 1; }

  local root tasks date_prefix dir_name task_dir rel
  root="$(osc_repo_root)"
  ensure_dirs "$root"
  tasks="$(osc_tasks_dir "$root")"
  date_prefix="$(osc_date_prefix)"
  dir_name="${date_prefix}-${slug}"
  task_dir="$tasks/$dir_name"
  mkdir -p "$task_dir"

  rel="${task_dir#$root/}"
  local task_json="$task_dir/$FILE_TASK_JSON"

  if [[ -z "$branch" ]]; then
    branch="task/${slug}"
  fi

  jq -n \
    --arg name "$title" \
    --arg branch "$branch" \
    --arg priority "$priority" \
    --arg description "$description" \
    --arg type "$task_type" \
    --arg depends "$depends" \
    '{name:$name, type:$type, branch:$branch, priority:$priority, description:$description, depends_on:(if $depends == "" then [] else ($depends | split(",")) end), status:"planned", current_phase:0, next_action:[]}' \
    >"$task_json"

  # Type-specific prd.md templates
  case "$task_type" in
    bugfix)
      cat >"$task_dir/prd.md" <<EOF
# Bugfix: ${title}

## 问题描述

## 复现步骤
1.
2.
3.

## 期望行为

## 实际行为

## 根因分析

## 修复方案

## 回归测试
- [ ]
EOF
      ;;
    hotfix)
      cat >"$task_dir/prd.md" <<EOF
# Hotfix: ${title}

## 问题描述（紧急）

## 影响范围

## 修复方案

## 验证步骤
- [ ]

## 后续跟进
EOF
      ;;
    refactor)
      cat >"$task_dir/prd.md" <<EOF
# Refactor: ${title}

## 现状

## 目标架构

## 影响范围
- 文件:
- API:
- 测试:

## 回归范围

## 分步计划
1.
2.
3.
EOF
      ;;
    docs)
      cat >"$task_dir/prd.md" <<EOF
# Docs: ${title}

## 变更内容

## 影响页面/文件

## 审核要点
EOF
      ;;
    *) # feature (default)
      cat >"$task_dir/prd.md" <<EOF
# PRD: ${title}

## Problem

## Goals

## Non-goals

## Acceptance criteria
EOF
      ;;
  esac

  cat >"$task_dir/info.md" <<'EOF'
# Tech notes

- Architecture decisions
- Risks / mitigations
- Rollback plan
EOF

  # Default contexts used by Claude hook injection
  cat >"$task_dir/implement.jsonl" <<'EOF'
{"file": ".osc/workflow.md", "reason": "Workflow"}
{"file": ".osc/spec/shared/index.md", "reason": "Shared specs"}
EOF
  cat >"$task_dir/check.jsonl" <<'EOF'
{"file": ".osc/spec/shared/index.md", "reason": "Shared specs"}
{"file": ".claude/commands/osc/finish-work.md", "reason": "Finish checklist"}
EOF
  cat >"$task_dir/debug.jsonl" <<'EOF'
{"file": ".osc/spec/shared/index.md", "reason": "Shared specs"}
EOF

  echo "created: $rel"
  osc_set_current_task "$rel" "$root"
  echo "current: $rel"
}

cmd_select() {
  require_jq
  local root="${1:-$(osc_repo_root)}"
  local task_rel="$2"
  osc_set_current_task "$task_rel" "$root"
  echo "current: $task_rel"

  # Auto branch management: checkout or create task branch
  local tj="$root/$task_rel/$FILE_TASK_JSON"
  if [[ -f "$tj" ]]; then
    local branch
    branch="$(jq -r '.branch // ""' "$tj" 2>/dev/null)"
    if [[ -n "$branch" ]]; then
      # Check if working tree is clean
      if ! git -C "$root" diff --quiet 2>/dev/null || ! git -C "$root" diff --cached --quiet 2>/dev/null; then
        echo "warn: working tree not clean, skipping branch switch (git stash first)"
      else
        if git -C "$root" show-ref --verify --quiet "refs/heads/$branch" 2>/dev/null; then
          git -C "$root" checkout "$branch" 2>/dev/null && echo "branch: switched to $branch" || echo "warn: could not switch to $branch"
        else
          git -C "$root" checkout -b "$branch" 2>/dev/null && echo "branch: created $branch" || echo "warn: could not create $branch"
        fi
      fi
    fi
  fi
}

cmd_archive() {
  local root="${1:-$(osc_repo_root)}"
  local task_rel="$2"
  local abs="$root/$task_rel"
  [[ -d "$abs" ]] || { echo "error: not found: $task_rel" >&2; exit 1; }
  local dest_dir
  dest_dir="$(osc_archive_dir "$root")"
  mkdir -p "$dest_dir"
  local base
  base="$(basename "$abs")"
  mv "$abs" "$dest_dir/$base"
  echo "archived: $task_rel -> ${dest_dir#$root/}/$base"
  local current
  current="$(osc_current_task_rel "$root")"
  if [[ "$current" == "$task_rel" ]]; then
    osc_clear_current_task "$root"
    echo "current cleared"
  fi
}

cmd_next() {
  require_jq
  local root
  root="$(osc_repo_root)"
  local found=""
  while IFS= read -r d; do
    local tj="$d/$FILE_TASK_JSON"
    [[ -f "$tj" ]] || continue
    local status
    status="$(jq -r '.status // "planned"' "$tj" 2>/dev/null)"
    [[ "$status" == "done" ]] && continue

    # Check dependencies: skip if any dependency is not done
    local blocked=false
    local deps
    deps="$(jq -r '.depends_on // [] | .[]' "$tj" 2>/dev/null)"
    while IFS= read -r dep; do
      [[ -n "$dep" ]] || continue
      local dep_json="$root/$dep/$FILE_TASK_JSON"
      if [[ -f "$dep_json" ]]; then
        local dep_status
        dep_status="$(jq -r '.status // "planned"' "$dep_json" 2>/dev/null)"
        if [[ "$dep_status" != "done" ]]; then
          blocked=true
          break
        fi
      fi
    done <<< "$deps"
    [[ "$blocked" == "true" ]] && continue

    found="${d#$root/}"
    break
  done < <(osc_list_task_dirs "$root")

  if [[ -z "$found" ]]; then
    echo "no pending tasks (all done or blocked)"
    return 0
  fi

  osc_set_current_task "$found" "$root"
  echo "switched to: $found"
}

cmd_clear() {
  local root="${1:-$(osc_repo_root)}"
  osc_clear_current_task "$root"
  echo "current cleared"
}

cmd_status() {
  require_jq
  local root task_rel task_dir task_json
  root="$(osc_repo_root)"
  task_rel="${1:-$(osc_current_task_rel "$root")}"
  [[ -n "$task_rel" ]] || { echo "error: no task selected" >&2; exit 1; }
  task_dir="$root/$task_rel"
  task_json="$task_dir/$FILE_TASK_JSON"
  [[ -f "$task_json" ]] || { echo "error: task.json not found" >&2; exit 1; }

  echo "Task: $task_rel"
  echo "---"
  jq -r '"Name: \(.name)\nStatus: \(.status)\nPriority: \(.priority)\nBranch: \(.branch)"' "$task_json"

  # Show progress log if exists
  local progress_log="$task_dir/progress.log"
  if [[ -f "$progress_log" ]]; then
    echo "---"
    echo "Progress:"
    tail -10 "$progress_log"
  fi
}

cmd_done() {
  require_jq
  local root task_rel task_dir task_json
  root="$(osc_repo_root)"
  task_rel="${1:-$(osc_current_task_rel "$root")}"
  [[ -n "$task_rel" ]] || { echo "error: no task selected" >&2; exit 1; }
  task_dir="$root/$task_rel"
  task_json="$task_dir/$FILE_TASK_JSON"
  [[ -f "$task_json" ]] || { echo "error: task.json not found" >&2; exit 1; }

  local tmp="${task_json}.tmp"
  local now
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  jq --arg now "$now" '.status = "done" | .completed_at = $now' "$task_json" >"$tmp" && mv "$tmp" "$task_json"

  # Append to progress log
  echo "[$now] DONE" >>"$task_dir/progress.log"

  echo "marked done: $task_rel"

  # Reset edit counter
  local edit_count_file="$root/$DIR_OSC/.edit-count"
  echo "0" > "$edit_count_file" 2>/dev/null || true

  # Branch merge hint
  local branch
  branch="$(jq -r '.branch // ""' "$task_json" 2>/dev/null)"
  if [[ -n "$branch" ]]; then
    local current_branch
    current_branch="$(git -C "$root" branch --show-current 2>/dev/null)"
    if [[ "$current_branch" == "$branch" ]]; then
      echo "---"
      echo "hint: you are on branch '$branch'"
      echo "  merge: git checkout main && git merge $branch"
      echo "  or PR: git push -u origin $branch"
    fi
  fi
}

cmd_progress() {
  local message="$1"
  [[ -n "$message" ]] || { echo "error: message required" >&2; exit 1; }

  local root task_rel task_dir
  root="$(osc_repo_root)"
  task_rel="${2:-$(osc_current_task_rel "$root")}"
  [[ -n "$task_rel" ]] || { echo "error: no task selected" >&2; exit 1; }
  task_dir="$root/$task_rel"
  [[ -d "$task_dir" ]] || { echo "error: task dir not found" >&2; exit 1; }

  local now
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "[$now] $message" >>"$task_dir/progress.log"
  echo "logged: $message"
}

main() {
  local cmd="${1:-}"
  case "$cmd" in
    list) shift; cmd_list ;;
    create) shift; cmd_create "${1:-}" "${@:2}" ;;
    select) shift; cmd_select "$(osc_repo_root)" "${1:-}" ;;
    next) shift; cmd_next ;;
    clear) shift; cmd_clear ;;
    archive) shift; cmd_archive "$(osc_repo_root)" "${1:-}" ;;
    status) shift; cmd_status "${1:-}" ;;
    done) shift; cmd_done "${1:-}" ;;
    progress) shift; cmd_progress "${1:-}" "${2:-}" ;;
    ""|-h|--help) usage ;;
    *) usage; exit 1 ;;
  esac
}

main "$@"

