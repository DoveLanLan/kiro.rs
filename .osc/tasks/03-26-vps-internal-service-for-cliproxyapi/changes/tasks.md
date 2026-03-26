# Tasks: Deploy kiro-rs To VPS As Internal Service For CLIProxyAPI

- Date: 2026-03-26
- Owner(s): hewei
- Related: `proposal.md`, `spec.md`

## Assumptions

- The target VPS already runs the user's CLIProxyAPI production stack.
- The Docker network `cli-proxy-api-proxy` already exists or can be created before the first `kiro-rs` deploy.
- The target branch for auto-deploy remains `master`.

## Checklist

- [x] 1) Add production deployment artifacts
  - Target: new `deploy/` directory
  - Change: add production Compose, env template, remote deploy script, and deployment docs for an internal-only service
  - Verify: inspect files for no host port publication and external network usage

- [x] 2) Rework GHCR image publishing for branch deploys
  - Target: `.github/workflows/docker-build.yaml`
  - Change: publish deterministic amd64 image tags for `master` and release tags
  - Verify: workflow tags reference GHCR under the fork namespace and include branch/SHA tags

- [x] 3) Add production deploy workflow
  - Target: new deployment workflow
  - Change: add SSH deployment to `/opt/kiro-rs` with `docker compose pull` / `up -d`
  - Verify: workflow includes deploy asset upload, remote script execution, and uses production environment secrets

- [x] 4) Document CLIProxyAPI integration path
  - Target: deployment docs
  - Change: explain that CLIProxyAPI should use `http://kiro-rs:8990` on the shared Docker network
  - Verify: docs contain the internal upstream URL and config expectations

- [x] 5) Run quality checks for deployment changes
  - Target: workflow files, deploy files, repo quality gates
  - Change: validate YAML, shell syntax, compose rendering, and backend build gates
  - Verify: results captured in `.osc/quality-gate.md`

## Notes

- Public ingress is intentionally out of scope because this service is a backend dependency for CLIProxyAPI, not a user-facing endpoint.
- The production design deliberately depends on the external Docker network created by the deployed CLIProxyAPI stack.
