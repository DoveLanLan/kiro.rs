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
import sys
from datetime import datetime, timezone
from pathlib import Path


DIR_OSC = ".osc"
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
    r"要增加",
    r"要添加",
    r"要修改",
    r"要调整",
    r"要删除",
    r"要去掉",
    r"要改成",
    r"要换成",
    r"需要增加",
    r"需要添加",
    r"需要修改",
    r"需要调整",
    r"帮我[加增添]",
    r"帮我[改修]",
    r"帮我[删去移]",
    r"现在有个[调修改]",
    r"有个.{0,3}需求",
    r"有个调整",
    r"有个修改",
    r"[这那]个[页面功能模块].+[要需]",
    r"上传框.+[增加添加]",
    r"[增加添加].+提示",
    r"[增加添加].+按钮",
    r"[增加添加].+字段",
    r"[增加添加].+功能",
    # Bug reports
    r"有一个bug",
    r"有个bug",
    r"发现.+bug",
    r"这个bug",
    r"那个bug",
    r".+有问题",
    r".+出问题了",
    r".+不对",
    r".+报错",
    # English
    r"(?i)please\s+add",
    r"(?i)please\s+change",
    r"(?i)please\s+modify",
    r"(?i)please\s+update",
    r"(?i)please\s+remove",
    r"(?i)please\s+delete",
    r"(?i)need\s+to\s+add",
    r"(?i)need\s+to\s+change",
    r"(?i)need\s+to\s+modify",
    r"(?i)want\s+to\s+add",
    r"(?i)want\s+to\s+change",
    r"(?i)should\s+add",
    r"(?i)should\s+have",
    r"(?i)add\s+a\s+.+\s+(button|field|tooltip|hint|message)",
    r"(?i)change\s+the\s+.+\s+to",
    # Bug reports - English
    r"(?i)there\s+is\s+a\s+bug",
    r"(?i)found\s+a\s+bug",
    r"(?i)there'?s\s+a\s+bug",
    r"(?i)bug\s*:\s*.+",
    r"(?i).+is\s+broken",
    r"(?i).+doesn'?t\s+work",
]

# Intent patterns (Chinese + English)
INTENT_PATTERNS = {
    "task": [
        # Chinese
        r"任务",
        r"待办",
        r"进度",
        r"还有什么.+没[完做]",
        r"还[剩有].*任务",
        r"哪些.*没[完做]",
        r"完成情况",
        r"扫描.*任务",
        r"查看.*任务",
        r"列出.*任务",
        r"当前.*任务",
        r"未完成",
        r"todo",
        # English
        r"(?i)tasks?\s*(left|remaining|pending|incomplete|status|list|progress)",
        r"(?i)what.*(left|remaining|todo|pending|incomplete)",
        r"(?i)show\s+.*tasks?",
        r"(?i)list\s+.*tasks?",
        r"(?i)scan\s+.*tasks?",
        r"(?i)check\s+.*progress",
        r"(?i)unfinished",
    ],
    "change": [
        # Chinese
        r"需求[：:].+",
        r"新增.+功能",
        r"添加.+功能",
        r"实现.+功能",
        r"改[一下]*.+",
        r"修改.+",
        r"重构.+",
        r"优化.+",
        r"增加.+",
        r"删除.+",
        r"移除.+",
        r"更新.+",
        r"升级.+",
        r"迁移.+",
        r"接入.+",
        r"集成.+",
        r"支持.+",
        r"加[一个]*.+",
        # English
        r"(?i)add\s+.+",
        r"(?i)implement\s+.+",
        r"(?i)create\s+.+",
        r"(?i)build\s+.+",
        r"(?i)develop\s+.+",
        r"(?i)refactor\s+.+",
        r"(?i)update\s+.+",
        r"(?i)change\s+.+",
        r"(?i)modify\s+.+",
        r"(?i)integrate\s+.+",
        r"(?i)migrate\s+.+",
        r"(?i)new\s+feature.+",
        r"(?i)feature\s*[：:].+",
    ],
    "bugfix": [
        # Chinese
        r"bug[：:].+",
        r"修复.+",
        r"修[一下]*.+bug",
        r"解决.+问题",
        r"处理.+错误",
        r"报错.+",
        r".+不工作",
        r".+失败了",
        r".+出错了",
        r".+有问题",
        # English
        r"(?i)fix\s+.+",
        r"(?i)bug[：:].+",
        r"(?i)debug\s+.+",
        r"(?i)resolve\s+.+",
        r"(?i).+is\s+broken",
        r"(?i).+not\s+working",
        r"(?i).+fails",
        r"(?i).+error",
    ],
    "quality": [
        # Chinese
        r"检查.+",
        r"测试.+",
        r"跑[一下]*测试",
        r"lint.+",
        r"提PR",
        r"提交PR",
        r"准备提交",
        r"代码审查",
        r"review.+",
        # English
        r"(?i)run\s+tests?",
        r"(?i)check\s+.+",
        r"(?i)lint\s+.+",
        r"(?i)prepare\s+pr",
        r"(?i)ready\s+for\s+pr",
        r"(?i)code\s+review",
    ],
    "explore": [
        # Chinese
        r"这个项目.+",
        r"项目结构.+",
        r"代码结构.+",
        r"怎么.+的",
        r"如何.+的",
        r"在哪[里儿]*.+",
        r"哪个文件.+",
        r"找[一下]*.+",
        # English
        r"(?i)how\s+does\s+.+work",
        r"(?i)where\s+is\s+.+",
        r"(?i)find\s+.+",
        r"(?i)show\s+me\s+.+structure",
        r"(?i)project\s+structure",
        r"(?i)codebase\s+.+",
    ],
}

