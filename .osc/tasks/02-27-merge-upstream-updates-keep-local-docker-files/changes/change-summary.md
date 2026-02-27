# Change Summary: Merge Upstream Updates While Keeping Local Docker Files

- Date: 2026-02-27
- Owner(s): hewei
- Related: ./proposal.md, ./spec.md, ./tasks.md

## What changed
- Merged `upstream/master` into local `master` with merge commit `f32526c`.
- Preserved local docker-related files by restoring local versions before merge commit finalization:
  - `Dockerfile`
  - `docker-compose.yml`
  - `.dockerignore`
  - `.github/workflows/docker-build.yaml`
- Integrated upstream non-docker updates affecting backend, websearch stream handling, admin UI import flow, config defaults, and build workflow.

## Why
- Upstream introduced fixes/features up to `v2026.2.7` that are needed in fork branch.
- User explicitly required docker-related files to stay on current fork implementation.

## Notable decisions
- Used `git merge --no-commit --no-ff` + path-level restore from pre-merge `HEAD` to enforce docker-file protection in a single merge commit.
- Stashed and restored pre-existing local uncommitted changes to avoid loss while merging.
