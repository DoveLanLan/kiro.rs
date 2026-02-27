# Spec: Add Proxy Config For AWS UsageLimits Connectivity

- Date: 2026-02-27
- Owner(s): hewei
- Related: ./proposal.md, ./tasks.md

## Repo Snapshot (from step 0)
- Modules/components:
  - Rust proxy service in `src/` with credential/token/network handling (`src/kiro`, `src/http_client.rs`).
  - Runtime local config in `config/` (`config/config.json`, `config/credentials.json`).
  - Admin UI build artifacts and embedding (`admin-ui/`, `src/admin_ui/`).
- Toolchains:
  - Build: `cargo build`, `cargo build --release`; frontend `pnpm build`.
  - Test/quality: `cargo test`, `cargo fmt`, `cargo clippy --all-targets --all-features`.
  - CI: artifact build/release workflows under `.github/workflows/*.yaml`.
- Confidence: High.
- Evidence: `AGENTS.md`, `Cargo.toml`, `admin-ui/package.json`, `.github/workflows/build.yaml`, `.github/workflows/docker-build.yaml`, `src/http_client.rs`, `src/kiro/token_manager.rs`, `config/config.json`.

## Scope
### In scope
- Add explicit global `proxyUrl` to local runtime config so outbound AWS calls do not depend only on shell environment inheritance.
- Validate resulting path for IdC refresh and `getUsageLimits` connectivity using current `id=1` credentials.

### Out of scope
- Source code changes in Rust modules.
- Credential rotation or account-level permission changes.

## Acceptance Criteria (testable)
1. `config/config.json` includes non-empty `proxyUrl` with the intended local proxy endpoint. (Verify: `jq '.proxyUrl' config/config.json`)
2. `id=1` can complete IdC refresh + `getUsageLimits` through configured proxy path. (Verify: local curl checks with HTTP 200)
3. Existing `id=2` credential record remains present and unchanged for its critical fields (`id`, `priority`, `authMethod`). (Verify: `jq` comparison)

## Behavior / Requirements
- Application must build HTTP clients with configured `proxyUrl` from config layer when credential does not override proxy.
- No changes to region precedence or auth method resolution.
- Runtime behavior should remain backward-compatible: removing `proxyUrl` returns to previous environment-driven behavior.

## Edge Cases
- Local proxy is down or port unavailable.
- Running inside Docker where `127.0.0.1` points to container itself.
- Proxy protocol mismatch (`http://` vs `socks5://`) for local listener.

## Compatibility Notes
- Backwards compatibility: preserved (config addition only).
- Data/migrations: none.
- Config/flags: only `proxyUrl` in local config file.

## API/UX Decisions (if applicable)
- Inputs/outputs: no API contract change.
- States/errors: network failures still surface as upstream request send errors.
- Telemetry/logging: existing tracing lines continue to indicate proxy usage.
- Accessibility/i18n (if UI): not applicable.
