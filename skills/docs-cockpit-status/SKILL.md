---
name: docs-cockpit-status
description: |
  Read an existing docs-cockpit project's `docs/state.json` and answer interpretive questions about module status, sprint progress, blockers, stale docs, and weekly diffs. Doesn't write or run anything — just reads structured frontmatter data (`modules[]` with id / status / progress / sprint / desc / docs / subtasks, `concepts[]`, `systemDocs[]`) and produces narrative summaries.

  TRIGGER this skill when the user asks status / health / progress questions about a project that already has docs-cockpit set up. Common phrasings: "what's blocked", "what's blocked in <project>", "sprint M1.3 progress", "how's the project going", "weekly status from docs", "generate a standup report", "which modules haven't moved", "show me sprint M1.X modules", "what changed in the cockpit this week", "项目进度怎么样", "哪些模块卡了", "M1.2 sprint 还差啥", "给我一份周报", "哪些 module 子任务做完了", "总体完成度多少". Also trigger for status diffs over time if historical state.json snapshots exist.

  Do NOT trigger for: setting up a cockpit when no state.json exists (→ sibling `docs-cockpit`); changing config / yaml / MD files (writing → `docs-cockpit`); rendering or building (→ `docs-cockpit`); questions about a project that doesn't have docs-cockpit installed (state.json doesn't exist — suggest installing docs-cockpit first). The discriminator: `docs/state.json` (or a custom path equivalent) **exists** AND the user wants **narrative output with no file changes** → this skill. Anything that writes a yaml / MD / HTML / hook → the sibling.
---

# docs-cockpit-status (0.2.0+)

> Read the cockpit's `state.json`. Tell the user what's going on. No file writes — narrative only.

## Scope · what's in this skill vs the siblings

**This skill** (`docs-cockpit-status`) — **reads only**. Answers questions about a cockpit's current state. Outputs are tables, prose, bullet lists. **No project files change.**

**Sibling `docs-cockpit`** — **writes/edits**. Setup, extend modules / concepts, build, frontmatter wiring, debug. If the user wants to *change* the cockpit, hand off.

**Sibling `docs-cockpit-update`** — **handles upgrades**. If `docs/state.json` is **missing**, or has the old 0.1.x shape (`groups[]` / `cards[]` / `kpi{}` instead of `modules[]` / `concepts[]` / `systemDocs[]`), the user's CLI is stale → hand off to `docs-cockpit-update` rather than try to fall back.

## Data source: `docs/state.json` (0.2.0 schema)

Every `docs-cockpit build` writes `<output_dir>/state.json` next to `index.html`. That's your primary input.

### Where to find it

- Default: `<project_root>/docs/state.json`
- Custom: if `project.output` in `docs-cockpit.yaml` is e.g. `site/foo.html`, state.json is at `site/state.json` (sibling of the HTML)

### Schema (top-level)

```json
{
  "project": {
    "name": "MyProject",
    "tagline": "项目进度概览…",
    "eyebrow": "DASHBOARD",
    "mark": "M",
    "lastBuild": "2026-05-15 10:30"
  },
  "systemDocs": [
    { "id": "claude-md", "title": "CLAUDE.md", "path": "<abs>", "desc": "...", "icon": "memory" }
  ],
  "modules": [
    {
      "id": "M07",
      "title": "Job FSM",
      "status": "in-progress",     // not-started | planned | in-progress | blocked | done | deferred
      "sprint": "M1.2",
      "progress": 45,              // 0-100
      "desc": "12 类核心 FSM 状态机",
      "docs": [{ "title": "Schema 设计文档", "path": "docs/design/schemas.md" }],
      "subtasks": [
        { "title": "核心实体定义(12 类)", "done": true },
        { "title": "字段校验与 strict 模式", "done": false }
      ],
      "manualProgress": false,
      "path": "<abs path to MD>",
      "mtime": "2026-05-14 12:00:00",
      "owner": "harvey",
      "prd_ref": "§6.3.7",
      "depends_on": ["M04"],
      "blocks": ["M08"],
      "updated_at": "2026-05-14"
    }
  ],
  "concepts": [
    {
      "id": "C03",
      "title": "Site Adapter",
      "status": "in-progress",
      "sprint": "M1.2",
      "progress": 60
    }
  ],
  "warnings": [
    "M09-foo.md: progress=80 out of range [0, 15] for status=planned"
  ]
}
```

**Notes**:
- `modules[]` are full-featured (subtasks / docs / desc / owner / depends_on / blocks). Concepts are minimal.
- `subtasks[*].done` reflects the **MD frontmatter** state, NOT user's localStorage overrides. User overrides only persist in browser localStorage; they don't write back to MD.
- `progress` is the **stored value** (from frontmatter). If `manualProgress: false`, the rendered Kanban auto-derives from subtask done ratio in the browser — but `state.json` keeps the raw frontmatter `progress` value.

### If state.json doesn't exist or has wrong shape

Three diagnostic cases:

1. **state.json missing entirely** → tell the user `/docs-cockpit:build` first. Don't try to read MD files yourself as fallback.
2. **state.json exists but uses 0.1.x shape** (`{groups, cards, kpi}` instead of `{modules, concepts, systemDocs}`) → user's CLI is pre-0.2.0. Hand off to `docs-cockpit-update`. Don't try to read the old shape.
3. **state.json exists but `lastBuild` > 7 days ago** → note the staleness in your output but still answer.

## Workflow

### 1. Locate and load state.json

```python
# Just read the file. It's plain JSON.
```

### 2. Decide which slice answers the question

| User asks about | Read from |
|---|---|
| Blockers | `modules` where `status == "blocked"` + `blocks` / `depends_on` graph |
| Sprint progress | `modules` filtered by `sprint == X` + sum `progress` |
| Stale modules | `modules[*].mtime` (or `updated_at`) |
| Overall health | derived counts from `modules` |
| What changed | compare two state.json snapshots over time (git history or archive) |
| Specific module/concept by id | filter by `id` |
| Owner workload | `modules` grouped by `owner` |
| Subtask completion | per module, count `subtasks[*].done` |

### 3. Compose narrative output

**No file writes.** Reply directly to the user. Match output shape to question shape (see "Output format" below).

## Common question patterns

### A — "What's blocked?"

1. Filter `modules` → `status == "blocked"`
2. For each, pull `blocks` (what this gates) and `depends_on` (what gates this)
3. Output as a table:

```markdown
| Module | Sprint | Blocks | Depends on |
|---|---|---|---|
| M07 · Job FSM | M1.2 | M08, M09 | M04 (✓ done) |
| M11 · Quota Enforcer | M1.3 | — | RFC-002 (planned) |
```

If 0 blockers: "Nothing's blocked right now. Total modules: N (done=X, in-progress=Y, planned=Z)."

### B — "Sprint M1.X progress"

1. Filter `modules` → `sprint == X`
2. Group by `status`, count each
3. Sum `progress` / count for overall %

```markdown
**Sprint M1.2** · 3/8 done · 45% overall

- ✅ Done: M04, M05, M06
- 🔄 In progress: M07 (45%), M08 (20%)
- ⏳ Planned: M09, M10
- 🚫 Blocked: M11
```

### C — "What's stale?"

1. Read `modules[*].mtime` (or `updated_at`)
2. Filter by older than threshold (default: 30 days)
3. Output table oldest first

### D — "Weekly diff"

Requires a previous state.json snapshot. Options:
- User keeps `docs/state-archive/<date>.json` weekly
- User has git history of `docs/state.json` → `git show HEAD~7:docs/state.json`
- If neither: tell user "I'd need a prior snapshot — commit `docs/state.json` weekly and I can `git show HEAD~7:docs/state.json`."

If two snapshots available, diff `modules` by `id`:

```markdown
**Diff: 2026-05-07 → 2026-05-14**

🆕 New (2): M12 · Webhook FSM (planned), RFC-004 (planned)
✅ Newly done (1): M05 · Login flow (was 80% in-progress)
📈 Progress (2): M07 30%→45%, M08 0%→20%
🚫 Newly blocked (1): M11 · Quota enforcer
```

### E — "Generate a standup / weekly report"

Combine A + B + C + D into paste-ready Markdown:

```markdown
## 2026-05-14 · Weekly status · Sprint M1.2

**KPI**: 24 modules · 5 done · 8 in-progress · 2 blocked · 7 planned · 32% overall

### 🚀 Wins this week
- M05 · Login flow shipped (was 80%)
- M07 · Job FSM now 45% (was 30%)

### 🔥 Blockers
- M11 · Quota enforcer (gated on RFC-002)

### 📋 In flight
- M07 (45%), M08 (20%)

### 🥶 Stale (>30 days)
- C03 · Site Adapter (90d ago)
- RFC-001 · Tech stack (74d ago)

### ⚠️ Frontmatter warnings (2)
- M09 progress=80 vs status=planned (range [0,15])
- RFC-003 missing updated_at
```

## Output format conventions

- **Tables** for multi-row data (3+ modules, blockers, stale list)
- **Prose** for single-answer questions ("How's M07?" → "M07 · Job FSM is in-progress at 45%, in sprint M1.2, blocks M08 and M09, depends on M04 which is done. 2/4 subtasks complete.")
- **Bullet lists** for short enumerations (≤4 items)
- **Always include `lastBuild`** so user knows data freshness: "Based on `docs/state.json` built 2026-05-15 10:30"
- **Always note `warnings[]`** if non-empty — surface frontmatter issues so user can fix

## Failure modes

- **state.json missing** → tell user `/docs-cockpit:build`, don't scan MD as fallback
- **state.json has 0.1.x shape** → hand off to `docs-cockpit-update`
- **state.json `modules` array empty** → no module MDs have `id` frontmatter; tell user "no modules visible — add `id:` to your module MDs"
- **`lastBuild` > 7 days** → note staleness: "This data is from 2026-05-01 — may be stale. Run `docs-cockpit build` for fresh state."
- **User asks about content of an MD** → this skill only sees frontmatter (no markdown body in state.json). For body queries, suggest opening the MD directly OR hand off to `docs-cockpit` for build context.
