# Regression Checklist: Merge Upstream Updates While Keeping Local Docker Files

- Date: 2026-02-27
- Related: ./spec.md, ./tasks.md, ./change-summary.md

## Gates (from Repo Snapshot)
- Merge ancestry check: `git merge-base --is-ancestor upstream/master HEAD`
- Delta sanity: `git log --oneline --left-right HEAD...upstream/master`
- Protected docker paths unchanged: `git diff --name-status <pre-merge-head>..HEAD -- Dockerfile docker-compose.yml .dockerignore .github/workflows/docker-build.yaml`
- Upstream integrated file set review: `git diff --name-status <pre-merge-head>..HEAD`

## Manual checks (if applicable)
- Verify key upstream fixes are present in:
  - `src/anthropic/websearch.rs`
  - `src/admin/service.rs`
  - `admin-ui/src/components/kam-import-dialog.tsx`
- Verify docker runtime behavior still follows fork-local implementation by reviewing local `Dockerfile` and `docker-compose.yml`.

## Edge-case re-tests
- If local uncommitted changes touched merged files, run a quick diff review to ensure expected local edits are still present after stash pop.
- If preparing release, run backend build/tests and admin-ui build to ensure no hidden integration break.
