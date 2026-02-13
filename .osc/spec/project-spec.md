# Project Specification: kiro.rs

## Overview

**kiro.rs** 是一个用 Rust 编写的 Anthropic Claude API 兼容代理服务，将 Anthropic API 请求转换为 Kiro API 请求。

**定位**：作为 Claude API 的本地中间层或企业级部署方案，让用户可以用标准 Anthropic API 格式调用 Kiro 后端。

---

## Core Features

| 功能 | 描述 |
|------|------|
| Anthropic API 兼容 | 完整支持 `/v1/messages`、`/v1/models`、`/v1/messages/count_tokens` |
| Claude Code 兼容 | `/cc/v1/messages` 缓冲模式，返回准确的 `input_tokens` |
| 流式响应 | SSE (Server-Sent Events) 实时输出 |
| Token 自动刷新 | OAuth Token 过期自动刷新，支持 social 和 idc 两种认证方式 |
| 多凭据支持 | 按优先级故障转移，单凭据最多重试 3 次，单请求最多重试 9 次 |
| Extended Thinking | 支持 Claude 的 thinking 模式 |
| Tool Use | 完整支持 function calling / tool use |
| Admin API | 可选的凭据管理 API 和 Web UI |

---

## Tech Stack

| 层级 | 技术 |
|------|------|
| 语言 | Rust (Edition 2024) |
| Web 框架 | Axum 0.8 |
| 异步运行时 | Tokio |
| HTTP 客户端 | Reqwest 0.12 (支持 rustls / native-tls) |
| 序列化 | Serde + serde_json |
| 日志 | tracing + tracing-subscriber |
| CLI | Clap 4.5 |
| 前端 (Admin UI) | React + TypeScript + Vite |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client                                  │
│              (Claude Code / curl / SDK)                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      kiro.rs Proxy                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Anthropic Layer                         │   │
│  │  - Router (/v1, /cc/v1)                                  │   │
│  │  - Auth Middleware (x-api-key / Bearer)                  │   │
│  │  - Request Converter (Anthropic → Kiro)                  │   │
│  │  - Response Stream (AWS Event Stream → SSE)              │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Kiro Layer                            │   │
│  │  - KiroProvider (API 调用)                               │   │
│  │  - MultiTokenManager (多凭据管理)                         │   │
│  │  - AWS Event Stream Parser                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Admin Layer (可选)                      │   │
│  │  - Admin API (凭据 CRUD)                                 │   │
│  │  - Admin UI (嵌入式 React SPA)                           │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Kiro API                                  │
│                  (AWS Event Stream)                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
kiro-rs/
├── src/
│   ├── main.rs                 # 程序入口
│   ├── model/                  # 配置和参数模型
│   │   ├── config.rs           # 应用配置 (host, port, apiKey, region, etc.)
│   │   └── arg.rs              # 命令行参数 (clap)
│   ├── anthropic/              # Anthropic API 兼容层
│   │   ├── router.rs           # 路由配置 (/v1, /cc/v1)
│   │   ├── handlers.rs         # 请求处理器 (models, messages, count_tokens)
│   │   ├── middleware.rs       # 认证中间件 + CORS
│   │   ├── types.rs            # 请求/响应类型定义
│   │   ├── converter.rs        # Anthropic ↔ Kiro 协议转换
│   │   ├── stream.rs           # 流式响应处理 (SSE)
│   │   └── websearch.rs        # WebSearch 工具转换
│   ├── kiro/                   # Kiro API 客户端
│   │   ├── provider.rs         # API 提供者 (与 Kiro API 通信)
│   │   ├── token_manager.rs    # Token 管理和刷新
│   │   ├── machine_id.rs       # 设备指纹生成
│   │   ├── model/              # 数据模型
│   │   │   ├── credentials.rs  # OAuth 凭证配置
│   │   │   ├── events/         # 响应事件类型
│   │   │   ├── requests/       # 请求类型
│   │   │   └── common/         # 共享类型
│   │   └── parser/             # AWS Event Stream 解析器
│   │       ├── decoder.rs      # 流式解码器
│   │       ├── frame.rs        # 帧解析
│   │       ├── header.rs       # 头部解析
│   │       └── crc.rs          # CRC32C 校验
│   ├── admin/                  # Admin API 模块
│   │   ├── router.rs           # Admin 路由
│   │   ├── handlers.rs         # Admin 请求处理器
│   │   ├── service.rs          # Admin 业务逻辑
│   │   └── middleware.rs       # Admin 认证中间件
│   ├── common/                 # 公共工具
│   └── http_client.rs          # HTTP 客户端工厂
├── admin-ui/                   # Admin UI 前端 (React + Vite)
├── tools/                      # 辅助工具脚本
├── config.example.json         # 配置示例
├── credentials.example.*.json  # 凭证示例
├── Dockerfile                  # Docker 构建
└── docker-compose.yml          # Docker Compose 编排
```

---

## API Endpoints

### Standard Endpoints (/v1)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/models` | 获取可用模型列表 |
| POST | `/v1/messages` | 创建消息（流式响应） |
| POST | `/v1/messages/count_tokens` | 估算 Token 数量 |

