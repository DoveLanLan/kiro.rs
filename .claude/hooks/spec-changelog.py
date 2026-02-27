#!/usr/bin/env python3
"""
PostToolUse hook: track changes to spec files.

When a file under .osc/spec/ is edited, appends a record to .osc/spec/changelog.log.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _osc_utils import DIR_OSC, find_repo_root, hook_output, read_hook_input, relative_path


def main() -> int:
    input_data = read_hook_input()
    if not input_data:
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

    rel_path = relative_path(file_path, repo_root)
    if not rel_path or not rel_path.startswith(".osc/spec/"):
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

    hook_output("PostToolUse", f"[osc] Spec 变更已记录: {rel_path} -> .osc/spec/changelog.log")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
