# Tasks: Fix Claude Code Opus 5 Streaming

- Date: 2026-08-28
- Owner(s): hewei
- Related: `proposal.md`, `spec.md`

## Assumptions

- Claude Code reaches the Anthropic-compatible endpoint through a proxy or CLIProxyAPI that supports SSE but may apply a short idle timeout.
- The existing Opus 5 mapping is correct and should not be changed.

## Checklist

- [x] 1) Harden Anthropic SSE response liveness
  - Target: `src/anthropic/handlers.rs`
  - Change: add `X-Accel-Buffering: no` and reduce the heartbeat interval to 10 seconds for both streaming paths.
  - Verify: focused tests/header inspection and stream code review.

- [x] 2) Add/update regression documentation and tests
  - Target: `src/anthropic/handlers.rs`, `README.md`
  - Change: cover the response contract and document the intended keepalive behavior.
  - Verify: `cargo test` and inspect the documented `/cc/v1` behavior.

- [x] 3) Run backend quality gates
  - Target: repository backend
  - Change: format, test, and build the Rust service.
  - Verify: `cargo fmt --check`, `cargo test`, `cargo build`; focused tests and both builds pass, while existing repository-wide format/test/clippy baselines remain red as recorded in the quality-gate report.
