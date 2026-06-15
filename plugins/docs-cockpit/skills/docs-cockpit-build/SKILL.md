---
name: docs-cockpit-build
description: "Build or set up docs-cockpit from 0→1: create docs-cockpit.yaml, wire modules to specs/plans, add anchors, draft missing docs, and render the dashboard."
---

# docs-cockpit-build

**The 7-phase workflow for building a project's module ↔ subtask ↔ spec/plan/RFC association system, from nothing (or from gaps) to a rendered dashboard.**

## Why this skill exists

The hard part of a docs cockpit was never the rendering — it's the association: which subtask is backed by which plan section, which module's spec actually exists, which RFC explains a decision. That is **cognitive work** (search, read, judge), and trying to encode it in Python produced exactly the failure mode users reported: modules with no docs linkage, subtasks pointing nowhere, and no highlighted evidence for why a link exists. So the v1.0 north-star: **cognition lives in skills; Python only renders**. This skill is the cognition — it orchestrates four atomic methods (discovery / reasoning / dry-run / highlight) and a dialogue loop with the user, then hands a fully-anchored doc set to the rendering CLI.

One principle governs every phase: **a wrong anchor is worse than a missing anchor.** A missing anchor is an honest gap; a wrong one sends the user to irrelevant content and destroys trust in the whole dashboard. When in doubt, mark the gap and ask — never guess line numbers.

## How this skill is layered

This skill is the **orchestration layer** — it tells you which phase to run when. The details live in references (do not restate them; read them when the phase needs them):

| Reference | Holds | Used by |
|---|---|---|
| `references/schema.md` | frontmatter fields · subtask forms · code/doc anchor formats · file naming | Phase 3, 6 |
| `references/association-method.md` | the 4 atomic methods (discovery / reasoning / dry-run / highlight) | Phase 1–4 |
| `references/operations.md` | CLI bootstrap · config skeleton · upgrade | Phase 0 |
| `references/health-check.md` | nine-department checkup methodology · three-part report template · five-bucket triage · HEALTH.md writing rules | Phase 5 (admission checkup), 6 (bucket landing) |

Default scope is the **whole project** — every module's spec/plan, every subtask's anchors. The user can narrow it ("only M07", "only the new sprint"); say so explicitly in Phase 1's output if scoped down.

---

## Phase 0 · Ensure the cockpit exists

- **Goal** — a working `docs-cockpit.yaml` + installed CLI, so later phases have a config to build against.
- **Actions** — check for `docs-cockpit.yaml` in the repo root. Missing CLI → bootstrap per `references/operations.md` (uv → pipx → pip --user priority; tell the user, never install silently). Missing config → run `docs-cockpit init`, then fill the minimal skeleton (see operations.md · config section).
- **Reference** — `references/operations.md` (bootstrap + config skeleton).
- **Output** — confirmed `docs-cockpit.yaml` + `docs-cockpit --version` succeeding.

**Codex / non-Claude agent adaptation — AGENTS.md anchor (idempotent).** Codex-style agents don't load Claude Code hooks; they read the project-root `AGENTS.md` by convention. So this phase also plants a routing anchor there:

1. **Three-state check**: grep `AGENTS.md` for the substring `docs-cockpit:begin` (substring match — the actual marker line carries a managed-by suffix, so do NOT grep for the full `<!-- docs-cockpit:begin -->` literal).
   - **Not found** → `AGENTS.md` exists: append the block below at the end of the file. `AGENTS.md` doesn't exist: create it containing only the block.
   - **Found, content matches current template** → skip entirely (already up to date; never write a duplicate).
   - **Found, content differs from current template** → replace the entire block between `docs-cockpit:begin` and `docs-cockpit:end` (inclusive of both marker lines) with the current template below (self-healing — refreshes stale blocks planted by older runs).

Anchor block template (verbatim, including markers):

```markdown
<!-- docs-cockpit:begin · managed by docs-cockpit-build Phase 0 · do not edit inside this block -->
## docs-cockpit

This project's documentation association (module ↔ subtask ↔ spec/plan/RFC anchors)
is managed by the docs-cockpit skill family. The `use-docs-cockpit` entry skill is
the router — consult it before any doc-association work. Routing summary:

- Build the association system (0→1, whole-project planning, fill anchor gaps)
  → `docs-cockpit-build` skill
- Refresh an existing association that drifted (post-refactor, stale anchors,
  spec evolved) → `docs-cockpit-rebuild` skill
- Just re-render the dashboard HTML, no association change
  → CLI `docs-cockpit render`

Field formats and frontmatter schema: `references/schema.md` in the docs-cockpit plugin.
<!-- docs-cockpit:end -->
```