# Skip patterns - don't trigger workflow for these
SKIP_PATTERNS = [
    r"^[/\\]",  # Slash commands
    r"^帮我提交",
    r"^提交",
    r"^commit",
    r"^push",
    r"^git\s+",
    r"^继续",
    r"^好[的]?$",
    r"^是[的]?$",
    r"^yes",
    r"^no",
    r"^ok",
    r"^确[认定]",
    r"^取消",
    r"^停",
    r"^等",
]

INTENT_MESSAGES = {
    "task": (
        "[osc] 任务数据在 .osc/tasks/ 目录下，请扫描该目录。\n"
        "每个子目录是一个任务，包含 task.json（状态/优先级）、prd.md、progress.log。\n"
        "当前任务指针: .osc/.current-task\n"
        "可用命令: ./.osc/scripts/task.sh list | status | done"
    ),
    "change": (
        "[osc] 检测到变更意图。建议先使用 /change-workflow 记录需求，"
        "产出 proposal/spec/tasks 后再实现。\n"
        "如果只是简单讨论，可以忽略此提示。"
    ),
    "bugfix": (
        "[osc] 检测到 Bug 修复意图。建议使用 /change-workflow 记录问题，"
        "明确复现步骤和修复方案后再动手。\n"
        "如果只是简单讨论，可以忽略此提示。"
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


def find_repo_root(start: Path) -> Path | None:
    current = start.resolve()
    while current != current.parent:
        if (current / DIR_OSC).is_dir():
            return current
        if (current / ".git").exists():
            return current
        current = current.parent
    return None


def should_skip(prompt: str) -> bool:
    prompt_lower = prompt.strip().lower()
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, prompt_lower):
            return True
    # Very short prompts are usually confirmations
    if len(prompt.strip()) < 5:
        return True
    return False


def detect_intent(prompt: str) -> str | None:
    """Detect user intent from prompt. Returns intent type or None."""
    prompt_clean = prompt.strip()

    # Check in priority order: task > bugfix > change > quality > explore
    for intent in ["task", "bugfix", "change", "quality", "explore"]:
        patterns = INTENT_PATTERNS.get(intent, [])
        for pattern in patterns:
            if re.search(pattern, prompt_clean):
                return intent
    return None


def is_concrete_requirement(prompt: str) -> bool:
    """Check if prompt contains a concrete requirement (not just discussion)."""
    prompt_clean = prompt.strip()
    for pattern in REQUIREMENT_KEYWORDS:
        if re.search(pattern, prompt_clean):
            return True
    return False


def log_requirement(repo_root: Path, current_task: str | None, prompt: str) -> None:
    """Log a detected requirement to requirements.log in the current task directory."""
    if not current_task:
        # No active task, log to .osc/requirements.log
        log_path = repo_root / DIR_OSC / FILE_REQUIREMENTS_LOG
    else:
        # Log to current task's requirements.log
        task_dir = repo_root / current_task
        if not task_dir.is_dir():
            task_dir = repo_root / DIR_OSC / "tasks" / current_task
        log_path = task_dir / FILE_REQUIREMENTS_LOG

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        # Truncate long prompts but keep enough context
        prompt_summary = prompt.strip()
        if len(prompt_summary) > 500:
            prompt_summary = prompt_summary[:500] + "..."
        # Escape newlines for single-line log entry
        prompt_summary = prompt_summary.replace("\n", " ").replace("\r", "")

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{now}] {prompt_summary}\n")
    except Exception:
        pass  # Silent fail - don't block user workflow


def get_current_task(repo_root: Path) -> str | None:
    p = repo_root / DIR_OSC / ".current-task"
    try:
        v = p.read_text(encoding="utf-8").strip()
        return v or None
    except Exception:
        return None


