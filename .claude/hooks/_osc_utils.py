"""Shared utilities for Claude Code hook scripts.

All hooks in this directory can import from this module after adding
the hook directory to sys.path:

    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _osc_utils import find_repo_root, read_hook_input, ...
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

DIR_OSC = ".osc"
FILE_CURRENT_TASK = ".current-task"
FILE_CHANGE_PENDING = ".change-pending"
FILE_OSC_CONFIG = "osc-config.json"


def find_repo_root(start: Path | None = None) -> Path | None:
    """Walk up from *start* (default: cwd) looking for .osc/ or .git/."""
    if start is None:
        start = Path.cwd()
    current = start.resolve()
    while current != current.parent:
        if (current / DIR_OSC).is_dir():
            return current
        if (current / ".git").exists():
            return current
        current = current.parent
    return None


def get_current_task(repo_root: Path) -> str | None:
    """Read .osc/.current-task → relative task path, or None."""
    p = repo_root / DIR_OSC / FILE_CURRENT_TASK
    try:
        v = p.read_text(encoding="utf-8").strip()
        if not v:
            return None
        rel = normalize_rel_path(v)
        if not rel:
            return None
        if not (repo_root / rel).is_dir():
            return None
        return rel
    except Exception:
        return None


def read_text(path: Path, fallback: str = "", max_chars: int = 0) -> str:
    """Read a text file safely. Returns *fallback* on any error."""
    try:
        content = path.read_text(encoding="utf-8")
        if max_chars > 0 and len(content) > max_chars:
            return content[:max_chars] + "\n…(truncated)"
        return content
    except Exception:
        return fallback


def read_hook_input() -> dict:
    """Parse JSON from stdin. Returns empty dict on failure or empty input."""
    try:
        raw = sys.stdin.read()
        if not raw or not raw.strip():
            return {}
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def read_json(path: Path) -> Any:
    """Read and parse a JSON file. Returns None on failure."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def normalize_rel_path(path_value: str | None) -> str:
    """Normalize a repo-relative path for stable comparisons."""
    if not path_value:
        return ""
    value = str(path_value).strip().replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    return value.rstrip("/")


# ---------------------------------------------------------------------------
# OSC config
# ---------------------------------------------------------------------------

def read_osc_config(repo_root: Path) -> dict[str, Any]:
    """Read .osc/osc-config.json. Returns empty dict on failure."""
    config_path = repo_root / DIR_OSC / FILE_OSC_CONFIG
    data = read_json(config_path)
    return data if isinstance(data, dict) else {}


def is_team_enabled(repo_root: Path) -> bool:
    """Check if the team system is enabled for this environment.

    Reads ``teamSystem`` from ``.osc/osc-config.json``:
    - ``"codex-only"``  → enabled only when ``OSC_RUNTIME=codex``
    - ``"all"``         → always enabled (default when key is absent)
    - ``"disabled"``    → always disabled
    """
    config = read_osc_config(repo_root)
    mode = str(config.get("teamSystem", "all")).strip().lower()
    if mode == "disabled":
        return False
    if mode == "codex-only":
        return os.environ.get("OSC_RUNTIME", "").lower() == "codex"
    return True  # "all" or unrecognized → enabled


def run_team_command(
    repo_root: Path,
    args: list[str],
    timeout_sec: int = 20,
) -> dict[str, Any]:
    """Run .osc/scripts/team.sh command and return structured result."""
    script = repo_root / DIR_OSC / "scripts" / "team.sh"
    if not script.exists():
        return {
            "ok": False,
            "code": 127,
            "stdout": "",
            "stderr": f"team script not found: {script}",
            "cmd": [],
        }

    cmd = [str(script)] + args
    if not os.access(script, os.X_OK):
        cmd = ["bash", str(script)] + args

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "code": 124,
            "stdout": "",
            "stderr": f"team command timed out after {timeout_sec}s",
            "cmd": cmd,
        }
    except Exception as exc:
        return {
            "ok": False,
            "code": 1,
            "stdout": "",
            "stderr": str(exc),
            "cmd": cmd,
        }

    return {
        "ok": proc.returncode == 0,
        "code": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
        "cmd": cmd,
    }


