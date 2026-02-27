#!/usr/bin/env python3
"""
PostToolUse hook: detect file conflicts between concurrent agents in a team.

When an agent edits a file, check if any other running agent in the same team
has also edited or locked that file. If so, warn about potential conflicts.
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
    find_repo_root,
    hook_output,
    read_hook_input,
    read_json,
    relative_path,
    write_json,
)


def get_running_teams(repo_root: Path) -> list[Path]:
    """Find all running team directories."""
    teams_dir = repo_root / DIR_OSC / "teams"
    if not teams_dir.is_dir():
        return []
    result = []
    for d in teams_dir.iterdir():
        if not d.is_dir():
            continue
        data = read_json(d / "team.json")
        if isinstance(data, dict) and data.get("status") == "running":
            result.append(d)
    return result


def record_file_edit(team_dir: Path, agent_name: str, file_path: str) -> None:
    """Record that an agent edited a file, for conflict tracking."""
    edits_file = team_dir / "file-edits" / "edits.json"
    edits = read_json(edits_file)
    if not isinstance(edits, list):
        edits = []

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    edits.append({"agent": agent_name, "file": file_path, "timestamp": now})

    # Keep only last 200 entries
    if len(edits) > 200:
        edits = edits[-200:]

    write_json(edits_file, edits)


def check_conflicts(team_dir: Path, current_agent: str, file_path: str) -> list[str]:
    """Check if other agents have edited the same file."""
    edits = read_json(team_dir / "file-edits" / "edits.json")
    if not isinstance(edits, list):
        return []

    other_agents = {
        edit.get("agent", "unknown")
        for edit in edits
        if edit.get("file") == file_path and edit.get("agent") != current_agent
    }
    if not other_agents:
        return []

    agents_str = ", ".join(sorted(other_agents))
    return [
        f"[osc] ⚠️ 文件冲突预警: {file_path}\n"
        f"  当前 agent: {current_agent}\n"
        f"  同一文件也被以下 agent 编辑过: {agents_str}\n"
        f"  团队: {team_dir.name}\n"
        f"  建议: 检查是否有冲突，必要时协调分工或手动 merge。"
    ]


def detect_current_agent() -> str:
    """Try to detect the current agent name from environment."""
    for var in ("CLAUDE_AGENT_NAME", "OSC_AGENT_NAME"):
        val = os.environ.get(var, "").strip()
        if val:
            return val
    return "unknown"


def main() -> int:
    input_data = read_hook_input()
    if not input_data:
        return 0

    if input_data.get("tool_name", "") not in ("Edit", "Write"):
        return 0

    cwd = Path(input_data.get("cwd", os.getcwd()))
    repo_root = find_repo_root(cwd)
    if not repo_root:
        return 0

    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "") or tool_input.get("path", "")
    if not file_path:
        return 0

    rel_path = relative_path(file_path, repo_root)
    if not rel_path:
        return 0

    # Skip internal files
    if rel_path.startswith(".osc/") or rel_path.startswith(".claude/"):
        return 0

    current_agent = detect_current_agent()
    running_teams = get_running_teams(repo_root)
    if not running_teams:
        return 0

    messages = []
    for team_dir in running_teams:
        record_file_edit(team_dir, current_agent, rel_path)
        messages.extend(check_conflicts(team_dir, current_agent, rel_path))

    if messages:
        hook_output("PostToolUse", "\n\n".join(messages))
    else:
        # Output success marker even when no conflicts
        sys.stderr.write("PostToolUse:conflict-detect hook success\n")
        sys.stderr.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
