#!/usr/bin/env python3
"""
UserPromptSubmit hook: intent detection + requirement capture + context decay compensation + session resume.

Features:
1. Intent detection: guide Claude to use appropriate skills
2. Requirement capture: auto-log user requirements to requirements.log
3. Context decay: re-inject key rules every N prompts to fight context window decay
4. Session resume: detect context loss after compaction and re-inject
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _osc_utils import (
    DIR_OSC,
    check_change_artifacts_exist,
    clear_change_pending,
    find_existing_active_team,
    find_repo_root,
    get_current_task,
    hook_output,
    is_change_pending,
    is_team_enabled,
    read_hook_input,
    read_json,
    read_text,
    run_team_command,
    scan_task_list,
    task_requires_change_workflow,
    update_task_change_status,
    write_change_pending,
)

FILE_PROMPT_COUNT = ".prompt-count"
FILE_SESSION_MARKER = ".session-active"
FILE_REQUIREMENTS_LOG = "requirements.log"
CONTEXT_REINJECT_INTERVAL = 15

# Requirement capture keywords (more specific than intent patterns)
# These indicate user is stating a concrete requirement, not just discussing
REQUIREMENT_KEYWORDS = [
    # Prefix patterns (recommended for clarity) - use \A for start of string
    r"(?i)\Achange\s*[:：]",
    r"(?i)\Abug\s*[:：]",
    r"(?i)\Afix\s*[:：]",
    r"(?i)\Afeature\s*[:：]",
    r"(?i)\A需求\s*[:：]",
    r"(?i)\A问题\s*[:：]",
    # Chinese - action verbs indicating concrete changes
    r"要增加", r"要添加", r"要修改", r"要调整", r"要删除", r"要去掉", r"要改成", r"要换成",
    r"需要增加", r"需要添加", r"需要修改", r"需要调整",
    r"帮我[加增添]", r"帮我[改修]", r"帮我[删去移]",
    r"现在有个[调修改]", r"有个.{0,3}需求", r"有个调整", r"有个修改",
    r"[这那]个[页面功能模块].+[要需]",
    r"上传框.+[增加添加]", r"[增加添加].+提示", r"[增加添加].+按钮", r"[增加添加].+字段", r"[增加添加].+功能",
    # Bug reports
    r"有一个bug", r"有个bug", r"发现.+bug", r"这个bug", r"那个bug",
    r".+有问题", r".+出问题了", r".+不对", r".+报错",
    # English
    r"(?i)please\s+add", r"(?i)please\s+change", r"(?i)please\s+modify",
    r"(?i)please\s+update", r"(?i)please\s+remove", r"(?i)please\s+delete",
    r"(?i)need\s+to\s+add", r"(?i)need\s+to\s+change", r"(?i)need\s+to\s+modify",
    r"(?i)want\s+to\s+add", r"(?i)want\s+to\s+change",
    r"(?i)should\s+add", r"(?i)should\s+have",
    r"(?i)add\s+a\s+.+\s+(button|field|tooltip|hint|message)",
    r"(?i)change\s+the\s+.+\s+to",
    # Bug reports - English
    r"(?i)there\s+is\s+a\s+bug", r"(?i)found\s+a\s+bug", r"(?i)there'?s\s+a\s+bug",
    r"(?i)bug\s*:\s*.+", r"(?i).+is\s+broken", r"(?i).+doesn'?t\s+work",
]

# Intent patterns (Chinese + English)
INTENT_PATTERNS = {
    "task": [
        r"任务", r"待办", r"进度", r"还有什么.+没[完做]", r"还[剩有].*任务",
        r"哪些.*没[完做]", r"完成情况", r"扫描.*任务", r"查看.*任务", r"列出.*任务",
        r"当前.*任务", r"未完成", r"todo",
        r"(?i)tasks?\s*(left|remaining|pending|incomplete|status|list|progress)",
        r"(?i)what.*(left|remaining|todo|pending|incomplete)",
        r"(?i)show\s+.*tasks?", r"(?i)list\s+.*tasks?", r"(?i)scan\s+.*tasks?",
        r"(?i)check\s+.*progress", r"(?i)unfinished",
    ],
    "change": [
        r"需求[：:].+", r"新增.+功能", r"添加.+功能", r"实现.+功能",
        r"改[一下]*.+", r"修改.+", r"重构.+", r"优化.+", r"增加.+",
        r"删除.+", r"移除.+", r"更新.+", r"升级.+", r"迁移.+", r"接入.+",
        r"集成.+", r"支持.+", r"加[一个]*.+",
        r"(?i)add\s+.+", r"(?i)implement\s+.+", r"(?i)create\s+.+",
        r"(?i)build\s+.+", r"(?i)develop\s+.+", r"(?i)refactor\s+.+",
        r"(?i)update\s+.+", r"(?i)change\s+.+", r"(?i)modify\s+.+",
        r"(?i)integrate\s+.+", r"(?i)migrate\s+.+",
        r"(?i)new\s+feature.+", r"(?i)feature\s*[：:].+",
    ],
    "bugfix": [
        r"bug[：:].+", r"修复.+", r"修[一下]*.+bug", r"解决.+问题",
        r"处理.+错误", r"报错.+", r".+不工作", r".+失败了", r".+出错了", r".+有问题",
        r"(?i)fix\s+.+", r"(?i)bug[：:].+", r"(?i)debug\s+.+", r"(?i)resolve\s+.+",
        r"(?i).+is\s+broken", r"(?i).+not\s+working", r"(?i).+fails", r"(?i).+error",
    ],
    "quality": [
        r"检查.+", r"测试.+", r"跑[一下]*测试", r"lint.+",
        r"提PR", r"提交PR", r"准备提交", r"代码审查", r"review.+",
        r"(?i)run\s+tests?", r"(?i)check\s+.+", r"(?i)lint\s+.+",
        r"(?i)prepare\s+pr", r"(?i)ready\s+for\s+pr", r"(?i)code\s+review",
    ],
    "explore": [
        r"这个项目.+", r"项目结构.+", r"代码结构.+",
        r"怎么.+的", r"如何.+的", r"在哪[里儿]*.+", r"哪个文件.+", r"找[一下]*.+",
        r"(?i)how\s+does\s+.+work", r"(?i)where\s+is\s+.+", r"(?i)find\s+.+",
        r"(?i)show\s+me\s+.+structure", r"(?i)project\s+structure", r"(?i)codebase\s+.+",
    ],
}

# PLACEHOLDER_REST

# Skip patterns - don't trigger workflow for these
SKIP_PATTERNS = [
    r"^[/\\]", r"^帮我提交", r"^提交", r"^commit", r"^push", r"^git\s+",
    r"^继续", r"^好[的]?$", r"^是[的]?$", r"^yes", r"^no", r"^ok",
    r"^确[认定]", r"^取消", r"^停", r"^等",
]

# Patterns that explicitly skip the change-workflow enforcement
WORKFLOW_SKIP_PATTERNS = [
    r"(?i)直接[改做修写]",
    r"(?i)跳过.{0,4}流程",
    r"(?i)不用.{0,4}流程",
    r"(?i)skip\s*workflow",
    r"(?i)just\s+do\s+it",
    r"(?i)just\s+(fix|change|modify|update|add|implement)",
    r"(?i)no\s+workflow",
    r"(?i)skip\s+change",
]

# Patterns that signal multiple sub-tasks / parallel work in a single prompt
MULTI_TASK_PATTERNS = [
    # Chinese
    r"同时.{0,6}(开发|实现|修复|添加|修改|完成|处理)",
    r"(一起|一并|顺便).{0,6}(开发|实现|修复|添加|修改|完成|处理)",
    r"(几个|多个|两个|三个|四个|五个)\s*(功能|bug|问题|任务|需求|模块|接口)",
    r"(第[一二三四五1-9].{0,4}[，,；;].{0,30}){2,}",
    r"(另外|还有|以及|并且).{0,6}(修复|添加|实现|修改|开发|完成|处理)",
    r"分别.{0,6}(修复|添加|实现|修改|开发|完成|处理)",
    # English
    r"(?i)(also|and\s+also|additionally|plus|as\s+well\s+as).{0,10}(fix|add|implement|create|update|modify|build|develop)",
    r"(?i)(several|multiple|a\s+few|two|three|four|five)\s+(features?|bugs?|issues?|tasks?|changes?|fixes)",
    r"(?i)(both|all\s+of).{0,10}(fix|add|implement|create|update|modify)",
    r"(?i)\d+\.\s+.+\n\s*\d+\.\s+",  # numbered list (1. ... 2. ...)
]

INTENT_MESSAGES = {
    "task": (
        "[osc] 任务数据在 .osc/tasks/ 目录下，请扫描该目录。\n"
        "每个子目录是一个任务，包含 task.json（状态/优先级）、prd.md、progress.log。\n"
        "当前任务指针: .osc/.current-task\n"
        "可用命令: ./.osc/scripts/task.sh list | status | done"
    ),
    "change": (
        "[osc] 检测到变更意图。\n"
        "MANDATORY: 你必须先执行 change-workflow。\n"
        "产物路径: {change_path}\n"
        "创建 proposal.md、spec.md、tasks.md 后才能修改代码。\n"
        "scope-check 钩子将阻止所有代码编辑直到产物存在。\n"
        "⚠️ 请先澄清需求：分析用户需求中的模糊点和不确定性，列出疑问与用户确认后再编码。\n"
        "如用户明确表示跳过（「直接改」、「skip workflow」），可忽略此限制。"
    ),
    "bugfix": (
        "[osc] 检测到 Bug 修复意图。\n"
        "MANDATORY: 你必须先执行 change-workflow。\n"
        "产物路径: {change_path}\n"
        "创建 proposal.md、spec.md、tasks.md 后才能修改代码。\n"
        "scope-check 钩子将阻止所有代码编辑直到产物存在。\n"
        "⚠️ 请先澄清问题：确认复现步骤、影响范围和预期行为，与用户确认后再修复。\n"
        "如用户明确表示跳过（「直接改」、「skip workflow」），可忽略此限制。"
    ),
    "quality": (
        "[osc] 检测到质量检查意图。建议使用 /quality-gate 运行完整检查，"
        "确保 lint/test/build 通过后再提 PR。"
    ),
    "explore": (
        "[osc] 检测到项目探索意图。如果不熟悉项目，建议先使用 /project-spec "
        "了解项目结构和规范。"
    ),
}


def env_flag_enabled(name: str) -> bool:
    value = (os.environ.get(name) or "").strip().lower()
    return value in ("1", "true", "yes", "on")


def parse_created_team_id(output: str) -> str | None:
    for line in output.splitlines():
        m = re.search(r"created team:\s*(\S+)", line.strip())
        if m:
            return m.group(1)
    return None


def maybe_auto_create_team(repo_root: Path, current_task: str | None, intent: str | None) -> str | None:
    """Auto-create team for change/bugfix when enabled."""
    if intent not in ("change", "bugfix"):
        return None
    if not current_task:
        return None
    if not is_team_enabled(repo_root):
        return None
    if not env_flag_enabled("OSC_AUTO_TEAM_CREATE"):
        return None

    existing = find_existing_active_team(repo_root, current_task)
    if existing:
        team_id = existing.get("id", "?")
        status = existing.get("status", "?")
        template = existing.get("template", "?")
        return (
            f"[osc] 自动建队跳过：当前任务已存在团队 `{team_id}` "
            f"(status={status}, template={template})。"
        )

    result = run_team_command(repo_root, ["create", current_task, "--auto"], timeout_sec=20)
    if result.get("ok"):
        team_id = parse_created_team_id(result.get("stdout", "")) or "<unknown>"
        return (
            f"[osc] 已自动创建团队 `{team_id}`（task={current_task}, mode=--auto）。\n"
            "可运行 `./.osc/scripts/team.sh start <team-id>` 立即启动。"
        )

    err = result.get("stderr") or result.get("stdout") or f"exit {result.get('code')}"
    err_line = str(err).splitlines()[0] if err else "unknown error"
    return (
        "[osc] 自动建队失败（已降级为手动模式）："
        f"{err_line}\n"
        f"请手动执行：`./.osc/scripts/team.sh create {current_task} --auto`"
    )


def should_skip(prompt: str) -> bool:
    prompt_lower = prompt.strip().lower()
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, prompt_lower):
            return True
    return len(prompt.strip()) < 5


def detect_intent(prompt: str) -> str | None:
    """Detect user intent from prompt. Returns intent type or None."""
    prompt_clean = prompt.strip()
    for intent in ["task", "bugfix", "change", "quality", "explore"]:
        for pattern in INTENT_PATTERNS.get(intent, []):
            if re.search(pattern, prompt_clean):
                return intent
    return None


def is_concrete_requirement(prompt: str) -> bool:
    """Check if prompt contains a concrete requirement."""
    prompt_clean = prompt.strip()
    return any(re.search(p, prompt_clean) for p in REQUIREMENT_KEYWORDS)

# PLACEHOLDER_FUNCS

# Intent → task type mapping
INTENT_TYPE_MAP = {"change": "feature", "bugfix": "bugfix"}

# Refactor sub-detection (within "change" intent)
REFACTOR_PATTERNS = [r"(?i)重构", r"(?i)refactor"]


def _slugify_prompt(prompt: str, intent: str) -> str:
    """Generate a slug from prompt text. Handles Chinese-only prompts."""
    # Try to extract ASCII words first
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9]*", prompt)
    if words:
        slug = "-".join(w.lower() for w in words[:5])
    else:
        # No ASCII words (e.g. pure Chinese) — use intent + timestamp
        ts = datetime.now().strftime("%H%M%S")
        slug = f"{intent}-{ts}"
    # Ensure slug is not too long
    return slug[:50]


def auto_create_task(
    repo_root: Path, intent: str, prompt: str
) -> tuple[str | None, str | None]:
    """Auto-create a task based on detected intent.

    Returns (task_rel, message) or (None, error_message).
    """
    # Determine task type
    task_type = INTENT_TYPE_MAP.get(intent, "feature")
    if task_type == "feature" and any(
        re.search(p, prompt) for p in REFACTOR_PATTERNS
    ):
        task_type = "refactor"

    # Extract title: first line, up to 80 chars
    title = prompt.strip().split("\n")[0][:80]

    # Generate slug
    slug = _slugify_prompt(prompt, intent)

    # Find task.sh
    task_sh = repo_root / DIR_OSC / "scripts" / "task.sh"
    if not task_sh.is_file():
        return None, "[osc] task.sh not found, skipping auto task creation."

    cmd = [
        "bash", str(task_sh), "create", title,
        "--type", task_type, "--slug", slug,
    ]
    try:
        proc = subprocess.run(
            cmd, cwd=str(repo_root), capture_output=True,
            text=True, timeout=10, check=False,
        )
    except Exception as exc:
        return None, f"[osc] auto task creation failed: {exc}"

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip().split("\n")[0]
        return None, f"[osc] auto task creation failed: {err}"

    # Parse created task path from output (format: "created: .osc/tasks/XX-slug")
    task_rel = None
    for line in proc.stdout.strip().splitlines():
        if line.startswith("created:"):
            task_rel = line.split(":", 1)[1].strip()
            break

    if task_rel:
        msg = (
            f"[osc] 自动创建任务: {task_rel} (type={task_type})\n"
            f"标题: {title}"
        )
        return task_rel, msg
    return None, "[osc] auto task creation: could not parse output."


def matches_workflow_skip(prompt: str) -> bool:
    """Check if prompt matches a pattern that explicitly skips the change-workflow."""
    prompt_clean = prompt.strip()
    return any(re.search(p, prompt_clean) for p in WORKFLOW_SKIP_PATTERNS)


def detect_multi_task_signal(prompt: str) -> bool:
    """Check if prompt contains signals of multiple sub-tasks / parallel work."""
    prompt_clean = prompt.strip()
    return any(re.search(p, prompt_clean) for p in MULTI_TASK_PATTERNS)


def build_parallel_strategy_message() -> str:
    """Build the parallel execution strategy suggestion for Claude Code."""
    runtime = os.environ.get("OSC_RUNTIME", "").lower()
    if runtime == "codex":
        return (
            "[osc] 检测到多任务/并行信号。\n"
            "你的 prompt 包含多个子任务，建议：\n"
            "- 使用 OSC agent team 并行执行：./.osc/scripts/team.sh create <task> --auto\n"
            "注意：每个涉及代码变更的子任务仍需遵循 change-workflow。"
        )
    return (
        "[osc] 检测到多任务/并行信号。\n"
        "你的 prompt 包含多个子任务，请根据复杂度选择策略：\n"
        "- **Task tool（subagent）**：适合独立、只需报告结果的专注任务（成本低）\n"
        "- **Agent Teams（TeamCreate）**：适合需要队友之间讨论、协作和自我协调的复杂工作（成本高）\n"
        "  需要 CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 已启用\n"
        "根据任务是否需要 agent 间通信来决定。\n"
        "注意：每个涉及代码变更的子任务仍需遵循 change-workflow。"
    )


def log_requirement(repo_root: Path, current_task: str | None, prompt: str) -> None:
    """Log a detected requirement to requirements.log."""
    if not current_task:
        log_path = repo_root / DIR_OSC / FILE_REQUIREMENTS_LOG
    else:
        task_dir = repo_root / current_task
        if not task_dir.is_dir():
            task_dir = repo_root / DIR_OSC / "tasks" / current_task
        log_path = task_dir / FILE_REQUIREMENTS_LOG

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        prompt_summary = prompt.strip()
        if len(prompt_summary) > 500:
            prompt_summary = prompt_summary[:500] + "..."
        prompt_summary = prompt_summary.replace("\n", " ").replace("\r", "")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{now}] {prompt_summary}\n")
    except Exception:
        pass


def increment_prompt_count(repo_root: Path) -> int:
    """Increment and return the prompt counter."""
    count_file = repo_root / DIR_OSC / FILE_PROMPT_COUNT
    count = 0
    try:
        count = int(count_file.read_text(encoding="utf-8").strip())
    except Exception:
        pass
    count += 1
    try:
        count_file.parent.mkdir(parents=True, exist_ok=True)
        count_file.write_text(str(count), encoding="utf-8")
    except Exception:
        pass
    return count


def build_context_reinject(repo_root: Path, current_task: str | None) -> str:
    """Build a compact context re-injection message."""
    parts = ["[osc] 上下文刷新（防止长会话遗忘）:"]
    parts.append("核心原则: Write before code / 产物落盘 / 小步提交 / 避免 scope creep")
    if current_task:
        parts.append(f"当前任务: {current_task}")
        tj = repo_root / current_task / "task.json"
        obj = read_json(tj)
        if isinstance(obj, dict):
            parts.append(f"  状态: {obj.get('status', '?')} | 类型: {obj.get('type', '?')} | 优先级: {obj.get('priority', '?')}")
    parts.append("常用命令: ./.osc/scripts/task.sh status|done|progress")
    parts.append("收尾: /osc:finish-work | 质量门禁: /quality-gate")
    return "\n".join(parts)


def ensure_session_marker(repo_root: Path) -> None:
    """Create/update session marker file."""
    marker = repo_root / DIR_OSC / FILE_SESSION_MARKER
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        marker.write_text(now, encoding="utf-8")
    except Exception:
        pass


def check_session_resume(repo_root: Path, current_task: str | None) -> str | None:
    """Detect if session context was lost. Returns re-inject message or None."""
    marker = repo_root / DIR_OSC / FILE_SESSION_MARKER
    if marker.exists():
        return None

    ensure_session_marker(repo_root)
    parts = ["[osc] 会话上下文恢复（检测到上下文可能丢失）:"]

    workflow = read_text(repo_root / DIR_OSC / "workflow.md")
    if workflow:
        lines = workflow.splitlines()[:5]
        parts.append("工作流: " + " | ".join(l.strip("# ").strip() for l in lines if l.strip()))

    if current_task:
        parts.append(f"当前任务: {current_task}")
        prd = read_text(repo_root / current_task / "prd.md")
        if prd:
            parts.append(f"PRD 摘要:\n{prd[:500]}")

    parts.append("任务数据: .osc/tasks/ | 规范: .osc/spec/ | 命令: ./.osc/scripts/task.sh")
    parts.append("建议: 如果上下文不完整，运行 /osc:start 重新加载。")
    return "\n".join(parts)

# PLACEHOLDER_MAIN


def main() -> int:
    input_data = read_hook_input()
    if not input_data:
        return 0

    prompt = input_data.get("prompt", "") or ""
    if not prompt.strip():
        return 0

    if should_skip(prompt):
        return 0

    cwd = Path(input_data.get("cwd", os.getcwd()))
    repo_root = find_repo_root(cwd)
    if not repo_root:
        return 0

    # --- Workflow skip: clear .change-pending if user explicitly skips ---
    pending = is_change_pending(repo_root)
    if pending and matches_workflow_skip(prompt):
        clear_change_pending(repo_root)
        # Also update task change_workflow_status if applicable
        current_task = get_current_task(repo_root)
        if current_task and task_requires_change_workflow(repo_root, current_task):
            update_task_change_status(repo_root, current_task, "skipped")
        hook_output(
            "UserPromptSubmit",
            "[osc] 用户显式跳过 change-workflow，已清除 .change-pending。可直接修改代码。",
        )
        return 0

    current_task = get_current_task(repo_root)
    messages = []

    # Session resume detection
    resume_msg = check_session_resume(repo_root, current_task)
    if resume_msg:
        messages.append(resume_msg)

    # Context decay compensation
    prompt_count = increment_prompt_count(repo_root)
    if prompt_count > 1 and prompt_count % CONTEXT_REINJECT_INTERVAL == 0:
        messages.append(build_context_reinject(repo_root, current_task))

    # Intent detection
    intent = detect_intent(prompt)

    # Auto-create task if change/bugfix intent and no current task
    if intent in ("change", "bugfix") and not current_task:
        created_rel, create_msg = auto_create_task(repo_root, intent, prompt)
        if create_msg:
            messages.append(create_msg)
        if created_rel:
            current_task = created_rel  # use newly created task going forward

    auto_team_msg = maybe_auto_create_team(repo_root, current_task, intent)
    if auto_team_msg:
        messages.append(auto_team_msg)

    # Multi-task parallel strategy (when team system is not active)
    if not auto_team_msg and detect_multi_task_signal(prompt):
        messages.append(build_parallel_strategy_message())

    # Requirement capture
    if is_concrete_requirement(prompt):
        log_requirement(repo_root, current_task, prompt)
        messages.append("[osc] 需求已记录到 requirements.log")

    if intent:
        suppress = current_task and intent in ("change", "bugfix", "explore")

        # --- Change-workflow enforcement for change/bugfix ---
        if intent in ("change", "bugfix"):
            # Determine change path based on current task
            if current_task and task_requires_change_workflow(repo_root, current_task):
                change_path = f"{current_task}/changes/"
            else:
                change_path = ".osc/tasks/<task-dir>/changes/"

            # Check if artifacts already exist
            if check_change_artifacts_exist(repo_root, current_task):
                clear_change_pending(repo_root)
                if current_task:
                    update_task_change_status(repo_root, current_task, "ready")
                messages.append(
                    "[osc] change-workflow 产物已存在，可直接修改代码。"
                )
            else:
                # Write .change-pending to activate scope-check blocking
                prompt_summary = prompt.strip()[:200]
                write_change_pending(repo_root, intent, prompt_summary)

                # Emit the mandatory message with resolved path
                message = INTENT_MESSAGES.get(intent, "")
                if message:
                    message = message.format(change_path=change_path)
                    if not current_task:
                        message = (
                            "[osc] 未检测到当前任务。\n"
                            "请先创建/选择任务，再执行 change-workflow。\n"
                            "可用命令：`./.osc/scripts/task.sh create \"<title>\"` 或 "
                            "`./.osc/scripts/task.sh select .osc/tasks/<task-dir>`。\n\n"
                        ) + message
                    if current_task:
                        message = f"[osc] 当前任务: {current_task}\n\n" + message
                    messages.append(message)

        elif not suppress:
            message = INTENT_MESSAGES.get(intent, "")
            if message:
                if intent == "task":
                    message = message + "\n\n任务列表:\n" + scan_task_list(repo_root)
                if current_task:
                    message = f"[osc] 当前任务: {current_task}\n\n" + message
                messages.append(message)

    ensure_session_marker(repo_root)

    if not messages:
        hook_output("UserPromptSubmit", "Success")
        return 0

    hook_output("UserPromptSubmit", "\n\n".join(messages))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
