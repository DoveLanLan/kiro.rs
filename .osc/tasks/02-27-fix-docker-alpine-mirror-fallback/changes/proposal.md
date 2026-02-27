# Proposal: Fix Docker Alpine Mirror Fallback

- Date: 2026-02-27
- Owner(s): hewei
- Stakeholders: local Docker users, CI/build users
- Status: Proposed

## Context / Problem
`docker compose up -d --build` fails at runtime image stage because Dockerfile forcibly rewrites Alpine repository host to `mirrors.tuna.tsinghua.edu.cn`. In non-CN networks, this mirror can be unavailable, causing `apk add --no-cache ca-certificates` to fail.

## Goals (Why/What)
- Make Docker build succeed reliably across different networks.
- Keep mirror acceleration optional for users who need region-specific mirrors.

## Constraints
- Must keep changes limited to Docker-related files.
- Must preserve current multi-stage build flow and runtime package installation behavior.

## Non-goals
- No changes to Rust business logic.
- No changes to application runtime config semantics.

## Proposed Approach (high-level)
Replace hardcoded Tsinghua mirror rewrite with configurable build arg (`ALPINE_MIRROR`) and add fallback logic: if package install fails on custom mirror, automatically restore official Alpine mirror and retry once.

## Risks & Mitigations
- Risk: custom mirror string malformed.
  - Mitigation: default to official mirror and fallback retry to official host.
- Risk: fallback sed replacement misses repository format.
  - Mitigation: replace host in `/etc/apk/repositories` with robust host-level rule before retry.

## Open Questions (max 3)
- none
