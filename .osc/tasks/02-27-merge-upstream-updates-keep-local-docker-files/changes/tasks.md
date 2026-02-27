# Tasks: Merge Upstream Updates While Keeping Local Docker Files

- Date: 2026-02-27
- Owner(s): hewei
- Related: ./proposal.md, ./spec.md

## Assumptions
- Merge target is `upstream/master` into local `master`.
- Docker-related protected set is:
  - `Dockerfile`
  - `docker-compose.yml`
  - `.dockerignore`
  - `.github/workflows/docker-build.yaml`

## Checklist
- [x] 1) Prepare task artifacts before code merge
  - Target: `.osc/tasks/02-27-merge-upstream-updates-keep-local-docker-files/changes/`
  - Change: write `proposal.md`, `spec.md`, `tasks.md`.
  - Verify: files exist and describe protected path policy.

- [x] 2) Fetch and analyze upstream delta
  - Target: git history
  - Change: fetch `upstream/master`, list ahead/behind commits and changed paths.
  - Verify: upstream head SHA and diff summary recorded.

- [x] 3) Execute merge with docker-path protection
  - Target: branch `master`
  - Change: merge `upstream/master`; keep local versions for protected docker paths.
  - Verify: no upstream-only commits remain; protected files match local pre-merge.

- [x] 4) Restore local uncommitted workspace state
  - Target: git working tree
  - Change: re-apply stashed changes and resolve conflicts if any.
  - Verify: expected local modifications reappear in `git status`.

- [x] 5) Document merge outcome and quality gate
  - Target: `change-summary.md`, `regression-checklist.md`, `rollback-notes.md`, `.osc/quality-gate.md`
  - Change: persist merged scope, validation, rollback instructions.
  - Verify: markdown artifacts exist and include commands/results.

## Notes
- If protected docker files are modified upstream, keep local branch versions by restoring from pre-merge `HEAD` before committing merge.
