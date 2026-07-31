# Regression Checklist: Handle Overage Quota Exhaustion Failover

- Date: 2026-07-31

## Automated checks

- [x] `cargo test kiro::endpoint::tests::test_default_ -- --nocapture`
  - Result: 6 passed, 0 failed.
- [x] `cargo clippy --all-targets --all-features`
  - Result: passed with existing repository warnings; no new warning from the
    changed endpoint module.
- [ ] `cargo test`
  - Result: 207 passed, 8 failed. All failures are pre-existing
    `claude-sonnet-4` / legacy opus model-mapping test expectations in
    `src/anthropic/converter.rs`, outside this change.
- [ ] `cargo fmt --check`
  - Result: blocked by pre-existing formatting drift across unrelated source
    files. The changed endpoint module was formatted and `git diff --check`
    passed.

## Deployment checks

- [x] GitHub Actions Docker build completed successfully.
- [x] bytevirt runs SHA-tagged image revision `9a7273e...`.
- [x] Container restart count is zero.
- [x] `GET /v1/models` returns HTTP 200 and 20 models.
- [x] Runtime logs confirm the configured split proxy is loaded.
