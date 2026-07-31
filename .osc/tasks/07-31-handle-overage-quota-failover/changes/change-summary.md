# Change Summary: Handle Overage Quota Exhaustion Failover

- Date: 2026-07-31
- Source commit: `9a7273e4447692ac2aa37b08d99099665b960e3e`

## What changed

- Added `OVERAGE_REQUEST_LIMIT_EXCEEDED` to the endpoint quota-exhaustion
  classifier alongside `MONTHLY_REQUEST_COUNT`.
- Added unit tests for top-level and nested overage reason payloads.
- Deployed the exact SHA-tagged GHCR image to bytevirt.

## Runtime result

- Container image revision matches source commit `9a7273e...`.
- Container is running with zero restarts.
- Authenticated `GET /v1/models` returns HTTP 200 with 20 models.
- Existing priority load balancing and `http://split-proxy:3128` remain loaded.

## Behavioral result

An HTTP 402 response carrying `OVERAGE_REQUEST_LIMIT_EXCEEDED` now enters the
existing quota-exhausted branch, disables the current credential in memory,
and retries with the highest-priority enabled credential.