def scan_tasks(repo_root: Path) -> str:
    """Scan .osc/tasks/ and return a brief summary."""
    tasks_dir = repo_root / DIR_OSC / "tasks"
    if not tasks_dir.is_dir():
        return "（.osc/tasks/ 目录不存在）"

    lines = []
    for d in sorted(tasks_dir.iterdir()):
        if not d.is_dir():
            continue
        task_json = d / "task.json"
        if not task_json.exists():
            lines.append(f"  - {d.name} (no task.json)")
            continue
        try:
            obj = json.loads(task_json.read_text(encoding="utf-8"))
            name = obj.get("name", d.name)
            status = obj.get("status", "unknown")
            priority = obj.get("priority", "")
            lines.append(f"  - [{status}] {name} ({priority}) -> {d.name}")
        except Exception:
            lines.append(f"  - {d.name} (parse error)")

    if not lines:
        return "（.osc/tasks/ 下没有任务）"
    return "\n".join(lines)


# --- 4.3: Prompt counter for context decay compensation ---

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

    # Core workflow principles
    parts.append("核心原则: Write before code / 产物落盘 / 小步提交 / 避免 scope creep")

    # Current task
    if current_task:
        parts.append(f"当前任务: {current_task}")
        task_dir = repo_root / current_task
        tj = task_dir / "task.json"
        if tj.exists():
            try:
                obj = json.loads(tj.read_text(encoding="utf-8"))
                parts.append(f"  状态: {obj.get('status', '?')} | 类型: {obj.get('type', '?')} | 优先级: {obj.get('priority', '?')}")
            except Exception:
                pass

    # Key commands reminder
    parts.append("常用命令: ./.osc/scripts/task.sh status|done|progress")
    parts.append("收尾: /osc:finish-work | 质量门禁: /quality-gate")

    return "\n".join(parts)


# --- 4.6: Session resume detection ---

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
    """Detect if session context was lost (e.g. after compaction). Returns re-inject message or None."""
    marker = repo_root / DIR_OSC / FILE_SESSION_MARKER
    if marker.exists():
        # Session marker exists — normal operation
        return None

    # No marker = first prompt after session start or after compaction
    # Create the marker and inject context
    ensure_session_marker(repo_root)

    parts = ["[osc] 会话上下文恢复（检测到上下文可能丢失）:"]

    # Read workflow summary
    workflow = repo_root / DIR_OSC / "workflow.md"
    if workflow.exists():
        try:
            content = workflow.read_text(encoding="utf-8")
            # Extract just the first few key lines
            lines = content.splitlines()[:5]
            parts.append("工作流: " + " | ".join(l.strip("# ").strip() for l in lines if l.strip()))
        except Exception:
            pass

    if current_task:
        parts.append(f"当前任务: {current_task}")
        task_dir = repo_root / current_task
        prd = task_dir / "prd.md"
        if prd.exists():
            try:
                content = prd.read_text(encoding="utf-8")
                # First 500 chars of PRD
                parts.append(f"PRD 摘要:\n{content[:500]}")
            except Exception:
                pass

    parts.append("任务数据: .osc/tasks/ | 规范: .osc/spec/ | 命令: ./.osc/scripts/task.sh")
    parts.append("建议: 如果上下文不完整，运行 /osc:start 重新加载。")

    return "\n".join(parts)


def main() -> int:
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    prompt = input_data.get("prompt", "") or ""
    if not prompt.strip():
        return 0

    # Skip certain patterns
    if should_skip(prompt):
        return 0

    cwd = Path(input_data.get("cwd", os.getcwd()))
    repo_root = find_repo_root(cwd)
    if not repo_root:
        return 0

    current_task = get_current_task(repo_root)
    messages = []

    # --- 4.6: Session resume detection ---
    resume_msg = check_session_resume(repo_root, current_task)
    if resume_msg:
        messages.append(resume_msg)

    # --- 4.3: Context decay compensation ---
    prompt_count = increment_prompt_count(repo_root)
    if prompt_count > 1 and prompt_count % CONTEXT_REINJECT_INTERVAL == 0:
        reinject = build_context_reinject(repo_root, current_task)
        messages.append(reinject)

    # --- Intent detection ---
    intent = detect_intent(prompt)

    # --- Requirement capture (before intent message) ---
    if is_concrete_requirement(prompt):
        log_requirement(repo_root, current_task, prompt)
        # Add a subtle confirmation to the message
        req_confirm = f"[osc] 需求已记录到 requirements.log"
        messages.append(req_confirm)

    if intent:
        # If already working on a task, only remind for task queries and quality checks
        suppress = current_task and intent in ("change", "bugfix", "explore")
        if not suppress:
            message = INTENT_MESSAGES.get(intent, "")
            if message:
                if intent == "task":
                    task_summary = scan_tasks(repo_root)
                    message = message + "\n\n任务列表:\n" + task_summary
                if current_task:
                    message = f"[osc] 当前任务: {current_task}\n\n" + message
                messages.append(message)

    # Update session marker on every prompt
    ensure_session_marker(repo_root)

    if not messages:
        return 0

    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "message": "\n\n".join(messages),
        }
    }

    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
