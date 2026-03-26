# Change Summary: Deploy kiro-rs To VPS As Internal Service For CLIProxyAPI

- Date: 2026-03-26
- Owner(s): hewei
- Related: `proposal.md`, `spec.md`, `tasks.md`

## What changed

- Added a task-scoped deployment proposal/spec/tasks package for the internal-only VPS deployment.
- Added a dedicated `deploy/` package with:
  - `compose.production.yml`
  - `.env.example`
  - remote deployment script
  - server/bootstrap and integration documentation
- Reworked the Docker GHCR workflow to publish deterministic amd64 tags for `master`, release tags, and manual dispatch.
- Added a production deployment workflow that deploys the service to `root@23.175.201.12:/opt/kiro-rs`.
- Kept the service internal-only by avoiding any public host port publishing and instead joining the external Docker network used by CLIProxyAPI.

## Why

The user wants `kiro-rs` to run on the same VPS as CLIProxyAPI as a backend dependency, not as a separate public-facing service. The new deployment path keeps `kiro-rs` private, reachable only from the shared Docker network, and gives the fork an automated GHCR-to-VPS rollout similar to the CLIProxyAPI deployment.

## Notable decisions

- Chose no public host port mapping at all.
- Chose the stable external Docker network name `cli-proxy-api-proxy` so CLIProxyAPI can use `http://kiro-rs:8990`.
- Chose amd64-only production image publication because the VPS target is `x86_64`.
- Kept live `config.json` and `credentials.json` on the VPS, not in the repo.
