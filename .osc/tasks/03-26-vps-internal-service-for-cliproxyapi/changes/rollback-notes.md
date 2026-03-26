# Rollback Notes: Deploy kiro-rs To VPS As Internal Service For CLIProxyAPI

- Date: 2026-03-26
- Related: `spec.md`, `tasks.md`

## Rollback strategy

- Revert the workflow and `deploy/` changes from git if the deployment design needs to be abandoned.
- On the VPS, redeploy a previous known-good image tag:

```bash
cd /opt/kiro-rs
KIRO_RS_IMAGE=ghcr.io/dovelanlan/kiro-rs:<older-tag> SHARED_NETWORK_NAME=cli-proxy-api-proxy bash scripts/remote-deploy.sh
```

- If the stack must be stopped entirely:

```bash
cd /opt/kiro-rs
docker compose -f compose.production.yml down
```

## Data / migration considerations

- No schema or database migrations are involved.
- Keep `config.json`, `credentials.json`, and AWS SSO cache files intact during rollback.
- GHCR visibility changes are separate operational settings and are not reverted automatically with git changes.

## Operational notes

- Monitoring/alerts to watch: failed GHCR pulls, missing Docker network, invalid Kiro credentials, and upstream connection failures from CLIProxyAPI.
- Known residual effects: removing repo changes does not automatically delete `/opt/kiro-rs` on the VPS.
