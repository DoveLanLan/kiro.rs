# Proposal: Add Proxy Config For AWS UsageLimits Connectivity

- Date: 2026-02-27
- Owner(s): hewei
- Stakeholders: local operator, API consumers
- Status: Proposed

## Context / Problem
`id=1` credential intermittently fails with `error sending request for url (https://q.us-east-1.amazonaws.com/getUsageLimits...)` when service startup/runtime does not inherit shell proxy environment variables. Current `config/config.json` does not set `proxyUrl`, so runtime network behavior depends on process environment.

## Goals (Why/What)
- Make outbound AWS API connectivity deterministic by setting explicit proxy in local runtime config.
- Keep existing credentials behavior (`id=2` retained) while enabling `id=1` refresh/usage checks through the same stable network path.

## Constraints
- Must not modify Rust source logic for this request; config-only change.
- Keep secrets/tokens out of new artifacts; only non-sensitive config keys are documented.

## Non-goals
- No refactor of token manager/provider retry logic.
- No CI/workflow behavior changes.

## Proposed Approach (high-level)
Update `config/config.json` to include a concrete `proxyUrl` endpoint that matches the working local proxy path already validated in shell environment. Keep region/auth settings unchanged. Verify by checking that IdC refresh and `getUsageLimits` can be reached with the updated config path.

## Risks & Mitigations
- Risk: proxy process not running on configured port causes immediate request failures.
  - Mitigation: verify local proxy listener and keep rollback by removing `proxyUrl`.
- Risk: container runtime cannot reach host loopback (`127.0.0.1`) in Docker mode.
  - Mitigation: document host mapping alternative for container runs (`host.docker.internal` or bridge IP).

## Open Questions (max 3)
- none
