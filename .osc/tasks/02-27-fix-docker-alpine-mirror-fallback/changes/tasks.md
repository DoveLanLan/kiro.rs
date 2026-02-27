# Tasks: Fix Docker Alpine Mirror Fallback

- Date: 2026-02-27
- Owner(s): hewei
- Related: ./proposal.md, ./spec.md

## Assumptions
- User runs `docker compose up -d --build` locally.
- Current failure is caused by custom Alpine mirror unreachability.

## Checklist
- [x] 1) Prepare OSC change artifacts
  - Target: `.osc/tasks/02-27-fix-docker-alpine-mirror-fallback/changes/`
  - Change: create `proposal.md`, `spec.md`, `tasks.md`.
  - Verify: files exist with acceptance criteria.

- [x] 2) Make Dockerfile mirror strategy resilient
  - Target: `Dockerfile`
  - Change: replace hardcoded mirror rewrite with configurable mirror + fallback to official source.
  - Verify: Dockerfile runtime stage includes fallback retry logic.

- [x] 3) Expose mirror override in compose
  - Target: `docker-compose.yml`
  - Change: add optional build arg `ALPINE_MIRROR`.
  - Verify: compose build args contain `ALPINE_MIRROR` with safe default.

- [x] 4) Document quality gate and rollback
  - Target: `.osc/quality-gate.md`, `change-summary.md`, `regression-checklist.md`, `rollback-notes.md`
  - Change: record what changed, how to validate, and how to revert.
  - Verify: markdown artifacts are present.

## Notes
- Keep docker-only scope to match user requirement.
