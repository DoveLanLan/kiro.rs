#!/usr/bin/env python3
"""
Stop hook: auto-log session summary to current task's progress.log.

When a session ends with an active task, appends a brief summary to the task's progress log.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


DIR_OSC = ".osc"
FILE_CURRENT_TASK = ".current-task"


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


def get_changed_files(repo_root: Path, max_files: int = 10) -> str:
    """Get list of changed files via git diff --stat."""
    try:
        r = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=3,
        )
        files = [f.strip() for f in r.stdout.strip().splitlines() if f.strip()]
        # Also include untracked files
        r2 = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=3,
        )
        untracked = [f.strip() for f in r2.stdout.strip().splitlines() if f.strip()]
        all_files = list(dict.fromkeys(files + untracked))  # dedupe, preserve order
        if not all_files:
            return ""
        shown = all_files[:max_files]
        extra = len(all_files) - len(shown)
        result = ", ".join(shown)
        if extra > 0:
            result += f" (+{extra} more)"
        return result
    except Exception:
        return ""


def cleanup_session_state(repo_root: Path) -> None:
    """Clean up session marker and reset counters."""
    osc_dir = repo_root / DIR_OSC
    # Remove session marker so next session start is detected
    for f in (".session-active", ".prompt-count", ".edit-count"):
        try:
            (osc_dir / f).unlink(missing_ok=True)
        except Exception:
            pass


def main() -> int:
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    cwd = Path(input_data.get("cwd", os.getcwd()))
    repo_root = find_repo_root(cwd)
    if not repo_root:
        return 0

    # Always clean up session state
    cleanup_session_state(repo_root)

    task_rel = get_current_task(repo_root)
    if not task_rel:
        return 0

    task_dir = repo_root / task_rel
    if not task_dir.is_dir():
        return 0

    # Append session end marker with changed files to progress log
    progress_log = task_dir / "progress.log"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    changed = get_changed_files(repo_root)
    if changed:
        entry = f"[{now}] Session ended. Changed: {changed}\n"
    else:
        entry = f"[{now}] Session ended (no uncommitted changes)\n"

    try:
        with open(progress_log, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
