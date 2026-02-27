# Proposal: Merge Upstream Updates While Keeping Local Docker Files

- Date: 2026-02-27
- Owner(s): hewei
- Stakeholders: fork maintainer, local deploy operator
- Status: Proposed

## Context / Problem
The fork branch `master` is behind `upstream/master` (new commits up to `ea820a4` / `v2026.2.7`). The user wants upstream updates merged into current branch, but docker-related files must keep current fork versions.

## Goals (Why/What)
- Merge upstream feature/fix commits into current branch.
- Preserve fork-local docker-related files unchanged.
- Provide a clear list of what changed and what was intentionally kept.

## Constraints
- Must keep local versions for docker-related files.
- Must not discard existing local uncommitted work in the repository.

## Non-goals
- No large refactor outside upstream sync scope.
- No secret/config content rewrite unrelated to upstream merge.

## Proposed Approach (high-level)
Create a merge task, temporarily stash local working tree changes, run a non-fast-forward merge from `upstream/master`, then explicitly restore docker-related paths from pre-merge `HEAD` before committing the merge. Finally re-apply stashed local changes and report merged file set and any conflicts.

## Risks & Mitigations
- Risk: stashed local changes conflict when reapplied.
  - Mitigation: keep stash entry until verification; resolve conflicts path-by-path.
- Risk: ambiguous docker-related path scope.
  - Mitigation: treat `Dockerfile`, `docker-compose.yml`, `.dockerignore`, and `.github/workflows/docker-build.yaml` as protected set for this merge.
- Risk: merge touches workflow/tooling files heavily.
  - Mitigation: inspect merge diff and summarize intentional keeps vs upstream updates.

## Open Questions (max 3)
- none
