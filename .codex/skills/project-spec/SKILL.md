---
name: project-spec
description: 仓库必读规则与结构图（project spec/repo rules/Repo Snapshot）：新仓库或不熟悉项目，且在实现/重构/修Bug/加测试/处理CI失败前调用；纯概念问答或无需读仓库时不调用。
---

# When to use

Mandatory baseline repo rulebook + project-spec generator; trigger on new-repo/unknown-repo work or requests like "project spec", "repo rules", "architecture map", "Repo Snapshot", "生成项目规范", "仓库结构", "代码规范"; exclude generic Q&A, creative writing, or format-only edits that don’t require repo introspection.


# Project Spec (Repository Baseline Rulebook)

This is an instruction-only skill. Do not claim you executed any commands or observed any repository state unless it is explicitly provided by the user or present in your tool output for this run.

## Deterministic Workflow (Follow In Order)

### 0) Preconditions (Always)

1. Treat **authoritative repository docs** as source of truth when present (e.g., contribution guides, architecture notes, ADRs).
2. Treat **AGENTS.md** instructions (if any) as binding within their scope.
3. If any instruction sources conflict, apply this precedence order:
   1) System/developer/user instructions in the current chat
   2) Repo-local agent instructions (e.g., AGENTS.md) within scope
   3) This skill’s rules (only where not overridden)
4. Ask **at most one** clarifying question if truly blocking; otherwise proceed with explicit assumptions.

### 1) Repo Introspection (MANDATORY FIRST STEP)

Inspect the repository tree **only to top-level + up to 2 directory levels**. Do not deep-scan unless the user explicitly asks.

Collect evidence using **only these categories** (do not hardcode language/framework names here):

- Dependency manifests / lockfiles
- Build system configuration and wrapper scripts
- Formatter/linter/type-checker configs
- Test runner configs
- CI workflow definitions
- Existing contribution / architecture docs

**Method (auditable and repeatable):**

1. Build a file inventory (top-level + depth 2):
   - Note directories that look like modules/components (based on naming and co-located configs).
   - Note the presence/absence of files belonging to the evidence categories above.
2. For each evidence category, record:
   - Evidence file paths found
   - What they imply (toolchain, conventions, boundaries, or expectations)
   - A confidence level: **High / Medium / Low**
     - High: explicitly stated in authoritative docs or consistently enforced in CI configs
     - Medium: implied by multiple configs + patterns but not explicitly documented
     - Low: inferred from a single hint or weak signal
3. Derive the following artifacts:
   - (a) **Component/Module Map**: list modules, ownership boundaries, and coupling points
   - (b) **Build/Test/Lint Toolchains**: what commands likely exist and where defined
   - (c) **Style/Format Rules**: what is enforced and how (configs/CI hooks)
   - (d) **CI Expectations**: required checks, environments, and “gates”

#### Repo Snapshot (Always Output This)

Output a short section titled **Repo Snapshot** with this structure:

- **Modules/Components:** `<list>` (confidence: H/M/L) — evidence: `<paths>`
- **Toolchains:** build `<...>`, test `<...>`, lint/format `<...>`, type-check `<...>` (each with confidence) — evidence: `<paths>`
- **Style/Format Enforcement:** `<summary>` (confidence) — evidence: `<paths>`
- **CI Gates/Expectations:** `<summary>` (confidence) — evidence: `<paths>`
- **Open Questions (max 1):** `<only if truly blocking>`

Notes:
- If authoritative docs exist, prefer quoting their *meaning* (paraphrase) and point to exact file paths.
- If you must infer, label it explicitly as **Inferred**.

## Output persistence (AUTO-WRITE)

**Hard rule:** Do not leave the repo spec only in chat. You MUST write/update a markdown file in the repository.

- Default path: `.osc/spec/project-spec.md`
- If the repo already has an established location for repo rulebooks/architecture docs, prefer it; otherwise create `spec/` if missing and use the default path.
- Write the full content (Repo Snapshot + rulebook + top constraints) into that file.
- Chat response should only reference the file path(s) and summarize changes.

### 2) Generate Repo Rules (Source-of-Truth First)

Create a stable, numbered rulebook under the headings below. Every rule must be:

- **Actionable** (clear instruction, not a suggestion)
- **Auditable** (points to evidence paths)
- **Classified** as either:
  - **Documented**: directly backed by authoritative docs
  - **Inferred**: inferred from configs/code patterns and marked as such

Use the exact headings and numbering style:

#### A) Architecture & boundaries

1. ...
2. ...

#### B) Directory layout & naming

1. ...
2. ...

#### C) Code style & patterns

1. ...
2. ...

#### D) Testing strategy & coverage expectations

1. ...
2. ...

#### E) Commits/PRs & review checklist

1. ...
2. ...

**Evidence format for each rule:**

- End each rule with `— Evidence: <path1>, <path2> (Documented|Inferred; confidence: H/M/L)`

If evidence is missing for a rule, do not invent it. Either:
- Omit the rule, or
- Add it as a **provisional inference** with **Low** confidence and state what evidence would confirm it.

### 3) Quick Apply (Before Any Coding Plan)

Before proposing any coding plan, restate the **top 7 constraints** as bullets, derived from:
- The rulebook above (highest-impact constraints first), and
- Any explicit user requirements for this task.

Format:

- `Constraint 1: ...`
- `Constraint 2: ...`
- ...
- `Constraint 7: ...`

### 4) Conflict Handling (Strict and Explicit)

If the user request conflicts with:
- Authoritative repo docs,
- AGENTS.md rules within scope, or
- CI-enforced expectations,

Then:

1. Explicitly name the conflict: “Request X conflicts with rule Y because …”
2. Propose a compliant alternative that meets the user’s intent.
3. If there are multiple compliant options, pick one and briefly justify using evidence.

Do not silently “bend” rules.

### 5) Clarification Policy (Max One Question)

Ask **one** clarifying question only if:
- The choice materially affects architecture boundaries, data contracts, or CI gates; and
- The repository evidence cannot resolve it; and
- Proceeding with assumptions risks rework.

Otherwise:
- Proceed with stated assumptions.

## Output Templates (Copy/Paste)

### Repo Snapshot Template

**Repo Snapshot**
- **Modules/Components:** …
- **Toolchains:** build …; test …; lint/format …; type-check …
- **Style/Format Enforcement:** …
- **CI Gates/Expectations:** …
- **Open Questions (max 1):** …

### Rulebook Template

#### A) Architecture & boundaries
1. … — Evidence: … (Documented|Inferred; confidence: H/M/L)

#### B) Directory layout & naming
1. … — Evidence: … (Documented|Inferred; confidence: H/M/L)

#### C) Code style & patterns
1. … — Evidence: … (Documented|Inferred; confidence: H/M/L)

#### D) Testing strategy & coverage expectations
1. … — Evidence: … (Documented|Inferred; confidence: H/M/L)

#### E) Commits/PRs & review checklist
1. … — Evidence: … (Documented|Inferred; confidence: H/M/L)

### Top 7 Constraints Template

- Constraint 1: …
- Constraint 2: …
- Constraint 3: …
- Constraint 4: …
- Constraint 5: …
- Constraint 6: …
- Constraint 7: …