def find_task_teams(
    repo_root: Path,
    task_rel: str | None,
    statuses: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """Return teams for a task, optionally filtered by status."""
    normalized_task = normalize_rel_path(task_rel)
    if not normalized_task:
        return []

    teams_dir = repo_root / DIR_OSC / "teams"
    if not teams_dir.is_dir():
        return []

    teams: list[dict[str, Any]] = []
    for team_dir in sorted(teams_dir.iterdir(), key=lambda p: p.name, reverse=True):
        if not team_dir.is_dir():
            continue
        tdata = read_json(team_dir / "team.json")
        if not isinstance(tdata, dict):
            continue
        team_task = normalize_rel_path(str(tdata.get("task", "")))
        status = str(tdata.get("status", ""))
        if team_task != normalized_task:
            continue
        if statuses and status not in statuses:
            continue
        merged = dict(tdata)
        merged["_team_dir"] = str(team_dir)
        teams.append(merged)
    return teams


def find_existing_active_team(repo_root: Path, task_rel: str | None) -> dict[str, Any] | None:
    """Find latest created/running team for a task."""
    matches = find_task_teams(repo_root, task_rel, statuses=("created", "running"))
    return matches[0] if matches else None


def scan_unfinished_teams(repo_root: Path) -> list[dict[str, Any]]:
    """Scan .osc/teams and collect teams that are created/running."""
    teams_dir = repo_root / DIR_OSC / "teams"
    if not teams_dir.is_dir():
        return []

    unfinished: list[dict[str, Any]] = []
    for team_dir in sorted(teams_dir.iterdir(), key=lambda p: p.name):
        if not team_dir.is_dir():
            continue
        tdata = read_json(team_dir / "team.json")
        if not isinstance(tdata, dict):
            continue

        status = str(tdata.get("status", ""))
        if status not in ("running", "created"):
            continue

        team_id = str(tdata.get("id", team_dir.name))
        template = str(tdata.get("template", "?"))
        task = str(tdata.get("task", "?"))
        roles = tdata.get("roles", [])
        if not isinstance(roles, list):
            roles = []

        completed = 0
        agent_statuses: list[str] = []
        for role in roles:
            if not isinstance(role, dict):
                continue
            agent_name = str(role.get("agent", "?"))
            agent_status = str(role.get("status", "pending"))
            ad = read_json(team_dir / "agents" / f"{agent_name}.json")
            if isinstance(ad, dict):
                agent_status = str(ad.get("status", agent_status))
            if agent_status in ("completed", "done"):
                completed += 1
            agent_statuses.append(f"{agent_name}[{agent_status}]")

        unfinished.append(
            {
                "id": team_id,
                "template": template,
                "task": task,
                "status": status,
                "progress": f"{completed}/{len(roles)}",
                "agents": ", ".join(agent_statuses),
            }
        )
    return unfinished


def write_json(path: Path, data: Any, indent: int = 2) -> bool:
    """Write *data* as JSON. Creates parent dirs. Returns True on success."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=indent) + "\n",
            encoding="utf-8",
        )
        return True
    except Exception:
        return False


def relative_path(file_path: str, repo_root: Path) -> str | None:
    """Make *file_path* relative to *repo_root*. Returns None on failure."""
    try:
        abs_path = Path(file_path).resolve()
        return str(abs_path.relative_to(repo_root.resolve()))
    except (ValueError, RuntimeError):
        return None


def hook_output(event_name: str, message: str = "", **extra: Any) -> None:
    """Print hook-specific JSON output to stdout and success marker to stderr."""
    inner: dict[str, Any] = {"hookEventName": event_name}
    if message:
        inner["message"] = message
    inner.update(extra)
    print(json.dumps({"hookSpecificOutput": inner}, ensure_ascii=False))

    # Output success marker to stderr for visibility
    status = "success" if message else "success"
    sys.stderr.write(f"{event_name} hook {status}\n")
    sys.stderr.flush()


# ---------------------------------------------------------------------------
# Minimal YAML parser (handles the subset used by agent definitions)
# ---------------------------------------------------------------------------

def parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the simple YAML subset used by agent/team-template definitions.

    Handles: scalars, block lists (``- item``), inline lists (``[a, b]``),
    one-level nested maps.  Does NOT handle anchors, tags, multi-line scalars.
    """
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-2, root)]  # (indent, container)

    def _scalar(s: str) -> Any:
        s = s.strip()
        if not s:
            return ""
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            return s[1:-1]
        if s == "true":
            return True
        if s == "false":
            return False
        if s == "null":
            return None
        try:
            return int(s)
        except ValueError:
            pass
        try:
            return float(s)
        except ValueError:
            pass
        return s

    def _strip_comment(line: str) -> str:
        in_sq = in_dq = False
        for i, ch in enumerate(line):
            if ch == "'" and not in_dq:
                in_sq = not in_sq
            elif ch == '"' and not in_sq:
                in_dq = not in_dq
            elif ch == "#" and not in_sq and not in_dq and (i == 0 or line[i - 1] == " "):
                return line[:i]
        return line

    lines = text.split("\n")
    for idx, raw in enumerate(lines):
        stripped = _strip_comment(raw).rstrip()
        content = stripped.lstrip()
        if not content:
            continue
        indent = len(stripped) - len(content)

        # Pop deeper/equal entries
        while len(stack) > 1 and stack[-1][0] >= indent:
            stack.pop()

        # List item
        if content.startswith("- "):
            item = content[2:].strip()
            _, container = stack[-1]
            if not isinstance(container, list):
                continue
            if ":" in item:
                obj: dict[str, Any] = {}
                ci = item.index(":")
                k = item[:ci].strip()
                v = item[ci + 1 :].strip()
                if v.startswith("[") and v.endswith("]"):
                    obj[k] = [_scalar(x) for x in v[1:-1].split(",") if x.strip()]
                else:
                    obj[k] = _scalar(v)
                container.append(obj)
                stack.append((indent + 1, obj))
            else:
                container.append(_scalar(item))
            continue

        # Key: value
        ci = content.find(":")
        if ci > 0:
            key = content[:ci].strip()
            rest = content[ci + 1 :].strip()
            _, container = stack[-1]
            if not isinstance(container, dict):
                continue
            if not rest:
                # Peek next non-empty line to decide list vs map
                nxt = ""
                for j in range(idx + 1, len(lines)):
                    t = lines[j].strip()
                    if t and not t.startswith("#"):
                        nxt = t
                        break
                if nxt.startswith("- "):
                    container[key] = []
                    stack.append((indent + 1, container[key]))
                else:
                    container[key] = {}
                    stack.append((indent + 1, container[key]))
            elif rest.startswith("[") and rest.endswith("]"):
                container[key] = [_scalar(x) for x in rest[1:-1].split(",") if x.strip()]
            else:
                container[key] = _scalar(rest)

    return root


