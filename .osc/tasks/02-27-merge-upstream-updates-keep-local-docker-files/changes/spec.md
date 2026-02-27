# Spec: Merge Upstream Updates While Keeping Local Docker Files

- Date: 2026-02-27
- Owner(s): hewei
- Related: ./proposal.md, ./tasks.md

## Repo Snapshot (from step 0)
- Modules/components:
  - Rust backend in `src/` (`anthropic`, `kiro`, `admin`)
  - Admin UI in `admin-ui/`
  - Docker/runtime packaging in `Dockerfile`, `docker-compose.yml`, `.github/workflows/docker-build.yaml`
  - OSC workflow artifacts under `.osc/`
- Toolchains:
  - Build/test/lint: `cargo build`, `cargo test`, `cargo fmt`, `cargo clippy`
  - Frontend build: `admin-ui` `pnpm build`
  - CI: GitHub Actions under `.github/workflows/`
- Confidence: High
- Evidence: `AGENTS.md`, `Cargo.toml`, `admin-ui/package.json`, `.github/workflows/build.yaml`, `.github/workflows/docker-build.yaml`, `git log HEAD...upstream/master`.

## Scope
### In scope
- Merge upstream commits from divergence base to latest `upstream/master`.
- Keep local versions for docker-related files:
  - `Dockerfile`
  - `docker-compose.yml`
  - `.dockerignore`
  - `.github/workflows/docker-build.yaml`
- Reapply local uncommitted workspace changes after merge.

### Out of scope
- Manual feature development unrelated to upstream sync.
- Reworking docker strategy beyond “keep local version”.

## Acceptance Criteria (testable)
1. Current branch contains upstream latest commit history via merge commit. (Verify: `git merge-base --is-ancestor upstream/master HEAD`)
2. Protected docker-related files in working tree match pre-merge local versions. (Verify: path-level diff against pre-merge snapshot)
3. Non-docker upstream changes are present in branch diff/history. (Verify: `git log --left-right HEAD...upstream/master` shows no upstream-only commits)
4. Pre-existing local uncommitted changes are restored after merge. (Verify: stash reapplied and `git status` includes expected local edits)

## Behavior / Requirements
- Merge operation should be non-destructive to existing local work.
- In case of conflict, resolve in favor of upstream except protected docker paths.
- Provide post-merge summary with changed files and any manual conflict resolution notes.

## Edge Cases
- Stash pop conflicts on files modified by upstream.
- Upstream renames/deletes files that fork modified locally.
- Protected docker files changed upstream and local simultaneously.

## Compatibility Notes
- Backwards compatibility: follows upstream baseline except intentional docker divergence.
- Data/migrations: none expected for merge-only operation.
- Config/flags: may inherit upstream config defaults outside protected docker files.

## API/UX Decisions (if applicable)
- Inputs/outputs: no direct API redesign in this task; behavior follows upstream merged code.
- States/errors: conflict resolution policy is explicit by file category.
- Telemetry/logging: unchanged unless upstream altered logging.
- Accessibility/i18n (if UI): follows upstream changes.
