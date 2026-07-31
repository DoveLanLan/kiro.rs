# Spec: Handle Overage Quota Exhaustion Failover

- Date: 2026-07-31
- Related: `proposal.md`, `tasks.md`

## Scope

### In scope

- `src/kiro/endpoint/mod.rs` quota exhaustion classification.
- Unit tests for the observed overage reason.
- Rebuild and redeploy the `kiro-rs` service on bytevirt.

### Out of scope

- Credential-file schema changes.
- Persisting automatically disabled quota state across restarts.
- Broad changes to retry counts or load-balancing policy.

## Requirements

1. `MONTHLY_REQUEST_COUNT` remains recognized.
2. `OVERAGE_REQUEST_LIMIT_EXCEEDED` is recognized in top-level `reason` and
   nested `error.reason` payloads.
3. An unrelated reason such as `DAILY_REQUEST_COUNT` remains unrecognized.
4. Matching only enters failover when the provider receives HTTP 402, as it
   does today.

## Acceptance Criteria

- Focused endpoint unit tests pass.
- Full `cargo test` passes.
- `cargo fmt --check` and `cargo clippy --all-targets --all-features` pass, with
  no new warnings attributable to this change.
- The bytevirt container runs the rebuilt image and reaches a healthy/running
  state without startup errors.

## Compatibility

No API or configuration contract changes. Existing quota and non-quota error
handling remains backward-compatible.