# ---------------------------------------------------------------------------
# Agent definition helpers
# ---------------------------------------------------------------------------

AGENT_REQUIRED_FIELDS = ("name", "scope", "tools")

KNOWN_TOOLS = frozenset({
    "Read", "Edit", "Write", "Bash", "Grep", "Glob",
    "WebFetch", "WebSearch", "Task", "NotebookEdit",
})

# Maps agent scope categories → file-path prefixes / patterns.
# "all" means no restriction.
SCOPE_PATH_MAP: dict[str, list[str]] = {
    "source-code": ["src/", "lib/", "bin/", "app/", "pkg/", "cmd/", "internal/"],
    "tests":       ["test/", "tests/", "__tests__/", "spec/"],
    "config":      [".env", "package.json", "tsconfig", "jest.config", "vite.config",
                    "webpack.config", ".eslintrc", ".prettierrc", "Makefile",
                    "Dockerfile", "docker-compose", "pyproject.toml", "setup.cfg"],
    "docs":        ["docs/", "doc/", "README", "CHANGELOG", "LICENSE"],
    "specs":       [".osc/spec/", ".osc/tasks/"],
    "tasks":       [".osc/tasks/"],
    "logs":        ["logs/", ".log"],
    "external":    [],  # web-only, no file restrictions enforced
}


def load_agent_def(repo_root: Path, agent_name: str) -> dict[str, Any] | None:
    """Load and parse an agent YAML definition. Returns None if not found."""
    agent_file = repo_root / DIR_OSC / "agents" / f"{agent_name}.yaml"
    if not agent_file.is_file():
        return None
    try:
        return parse_simple_yaml(agent_file.read_text(encoding="utf-8"))
    except Exception:
        return None


def validate_agent_def(agent_def: dict[str, Any]) -> list[str]:
    """Validate an agent definition dict. Returns a list of error messages (empty = valid)."""
    errors: list[str] = []
    if not isinstance(agent_def, dict):
        return ["agent definition is not a mapping"]

    for field in AGENT_REQUIRED_FIELDS:
        if field not in agent_def:
            errors.append(f"missing required field: {field}")

    name = agent_def.get("name", "")
    if name and not isinstance(name, str):
        errors.append("'name' must be a string")

    scope = agent_def.get("scope")
    if scope is not None:
        if not isinstance(scope, list):
            errors.append("'scope' must be a list")

    tools = agent_def.get("tools")
    if tools is not None:
        if not isinstance(tools, list):
            errors.append("'tools' must be a list")
        else:
            unknown = [t for t in tools if t not in KNOWN_TOOLS]
            if unknown:
                errors.append(f"unknown tools: {', '.join(unknown)}")

    return errors


