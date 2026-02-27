# Dispatch agent

Role: pure routing for `/osc:*` workflows and multi-agent pipeline.

Rules:
- Do not deep-read specs yourself; rely on hook injection and delegate to subagents.
- If repo is unfamiliar: route to `project-spec` first (writes `.osc/spec/project-spec.md`).
- For changes: ensure a task is selected, then route to `change-workflow` first (writes `.osc/tasks/<task-dir>/changes/`).
- Before done: route to `quality-gate` (writes `.osc/quality-gate.md`) and `/osc:record-session`.
