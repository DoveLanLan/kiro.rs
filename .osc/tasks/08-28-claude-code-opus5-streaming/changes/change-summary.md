# Change Summary: Fix Claude Code Opus 5 Streaming

- Date: 2026-08-28
- Owner(s): hewei
- Related: `proposal.md`, `spec.md`, `tasks.md`

## What changed

- Added a shared SSE response builder that sets `X-Accel-Buffering: no` and `Cache-Control: no-cache, no-transform`.
- Reduced the Anthropic SSE heartbeat interval from 25 seconds to 10 seconds for both `/v1/messages` and `/cc/v1/messages`.
- Added focused tests for the SSE headers and heartbeat contract.
- Updated the `/cc/v1` README documentation.
- Added deployment guidance for intermediaries that proxy Claude Code SSE traffic.

## Why

Claude Code can wait for a usable Opus 5 event while `/cc/v1` buffers the Kiro stream. A short intermediary idle timeout or response buffering can close the connection before Claude Code receives a complete Anthropic event. The response header and shorter heartbeat reduce that failure window while preserving the existing event conversion and Opus 5 mapping.

## Notable decisions

- Kept `/cc/v1` buffering and context-derived input-token correction unchanged.
- Did not change credentials, Kiro request bodies, model mapping, or external proxy configuration.
