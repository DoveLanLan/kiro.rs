# Rollback Notes: Merge Upstream Updates While Keeping Local Docker Files

- Date: 2026-02-27
- Related: ./change-summary.md, ./spec.md

## Rollback strategy
- Revert the merge commit with first-parent strategy:
  - `git revert -m 1 f32526c`
- This restores branch content to pre-merge state while keeping commit history auditable.

## Data / migration considerations
- No database or schema migrations included in this merge.
- Runtime config/credentials files in local workspace are unaffected by merge rollback unless separately modified.

## Operational notes
- Monitoring/alerts to watch: regressions in websearch SSE behavior, admin credential operations, and UI import flow.
- Known residual effects: local uncommitted workspace changes remain outside merge commit scope; review separately if rollback is needed.
