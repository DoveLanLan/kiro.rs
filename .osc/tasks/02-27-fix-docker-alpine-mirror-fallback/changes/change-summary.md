# Change Summary: Fix Docker Alpine Mirror Fallback

- Date: 2026-02-27
- Owner(s): hewei
- Related: ./proposal.md, ./spec.md, ./tasks.md

## What changed
- Replaced hardcoded Alpine mirror behavior in `Dockerfile` with resilient mirror retry logic in builder stage.
- Added optional `ALPINE_MIRROR` build arg support in `docker-compose.yml`.
- Removed runtime-stage `apk add` dependency by copying `/etc/ssl` from builder stage, avoiding extra repository fetch in final image stage.

## Why
The previous Dockerfile forcibly switched runtime stage to Tsinghua mirror, causing build failure when that mirror was temporarily unavailable. The new logic allows custom mirror usage while automatically trying multiple mirrors and reducing runtime-stage network dependency.

## Notable decisions
- Mirror retries now cover custom mirror, official mirror, Aliyun mirror, and Tsinghua mirror.
- Runtime certificate provisioning is done via stage-to-stage copy to avoid duplicate package install in stage-2.