### Claude Code Endpoints (/cc/v1)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/cc/v1/messages` | 创建消息（缓冲模式，准确 input_tokens） |
| POST | `/cc/v1/messages/count_tokens` | 估算 Token 数量 |

### Admin API (可选)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/admin/credentials` | 获取所有凭据状态 |
| POST | `/api/admin/credentials` | 添加新凭据 |
| DELETE | `/api/admin/credentials/:id` | 删除凭据 |
| POST | `/api/admin/credentials/:id/disabled` | 设置禁用状态 |
| POST | `/api/admin/credentials/:id/priority` | 设置优先级 |
| POST | `/api/admin/credentials/:id/reset` | 重置失败计数 |
| GET | `/api/admin/credentials/:id/balance` | 获取凭据余额 |
| GET | `/admin` | Admin Web UI |

---

## Configuration

### config.json

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `host` | string | ✓ | 监听地址 |
| `port` | number | ✓ | 监听端口 |
| `apiKey` | string | ✓ | 客户端认证 API Key |
| `region` | string | ✓ | AWS 区域 (默认 us-east-1) |
| `tlsBackend` | string | | TLS 后端: rustls / native-tls |
| `proxyUrl` | string | | HTTP/SOCKS5 代理地址 |
| `adminApiKey` | string | | Admin API 密钥 |

### credentials.json

支持单对象或数组格式（多凭据）。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `refreshToken` | string | ✓ | OAuth 刷新令牌 |
| `expiresAt` | string | ✓ | Token 过期时间 (RFC3339) |
| `authMethod` | string | ✓ | 认证方式: social / idc |
| `clientId` | string | idc | IdC 客户端 ID |
| `clientSecret` | string | idc | IdC 客户端密钥 |
| `priority` | number | | 凭据优先级 (越小越优先) |

---

## Model Mapping

| Anthropic Model | Kiro Model |
|-----------------|------------|
| `*sonnet*` | `claude-sonnet-4.5` |
| `*opus*` | `claude-opus-4.5` |
| `*haiku*` | `claude-haiku-4.5` |

---

## Development

### Prerequisites

- Rust (Edition 2024)
- Node.js + pnpm (for Admin UI)

### Build

```bash
# 构建 Admin UI
cd admin-ui && pnpm install && pnpm build && cd ..

# 构建 Rust 项目
cargo build --release
```

### Run

```bash
./target/release/kiro-rs -c config.json --credentials credentials.json
```

### Docker

```bash
docker compose up --build
```

---

## Key Design Decisions

1. **协议转换分离**：`anthropic/converter.rs` 负责 Anthropic ↔ Kiro 格式转换，与业务逻辑解耦
2. **多凭据故障转移**：`MultiTokenManager` 管理多个凭据，自动切换失败凭据
3. **流式响应处理**：自研 AWS Event Stream 解析器，支持实时流式输出
4. **嵌入式 Admin UI**：使用 `rust-embed` 将前端构建产物嵌入二进制，单文件部署
5. **TLS 后端可选**：支持 rustls（默认）和 native-tls，解决不同环境的兼容性问题

---

## Known Issues

- **Write Failed/会话卡死**：输出过长被截断时可能导致会话不可用，参考 Issue #22 和 #49
- **TLS 兼容性**：某些环境下 rustls 可能无法正常工作，需切换到 native-tls

---

## References

- [Anthropic API Documentation](https://docs.anthropic.com/en/api)
- [kiro2api](https://github.com/caidaoli/kiro2api)
- [proxycast](https://github.com/aiclientproxy/proxycast)