## Phase 1 · Discovery（检索）

- **Goal** — a full panorama of the project's docs: what exists, who references whom, what's orphaned.
- **Actions** — apply **Method 1** to the whole project: Glob the five doc kinds, keyword cross-grep per module (≥2 distinct-dimension keyword hits → candidate pool), and mark the two gap classes (orphan docs · 0-anchor subtasks — `docs-cockpit lint` gives the latter list for free (look for the `subtask-missing-anchors` issues in the lint output)).
- **Atomic method** — Method 1 · discovery (`references/association-method.md`).
- **Output** — panorama table (doc → kind → referenced-by) + per-module candidate pool + orphan/gap list.

## Phase 2 · Reasoning（推理）

- **Goal** — for every module/subtask, a concrete *should-link-to* target: not a file, a **section**.
- **Actions** — apply **Method 2** to each candidate: extract the subtask's need X, actually Read the candidate body, locate the §N that answers "why" or "how" for X. No match → record it as a gap, don't force the nearest section. Aggregate the gap list along three axes: modules with no spec · sprints with no plan · subtasks with 0 anchors.
- **Atomic method** — Method 2 · reasoning (`references/association-method.md`).
- **Output** — proposed anchor per module/subtask (path + section) + the three-axis gap list (feeds Phase 6 drafting).

## Phase 3 · Dry-run（预演）

- **Goal** — every proposed anchor verified against the real file content **before** anything is written.
- **Actions** — apply **Method 3**: Read the exact target slice of each candidate anchor (offset/limit for `:lines`, heading scan for `#§N`) (limit = end − start + 1, not the end line number — see Method 3 in references/association-method.md) and assign one of the 4 verdicts (accurate / partial / wrong / missing). `partial` → adjust the range now; `wrong` → re-run Phase 1+2 for that item or mark TODO. Never write an unverified line range.
- **Atomic method** — Method 3 · dry-run (`references/association-method.md`); anchor syntax per `references/schema.md`.
- **Output** — verdict table: every candidate anchor → verdict → adjustment taken.

## Phase 4 · Highlight（高亮）

- **Goal** — each surviving association carries its evidence: the specific lines plus a one-sentence reason.
- **Actions** — apply **Method 4** to every accurate anchor: precise line range or heading + one sentence naming (a) what the cited slice says and (b) why that supports this subtask. Can't write (b) → the association itself is suspect; send it back to Phase 2.
- **Atomic method** — Method 4 · highlight (`references/association-method.md`).
- **Output** — the presentation-ready proposal list (anchor + highlighted lines + reason) consumed by Phase 5.

## Phase 5 · Dialogue decisions（对话决策）

**Entry step · admission baseline checkup（入院体检）.** Before presenting any association proposal, consolidate the findings Phases 1–3 already produced (lint issues, anchor verdicts, coverage gaps) into an admission checkup per `references/health-check.md` — quick mode, reusing what those phases measured rather than re-running checks:

1. Write `docs/HEALTH.md` — frontmatter per `references/schema.md · health-report schema`; writing rules (stable `RX-NNN` ids, real module ids only, anchors pre-verified by Method 3, checkup-day `date`) per health-check.md's HEALTH.md 写入规范 section.
2. Present the three-part report（诊断 / 处方 / 行动规划）using health-check.md's template.
3. Walk the five buckets one by one for the user's ruling（五桶逐桶确认）— triage criteria per health-check.md.
4. Confirmed items merge into this phase's existing decision flow below; their on-disk landing rules live in Phase 6.

**The admission checkup is not skippable — greenfield included.** Creating new planned cards on an empty or just-cleaned board is still an admission: the newly drafted cards/docs are themselves checkup subjects — ① their frontmatter conformance, ④ whether each new card links a real upstream doc (ROADMAP / PRD / plan) or is an orphan, plus a wording pass on their desc/scope quality. Departments with no subject yet (e.g. anchor verdicts when no anchors exist) report **N/A** — N/A is a verdict, not a reason to skip the checkup. Always write the baseline HEALTH.md: a clean greenfield board honestly grades A, and that baseline is what the next rebuild checkup diffs against.