def file_in_agent_scope(rel_path: str, scope_list: list[str]) -> bool:
    """Check whether *rel_path* falls within the agent's declared scope categories.

    Returns True if the file is in scope (or scope is unrestricted).
    """
    if not scope_list or "all" in scope_list:
        return True

    for category in scope_list:
        prefixes = SCOPE_PATH_MAP.get(category, [])
        for prefix in prefixes:
            # Directory prefixes (ending with /) — check path starts with it
            if prefix.endswith("/") and rel_path.startswith(prefix):
                return True
            # File-name fragments (e.g. ".log", "package.json") — check basename
            if not prefix.endswith("/"):
                base = rel_path.rsplit("/", 1)[-1] if "/" in rel_path else rel_path
                if base == prefix or base.startswith(prefix) or base.endswith(prefix):
                    return True

    # Also allow test-like filenames for "tests" scope
    if "tests" in scope_list:
        base = rel_path.rsplit("/", 1)[-1] if "/" in rel_path else rel_path
        if ".test." in base or ".spec." in base or base.startswith("test_"):
            return True

    return False


def scan_task_list(repo_root: Path) -> str:
    """Scan .osc/tasks/ and return a brief listing."""
    tasks_dir = repo_root / DIR_OSC / "tasks"
    if not tasks_dir.is_dir():
        return "No tasks directory"
    lines: list[str] = []
    for d in sorted(tasks_dir.iterdir()):
        if not d.is_dir():
            continue
        tj = d / "task.json"
        if not tj.exists():
            lines.append(f"- {d.name} (no task.json)")
            continue
        try:
            obj = json.loads(tj.read_text(encoding="utf-8"))
            name = obj.get("name", d.name)
            status = obj.get("status", "?")
            priority = obj.get("priority", "")
            lines.append(f"- [{status}] {name} ({priority})")
        except Exception:
            lines.append(f"- {d.name}")
    return "\n".join(lines) if lines else "No tasks found"


# ---------------------------------------------------------------------------
# Change-pending state management
# ---------------------------------------------------------------------------

def write_change_pending(repo_root: Path, intent: str, prompt_summary: str) -> bool:
    """Create .osc/.change-pending to signal that change-workflow is required.

    Returns True on success.
    """
    from datetime import datetime, timezone

    pending_path = repo_root / DIR_OSC / FILE_CHANGE_PENDING
    data = {
        "intent": intent,
        "prompt_summary": prompt_summary[:300],
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return write_json(pending_path, data)


def is_change_pending(repo_root: Path) -> dict[str, Any] | None:
    """Read .osc/.change-pending and return its content, or None if absent."""
    pending_path = repo_root / DIR_OSC / FILE_CHANGE_PENDING
    data = read_json(pending_path)
    if isinstance(data, dict) and data.get("intent"):
        return data
    return None


def check_change_artifacts_exist(repo_root: Path, task_rel: str | None = None) -> bool:
    """Check if change-workflow artifacts (proposal.md, spec.md, tasks.md) exist.

    Rules:
    1. If task_rel is provided, check ONLY <task_dir>/changes/ (strict task mode).
    2. If task_rel is not provided, return False (task is mandatory).
    """
    if not task_rel:
        return False

    required = ("proposal.md", "spec.md", "tasks.md")

    # Task-level check (strict)
    rel = normalize_rel_path(task_rel)
    if not rel:
        return False

    task_dir = repo_root / rel
    if not task_dir.is_dir():
        return False

    task_changes = task_dir / "changes"
    return task_changes.is_dir() and all((task_changes / f).is_file() for f in required)


def clear_change_pending(repo_root: Path) -> bool:
    """Delete .osc/.change-pending. Returns True if removed (or already absent)."""
    pending_path = repo_root / DIR_OSC / FILE_CHANGE_PENDING
    try:
        pending_path.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def task_requires_change_workflow(repo_root: Path, task_rel: str | None) -> bool:
    """Check if a task requires change-workflow based on task.json.

    Returns True (conservative) if task_rel is None or field is missing.
    """
    if not task_rel:
        return True
    tj = repo_root / task_rel / "task.json"
    obj = read_json(tj)
    if not isinstance(obj, dict):
        return True
    return obj.get("requires_change_workflow", True)


def get_task_change_status(repo_root: Path, task_rel: str | None) -> str | None:
    """Read change_workflow_status from task.json. Returns None if not applicable."""
    if not task_rel:
        return None
    tj = repo_root / task_rel / "task.json"
    obj = read_json(tj)
    if not isinstance(obj, dict):
        return None
    return obj.get("change_workflow_status")


def update_task_change_status(repo_root: Path, task_rel: str, status: str) -> bool:
    """Update change_workflow_status in task.json."""
    tj = repo_root / task_rel / "task.json"
    obj = read_json(tj)
    if not isinstance(obj, dict):
        return False
    obj["change_workflow_status"] = status
    return write_json(tj, obj)
