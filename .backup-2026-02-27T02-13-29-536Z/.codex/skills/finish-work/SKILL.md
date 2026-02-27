---
name: finish-work
description: 收尾清单：更新变更文档、运行质量门禁、记录会话、标记任务完成、提交代码。
---

# When to Use

Before committing or submitting a PR, run this checklist to wrap up your work.

# Steps

1) Update change docs: `.osc/changes/<date>-<slug>/change-summary.md`
2) Run quality gate: follow `.osc/quality-gate.md`
3) Record session: use `record-session` skill
4) Mark task done:
   ```bash
   ./.osc/scripts/task.sh done
   ```
   (auto-updates task.json status → done, logs to progress.log, prompts branch merge)
5) Commit code: ensure all changes are committed

# Notes

Step 4 automatically handles branch prompts — if on a task branch it will suggest merge or push.
