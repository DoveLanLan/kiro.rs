# Bugfix: Fix Claude Code Opus 5 streaming

## 问题描述

Claude Code CLI 请求 Opus 5 时提示 `Streaming response ended before any complete data was received`，随后退回非流式请求。部署链路中的短空闲超时或 SSE 缓冲会在 `/cc/v1/messages` 等待 Kiro 上游结果期间提前关闭连接。

## 复现步骤

1. 通过 CLIProxyAPI/反向代理向 kiro-rs 的 `/cc/v1/messages` 发送 Opus 5 流式请求。
2. 让上游首个可用事件等待超过中间层的空闲超时。
3. Claude Code 收到空流并提示上述错误。

## 期望行为

Claude Code 能收到完整的 Anthropic SSE 事件序列，并正常使用 Opus 5 完成请求。

## 实际行为

流式连接在收到完整可用事件前被中间层关闭，Claude Code 自动重试非流式。

## 根因分析

kiro-rs 的 SSE 响应未显式声明关闭代理缓冲，且等待期间心跳为 25 秒；这对短超时的 CLIProxyAPI/反代链路不够稳健。

## 修复方案

统一 SSE 响应头，加入 `X-Accel-Buffering: no` 和 `no-transform`，并将心跳间隔缩短为 10 秒；保留现有 Opus 5 映射和事件顺序。

## 回归测试

- [x] SSE 响应头和 10 秒心跳单测
- [x] Opus 5 映射单测
- [x] `cargo build` 与 `cargo build --release`
- [ ] VPS 上通过 CLIProxyAPI 实际请求 Claude Code Opus 5
