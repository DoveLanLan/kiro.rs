#!/usr/bin/env python3
"""
PostToolUse hook: track changes to spec files.

When a file under .osc/spec/ is edited, appends a record to .osc/spec/changelog.log.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


DIR_OSC = ".osc"


def find_repo_root(start: Path) -> Path | None:
    current = start.resolve()
    while current != current.parent:
        if (current / DIR_OSC).is_dir():
            return current
        if (current / ".git").exists():
            return current
        current = current.parent
    return None


def main() -> int:
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    cwd = Path(input_data.get("cwd", os.getcwd()))
    repo_root = find_repo_root(cwd)
    if not repo_root:
        return 0

    # Get the file being edited
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

    # Only track .osc/spec/ files
    if not rel_path.startswith(".osc/spec/"):
        return 0

    # Get user identity
    user = os.environ.get("OPEN_SPEC_CODE_USER", "unknown")

    # Append to changelog
    changelog = repo_root / DIR_OSC / "spec" / "changelog.log"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        changelog.parent.mkdir(parents=True, exist_ok=True)
        with open(changelog, "a", encoding="utf-8") as f:
            f.write(f"[{now}] {user} edited {rel_path}\n")
    except Exception:
        return 0

    # Non-blocking info message
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "message": f"[osc] Spec 变更已记录: {rel_path} -> .osc/spec/changelog.log",
        }
    }
    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
