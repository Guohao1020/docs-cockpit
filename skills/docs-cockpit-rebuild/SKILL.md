---
name: docs-cockpit-rebuild
description: "Refresh an existing docs-cockpit: diagnose stale anchors, re-sync changed specs, answer status/progress questions, run health checks, and render fixes."
---

# docs-cockpit-rebuild

**The 5-phase workflow for diagnosing and refreshing an existing module ↔ subtask ↔ spec/plan/RFC association system — and for answering "how is the project doing" along the way.**

## Why this skill exists

`docs-cockpit-build` creates the association system; this skill keeps it true. Anchors are line ranges and section headings into living files — every refactor moves code, every spec revision moves sections, and an anchor that pointed at the right lines last sprint can silently point at garbage today. The same principle that governs build governs rebuild, only more urgently: **a wrong anchor is worse than a missing anchor.** A drifted anchor sends the user to irrelevant content while *looking* authoritative, which destroys trust in the entire dashboard. So rebuild's job is precision maintenance: re-verify everything, re-infer only what broke, and touch nothing that is still accurate.

## Rebuild vs build

Both skills share the same four atomic methods in `references/association-method.md` — they differ in direction and scope:

- **build** = 0→1. Whole-project association planning, every linkage decided WITH the user in dialogue, gap docs drafted.
- **rebuild** = incremental. An association already exists; diagnose which anchors drifted, refresh ONLY those, keep accurate ones byte-for-byte intact (minimal diff).

If no association exists at all (no `docs:` / `subtasks` anchors anywhere), stop and hand off to `docs-cockpit-build` — diagnosing an empty system is not a rebuild.

## Checkup runs（体检触发）

「体检一下」「全面体检」「健康检查」 / "health check" / "checkup" trigger a **checkup run**: execute Phase 1–2, present the three-part report, and STOP — the report IS the deliverable, with the same endpoint semantics as pure status queries ending at Phase 1. Treatment (Phase 3–4) starts only if the user then confirms buckets. Mode selection: the request contains 「深度」/「全面」/ "deep" / "full" → deep mode (all nine departments, full anchor-verdict pass); otherwise quick mode. Methodology, thresholds, and templates: `references/health-check.md`.

## How this skill is layered

This skill is the **orchestration layer** — it tells you which phase to run when. The details live in references (do not restate them; read them when the phase needs them):

| Reference | Holds | Used by |
|---|---|---|
| `references/association-method.md` | the 4 atomic methods (discovery / reasoning / dry-run / highlight) | Phase 2–3 |
| `references/schema.md` | frontmatter fields · subtask forms · code/doc anchor formats | Phase 4 |
| `references/health-check.md` | nine-department checkup methodology · three-part report template · five-bucket triage · HEALTH.md writing rules | Phase 2 (checkup report), 3–4 (bucket landing) |
| `docs/state.json` | machine-readable current state (input, not a doc to edit) | Phase 1 |

Default scope is **all existing anchors in the project**. The user can narrow it ("only M07", "only docs touched by this refactor"); say so explicitly in Phase 2's verdict table if scoped down.

---

## Phase 1 · Read current state

- **Goal** — an accurate narrative of the association system as it stands: module statuses, sprint progress, blockers, open issues.
- **Actions** — Read `docs/state.json`. Key fields: `modules[].status` / `modules[].progress` / `modules[].subtasks[]` (per-subtask `status` / `done` / code+doc anchors with `exists` flags), and `issues[]` (structured validator output). Cross-read the module MDs when `project.lastBuild` looks older than recent repo activity — state.json is a build artifact and can itself be stale. From this, answer the narrative questions directly: what's blocked and on what, which sprint is how far along, which modules haven't moved.
- **Reference** — `docs/state.json` (top-level shape: `project` / `systemDocs` / `modules` / `concepts` / `warnings` / `issues`).
Narrative shape (for status answers):

> Sprint M1.2 · 3/5 modules on track · 1 blocked.
> M07 (60%, in-progress): 2/4 subtasks done, latest anchor all ✅.
> M09 (blocked): waiting on RFC-004 decision — see issues[].
> Next action: unblock M09 or pull M11 forward.

Order: sprint overview → per-module status (group by status, blocked first) → concrete blockers from issues[] → suggested next action.

- **Output** — status narrative (progress / blockers / stalled modules) + a routing decision: continue to Phase 2, or stop here.

**Pure status queries END at this phase.** If the user asked "项目进度怎么样" / "what's blocked" / "sprint progress" and nothing suggests drift, Phase 1's narrative IS the deliverable — no lint, no anchor verification, no file edits. Only proceed to Phase 2 when the user reports drift ("关联乱了", "重构后失效"), when Phase 1 surfaces evidence of it (anchors with `exists: false`, `issues[]` about anchors), or when the user explicitly asks for a re-sync.

## Phase 2 · Diagnose drift

- **Goal** — a verdict for every existing anchor: which are still true, which drifted, which never existed.
- **Actions** — two passes. (a) Run `docs-cockpit lint` for the dead-rule layer: schema violations, missing ids, and the `subtask-missing-anchors` list of 0-anchor subtasks. (b) Apply **Method 3** (dry-run) to re-verify **ALL** existing anchors — Read each anchor's exact target slice (offset/limit for `:lines`, heading scan for `#§N`) and compare against the owning subtask's title. Assign each anchor one of the 4 verdicts: ✅ accurate / ⚠️ partial / ❌ wrong / ❓ missing.
- **Atomic method** — Method 3 · dry-run (`references/association-method.md`).
- **Output** — full verdict table: every existing anchor → verdict → evidence note (what the target slice actually says now). Nothing in the table is accurate-by-assumption — every ✅ was actually Read this session.

