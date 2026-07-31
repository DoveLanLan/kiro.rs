# Proposal: Handle Overage Quota Exhaustion Failover

- Date: 2026-07-31
- Status: Proposed

## Context / Problem

The deployed Kiro upstream returned HTTP 402 with
`reason=OVERAGE_REQUEST_LIMIT_EXCEEDED`. The provider only classifies
`MONTHLY_REQUEST_COUNT` as quota exhaustion, so this equivalent terminal quota
condition bypasses the existing credential failover path.

## Goals

- Recognize `OVERAGE_REQUEST_LIMIT_EXCEEDED` as exhausted quota.
- Reuse the existing disable-and-switch behavior for HTTP 402 responses.
- Prevent regression with focused unit tests.

## Non-goals

- Do not change handling of HTTP 400, 401, 403, 408, 429, or 5xx responses.
- Do not change credential priority or persistence semantics.
- Do not add message-text matching without a recognized reason code.

## Proposed Approach

Extend the shared endpoint quota-reason predicate with the newly observed
reason. Test both top-level and nested JSON response shapes. The provider's
existing HTTP 402 guard remains responsible for invoking failover.

## Risk / Rollback

Risk is low because the new match is an exact upstream reason code and remains
gated by HTTP 402. Roll back the predicate and its tests, then redeploy the
previous image if needed.
