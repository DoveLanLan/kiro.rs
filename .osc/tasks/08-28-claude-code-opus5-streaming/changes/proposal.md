# Proposal: Fix Claude Code Opus 5 Streaming

- Date: 2026-08-28
- Owner(s): hewei
- Stakeholders: Claude Code CLI users, CLIProxyAPI operators
- Status: Proposed

## Context / Problem

Claude Code reports `Streaming response ended before any complete data was received` when requesting Opus 5 through the deployed proxy. The downstream Anthropic-compatible response can remain silent while `/cc/v1/messages` buffers the upstream Kiro stream, and the current heartbeat interval is longer than some proxy idle timeouts. Streaming responses also do not explicitly advertise that intermediary buffering must be disabled.

## Goals (Why/What)

- Make Opus 5 requests through Claude Code receive a usable Anthropic SSE event before common intermediary idle timeouts.
- Preserve the existing Anthropic event ordering and `/cc/v1` buffered input-token behavior.
- Keep `/v1/messages` and `/cc/v1/messages` compatible with existing clients.

## Constraints

- Keep the change limited to the Anthropic streaming response layer and its tests/docs.
- Do not expose or modify credentials, API keys, or deployment secrets.
- Do not remove Opus 5 model mapping or change Kiro upstream request semantics.

## Non-goals

- Rework CLIProxyAPI, Nginx, Caddy, or Cloudflare configuration.
- Change model quotas, token refresh, or credential failover behavior.
- Guarantee streaming through an intermediary that deliberately buffers or terminates SSE.

## Proposed Approach (high-level)

Advertise `X-Accel-Buffering: no` on generated SSE responses and send heartbeats more frequently than the observed short idle timeout. Add focused tests for the response headers/heartbeat contract and document that the deployment's intermediary must still pass SSE bodies through without buffering.

## Risks & Mitigations

- Risk: More frequent heartbeats add a small amount of network traffic.
  - Mitigation: Use a 10-second interval, only while the upstream stream is active.
- Risk: An intermediary may ignore the header.
  - Mitigation: Keep the existing `/v1` fallback and document proxy-level buffering/timeout settings.
- Risk: Existing consumers may depend on the 25-second heartbeat cadence.
  - Mitigation: Heartbeats are valid SSE events; lowering the interval is backward-compatible and improves liveness.

## Open Questions (max 3)

- None blocking implementation.
