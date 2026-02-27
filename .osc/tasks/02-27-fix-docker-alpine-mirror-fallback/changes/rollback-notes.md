# Rollback Notes: Fix Docker Alpine Mirror Fallback

- Date: 2026-02-27
- Related: ./change-summary.md, ./spec.md

## Rollback strategy
- Revert `Dockerfile` and `docker-compose.yml` to previous versions.
- Re-run `docker compose build --no-cache kiro`.

## Data / migration considerations
- No data/schema migration involved.
- This change only affects container build-time behavior.

## Operational notes
- Monitoring/alerts to watch: docker build failures at Alpine package install step.
- Known residual effects: if all candidate Alpine mirrors are unavailable from local network, builder stage will still fail.
