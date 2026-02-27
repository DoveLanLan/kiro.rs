---
name: create-command
description: 创建新的 osc 命令文件，描述目的、输入、输出与落盘路径。
---

# When to Use

When you need to create a new osc command/skill.

# Steps

1) Create new file: `.claude/commands/osc/<name>.md` (for Claude Code) or `skills/<name>/SKILL.md` (for Codex)
2) Describe the purpose, inputs, outputs, and file output paths
3) Ensure the agent writes to files rather than only outputting in chat
