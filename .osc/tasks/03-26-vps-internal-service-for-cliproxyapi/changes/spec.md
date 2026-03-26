# Spec: Deploy kiro-rs To VPS As Internal Service For CLIProxyAPI

- Date: 2026-03-26
- Owner(s): hewei
- Related: `proposal.md`, `tasks.md`

## Repo Snapshot (from step 0)

- Modules/components:
  - Rust proxy runtime in `src/`
  - Embedded admin UI source in `admin-ui/`
  - Docker packaging via `Dockerfile` and `docker-compose.yml`
  - GitHub Actions build/docker workflows in `.github/workflows/`
- Toolchains:
  - Build: `cargo build --release`, `pnpm build`, Docker multi-stage image build
  - Quality: `cargo fmt`, `cargo clippy --all-targets --all-features`, `cargo test`
  - CI: artifact build workflow and Docker GHCR workflow
- Confidence: High
- Evidence: `AGENTS.md`, `README.md`, `Dockerfile`, `docker-compose.yml`, `.github/workflows/build.yaml`, `.github/workflows/docker-build.yaml`

## Scope

### In scope

- Add production deployment artifacts under `deploy/` for VPS deployment.
- Rework Docker GHCR publishing to support branch-driven amd64 images for this fork.
- Add a production deployment workflow for VPS rollout.
- Keep the service internal-only by avoiding public host port mapping.
- Attach the service to the external Docker network `cli-proxy-api-proxy` with a stable alias for CLIProxyAPI.
- Document required server-side runtime files and the expected upstream URL for CLIProxyAPI.

### Out of scope

- Public ingress or domain/TLS handling.
- Rust business logic changes.
- Frontend/admin UI feature changes.
- Multi-arch production deployment in this first version.

## Acceptance Criteria (testable)

1. The repository contains a production Compose file that runs `kiro-rs` from an image without publishing any host port. (Verify: inspect `deploy/compose.production.yml`)
2. The production Compose file joins the external Docker network `cli-proxy-api-proxy` and exposes a stable alias `kiro-rs`. (Verify: inspect network section and service aliases)
3. The repository contains a production deploy workflow that can publish and deploy the service on `master` updates. (Verify: inspect `.github/workflows/docker-build.yaml` and deployment workflow)
4. The deployment docs specify that production `config.json` uses `host: "0.0.0.0"` and `port: 8990`. (Verify: inspect deployment docs/templates)
5. The remote deploy script fails clearly when the external Docker network does not exist. (Verify: inspect script)
6. The deployment docs make it explicit that `CLIProxyAPI` should use `http://kiro-rs:8990` as the internal upstream URL after deployment. (Verify: inspect docs)

## Behavior / Requirements

- Production deployment should be idempotent and safe to rerun.
- The stack should not bind `8990` on the VPS public interfaces.
- The stack should rely on the existing `cli-proxy-api-proxy` Docker network created by the CLIProxyAPI deployment.
- Production runtime state should live on the VPS under a persistent path for `config.json` and `credentials.json`.
- The image publication flow should produce deterministic tags usable by the deployment workflow, including a commit-SHA-oriented tag and a stable branch tag.

## Edge Cases

- The external Docker network may be absent if CLIProxyAPI has not been deployed yet.
- `config.json` may be left on `127.0.0.1`, causing container-to-container connectivity failure.
- `credentials.json` may be missing or contain expired refresh tokens.
- GHCR package visibility may block image pulls if left private.

## Compatibility Notes

- Backwards compatibility: the existing local/dev `docker-compose.yml` remains available for local use.
- Data/migrations: none; only file-backed runtime config/credentials are involved.
- Config/flags: production config must listen on `0.0.0.0`; no public admin or domain config is introduced.

## API/UX Decisions (if applicable)

- Inputs/outputs: CLIProxyAPI should consume `kiro-rs` over `http://kiro-rs:8990` on the shared Docker network.
- States/errors: deployment should stop early on missing network or missing runtime files.
- Telemetry/logging: operators should inspect `docker compose logs` on the VPS for runtime failures.
- Accessibility/i18n: not applicable.
