---
name: record-session
description: 把本次会话的结论、决策、下一步、风险、回滚点整理为摘要并写入 journal。
---

# When to Use

At the end of a work session, to persist decisions and next steps.

# Steps

Write a summary of this session's conclusions/decisions/next steps/risks/rollback points to:
`.osc/workspace/<user>/journal-N.md`

Then update `.osc/workspace/<user>/index.md`.

# Notes

- `<user>` comes from `OPEN_SPEC_CODE_USER` (set in `.claude/settings.local.json` or `.codex/settings.local.json`).
- If unsure about N, read existing `journal-*.md` files in `.osc/workspace/<user>/` and pick the next number.
