---
name: change-workflow
description: 变更先写后做（proposal/spec/tasks）：新增或修改功能/接口/行为/配置/修Bug时先产出proposal+spec+tasks→按tasks执行→输出总结+回归+回滚；纯讨论不调用。
---

# When to Use

Spec-driven change workflow for feature/change requests, refactors, bugfixes, and design changes; infer repo conventions/toolchains first, then produce proposal/spec/tasks, implement sequentially, and close with summary/regression/rollback. Do not use for purely conceptual discussion without intent to change code.

# Change Workflow (Spec-Driven, Repo-Agnostic)

Follow this deterministic workflow to take any requested change from “what should we do?” to “done, verified, and safely revertible” without assuming a particular tech stack.

## Workflow (do not reorder)

0) Repo introspection (MANDATORY)
   - Scan repo evidence (top-level + up to 2 directory levels) to infer:
     - **Modules/components**: top-level directories, internal packages, services, apps, libraries, shared folders, docs structure.
     - **Build & test entrypoints**: scripts/targets, make-like entrypoints, task runners, build configs, test configs, CI scripts.
     - **Existing change process**: CONTRIBUTING, docs that describe PR/branching, release notes, migrations, ADRs, RFCs.
     - **CI gates**: workflows/pipelines, required checks, lint/format/test/build steps, coverage, static analysis.
   - Detection logic rules (do not hardcode any language/framework):
     - Prefer **evidence-first inference**: infer only what the repo’s files/configs explicitly indicate.
     - Classify evidence into these buckets: `structure`, `build`, `test`, `quality`, `ci`, `release`, `runtime`, `data/migrations`.
     - When multiple signals conflict, record uncertainty and defer strong claims.
   - Output a short **Repo Snapshot** (keep it ≤ 15 lines):
     - Modules/components (bulleted)
     - Toolchains (build/test/quality/CI) (bulleted)
     - Confidence (High/Medium/Low)
     - Evidence locations (paths) that justify the snapshot
   - If repo evidence is insufficient:
     - Ask at most ONE blocking question; otherwise proceed with explicit assumptions.

1) Phase 1 — Proposal
   - Output a concise proposal that answers:
     - **Why** (motivation / problem statement)
     - **What** (user-visible and internal outcomes)
     - **Constraints** (performance, security, compatibility, timelines, policies)
     - **Non-goals** (out of scope)
     - **Risks** (technical + delivery) and mitigations
     - **Stakeholders/owners** (best-effort from repo evidence; otherwise placeholders)

2) Phase 2 — Spec
   - Output a spec that includes:
     - **Acceptance criteria (testable)**: each criterion can be verified via a concrete check.
     - **Scope boundaries**: what changes and what explicitly does not.
     - **Edge cases**: failure modes, unusual inputs, concurrency, partial states, error handling, rollback scenarios.
     - **Compatibility notes**: backwards/forwards compatibility, versioning expectations, data/schema/migration concerns.
     - **API/UX decisions (if applicable)**: endpoints/inputs/outputs, UI states, error messages, telemetry, i18n/a11y.
   - Keep the spec implementation-agnostic where possible; bind to repo conventions when necessary.

3) Phase 3 — Tasks
   - Output a minimal executable checklist of tasks. Each task must:
     - Be independently doable (small, verifiable increments)
     - Name targeted files/areas (best-effort from Repo Snapshot)
     - Include a test/verification note (local command, CI gate, manual validation step, or review checklist)
   - State explicit assumptions if evidence is missing (e.g., unknown test runner, unclear module boundaries).

4) Execution rule
   - If asked to implement, follow the Tasks sequentially.
   - Do not jump steps; if a step must be skipped, justify the skip and state the risk introduced.
   - Keep changes aligned to repo gates (format/lint/tests/build) inferred in the Repo Snapshot.
   - Never claim commands were executed; only suggest actions and report expected outcomes.

5) Closure
   - Output:
     - **Change Summary**: what changed + why (tie back to proposal/spec)
     - **Regression Checklist**: what to re-test and how (aligned to repo CI gates)
     - **Rollback Notes**: how to revert safely (include migration/config/data considerations)

## Artifact templates (AUTO-WRITE)

Default folder path: `.osc/changes/<YYYY-MM-DD>-<slug>/`

