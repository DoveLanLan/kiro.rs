#!/usr/bin/env python3
"""
SessionStart hook for open-spec-code (osc).

Injects:
- Current state (via .osc/scripts/get-context.sh)
- Current task details (prd.md / info.md from .osc/.current-task)
- Workflow (.osc/workflow.md)
- Spec indexes (.osc/spec/*/index.md)
- Session instructions (.claude/commands/osc/start.md)
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def should_skip() -> bool:
    # Multi-agent scripts can set this to avoid duplicate injections.
    return os.environ.get("CLAUDE_NON_INTERACTIVE") == "1"


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    while current != current.parent:
        if (current / ".osc").is_dir():
            return current
        if (current / ".git").exists():
            return current
        current = current.parent
    return start.resolve()


def read_file(path: Path, fallback: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return fallback


def get_current_task(osc_dir: Path) -> str | None:
    p = osc_dir / ".current-task"
    try:
        v = p.read_text(encoding="utf-8").strip()
        return v or None
    except Exception:
        return None


def scan_task_list(repo_root: Path) -> str:
    """Scan .osc/tasks/ and return a brief listing."""
    import json as _json
    tasks_dir = repo_root / ".osc" / "tasks"
    if not tasks_dir.is_dir():
        return "No tasks directory"
    lines = []
    for d in sorted(tasks_dir.iterdir()):
        if not d.is_dir():
            continue
        tj = d / "task.json"
        if not tj.exists():
            lines.append(f"- {d.name} (no task.json)")
            continue
        try:
            obj = _json.loads(tj.read_text(encoding="utf-8"))
            name = obj.get("name", d.name)
            status = obj.get("status", "?")
            priority = obj.get("priority", "")
            lines.append(f"- [{status}] {name} ({priority})")
        except Exception:
            lines.append(f"- {d.name}")
    return "\n".join(lines) if lines else "No tasks found"


def run_script(path: Path, cwd: Path) -> str:
    try:
        result = subprocess.run(
            [str(path)],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        out = (result.stdout or "").strip()
        return out if out else "No context available"
    except Exception:
        return "No context available"


def main() -> int:
    if should_skip():
        return 0

    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
    repo_root = find_repo_root(project_dir)
    osc_dir = repo_root / ".osc"
    claude_dir = repo_root / ".claude"

    print(
        """<session-context>
You are starting a new session in an open-spec-code managed project.
Read and follow all instructions below carefully.
</session-context>
"""
    )

    # Current state
    print("<current-state>")
    ctx = run_script(osc_dir / "scripts" / "get-context.sh", repo_root)
    print(ctx)
    print("</current-state>\n")

    # Current task context
    task_rel = get_current_task(osc_dir)
    if task_rel:
        task_dir = repo_root / task_rel
        if task_dir.is_dir():
            print("<current-task>")
            print(f"Task: {task_rel}")
            prd = read_file(task_dir / "prd.md")
            if prd:
                print("\n## prd.md\n" + prd)
            info = read_file(task_dir / "info.md")
            if info:
                print("\n## info.md\n" + info)
            print("</current-task>\n")

    # Task list overview (so Claude knows where tasks live)
    print("<task-list>")
    print("Tasks location: .osc/tasks/ (each subdir = one task with task.json/prd.md/progress.log)")
    print("Task commands: ./.osc/scripts/task.sh list | status | done | progress")
    print(scan_task_list(repo_root))
    print("</task-list>\n")

    # Workflow
    print("<workflow>")
    print(read_file(osc_dir / "workflow.md", "No .osc/workflow.md found"))
    print("</workflow>\n")

    # Spec indexes (keep it lightweight)
    print("<guidelines>")
    print("## Shared")
    print(read_file(osc_dir / "spec" / "shared" / "index.md", "Not configured"))
    print("\n## Frontend")
    print(read_file(osc_dir / "spec" / "frontend" / "index.md", "Not configured"))
    print("\n## Backend")
    print(read_file(osc_dir / "spec" / "backend" / "index.md", "Not configured"))
    print("\n## Guides")
    print(read_file(osc_dir / "spec" / "guides" / "index.md", "Not configured"))
    print("</guidelines>\n")

    # Session instructions
    print("<instructions>")
    print(read_file(claude_dir / "commands" / "osc" / "start.md", "No start.md found"))
    print("</instructions>\n")

    print(
        """<ready>
Context loaded. Wait for user's first message, then follow <instructions>.
</ready>"""
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