Scale note: if existing anchors > 30, don't brute-force every one. Run lint first (free, catches missing/dead files), then prioritize dry-run on anchors whose target files changed recently (git log / user-named refactor scope), batch the rest and report progress per batch.

Verdict presentation format (example):

```
【诊断 7/23】 M03 「Render Engine」 · subtask M03-S2 「drawer 内联渲染 linked docs」
  现存 anchor : @docs:docs/plans/2026-04-12-m03-render-plan.md#§3.1
  预演 verdict: ⚠️ partial —— §3.1 标题还在，但 drawer 内联逻辑在 v0.18 重排后挪到了 §3.4
  处理       : → Phase 3 重推理（候选 §3.4）
```

**End of phase · checkup consolidation（复查呈报）.** Phase 1–2 are this skill's recheck（复查）: consolidate their diagnostic output per `references/health-check.md` into a checkup report before any treatment:

1. Write or update `docs/HEALTH.md` — frontmatter per `references/schema.md · health-report schema`. RX ids are stable and monotonic: resolved prescriptions are removed (their numbers never reused), unresolved ones keep their original id, new ones continue from the last max.
2. Present the three-part report（诊断 / 处方 / 行动规划）per health-check.md's template.
3. Walk the five buckets for the user's ruling. On a checkup run the flow ENDS here; otherwise confirmed treatment items proceed to Phase 3–4, where the bucket landing rules live.

## Phase 3 · Re-infer

- **Goal** — a verified replacement candidate for every non-accurate anchor.
- **Actions** — for each ⚠️ partial / ❌ wrong / ❓ missing item, apply **Method 1** (discovery: re-Glob the five doc kinds, keyword cross-grep, ≥2 distinct-dimension hits → candidate pool) then **Method 2** (reasoning: Read the candidate body, locate the §N that answers the subtask's "why" or "how"). No genuine match → record an honest gap with a `# TODO` rather than forcing the nearest section. ✅ accurate anchors are **not re-inferred and not touched** — re-deriving them wastes effort and risks churn.
- **Atomic method** — Method 1 + Method 2 (`references/association-method.md`).
- **Output** — per-drifted-item proposal (new path + section, or honest-gap TODO), alongside the untouched-accurate list.

## Phase 4 · Refresh

- **Goal** — every drifted anchor corrected on disk, with the smallest possible diff.
- **Actions** — edit **only the broken anchors**; accurate links stay byte-identical (minimal diff is the contract — a rebuild that rewrites healthy lines is indistinguishable from churn in review). Write each fix in the form the target doc already uses — frontmatter `subtasks:` object array vs body `@code:` / `@docs:` inline — exact syntax per `references/schema.md`; never mix forms in one doc. **Destructive changes need the user's ruling first**: deleting an anchor outright, changing a module/subtask `id`, retargeting to a different doc kind — propose, explain why, wait. Range adjustments within the same file (⚠️ partial verdicts) are auto-applicable; all other structural changes (id rename, sprint reassignment, doc-kind change, anchor deletion) require the user's ruling. After editing, Read each changed subtask block once to confirm the written anchor matches the proposal — don't rely on Edit's success alone.
- **Reference** — `references/schema.md` (subtask forms · anchor formats).
- **Output** — minimal-diff edits to the module MDs; a short changelog of what moved where and why; a list of edited files (inputs to Phase 5).

What "minimal diff" looks like (the only changed bytes are the drifted anchor):

```diff
- - [ ] drawer 内联渲染 linked docs @docs:docs/plans/2026-04-12-m03-render-plan.md#§3.1
+ - [ ] drawer 内联渲染 linked docs @docs:docs/plans/2026-04-12-m03-render-plan.md#§3.4
```

**Checkup prescription landing（处方→subtask 闭环）.** Bucket decisions confirmed at the end of Phase 2 land here, with the same rules as build Phase 6:

- **`sprint`** — write the prescription as a subtask (title per schema.md's 4 rules) carrying a `@code:` anchor at the problem location, under the module named by the prescription's `module` field; no owning module → ask the user before creating a dedicated health-debt module（「健康债」）. Sync the sprint-plan `in_scope`.
- **`backlog`** — draft a plan doc（file naming per `references/schema.md · 文件命名约定`）with the prescription's anchors in its evidence section.
- **`accepted`** — record in `docs/HEALTH.md` `accepted_debts`（item / reason / review date — ledger rules per health-check.md）.
- **`watch`** — stays in `docs/HEALTH.md` `prescriptions` with `bucket: watch`; the next checkup verifies these first.
- **`now`** — treat on the spot in this phase（edit + `docs-cockpit render` verify）.

## Phase 5 · Render + verify

- **Goal** — a regenerated dashboard proving the refresh landed clean: 0 warnings traced to this rebuild.
- **Actions** — run `docs-cockpit render` and read the issue output. Any `❌`/`⚠️` traced to this rebuild's edits → fix (loop back to the relevant phase for that item) and re-render. Pre-existing unrelated warnings: surface to the user, don't block on them.
- **Reference** — CLI.
- **Output** — fresh `docs/index.html` + `docs/state.json`, 0 warnings from this rebuild's changes.
