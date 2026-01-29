# Repository Guidelines

This repository contains **kiro-rs**, an Axum-based proxy that accepts Anthropic Claude-compatible requests and forwards them to the Kiro API. It also includes a small React admin UI that is embedded into the Rust binary.

## Project Structure & Module Organization

- `src/main.rs`: CLI + server bootstrap.
- `src/anthropic/`: Anthropic-compatible routes, request conversion, SSE streaming.
- `src/kiro/`: Kiro request/response models, token refresh, parsing/decoding utilities.
- `src/admin/`: Admin API (credential management) and related middleware.
- `src/admin_ui/`: Serves embedded `admin-ui/dist` under `/admin/`.
- `admin-ui/`: Vite + React + TypeScript admin UI (Tailwind styling).
- `config.example.json`, `credentials.example*.json`: Safe templates for local setup.
- `tools/`: Small utilities (e.g., `tools/event-viewer.html`).

## Build, Test, and Development Commands

Backend (Rust):

- `cargo build` / `cargo build --release`: Build the proxy.
- `cargo run -- -c config.json --credentials credentials.json`: Run with local config files.
- `cargo fmt` and `cargo clippy --all-targets --all-features`: Format and lint.
- `cargo test`: Run unit tests (most live next to code in `#[cfg(test)]` blocks).

Admin UI (must be built before release builds that embed assets):

- `cd admin-ui && pnpm install`
- `pnpm dev`: Local UI dev server (see `admin-ui/vite.config.ts` for proxy).
- `pnpm build`: Produces `admin-ui/dist` for embedding.

Docker:

- `docker build -t kiro-rs .`
- `docker run -p 8990:8990 -v "$PWD/config:/app/config" kiro-rs`

## Coding Style & Naming Conventions

- Rust: follow `rustfmt` defaults; prefer `snake_case` for modules/functions and `CamelCase` for types.
- Keep HTTP handlers, routers, and middleware in their respective modules (`anthropic/`, `admin/`).
- Admin UI: TypeScript is `strict`; use `PascalCase.tsx` for components and `useX` for hooks.

## Commit & Pull Request Guidelines

- Use Conventional Commit-style subjects seen in history, e.g. `feat(scope): ...`, `fix(scope): ...`, `docs: ...`, `chore: ...`, `bump: vYYYY.M.D`.
- PRs should include: what changed, how to test (`cargo test`, `pnpm build` if UI touched), and screenshots for UI changes.

## Security & Configuration Tips

- Never commit real tokens or credentials. Use `config.example.json` and `credentials.example*.json` to create local `config.json` / `credentials.json`.
- When filing issues, redact `apiKey`, `refreshToken`, and any bearer tokens from logs.

