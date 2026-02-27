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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _osc_utils import (
    find_repo_root,
    get_current_task,
    is_team_enabled,
    read_text,
    run_team_command,
    scan_task_list,
    scan_unfinished_teams,
)


def should_skip() -> bool:
    # Multi-agent scripts can set this to avoid duplicate injections.
    return os.environ.get("CLAUDE_NON_INTERACTIVE") == "1"


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


def env_flag_enabled(name: str) -> bool:
    value = (os.environ.get(name) or "").strip().lower()
    return value in ("1", "true", "yes", "on")


def auto_resume_team(repo_root: Path, team: dict) -> str:
    """Auto start/resume one team. Returns one-line status."""
    team_id = str(team.get("id", ""))
    status = str(team.get("status", ""))
    if not team_id:
        return "  [skip] invalid team id"

    action = "start" if status == "created" else "resume"
    result = run_team_command(repo_root, [action, team_id], timeout_sec=30)
    if result.get("ok"):
        return f"  [ok] {action} {team_id}"

    err = result.get("stderr") or result.get("stdout") or f"exit {result.get('code')}"
    err_line = str(err).splitlines()[0] if err else "unknown error"
    return (
        f"  [degraded] {action} {team_id} failed: {err_line} "
        f"(manual: ./.osc/scripts/team.sh {action} {team_id})"
    )


def main() -> int:
    if should_skip():
        return 0

    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
    repo_root = find_repo_root(project_dir) or project_dir
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
    task_rel = get_current_task(repo_root)
    if task_rel:
        task_dir = repo_root / task_rel
        if task_dir.is_dir():
            print("<current-task>")
            print(f"Task: {task_rel}")
            prd = read_text(task_dir / "prd.md")
            if prd:
                print("\n## prd.md\n" + prd)
            info = read_text(task_dir / "info.md")
            if info:
                print("\n## info.md\n" + info)
            print("</current-task>\n")

    # Task list overview
    print("<task-list>")
    print("Tasks location: .osc/tasks/ (each subdir = one task with task.json/prd.md/progress.log)")
    print("Task commands: ./.osc/scripts/task.sh list | status | done | progress")
    print(scan_task_list(repo_root))
    print("</task-list>\n")

    # Detect unfinished teams (only when team system is enabled)
    unfinished = scan_unfinished_teams(repo_root) if is_team_enabled(repo_root) else []
    if unfinished:
        print("<unfinished-teams>")
        print("⚠️ 检测到未完成的团队任务，可以续接：")
        print("")
        for t in unfinished:
            print(f"  Team: {t['id']}")
            print(f"    模板: {t['template']} | 任务: {t['task']}")
            print(f"    状态: {t['status']} | 进度: {t['progress']} agents 完成")
            print(f"    Agents: {t['agents']}")
            print("")

        if env_flag_enabled("OSC_AUTO_TEAM_RESUME"):
            print("自动续接结果 (OSC_AUTO_TEAM_RESUME=1):")
            for t in unfinished:
                print(auto_resume_team(repo_root, t))
            print("")
        else:
            print("提示: 设置 OSC_AUTO_TEAM_RESUME=1 可在 SessionStart 自动执行 start/resume。")
            print("")

        print("手动续接命令:")
        print("  ./.osc/scripts/team.sh start <team-id>   # 启动 created 团队")
        print("  ./.osc/scripts/team.sh resume <team-id>  # 续接 running/stopped 团队")
        print("  ./.osc/scripts/team.sh status <team-id>  # 查看详细状态")
        print("  ./.osc/scripts/team.sh stop <team-id>    # 放弃该团队")
        print("</unfinished-teams>\n")

    # Workflow
    print("<workflow>")
    print(read_text(osc_dir / "workflow.md", "No .osc/workflow.md found"))
    print("</workflow>\n")

    # Spec indexes
    print("<guidelines>")
    print("## Shared")
    print(read_text(osc_dir / "spec" / "shared" / "index.md", "Not configured"))
    print("\n## Frontend")
    print(read_text(osc_dir / "spec" / "frontend" / "index.md", "Not configured"))
    print("\n## Backend")
    print(read_text(osc_dir / "spec" / "backend" / "index.md", "Not configured"))
    print("\n## Guides")
    print(read_text(osc_dir / "spec" / "guides" / "index.md", "Not configured"))
    print("</guidelines>\n")

    # Session instructions
    print("<instructions>")
    print(read_text(claude_dir / "commands" / "osc" / "start.md", "No start.md found"))
    print("</instructions>\n")

    print(
        """<ready>
Context loaded. Wait for user's first message, then follow <instructions>.
</ready>"""
    )

    # Output success marker for hook status
    sys.stderr.write("SessionStart:startup hook success\n")
    sys.stderr.flush()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
