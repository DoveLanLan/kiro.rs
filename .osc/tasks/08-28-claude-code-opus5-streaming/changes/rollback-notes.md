# Rollback Notes: Fix Claude Code Opus 5 Streaming

- Date: 2026-08-28
- Related: `proposal.md`, `spec.md`, `tasks.md`

## Rollback strategy

- Revert the changes in `src/anthropic/handlers.rs` and `README.md`, then rebuild/redeploy the previous image.
- If the deployed image is tagged by commit SHA, redeploy the prior known-good SHA through the existing production deployment workflow.

## Data / migration considerations

- No database, credential, or configuration migration is involved.
- Existing `config.json`, `credentials.json`, and proxy settings are untouched.

## Operational notes

- Monitor `docker compose logs` for upstream stream errors and container restarts after deployment.
- If the error persists after rollback, inspect CLIProxyAPI/reverse-proxy buffering and idle timeout settings; those remain outside this patch.
