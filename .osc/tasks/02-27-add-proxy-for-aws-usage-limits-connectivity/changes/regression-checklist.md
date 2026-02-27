# Regression Checklist: Add Proxy Config For AWS UsageLimits Connectivity

- Date: 2026-02-27
- Related: ./spec.md, ./tasks.md

## Gates (from Repo Snapshot)
- Build: `cargo build`
- Tests: `cargo test`
- Lint/format: `cargo fmt --check` and `cargo clippy --all-targets --all-features`
- Other: connectivity checks for `oidc.us-east-1.amazonaws.com` and `q.us-east-1.amazonaws.com`

## Manual checks (if applicable)
- Start service with `-c config/config.json --credentials config/credentials.json` and verify startup logs show proxy configured.
- Trigger admin balance or a normal request path and verify no `error sending request for url` on `getUsageLimits` path.

## Edge-case re-tests
- Stop local proxy and confirm expected explicit network failure (to prove failure mode is transparent).
- If running in Docker, replace loopback proxy host when needed and re-test.
