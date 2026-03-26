# Proposal: Deploy kiro-rs To VPS As Internal Service For CLIProxyAPI

- Date: 2026-03-26
- Owner(s): hewei
- Stakeholders: hewei, operators of the VPS, CLIProxyAPI runtime using kiro-rs as an upstream
- Status: Proposed

## Context / Problem

The repository already has Docker packaging and a GHCR publishing workflow, but it is currently release-oriented and not designed for automatic VPS deployment on branch updates. The current compose file publishes port `8990` directly on the host, which is unnecessary for this use case because the user wants `kiro-rs` to be consumed only by `CLIProxyAPI` on the same VPS rather than exposed to the public internet.

The target VPS already runs the user's `CLIProxyAPI` stack in Docker. The cleanest integration path is to deploy `kiro-rs` as a second stack that joins the stable `cli-proxy-api-proxy` Docker network so `CLIProxyAPI` can reach it by container DNS name without host-port exposure.

## Goals (Why/What)

- Publish an amd64 `kiro-rs` image for the fork to GHCR from GitHub Actions.
- Deploy `kiro-rs` automatically to the VPS on `master` branch updates.
- Run `kiro-rs` without any public host port mapping.
- Join the existing `cli-proxy-api-proxy` Docker network and expose a stable internal DNS alias such as `kiro-rs`.
- Keep live `config.json` and `credentials.json` on the VPS, outside git.

## Constraints

- Must follow the repo's `osc` change workflow before editing tracked files.
- Must preserve the Rust + embedded admin-ui Docker build path.
- Must target `linux/amd64` first because the VPS is `x86_64`.
- Must not expose `8990` on the VPS public interfaces.
- Must assume the external Docker network name is `cli-proxy-api-proxy`, as currently created by the deployed CLIProxyAPI stack.
- Must not commit live Kiro credentials, tokens, or admin keys.

## Non-goals

- Reworking Rust request/response logic.
- Public reverse proxying or TLS for `kiro-rs`.
- Enabling public admin access for this service.
- Multi-arch production deployment in the first pass.

## Proposed Approach (high-level)

Add a dedicated production deployment package under `deploy/` that runs `kiro-rs` from GHCR with no host port publishing and attaches it to the pre-existing `cli-proxy-api-proxy` external Docker network using a stable alias. Rework the GHCR Docker workflow so branch builds publish deterministic amd64 image tags for the fork, and add a production deployment workflow that pushes deployment assets to the VPS over SSH and runs `docker compose pull` / `up -d`.

The runtime config on the VPS will set `host` to `0.0.0.0` and `port` to `8990` so the process listens inside the container network. `CLIProxyAPI` can then point its upstream base URL at `http://kiro-rs:8990`.

## Risks & Mitigations

- Risk: the external Docker network `cli-proxy-api-proxy` does not exist when the stack starts.
  - Mitigation: fail fast in the remote deployment script with a clear message and document that CLIProxyAPI must be deployed first or the network must be created manually.
- Risk: live credentials or admin keys could be accidentally committed.
  - Mitigation: keep `config.json` and `credentials.json` server-side only and document the expected server layout.
- Risk: branch deployments produce a package that is private by default, blocking VPS pulls.
  - Mitigation: document GHCR package visibility expectations exactly as in the CLIProxyAPI deployment flow.
- Risk: `kiro-rs` may listen only on loopback inside the container if the config is left at `127.0.0.1`.
  - Mitigation: document and template `host: "0.0.0.0"` for the production config.

## Open Questions (max 3)

- None. The current repo and deployment context are sufficient to implement the internal-service deployment path.
