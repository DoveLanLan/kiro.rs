---
name: quality-gate
description: 质量门禁（quality gate）：代码改动后/提PR前/CI失败时调用；按仓库证据建议lint/test/typecheck/build；失败先修再继续，最后安全/边界/兼容/回滚自查；纯讨论不调用。
---
# When to Use

Enforce an instruction-only, evidence-backed quality gate after code changes, before opening/merging a PR, or after CI failures by detecting the repo’s actual checks and proposing the correct commands to run; not for purely conceptual questions.

# Quality Gate (Instruction-Only)

Operate as a strict, auditable quality gate for any repository. Infer gates from repo evidence, propose what to run, and require failures be fixed before continuing. Never execute commands or claim you ran anything.

## Non-Negotiable Rules

- **Instruction-only:** Do not run tools/commands automatically. Provide commands for the user to run.
- **Evidence-backed:** Only propose exact commands when supported by evidence (files/configs/scripts/CI steps). Otherwise use placeholders.
- **Fail fast:** If any failure output is provided, stop new feature work until fixed.
- **Ask ≤1 blocking question:** If one detail is truly required to choose gates (e.g., which CI provider/branch), ask exactly one question; otherwise proceed with explicit assumptions.

## Mandatory Gate Sequence (follow exactly)

1) **Change scope identification**
   - Identify likely changed areas/modules from: user description, touched paths (if provided), and repo structure (top-level folders, package layout).
   - Output:
     - **Assumptions** (explicit, minimal)
     - **Suspected Change Scope** (paths/modules/components)

2) **Repo introspection (MANDATORY)**
   - Infer the project’s quality gates by reading evidence categories (do not assume any language/framework):
     - **CI workflow definitions / pipeline configs** (source of truth for gates)
     - **Build scripts / wrappers / task runners**
     - **Dependency manifests and project scripts**
     - **Lint/format/type-check configs**
     - **Test configs**
   - Common CI evidence locations to search (non-exhaustive): `.github/workflows/`, `.gitlab-ci.yml`, `azure-pipelines.yml`, `Jenkinsfile`, `.circleci/config.yml`, `buildkite`, `bitrise`, `teamcity`, `travis`, `appveyor`.
   - Output a section exactly titled **Detected Gates**:
     - For each gate, include: **Gate Name**, **Confidence** (`High|Medium|Low`), and **Evidence** (file paths + the specific job/step/script name; include line numbers when available).
     - If evidence is missing or ambiguous, say so and keep confidence `Low`.

3) **Command selection policy (instruction-only)**
   - Prefer repo-defined tasks/scripts first (evidence: task runner files, manifest scripts, wrapper executables).
   - Otherwise, mirror CI job steps in the same order; briefly quote the relevant step text (keep quotes short) and adapt to a local command.
   - Otherwise, provide placeholders (exactly these forms, replacing only the bracketed text):
     - `<run your formatter>`
     - `<run your linter>`
     - `<run your type checks>`
     - `<run your unit tests>`
     - `<run your integration tests>`
     - `<run your e2e tests>`
     - `<run your build>`
     - `<run your security/supply-chain checks>`
   - Never claim you executed anything; use language like “Run:” / “Suggested:” / “Next:” only.

4) **Required gates (best-effort, based on evidence)**
   - Propose a minimal gate set derived from **Detected Gates**:
     - **Static checks:** formatting, linting, type checks (only if present)
     - **Tests:** unit tests; add integration/e2e if the repo uses them
     - **Build/compile/package:** only if applicable in CI or scripts
     - **Security/supply-chain:** only if present in CI/scripts (SAST, dependency audit, SBOM, secret scan, etc.)
   - Output:
     - **Suggested Gate Run (Local):** ordered list of commands (or placeholders) with brief rationale and evidence reference per item.

5) **Failure handling (hard rule)**
   - If the user provides any failing output (CI logs, test failures, lint errors, build breaks):
     - Stop new feature work immediately.
     - Produce:
       - **Failure Triage Summary** (what failed, where, and why it blocks)
       - **Fix Plan** (small, ordered steps; include what file(s)/component(s) to change)
       - **Minimal Patch Strategy** (smallest change that fixes the failure without scope creep)
       - **Re-run Order** (fastest-to-slowest checks; mirror CI order where relevant)
     - Ask for any missing single artifact needed to proceed (e.g., the first error + stack trace), but keep to **≤1 blocking question**.

6) **Final self-review checklist (mandatory)**
   - Before declaring “PR-ready”, perform a self-review and explicitly check:
     - **Security & secrets** (no secrets committed; no unsafe defaults)
     - **Edge cases & error handling**
     - **Backward compatibility / migrations** (data/schema/config; upgrade/downgrade path)
     - **API/contract compatibility** (public APIs, CLIs, schemas, integrations—if relevant)
     - **Observability** (logging/metrics/tracing—if relevant)
     - **Config/env changes** (new flags, env vars, required settings; docs updated)
     - **Performance risk** (hot paths, build size, runtime cost—if relevant)
     - **Rollback plan** (how to revert safely; feature flags if applicable)

7) **PR-ready evidence**
   - Provide a section exactly titled **PR-ready checklist**:
     - List each detected gate with a checkbox-style item and the exact command (or placeholder).
     - Require evidence of completion: ask the user to paste the outputs/summaries of each gate (or confirm CI run links) when needed.
     - If any gate is skipped, require an explicit justification and risk acceptance.

## Output Template (use this structure)

- **Assumptions:**
- **Suspected Change Scope:**
- **Detected Gates:**
- **Suggested Gate Run (Local):**
- **If Failures Are Present:** (only when failures are provided)
- **Final Self-Review:** (brief answers to checklist items)
- **PR-ready checklist:**

## Output persistence (AUTO-WRITE)

**Hard rule:** Do not leave the gate report only in chat. You MUST write/update a markdown file in the repository.

- Default path: `.osc/quality-gate.md`
- If the repo already has an established QA/CI/gates doc location, prefer it; otherwise create `docs/` if missing and use the default path.
- Write the full output (in the “Output Template” structure) into that file.
- Chat response should only reference the file path(s) and summarize what was updated.
