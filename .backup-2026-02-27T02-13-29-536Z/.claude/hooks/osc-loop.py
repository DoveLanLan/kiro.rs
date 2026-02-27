#!/usr/bin/env python3
"""
SubagentStop hook (check): enforce verify gates or completion markers.

If `.osc/worktree.yaml` has a `verify:` list, run those commands (all must pass) and block stop on failure.
If not configured, fall back to completion markers derived from `<task>/check.jsonl` reasons.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


DIR_OSC = ".osc"
FILE_CURRENT_TASK = ".current-task"
STATE_FILE = ".osc-state.json"
WORKTREE_YAML = ".osc/worktree.yaml"

TARGET_AGENT = "check"
MAX_ITERATIONS = 3
STATE_TIMEOUT_MINUTES = 30


def find_repo_root(start: Path) -> Path | None:
    current = start.resolve()
    while current != current.parent:
        if (current / DIR_OSC).is_dir():
            return current
        if (current / ".git").exists():
            return current
        current = current.parent
    return None


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def get_current_task(repo_root: Path) -> str | None:
    p = repo_root / DIR_OSC / FILE_CURRENT_TASK
    if not p.exists():
        return None
    v = read_text(p).strip()
    return v or None


def load_state(repo_root: Path) -> dict:
    p = repo_root / DIR_OSC / STATE_FILE
    try:
        return json.loads(read_text(p) or "{}")
    except Exception:
        return {}


def save_state(repo_root: Path, state: dict) -> None:
    p = repo_root / DIR_OSC / STATE_FILE
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception:
        pass


def parse_verify_commands(repo_root: Path) -> list[str]:
    p = repo_root / WORKTREE_YAML
    if not p.exists():
        return []
    lines = read_text(p).splitlines()
    in_verify = False
    cmds: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("verify:"):
            in_verify = True
            continue
        if in_verify and stripped.endswith(":") and not line.startswith((" ", "\t")):
            in_verify = False
            continue
        if in_verify:
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("- "):
                cmd = stripped[2:].strip()
                if cmd:
                    cmds.append(cmd)
    return cmds


def run_verify(repo_root: Path, cmds: list[str]) -> tuple[bool, str]:
    for cmd in cmds:
        try:
            r = subprocess.run(
                cmd,
                shell=True,
                cwd=str(repo_root),
                capture_output=True,
                timeout=120,
            )
            if r.returncode != 0:
                out = (r.stderr or b"" or r.stdout or b"").decode("utf-8", errors="replace")
                out = out.strip()
                if len(out) > 800:
                    out = out[:800] + "…"
                return False, f"Command failed: {cmd}\n{out}"
        except subprocess.TimeoutExpired:
            return False, f"Command timed out: {cmd}"
        except Exception as e:
            return False, f"Command error: {cmd} ({e})"
    return True, "All verify commands passed"


def completion_markers(repo_root: Path, task_rel: str) -> list[str]:
    check_jsonl = repo_root / task_rel / "check.jsonl"
    markers: list[str] = []
    if check_jsonl.exists():
        for line in read_text(check_jsonl).splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                reason = str(obj.get("reason", "")).strip()
                if reason:
                    m = reason.upper().replace(" ", "_") + "_FINISH"
                    if m not in markers:
                        markers.append(m)
            except json.JSONDecodeError:
                continue
    return markers or ["ALL_CHECKS_FINISH"]


def main() -> int:
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    if input_data.get("hook_event_name") != "SubagentStop":
        return 0

    if input_data.get("subagent_type") != TARGET_AGENT:
        return 0

    cwd = Path(input_data.get("cwd", os.getcwd()))
    repo_root = find_repo_root(cwd)
    if not repo_root:
        return 0

    task_rel = get_current_task(repo_root)
    if not task_rel:
        return 0

    # iteration state
    state = load_state(repo_root)
    now = datetime.now(timezone.utc)
    started_at = None
    try:
        started_at = datetime.fromisoformat(state.get("started_at")) if state.get("started_at") else None
    except Exception:
        started_at = None

    if state.get("task") != task_rel or not started_at or (now - started_at) > timedelta(minutes=STATE_TIMEOUT_MINUTES):
        state = {"task": task_rel, "iteration": 0, "started_at": now.isoformat()}

    state["iteration"] = int(state.get("iteration", 0)) + 1
    save_state(repo_root, state)

    if state["iteration"] >= MAX_ITERATIONS:
        state["iteration"] = 0
        save_state(repo_root, state)
        print(json.dumps({"decision": "allow", "reason": "Max iterations reached; allowing stop."}, ensure_ascii=False))
        return 0

    cmds = parse_verify_commands(repo_root)
    if cmds:
        ok, msg = run_verify(repo_root, cmds)
        if ok:
            state["iteration"] = 0
            save_state(repo_root, state)
            print(json.dumps({"decision": "allow", "reason": msg}, ensure_ascii=False))
        else:
            print(
                json.dumps(
                    {
                        "decision": "block",
                        "reason": f"Iteration {state['iteration']}/{MAX_ITERATIONS}. Verification failed:\n{msg}\n\nFix and try again.",
                    },
                    ensure_ascii=False,
                )
            )
        return 0

    # marker fallback
    agent_output = input_data.get("agent_output", "") or ""
    markers = completion_markers(repo_root, task_rel)
    missing = [m for m in markers if m not in agent_output]
    if not missing:
        state["iteration"] = 0
        save_state(repo_root, state)
        print(json.dumps({"decision": "allow", "reason": "Completion markers found."}, ensure_ascii=False))
        return 0

    print(
        json.dumps(
            {
                "decision": "block",
                "reason": f"Iteration {state['iteration']}/{MAX_ITERATIONS}. Missing markers: {', '.join(missing)}.\n\nRun the gates and only output markers after they pass.",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

