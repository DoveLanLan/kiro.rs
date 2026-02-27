# Tasks: Add Proxy Config For AWS UsageLimits Connectivity

- Date: 2026-02-27
- Owner(s): hewei
- Related: ./proposal.md, ./spec.md

## Assumptions
- Local proxy endpoint `http://127.0.0.1:10808` is reachable on the machine running `kiro-rs`.
- User wants config-level deterministic proxy behavior instead of relying only on environment variables.

## Checklist
- [x] 1) Create OSC change artifacts
  - Target: `.osc/tasks/02-27-add-proxy-for-aws-usage-limits-connectivity/changes/`
  - Change: write `proposal.md`, `spec.md`, `tasks.md`.
  - Verify: files exist and include scope + acceptance criteria.

- [x] 2) Add proxy to runtime config
  - Target: `config/config.json`
  - Change: set `proxyUrl` to local proxy endpoint.
  - Verify: `jq '.proxyUrl' config/config.json` returns expected value.

- [x] 3) Validate connectivity with id=1
  - Target: runtime network path (`oidc.us-east-1.amazonaws.com`, `q.us-east-1.amazonaws.com`)
  - Change: run refresh + usage limits checks with redacted outputs.
  - Verify: status code indicates success (`200`).

## Notes
- If running in Docker, loopback proxy address may require replacement with `host.docker.internal` or host bridge IP.
