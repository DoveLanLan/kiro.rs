# Regression Checklist: Fix Docker Alpine Mirror Fallback

- Date: 2026-02-27
- Related: ./spec.md, ./tasks.md, ./change-summary.md

## Gates (from Repo Snapshot)
- Compose syntax/render check: `docker compose config`
- Docker build check: `docker compose build --no-cache kiro`
- Runtime check: `docker compose up -d && docker compose logs --tail=200 kiro`

## Manual checks (if applicable)
- Verify build logs show mirror retry messages only when first mirror fails.
- Verify runtime image starts without TLS/certificate errors when proxy forwards to AWS/Kiro endpoints.

## Edge-case re-tests
- Run with explicit mirror override:
  - `ALPINE_MIRROR=mirrors.tuna.tsinghua.edu.cn docker compose build --no-cache kiro`
- Run with default mirror:
  - `docker compose build --no-cache kiro`
