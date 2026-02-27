---
name: start
description: 开始写代码前，把工作流与上下文固化为可审计的落盘文档，并按步骤推进。
---

# When to Use

When starting a new coding session or task. This is the entry point for the spec-driven workflow.

# Steps (in order)

1) Read `.osc/workflow.md` and `.osc/spec/*/index.md` (if index is empty, fill in links/conventions first).
2) If the repo doesn't have a project spec yet: run `project-spec` skill, write to `.osc/spec/project-spec.md`.
3) If this is a change: run `change-workflow` skill, write to `.osc/changes/<YYYY-MM-DD>-<slug>/` (proposal/spec/tasks).
4) If the user explicitly asks to implement: follow `tasks.md` step by step.
5) Wrap up: run `quality-gate` skill, write to `.osc/quality-gate.md`.

# Rules

- Artifacts MUST be written to the corresponding `.md` files (don't just output in chat).
- Small commits, avoid scope creep.
