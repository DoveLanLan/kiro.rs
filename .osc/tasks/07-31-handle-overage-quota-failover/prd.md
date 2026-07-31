# Bugfix: Handle overage quota exhaustion failover

## 问题描述
Kiro may return HTTP 402 with `reason=OVERAGE_REQUEST_LIMIT_EXCEEDED` when an
account's paid overage balance is exhausted. The current endpoint classifier
only recognizes `MONTHLY_REQUEST_COUNT`, so the provider returns the 402
instead of disabling that credential and retrying another one.

## 复现步骤
1. Configure two or more enabled credentials in priority mode.
2. Make the current credential return HTTP 402 with
   `{"reason":"OVERAGE_REQUEST_LIMIT_EXCEEDED"}`.
3. Observe that the request exits through the generic 4xx branch.

## 期望行为
Treat the overage limit reason as quota exhaustion and use the existing
credential-disable and failover flow.

## 实际行为
The response is treated as an unrecognized client error; no credential switch
occurs.

## 根因分析
`default_is_monthly_request_limit` only matches `MONTHLY_REQUEST_COUNT`.

## 修复方案
Extend the endpoint quota classifier to recognize
`OVERAGE_REQUEST_LIMIT_EXCEEDED`, retaining the existing HTTP 402 guard and
adding unit coverage for top-level and nested reason payloads.

## 回归测试
- [ ] Both recognized quota reasons return `true`.
- [ ] Unrelated limit reasons still return `false`.
- [ ] Rust formatting, focused tests, full tests, and clippy pass.
