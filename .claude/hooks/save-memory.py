#!/usr/bin/env python3
"""
SubagentStop hook: persist agent memory (discoveries, decisions, patterns, warnings).

Reads agent output from stdin, extracts key information, and appends to
.osc/memory/by-agent/<agent-type>.json.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _osc_utils import DIR_OSC, find_repo_root, get_current_task, read_hook_input, read_json, write_json

AGENTS = {"implement", "check", "debug", "research", "plan", "general-purpose", "Explore", "Bash"}
MAX_MEMORIES = 50

# Patterns for classifying memory type
PATTERNS: list[tuple[str, re.Pattern]] = [
    ("decision", re.compile(r"(?:决定|decided|chose|choose|选择|decision)", re.IGNORECASE)),
    ("warning", re.compile(r"(?:注意|warning|caveat|坑|caution|careful|小心)", re.IGNORECASE)),
    ("pattern", re.compile(r"(?:模式|pattern|best.?practice|惯例|convention)", re.IGNORECASE)),
    ("discovery", re.compile(r"(?:发现|found|discovered|discover|notice[d]?)", re.IGNORECASE)),
]


def classify_output(text: str) -> tuple[str, str]:
    """Return (type, summary) from agent output."""
    for mtype, pattern in PATTERNS:
        match = pattern.search(text)
        if match:
            start = max(0, text.rfind("\n", 0, match.start()) + 1)
            end = text.find("\n", match.end())
            if end == -1:
                end = min(len(text), match.end() + 200)
            summary = text[start:end].strip()[:200]
            return mtype, summary

    if len(text) > 200:
        return "discovery", text[:200].strip()

    return "", ""


def main() -> int:
    input_data = read_hook_input()
    if not input_data:
        return 0

    tool_input = input_data.get("tool_input", {}) or {}
    subagent_type = (tool_input.get("subagent_type", "") or "").strip()
    if subagent_type not in AGENTS:
        return 0

    tool_result = input_data.get("tool_result", "") or ""
    if not tool_result or len(tool_result) < 50:
        return 0

    cwd = Path(input_data.get("cwd", os.getcwd()))
    repo_root = find_repo_root(cwd)
    if not repo_root:
        return 0

    mtype, summary = classify_output(tool_result)
    if not mtype or not summary:
        return 0

    task_rel = get_current_task(repo_root) or ""
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    entry = {
        "id": f"mem-{int(time.time())}",
        "agent": subagent_type,
        "task": task_rel,
        "timestamp": timestamp,
        "type": mtype,
        "summary": summary,
        "detail": tool_result[:500] if len(tool_result) > 200 else "",
        "tags": [],
        "relevance": "medium",
    }

    memory_file = repo_root / DIR_OSC / "memory" / "by-agent" / f"{subagent_type}.json"
    memories = read_json(memory_file)
    if not isinstance(memories, list):
        memories = []

    memories.append(entry)

    # Trim to MAX_MEMORIES (keep newest)
    if len(memories) > MAX_MEMORIES:
        memories.sort(key=lambda m: m.get("timestamp", ""))
        memories = memories[-MAX_MEMORIES:]

    write_json(memory_file, memories)

    # Output success marker to stderr
    sys.stderr.write("SubagentStop:save-memory hook success\n")
    sys.stderr.flush()

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        # Silent failure — never block the workflow
        pass
