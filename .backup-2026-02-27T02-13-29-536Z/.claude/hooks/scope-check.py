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


DIR_OSC = ".osc"
FILE_CURRENT_TASK = ".current-task"
FILE_EDIT_COUNT = ".edit-count"
COMMIT_REMIND_THRESHOLD = 8


def find_repo_root(start: Path) -> Path | None:
    current = start.resolve()
    while current != current.parent:
        if (current / DIR_OSC).is_dir():
            return current
        if (current / ".git").exists():
            return current
        current = current.parent
    return None


def get_current_task(repo_root: Path) -> str | None:
    p = repo_root / DIR_OSC / FILE_CURRENT_TASK
    try:
        v = p.read_text(encoding="utf-8").strip()
        return v or None
    except Exception:
        return None


def auto_transition_status(repo_root: Path, task_dir: Path) -> str | None:
    """If task status is 'planned', transition to 'in_progress'. Returns message or None."""
    task_json = task_dir / "task.json"
    if not task_json.exists():
        return None
    try:
        obj = json.loads(task_json.read_text(encoding="utf-8"))
        if obj.get("status") != "planned":
            return None
        obj["status"] = "in_progress"
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        obj["started_at"] = now
        task_json.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        # Log to progress
        progress = task_dir / "progress.log"
        with open(progress, "a", encoding="utf-8") as f:
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
    scope = set()
    impl_file = task_dir / "implement.jsonl"
    if not impl_file.exists():
        return scope
    try:
        for line in impl_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            f = obj.get("file", "")
            if f:
                scope.add(f)
    except Exception:
        pass
    return scope


def main() -> int:
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    cwd = Path(input_data.get("cwd", os.getcwd()))
    repo_root = find_repo_root(cwd)
    if not repo_root:
        return 0

    task_rel = get_current_task(repo_root)
    if not task_rel:
        return 0

    task_dir = repo_root / task_rel
    if not task_dir.is_dir():
        return 0

    # Get the file being edited from tool input
    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "") or tool_input.get("path", "")
    if not file_path:
        return 0

    # Make path relative to repo root
    try:
        abs_path = Path(file_path).resolve()
        rel_path = str(abs_path.relative_to(repo_root.resolve()))
    except (ValueError, RuntimeError):
        return 0

    # Skip .osc/ and .claude/ internal files
    if rel_path.startswith(".osc/") or rel_path.startswith(".claude/"):
        return 0

    messages = []

    # --- 4.1: Auto status transition ---
    status_msg = auto_transition_status(repo_root, task_dir)
    if status_msg:
        messages.append(status_msg)

    # --- 4.4: Edit counter & commit reminder ---
    edit_count = increment_edit_count(repo_root)
    if edit_count == COMMIT_REMIND_THRESHOLD:
        messages.append(
            f"[osc] 已编辑 {edit_count} 个文件，建议先 git commit 保存进度。"
        )
    elif edit_count > 0 and edit_count % (COMMIT_REMIND_THRESHOLD * 2) == 0:
        messages.append(
            f"[osc] 已累计编辑 {edit_count} 次，强烈建议 commit。"
        )

    # --- Scope check ---
    scope_files = load_scope_files(task_dir)
    if scope_files:
        in_scope = False
        for sf in scope_files:
            if rel_path == sf or rel_path.startswith(sf + "/") or sf.startswith(rel_path):
                in_scope = True
                break
        if not in_scope:
            messages.append(
                f"[osc] ⚠ Scope 提醒: {rel_path} 不在当前任务的 implement.jsonl 范围内。\n"
                f"当前任务: {task_rel}\n"
                f"如果确实需要修改，请更新 implement.jsonl 或忽略此提示。"
            )

    if not messages:
        return 0

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "message": "\n\n".join(messages),
        }
    }
    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
