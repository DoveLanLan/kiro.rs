# Regression Checklist: Deploy kiro-rs To VPS As Internal Service For CLIProxyAPI

- Date: 2026-03-26
- Related: `spec.md`, `tasks.md`

## Gates (from Repo Snapshot)

- Rust build: `cargo build -q`
- Workflow/config syntax: Ruby YAML parse over `.github/workflows/*.yaml` and `deploy/compose.production.yml`
- Compose validation: `docker compose --env-file deploy/.env.example -f deploy/compose.production.yml config`
- Shell validation: `bash -n deploy/scripts/remote-deploy.sh`

## Manual checks (if applicable)

- Confirm the GHCR package `ghcr.io/dovelanlan/kiro-rs` exists after first publish.
- Confirm the package visibility is `public` if the VPS is expected to pull anonymously.
- Confirm the external Docker network `cli-proxy-api-proxy` exists on the VPS before the first deploy.
- Confirm `/opt/kiro-rs/data/config.json` uses `"host": "0.0.0.0"` and `"port": 8990`.
- Confirm `docker exec cli-proxy-api getent hosts kiro-rs` works on the VPS after both stacks are running.
- Confirm CLIProxyAPI can successfully call `http://kiro-rs:8990`.

## Edge-case re-tests

- Re-run the deploy workflow with the same image tag to confirm idempotent rollout.
- Confirm deployment fails cleanly if the shared Docker network is absent.
- Confirm `kiro-rs` does not appear in `ss -ltnp` on public host ports after deployment.