- **Goal** — the user has ruled on every proposal: accept / adjust / skip. Nothing lands without a ruling.
- **Actions** — present Phase 4's proposals one by one (or in small batches for a long list — group by module). For each, show the anchor, the highlighted evidence, the verdict, and ask for a decision. Apply user adjustments back through a quick Phase 3 re-verify before accepting. Decision granularity rule: ≤3 proposals → present individually, one turn per proposal. 4-8 → group by module (one turn per module). >8 → present an overview table first, then ask the user: module-by-module, or bulk accept-with-exceptions. Never dump every proposal in a single turn without grouping.
- **Atomic method** — none (this phase is dialogue-driven; the only edits are user-approved now-bucket treatments).
- **Output** — decision ledger: each proposal → accepted / adjusted-to-what / skipped-why.

**Never silently fix.** Anything the validator rates `error`-level (a missing `id`, a placeholder id, a status×progress conflict) or any project-specific choice (id naming, sprint assignment, which doc kind a file should be) is the **user's** call — propose, explain, wait. You may auto-apply only mechanical, semantics-free fixes the user already approved as a class (e.g. "fix all whitespace-only issues").

Proposal presentation format (example):

```
【提议 3/12】 M07 「Job / Task FSM」 · subtask M07-S2 「worker 从队列取下一状态」
  建议 anchor : @docs:docs/plans/2026-05-03-m07-fsm-plan.md#§4.2
  高亮理由   : §4.2 第 88–104 行定义了队列消费循环和状态迁移触发条件 —— 正是该 subtask 的实现依据
  预演 verdict: ✅ accurate
  你的决定？  accept / 调整 / skip
```

## Phase 6 · Write anchors + draft missing docs（落地 + 补文档）

- **Goal** — every accepted decision is on disk: anchors written into the module MDs, gap docs drafted.
- **Actions** — write each accepted anchor in the form the target doc already uses (frontmatter `subtasks:` object array vs body `@code:`/`@docs:` inline — exact syntax per `references/schema.md`; remember frontmatter wins over body, so don't mix forms in one doc (if the target doc already has both forms, frontmatter takes precedence — write only to the frontmatter form and leave the body section as is)). For each Phase 2 gap the user approved: draft the missing spec/plan with conforming frontmatter and file naming (both per `references/schema.md`), then link it from the owning module's `docs:`. New planned cards drafted here meet a minimum bar: a concrete `desc`, a scope section in the body, and a real upstream link (`prd_ref` or `docs:` to ROADMAP / PRD / plan — never a fabricated anchor). Omitting `subtasks:` on a planned card is the honest state (subtasks arrive when the module is brainstormed), not a lint-evasion trick — and the card still goes through the Phase 5 admission checkup like everything else.
- **Reference** — `references/schema.md` (subtask forms · anchor formats · frontmatter schema · file naming).
- **Output** — edited module MDs + new spec/plan drafts + their `docs:` linkage.

**Checkup prescription landing（处方→subtask 闭环）.** Bucket decisions confirmed in Phase 5's checkup land here, alongside the anchor decisions:

- **`sprint`** — write the prescription as a subtask (title per schema.md's 4 rules) carrying a `@code:` anchor at the problem location, under the module named by the prescription's `module` field; no owning module → ask the user before creating a dedicated health-debt module（「健康债」）to hold it. Sync the sprint-plan `in_scope`.
- **`backlog`** — draft a plan doc（file naming per `references/schema.md · 文件命名约定`）; the prescription's anchors go into its evidence section, and conforming frontmatter puts it on the dashboard automatically.
- **`accepted`** — record in `docs/HEALTH.md` `accepted_debts`（item / reason / review date — ledger rules per health-check.md）.
- **`watch`** — stays in `docs/HEALTH.md` `prescriptions` with `bucket: watch`; the next checkup verifies these first.
- **`now`** — already treated during Phase 5's dialogue（edit + re-render）; nothing further lands here.

## Phase 7 · Render（渲染）

- **Goal** — a regenerated dashboard proving the association system is clean: 0 warnings.
- **Actions** — run `docs-cockpit render` and read the issue output. Any `❌`/`⚠️` traced to this build's edits → fix (loop back to the relevant phase for that item) and re-render. Pre-existing unrelated warnings: surface to the user, don't block on them.
- **Reference** — CLI.
- **Output** — fresh `docs/index.html` + `docs/state.json`, 0 warnings from this build's changes.
