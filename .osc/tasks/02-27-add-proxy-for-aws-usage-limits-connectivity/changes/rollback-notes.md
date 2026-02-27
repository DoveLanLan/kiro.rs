# Rollback Notes: Add Proxy Config For AWS UsageLimits Connectivity

- Date: 2026-02-27
- Related: ./change-summary.md, ./spec.md

## Rollback strategy
- Revert `config/config.json` `proxyUrl` to `null` (or previous value) and restart service.
- No source code rollback required.

## Data / migration considerations
- No schema/data migrations.
- Credential/token files are runtime state; rollback does not require data backfill.

## Operational notes
- Monitoring/alerts to watch: request send errors to AWS OIDC/Q endpoints after rollback.
- Known residual effects: if environment proxy vars are absent, previous intermittent connectivity issue may return.
