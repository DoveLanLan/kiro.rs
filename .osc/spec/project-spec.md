# Project Spec: kiro-rs (OSC Baseline)

- Updated: 2026-02-27
- Scope: Repository baseline rules for spec-driven changes in this repo.

## Repo Snapshot

- Modules/Components: Rust proxy service in `src/` (Anthropic layer, Kiro layer, admin layer), embedded admin static serving in `src/admin_ui`, React admin app in `admin-ui/`, Docker packaging at root. (confidence: High)  
  Evidence: `AGENTS.md`, `README.md`, `src/`, `admin-ui/`, `Dockerfile`, `docker-compose.yml`
- Toolchains:
  - Build: `cargo build` / `cargo build --release`; frontend build `pnpm build`; Docker build via `docker build` and workflow jobs. (confidence: High)
  - Test: `cargo test` for backend unit tests; no dedicated frontend test runner configured. (confidence: Medium)
  - Lint/format: `cargo fmt`, `cargo clippy --all-targets --all-features`; TypeScript strict compile via `tsc -b` inside `pnpm build`. (confidence: High)
  - Type-check: TypeScript strict mode enabled in `admin-ui/tsconfig.json`. (confidence: High)  
    Evidence: `AGENTS.md`, `Cargo.toml`, `admin-ui/package.json`, `admin-ui/tsconfig.json`, `.github/workflows/build.yaml`
- Style/Format Enforcement: Rust formatting/linting is documented; TypeScript strict/no-unused checks are configured; no separate ESLint/Prettier config detected at repo root or `admin-ui`. (confidence: Medium)  
  Evidence: `AGENTS.md`, `admin-ui/tsconfig.json`
- CI Gates/Expectations: GitHub Actions currently build release binaries and Docker images on tags/manual trigger; workflows do not explicitly run `cargo test` or `cargo clippy`. (confidence: High)  
  Evidence: `.github/workflows/build.yaml`, `.github/workflows/docker-build.yaml`
- Open Questions (max 1): none.

## Rulebook

### A) Architecture & boundaries

1. Keep Anthropic-compatible HTTP handling and protocol conversion in `src/anthropic/`; avoid mixing this with token refresh/provider internals. — Evidence: `AGENTS.md` (Documented; confidence: High)
2. Keep Kiro API request/response models, token refresh, and stream parsing under `src/kiro/` and related submodules. — Evidence: `AGENTS.md`, `src/kiro/` (Documented; confidence: High)
3. Keep admin credential-management API/middleware in `src/admin/` and embedded static serving concerns in `src/admin_ui/`. — Evidence: `AGENTS.md`, `src/admin/`, `src/admin_ui/` (Documented; confidence: High)
4. Treat `admin-ui/dist` as a build artifact consumed by Rust embedding/release flows; backend release builds depend on frontend build output. — Evidence: `AGENTS.md`, `README.md`, `Dockerfile`, `.github/workflows/build.yaml` (Documented; confidence: High)

### B) Directory layout & naming

1. Use Rust naming conventions: `snake_case` for modules/functions and `CamelCase` for types. — Evidence: `AGENTS.md` (Documented; confidence: High)
2. In admin UI, use `PascalCase.tsx` for components and `useX` naming for hooks. — Evidence: `AGENTS.md`, `admin-ui/src/components/`, `admin-ui/src/hooks/` (Documented; confidence: High)
3. Keep safe templates in `config.example.json` and `credentials.example*.json`; do not commit real credential files or secrets. — Evidence: `AGENTS.md`, `.gitignore` (Documented; confidence: High)
4. Keep small helper utilities under `tools/`; avoid coupling runtime server logic into tool scripts. — Evidence: `AGENTS.md`, `tools/` (Documented|Inferred; confidence: Medium)

### C) Code style & patterns

1. Apply Rust formatting/lint gates before merge: `cargo fmt` and `cargo clippy --all-targets --all-features`. — Evidence: `AGENTS.md` (Documented; confidence: High)
2. Keep TypeScript in strict mode and satisfy unused checks (`noUnusedLocals`, `noUnusedParameters`) as part of `pnpm build`. — Evidence: `admin-ui/tsconfig.json`, `admin-ui/package.json` (Documented; confidence: High)
3. Respect frontend runtime contract: Vite `base` is `/admin/`, and local dev API calls route through `/api` proxy to backend. — Evidence: `admin-ui/vite.config.ts` (Documented; confidence: High)
4. Preserve security hygiene in code/log output: redact API keys, refresh tokens, and bearer tokens in issues/logs. — Evidence: `AGENTS.md`, `README.md` (Documented; confidence: High)

### D) Testing strategy & coverage expectations

1. Backend unit tests should remain colocated with Rust modules (`#[cfg(test)]`) and be runnable via `cargo test`. — Evidence: `AGENTS.md` (Documented; confidence: High)
2. Frontend validation baseline is successful TypeScript build (`tsc -b && vite build`); no explicit unit-test framework is currently declared. — Evidence: `admin-ui/package.json`, `admin-ui/tsconfig.json` (Documented|Inferred; confidence: Medium)
3. For release-oriented changes, validate that admin UI build succeeds before backend release build to avoid broken embedded assets. — Evidence: `README.md`, `.github/workflows/build.yaml`, `Dockerfile` (Documented; confidence: High)
4. API/proxy behavior regressions should be verified with representative `/v1/messages` request flow from README examples. — Evidence: `README.md` (Documented|Inferred; confidence: Medium)

### E) Commits/PRs & review checklist

1. Use Conventional Commit style subjects (`feat(scope):`, `fix(scope):`, `docs:`, `chore:`, `bump:`). — Evidence: `AGENTS.md` (Documented; confidence: High)
2. PR descriptions must include what changed and how to test; include UI screenshots when frontend is touched. — Evidence: `AGENTS.md` (Documented; confidence: High)
3. Do not commit real credentials or tokens; use provided example config/credential templates. — Evidence: `AGENTS.md`, `.gitignore` (Documented; confidence: High)
4. Release CI currently guarantees build artifact generation (binary + Docker images) but not full lint/test gates, so local quality checks remain mandatory before PR. — Evidence: `.github/workflows/build.yaml`, `.github/workflows/docker-build.yaml` (Inferred; confidence: High)

## Top 7 Constraints (Quick Apply)

- Constraint 1: Follow write-before-code OSC flow; for code changes, create/select a task and create `proposal.md`, `spec.md`, `tasks.md` under `.osc/tasks/<task-dir>/changes/` before touching source files.
- Constraint 2: Keep module boundaries intact (`src/anthropic`, `src/kiro`, `src/admin`, `src/admin_ui`), and avoid cross-layer coupling without explicit spec updates.
- Constraint 3: Build admin UI before release packaging so embedded assets in `admin-ui/dist` are present.
- Constraint 4: Run and pass local quality checks (`cargo fmt`, `cargo clippy --all-targets --all-features`, `cargo test`, plus frontend `pnpm build` when UI changes).
- Constraint 5: Preserve strict TypeScript constraints and frontend route base/proxy contract (`/admin/`, `/api`).
- Constraint 6: Use Conventional Commits and include test evidence/screenshot requirements in PR-level documentation.
- Constraint 7: Never expose or commit secrets (`apiKey`, `refreshToken`, bearer tokens); keep sensitive values in ignored local config files.
