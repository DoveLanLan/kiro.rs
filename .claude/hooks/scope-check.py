#!/usr/bin/env python3
"""
PostToolUse hook: scope check + auto task status + commit reminder.

1. Scope check: warn if edited file is outside task's implement.jsonl scope.
2. Auto status: transition task from "planned" → "in_progress" on first code edit.
3. Commit reminder: after N edits, remind to commit.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _osc_utils import (
    DIR_OSC,
    check_change_artifacts_exist,
    clear_change_pending,
    file_in_agent_scope,
    find_repo_root,
    get_current_task,
    get_task_change_status,
    hook_output,
    is_change_pending,
    load_agent_def,
    read_hook_input,
    read_json,
    read_text,
    relative_path,
    task_requires_change_workflow,
    update_task_change_status,
    validate_agent_def,
    write_json,
)

FILE_EDIT_COUNT = ".edit-count"
COMMIT_REMIND_THRESHOLD = 8


def auto_transition_status(repo_root: Path, task_dir: Path) -> str | None:
    """If task status is 'planned', transition to 'in_progress'."""
    task_json = task_dir / "task.json"
    obj = read_json(task_json)
    if not isinstance(obj, dict) or obj.get("status") != "planned":
        return None
    try:
        obj["status"] = "in_progress"
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        obj["started_at"] = now
        write_json(task_json, obj)
        with open(task_dir / "progress.log", "a", encoding="utf-8") as f:
            f.write(f"[{now}] Status: planned → in_progress (auto)\n")
        task_rel = str(task_dir.relative_to(repo_root))
        return f"[osc] 任务状态自动更新: planned → in_progress ({task_rel})"
    except Exception:
        return None


def increment_edit_count(repo_root: Path) -> int:
    """Increment and return the edit counter."""
    count_file = repo_root / DIR_OSC / FILE_EDIT_COUNT
    count = 0
    try:
        count = int(count_file.read_text(encoding="utf-8").strip())
    except Exception:
        pass
    count += 1
    try:
        count_file.parent.mkdir(parents=True, exist_ok=True)
        count_file.write_text(str(count), encoding="utf-8")
    except Exception:
        pass
    return count


def reset_edit_count(repo_root: Path) -> None:
    """Reset the edit counter (called externally after commit)."""
    count_file = repo_root / DIR_OSC / FILE_EDIT_COUNT
    try:
        count_file.write_text("0", encoding="utf-8")
    except Exception:
        pass


def load_scope_files(task_dir: Path) -> set[str]:
    """Load file paths from implement.jsonl as the expected scope."""
    scope: set[str] = set()
    impl_file = task_dir / "implement.jsonl"
    if not impl_file.exists():
        return scope
    for line in read_text(impl_file).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            f = obj.get("file", "")
            if f:
                scope.add(f)
        except Exception:
            pass
    return scope


def main() -> int:
    input_data = read_hook_input()
    if not input_data:
        return 0

    cwd = Path(input_data.get("cwd", os.getcwd()))
    repo_root = find_repo_root(cwd)
    if not repo_root:
        return 0

    # Parse file_path and rel_path early (needed for change-pending check)
    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "") or tool_input.get("path", "")
    if not file_path:
        return 0

    rel_path = relative_path(file_path, repo_root)
    if not rel_path:
        return 0

    # --- Change-pending enforcement (task-aware) ---
    task_rel = get_current_task(repo_root)

    # Task-level change-workflow check (preferred over global .change-pending)
    if task_rel and task_requires_change_workflow(repo_root, task_rel):
        cw_status = get_task_change_status(repo_root, task_rel)
        if cw_status == "pending":
            if check_change_artifacts_exist(repo_root, task_rel):
                # Artifacts found — update status and allow
                update_task_change_status(repo_root, task_rel, "ready")
                clear_change_pending(repo_root)
            elif not rel_path.startswith(".osc/"):
                hook_output(
                    "PostToolUse",
                    f"[osc] BLOCKED: change-workflow 产物未创建。\n"
                    f"当前任务 {task_rel} 需要 change-workflow（type 要求）。\n"
                    f"请先运行 /change-workflow，产物将写入 {task_rel}/changes/。\n"
                    f"或让用户输入「直接改」/「skip workflow」跳过。\n"
                    f"被阻止的文件: {rel_path}",
                )
                return 0
    else:
        # No task or task doesn't require change-workflow — enforce pending state if present
        pending = is_change_pending(repo_root)
        if pending:
            if task_rel and check_change_artifacts_exist(repo_root, task_rel):
                clear_change_pending(repo_root)
            elif not rel_path.startswith(".osc/"):
                if not task_rel:
                    hook_output(
                        "PostToolUse",
                        "[osc] BLOCKED: change-workflow 产物未创建。\n"
                        f"检测到 .change-pending（intent={pending.get('intent', '?')}），"
                        "且当前没有选中任务。\n"
                        "请先创建/选择任务，再运行 /change-workflow，产物路径为 "
                        ".osc/tasks/<task-dir>/changes/。\n"
                        "可用命令：`./.osc/scripts/task.sh create \"<title>\"` 或 "
                        "`./.osc/scripts/task.sh select .osc/tasks/<task-dir>`。\n"
                        f"被阻止的文件: {rel_path}",
                    )
                else:
                    hook_output(
                        "PostToolUse",
                        "[osc] BLOCKED: change-workflow 产物未创建。\n"
                        f"检测到 .change-pending（intent={pending.get('intent', '?')}），"
                        "但未找到 proposal.md + spec.md + tasks.md。\n"
                        "请先运行 /change-workflow 创建变更产物，"
                        "或让用户输入「直接改」/「skip workflow」跳过。\n"
                        f"被阻止的文件: {rel_path}",
                    )
                return 0
    if not task_rel:
        return 0

    task_dir = repo_root / task_rel
    if not task_dir.is_dir():
        return 0

    # Skip .osc/ and .claude/ internal files
    if rel_path.startswith(".osc/") or rel_path.startswith(".claude/"):
        return 0

    messages = []

    # --- Auto status transition ---
    status_msg = auto_transition_status(repo_root, task_dir)
    if status_msg:
        messages.append(status_msg)

    # --- Edit counter & commit reminder ---
    edit_count = increment_edit_count(repo_root)
    if edit_count == COMMIT_REMIND_THRESHOLD:
        messages.append(f"[osc] 已编辑 {edit_count} 个文件，建议先 git commit 保存进度。")
    elif edit_count > 0 and edit_count % (COMMIT_REMIND_THRESHOLD * 2) == 0:
        messages.append(f"[osc] 已累计编辑 {edit_count} 次，强烈建议 commit。")

    # --- Scope check (implement.jsonl) ---
    scope_files = load_scope_files(task_dir)
    if scope_files:
        in_scope = any(
            rel_path == sf or rel_path.startswith(sf + "/") or sf.startswith(rel_path)
            for sf in scope_files
        )
        if not in_scope:
            messages.append(
                f"[osc] ⚠ Scope 提醒: {rel_path} 不在当前任务的 implement.jsonl 范围内。\n"
                f"当前任务: {task_rel}\n"
                f"如果确实需要修改，请更新 implement.jsonl 或忽略此提示。"
            )

    # --- Agent definition scope check ---
    agent_name = os.environ.get("OSC_AGENT", "")
    if agent_name:
        agent_def = load_agent_def(repo_root, agent_name)
        if agent_def is None:
            messages.append(
                f"[osc] ⚠ Agent '{agent_name}' 定义文件不存在: "
                f".osc/agents/{agent_name}.yaml"
            )
        else:
            # Validate definition format on first encounter
            errors = validate_agent_def(agent_def)
            if errors:
                messages.append(
                    f"[osc] ⚠ Agent '{agent_name}' 定义校验失败:\n"
                    + "\n".join(f"  - {e}" for e in errors)
                )
            else:
                scope_list = agent_def.get("scope", [])
                if not file_in_agent_scope(rel_path, scope_list):
                    categories = ", ".join(scope_list) if scope_list else "(none)"
                    messages.append(
                        f"[osc] ⚠ Agent scope 提醒: {rel_path} 不在 agent "
                        f"'{agent_name}' 的声明范围内。\n"
                        f"Agent scope: [{categories}]\n"
                        f"如果确实需要修改，请更新 agent 定义或忽略此提示。"
                    )

    if messages:
        hook_output("PostToolUse", "\n\n".join(messages))
    else:
        # Output success marker even when no warnings
        sys.stderr.write("PostToolUse:scope-check hook success\n")
        sys.stderr.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
