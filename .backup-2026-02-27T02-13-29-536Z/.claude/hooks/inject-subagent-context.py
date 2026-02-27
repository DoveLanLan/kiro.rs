#!/usr/bin/env python3
"""
PreToolUse hook (Task tool): inject subagent context for multi-agent pipeline.

Reads:
- current task pointer: .osc/.current-task
- task directory files: prd.md / info.md / <agent>.jsonl

Outputs updated Task tool input with expanded prompt including relevant file contents.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


DIR_OSC = ".osc"
FILE_CURRENT_TASK = ".current-task"

AGENTS = {"implement", "check", "debug", "research", "plan"}
AGENTS_REQUIRE_TASK = {"implement", "check", "debug"}


def find_repo_root(start: Path) -> Path | None:
    current = start.resolve()
    while current != current.parent:
        if (current / DIR_OSC).is_dir():
            return current
        if (current / ".git").exists():
            return current
        current = current.parent
    return None


def read_text(path: Path, max_chars: int = 20_000) -> str:
    try:
        content = path.read_text(encoding="utf-8")
        if len(content) > max_chars:
            return content[:max_chars] + "\n…(truncated)"
        return content
    except Exception:
        return ""


def get_current_task(repo_root: Path) -> str | None:
    p = repo_root / DIR_OSC / FILE_CURRENT_TASK
    if not p.exists():
        return None
    raw = read_text(p).strip()
    return raw or None


def load_jsonl_context(repo_root: Path, jsonl_path: Path) -> list[dict]:
    items: list[dict] = []
    if not jsonl_path.exists():
        return items
    for line in read_text(jsonl_path).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict) and "file" in obj:
                items.append(obj)
        except json.JSONDecodeError:
            continue
    return items


def load_agent_yaml(repo_root: Path, agent_name: str) -> str:
    """Read .osc/agents/<agent_name>.yaml and return raw text (empty string if missing)."""
    p = repo_root / DIR_OSC / "agents" / f"{agent_name}.yaml"
    return read_text(p) if p.exists() else ""


def load_inbox_messages(repo_root: Path, agent_name: str, max_messages: int = 5) -> str:
    """Load recent inbox messages for an agent from running teams."""
    teams_dir = repo_root / DIR_OSC / "teams"
    if not teams_dir.is_dir():
        return ""

    messages: list[dict] = []
    for team_dir in teams_dir.iterdir():
        if not team_dir.is_dir():
            continue
        team_json = team_dir / "team.json"
        if not team_json.exists():
            continue
        try:
            team_data = json.loads(team_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if team_data.get("status") != "running":
            continue

        msg_dir = team_dir / "messages"
        if not msg_dir.is_dir():
            continue
        for msg_file in msg_dir.glob("*.json"):
            try:
                msg = json.loads(msg_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if not isinstance(msg, dict):
                continue
            to = msg.get("to", "")
            if to == agent_name or to == "*":
                messages.append(msg)

    if not messages:
        return ""

    messages.sort(key=lambda m: m.get("timestamp", ""), reverse=True)
    messages = messages[:max_messages]

    lines: list[str] = []
    for msg in messages:
        sender = msg.get("from", "unknown")
        msg_type = msg.get("type", "message")
        ts = msg.get("timestamp", "")
        body = msg.get("body", "")
        lines.append(f"[from: {sender} | type: {msg_type} | {ts}]")
        lines.append(body)
        lines.append("")

    return "\n".join(lines).rstrip()


def build_prompt(subagent: str, original_prompt: str, repo_root: Path, task_dir: Path | None) -> str:
    osc_dir = repo_root / DIR_OSC
    parts: list[str] = []
    parts.append(f"[osc] Subagent: {subagent}")
    parts.append(f"[osc] Repo root: {repo_root}")
    if task_dir:
        parts.append(f"[osc] Task dir: {task_dir.relative_to(repo_root)}")
    parts.append("")

    # Task docs
    if task_dir:
        prd = read_text(task_dir / "prd.md")
        info = read_text(task_dir / "info.md")
        if prd:
            parts.append("=== prd.md ===\n" + prd)
        if info:
            parts.append("=== info.md ===\n" + info)

    # Spec quick index (always available)
    parts.append("=== .osc/workflow.md ===\n" + read_text(osc_dir / "workflow.md"))
    parts.append("=== .osc/spec/shared/index.md ===\n" + read_text(osc_dir / "spec/shared/index.md"))

    # Agent capability metadata
    agent_yaml = load_agent_yaml(repo_root, subagent)
    if agent_yaml:
        parts.append("=== Agent capabilities ===\n" + agent_yaml)

    # Team inbox messages
    inbox_text = load_inbox_messages(repo_root, subagent)
    if inbox_text:
        parts.append("=== Team inbox (recent messages) ===\n" + inbox_text)

    # Agent-specific jsonl context
    if task_dir:
        jsonl = task_dir / f"{subagent}.jsonl"
        items = load_jsonl_context(repo_root, jsonl)
        if items:
            parts.append(f"=== {jsonl.name} (files) ===")
            for item in items:
                f = str(item.get("file", "")).strip()
                reason = str(item.get("reason", "")).strip()
                if not f:
                    continue
                content = read_text(repo_root / f)
                header = f"--- {f} ---" + (f" ({reason})" if reason else "")
                parts.append(header + "\n" + content)

    parts.append("\n=== Original prompt ===\n" + (original_prompt or ""))
    return "\n\n".join(parts)


def main() -> int:
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    tool_name = input_data.get("tool_name", "")
    if tool_name != "Task":
        return 0

    tool_input = input_data.get("tool_input", {}) or {}
    subagent_type = (tool_input.get("subagent_type", "") or "").strip()
    if subagent_type not in AGENTS:
        return 0

    cwd = Path(input_data.get("cwd", os.getcwd()))
    repo_root = find_repo_root(cwd)
    if not repo_root:
        return 0

    task_rel = get_current_task(repo_root)
    task_dir = repo_root / task_rel if task_rel else None
    if subagent_type in AGENTS_REQUIRE_TASK:
        if not task_rel or not task_dir or not task_dir.exists():
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "message": (
                        '[osc] No active task. Run '
                        '`./.osc/scripts/task.sh create "<title>"` '
                        'or `./.osc/scripts/task.sh select <task-dir>` '
                        'first for full context injection.'
                    ),
                }
            }
            print(json.dumps(output, ensure_ascii=False))
            return 0

    original_prompt = tool_input.get("prompt", "") or ""
    new_prompt = build_prompt(subagent_type, original_prompt, repo_root, task_dir)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": {**tool_input, "prompt": new_prompt},
        }
    }

    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

