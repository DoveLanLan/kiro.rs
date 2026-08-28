# Spec: Fix Claude Code Opus 5 Streaming

- Date: 2026-08-28
- Owner(s): hewei
- Related: `proposal.md`, `tasks.md`

## Repo Snapshot (from step 0)

- Modules/components: Rust Anthropic handlers/stream conversion, Kiro provider/parser, Docker deployment, embedded React admin UI.
- Toolchains: `cargo test`, `cargo build`, `cargo fmt`, and `cargo clippy`; frontend `pnpm build` when UI changes.
- Confidence: High for backend gates; evidence: `AGENTS.md`, `Cargo.toml`, `README.md`, `.github/workflows/build.yaml`, `Dockerfile`.
- Runtime evidence: `/v1/messages` streams immediately; `/cc/v1/messages` buffers until upstream completion; evidence: `src/anthropic/handlers.rs`, `README.md`.

## Scope

### In scope

- Add an anti-buffering response header to both Anthropic SSE endpoints.
- Reduce the server heartbeat interval to 10 seconds.
- Add focused regression coverage for the SSE response contract.
- Update endpoint documentation to reflect the liveness behavior.

### Out of scope

- Changes to Kiro model mapping, credentials, token refresh, or provider request bodies.
- Changes to external CLIProxyAPI or reverse-proxy configuration.

## Acceptance Criteria (testable)

1. A streaming `/v1/messages` response includes `Content-Type: text/event-stream`, `Cache-Control: no-cache`, and `X-Accel-Buffering: no`. (Verify: focused handler/response test or header inspection.)
2. A streaming `/cc/v1/messages` response includes the same anti-buffering header and emits a heartbeat no less frequently than every 10 seconds while waiting for Kiro. (Verify: focused stream test/code review.)
3. Existing Opus 5 model IDs continue to map to `claude-opus-5`. (Verify: existing converter unit tests.)
4. Focused SSE/Opus 5 tests and both debug/release builds pass; repository-wide formatting, test, and clippy baseline exceptions are recorded rather than introduced by this patch. (Verify: local commands and `.osc/quality-gate.md`.)

## Behavior / Requirements

- Keep SSE event payloads and ordering unchanged.
- The anti-buffering header must be present on successful streaming responses only; it must not alter JSON error responses.
- Heartbeats remain valid `event: ping` SSE events and must not be emitted after the upstream stream has finished.
- `/cc/v1/messages` continues to buffer model events so its final `message_start` can use the context-derived input token count.

## Edge Cases

- Upstream returns an error before its first event: the handler still emits the existing terminal Anthropic events and closes cleanly.
- Upstream remains idle for longer than 10 seconds: heartbeat events keep the downstream connection active.
- A proxy ignores `X-Accel-Buffering`: operators still need to disable proxy buffering and configure a longer read timeout.

## Compatibility Notes

- Backwards compatibility: response event names and JSON schemas are unchanged; only an extra response header and more frequent valid pings are added.
- Data/migrations: none.
- Config/flags: none; the interval remains an internal constant.

## API/UX Decisions (if applicable)

- Inputs/outputs: no request or model ID changes.
- States/errors: no new error type; the client should receive a complete `message_stop` event when the upstream completes.
- Telemetry/logging: retain existing stream error logs.
