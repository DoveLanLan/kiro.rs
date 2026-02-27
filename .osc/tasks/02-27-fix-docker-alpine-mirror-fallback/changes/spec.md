# Spec: Fix Docker Alpine Mirror Fallback

- Date: 2026-02-27
- Owner(s): hewei
- Related: ./proposal.md, ./tasks.md

## Repo Snapshot (from step 0)
- Modules/components:
  - Docker runtime/build files: `Dockerfile`, `docker-compose.yml`.
  - Rust backend code under `src/` (not in scope for this fix).
- Toolchains:
  - Container build via `docker compose up -d --build` and `docker build`.
  - CI container workflows present in `.github/workflows/`.
- Confidence: High.
- Evidence: `Dockerfile`, `docker-compose.yml`, `AGENTS.md` (Docker section).

## Scope
### In scope
- Update runtime-stage Alpine package install logic to avoid single-mirror hard dependency.
- Expose Alpine mirror as optional build arg in compose config.

### Out of scope
- Application code changes in `src/`.
- Credential/config behavior changes.

## Acceptance Criteria (testable)
1. Default build path does not force Tsinghua mirror. (Verify: Dockerfile runtime stage uses official mirror by default)
2. Build succeeds when custom mirror is unavailable by retrying official mirror once. (Verify: fallback branch exists in Dockerfile command)
3. Compose allows optional mirror override. (Verify: `docker-compose.yml` build args include `ALPINE_MIRROR`)

## Behavior / Requirements
- If `ALPINE_MIRROR` is provided and reachable, use it.
- If custom mirror install fails, fallback to official `dl-cdn.alpinelinux.org` and retry installation.
- If no mirror arg is provided, build should use official mirror directly.

## Edge Cases
- Temporary network failures on both custom and official mirror.
- Empty/invalid `ALPINE_MIRROR` input.

## Compatibility Notes
- Backwards compatibility: existing builds continue to work; mirror acceleration remains optional.
- Data/migrations: none.
- Config/flags: new optional build arg `ALPINE_MIRROR`.

## API/UX Decisions (if applicable)
- Inputs/outputs: Docker build arg surface only.
- States/errors: clearer fallback behavior for mirror failures.
- Telemetry/logging: fallback message printed in build logs.
- Accessibility/i18n: not applicable.