**Hard rule:** When using this skill, do not only print the artifacts in chat. You MUST create or update the corresponding markdown files in the repository so the artifacts persist.

- Create the folder if missing.
- Write artifacts to the files listed below.
- Prefer updating existing files in-place rather than creating duplicates.
- If the repo has an established changelog/ADR/RFC/change-doc location that conflicts with this path, ask at most ONE blocking question; otherwise proceed with the default path.

### `proposal.md`

```markdown
# Proposal: <Title>

- Date: <YYYY-MM-DD>
- Owner(s): <name/handle>
- Stakeholders: <teams/users>
- Status: Draft | Proposed | Accepted | Rejected

## Context / Problem
<What’s happening today? What’s broken or missing? Why now?>

## Goals (Why/What)
- <goal 1>
- <goal 2>

## Constraints
- <constraint 1>
- <constraint 2>

## Non-goals
- <non-goal 1>

## Proposed Approach (high-level)
<One paragraph describing the change at a systems level. Avoid stack assumptions unless the repo dictates them.>

## Risks & Mitigations
- Risk: <...>
  - Mitigation: <...>

## Open Questions (max 3)
- <question 1>
```

### `spec.md`

```markdown
# Spec: <Title>

- Date: <YYYY-MM-DD>
- Owner(s): <name/handle>
- Related: <link to proposal/tasks/issue>

## Repo Snapshot (from step 0)
<Paste the snapshot here.>

## Scope
### In scope
- <...>

### Out of scope
- <...>

## Acceptance Criteria (testable)
1. <criterion> (Verify: <how>)
2. <criterion> (Verify: <how>)

## Behavior / Requirements
<Describe expected behavior, including error handling and partial states.>

## Edge Cases
- <edge case 1>
- <edge case 2>

## Compatibility Notes
- Backwards compatibility: <...>
- Data/migrations: <...>
- Config/flags: <...>

## API/UX Decisions (if applicable)
- Inputs/outputs: <...>
- States/errors: <...>
- Telemetry/logging: <...>
- Accessibility/i18n (if UI): <...>
```

### `tasks.md`

```markdown
# Tasks: <Title>

- Date: <YYYY-MM-DD>
- Owner(s): <name/handle>
- Related: <link to spec/proposal/issue>

## Assumptions
- <assumption 1>

## Checklist
- [ ] 1) <task name>
  - Target: <files/dirs/modules>
  - Change: <what to do>
  - Verify: <test/lint/build/manual check>

- [ ] 2) <task name>
  - Target: <files/dirs/modules>
  - Change: <what to do>
  - Verify: <test/lint/build/manual check>

## Notes
- <Anything learned during execution that should update the spec or tasks>
```

### `change-summary.md`

```markdown
# Change Summary: <Title>

- Date: <YYYY-MM-DD>
- Owner(s): <name/handle>
- Related: <link to spec/tasks/PR>

## What changed
- <bullet 1>
- <bullet 2>

## Why
<Tie back to the original problem, goals, and acceptance criteria.>

## Notable decisions
- <tradeoff/decision 1>
```

### `regression-checklist.md`

```markdown
# Regression Checklist: <Title>

- Date: <YYYY-MM-DD>
- Related: <link to spec/tasks/PR>

## Gates (from Repo Snapshot)
- Build: <how to run / CI step name>
- Tests: <how to run / CI step name>
- Lint/format: <how to run / CI step name>
- Other: <security scan, typecheck, etc.>

## Manual checks (if applicable)
- <scenario 1> (Expected: <...>)
- <scenario 2> (Expected: <...>)

## Edge-case re-tests
- <edge case 1>
```

### `rollback-notes.md`

```markdown
# Rollback Notes: <Title>

- Date: <YYYY-MM-DD>
- Related: <link to spec/tasks/PR>

## Rollback strategy
<How to revert safely (e.g., revert commit/PR, disable via config/flag, restore previous artifact).>

## Data / migration considerations
- <What must be reverted or is irreversible?>
- <Backfill / forward-only migration notes>

## Operational notes
- Monitoring/alerts to watch: <...>
- Known residual effects: <...>
```

## Output behavior (MANDATORY)

After writing/updating the artifact files, keep the chat response short:
- List the exact file paths you wrote (or updated) and what changed at a high level.
- Then continue to implementation only if the user explicitly asked to implement.
