# Regression Checklist: Fix Claude Code Opus 5 Streaming

- Date: 2026-08-28
- Related: `proposal.md`, `spec.md`, `tasks.md`

## Gates (from Repo Snapshot)

- Rust build: `cargo build` passed.
- Release build: `cargo build --release` passed.
- Focused handler tests: `cargo test anthropic::handlers::tests -- --nocapture` passed (2/2).
- Opus 5 mapping test: `cargo test anthropic::converter::tests::test_map_model_opus_5 -- --nocapture` passed (1/1).
- Full test suite: `cargo test` ran 227 tests; 219 passed and 8 pre-existing legacy model-mapping tests failed for generic `claude-sonnet-4`/opus expectations.
- Format: `cargo fmt -- --check` remains red because the repository already contains formatting drift in unrelated files; no new formatting issue was reported for the changed test block.
- Clippy: `cargo clippy --all-targets --all-features -- -D warnings` remains red on 105 pre-existing warnings/errors across unrelated modules.

## Manual checks (if applicable)

- From the CLIProxyAPI container, call `http://kiro-rs:8990/v1/messages` with `stream: true`. Expected: `event: message_start` arrives promptly and the stream ends with `event: message_stop`.
- Repeat against `/cc/v1/messages`. Expected: the response remains alive with `event: ping` heartbeats at most 10 seconds apart and eventually emits the complete event sequence.
- Run Claude Code with the Opus 5 model through the deployed endpoint. Expected: no `Streaming response ended before any complete data was received` warning.

## Edge-case re-tests

- Verify a proxy that honors `X-Accel-Buffering: no` does not buffer the SSE body.
- Verify an upstream stream error still produces the existing terminal Anthropic events.
- Verify the existing Opus 5 mapping test remains green.
