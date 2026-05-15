---
name: docs-cockpit-standup
description: |
  Read an existing docs-cockpit project's `docs/state.json` and answer interpretive questions about module status, sprint progress, blockers, stale docs, frontmatter issues, and weekly diffs. Generates standup-shaped narrative summaries. Doesn't write or run anything — just reads structured data (`modules[]` with id / status / progress / sprint / desc / docs / subtasks, `concepts[]`, `systemDocs[]`, `issues[]`) and produces tables / bullet lists / paste-ready Markdown reports.

  TRIGGER this skill when the user asks status / health / progress / blocker / standup questions about a project that already has docs-cockpit set up. Common phrasings: "what's blocked", "what's blocked in <project>", "sprint M1.3 progress", "how's the project going", "weekly status from docs", "generate a standup report", "which modules haven't moved", "show me sprint M1.X modules", "what changed in the cockpit this week", "项目进度怎么样", "哪些模块卡了", "M1.2 sprint 还差啥", "给我一份周报", "哪些 module 子任务做完了", "总体完成度多少", "frontmatter 校验有什么问题". Also trigger for status diffs over time if historical state.json snapshots exist.

  Do NOT trigger for: setting up a cockpit when no state.json exists (→ sibling `docs-cockpit`); changing config / yaml / MD files (writing → `docs-cockpit` for the cockpit itself, `docs-cockpit-author` for a single doc); rendering or building (→ `docs-cockpit`); upgrading docs-cockpit itself (→ `docs-cockpit upgrade` CLI). The discriminator: `docs/state.json` (or a custom path equivalent) **exists** AND the user wants **narrative output with no file changes** → this skill. Anything that writes a yaml / MD / HTML / hook → the sibling.
---

# docs-cockpit-standup (0.9.0+)

> Read the cockpit's `state.json`. Tell the user what's going on. No file writes — narrative only.
>
> _Renamed from `docs-cockpit-status` in 0.9.0 to avoid collision with the `/docs-cockpit:status` slash command (which itself triggers this skill). The skill still answers the same questions; the new name better describes the output (standup-shaped reports)._

## Scope · what's in this skill vs the siblings

**This skill** (`docs-cockpit-standup`) — **reads ONE cockpit's state.json**. Single-project narrative answers: what's blocked, sprint progress, blockers, weekly standup, lint summary, stale docs. **No project files change.**

**Sibling `docs-cockpit-portfolio`** (NEW in 0.10.0) — **reads MULTIPLE projects' state.json** via the user's portfolio registry (`~/.docs-cockpit/projects.yaml`). Composes cross-project weekly reports with week-over-week diffs from snapshots. **If the user asks for "周报" / "weekly report" without naming a project, or asks about progress across multiple projects, hand off to portfolio — this skill is single-project only.**

**Sibling `docs-cockpit`** — **writes/edits at the cockpit level**. Setup, extend modules / concepts list, build, wire `docs-cockpit.yaml`, debug. If the user wants to *change what the cockpit scans*, hand off.

**Sibling `docs-cockpit-author`** — **writes a single project doc** (plan / RFC / spec / module MD / concept MD) per the unified frontmatter spec. If the user wants to add a plan or fix frontmatter issues you surfaced from `issues[]`, hand off.

**CLI `docs-cockpit upgrade`** — **handles cockpit upgrades**. If `docs/state.json` is **missing**, or has the old 0.1.x shape (`groups[]` / `cards[]` / `kpi{}` instead of `modules[]` / `concepts[]` / `systemDocs[]`), the user's CLI is stale → tell them to run `docs-cockpit upgrade` rather than try to read the old shape.

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
  ],
  "issues": [
    {
      "severity": "error",
      "path": "<abs path>",
      "field": "id",
      "message": "missing required field — module/concept won't appear in dashboard",
      "suggestion": "add `id: M01-...` to frontmatter",
      "reference": "docs-cockpit-author · §2.1 required frontmatter"
    }
  ]
}
```

**Notes**:
- `modules[]` are full-featured (subtasks / docs / desc / owner / depends_on / blocks). Concepts are minimal.
- `subtasks[*].done` reflects the **MD frontmatter** state, NOT user's localStorage overrides. User overrides only persist in browser localStorage; they don't write back to MD.
- `progress` is the **stored value** (from frontmatter). If `manualProgress: false`, the rendered Kanban auto-derives from subtask done ratio in the browser — but `state.json` keeps the raw frontmatter `progress` value.
- **`issues[]`** (0.9.0+) is the structured frontmatter validation output. Each entry has `severity` (error / warn / hint) + `field` + `message` + `suggestion` + `reference` (pointing to a section of the `docs-cockpit-author` skill). The legacy `warnings[]` field is kept for backward compat but is just the messages without context.

### If state.json doesn't exist or has wrong shape

Three diagnostic cases:

1. **state.json missing entirely** → tell the user to run `/docs-cockpit:build` first. Don't try to read MD files yourself as fallback.
2. **state.json exists but uses 0.1.x shape** (`{groups, cards, kpi}` instead of `{modules, concepts, systemDocs}`) → user's CLI is pre-0.2.0. Tell them to run `docs-cockpit upgrade`. Don't try to read the old shape.
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

### ⚠️ Frontmatter issues (3 error · 5 warn · 8 hint)
- ❌ M11 missing `id` (won't appear on dashboard) · see docs-cockpit-author §2.1
- ⚠️ M09 progress=80 vs status=planned (range [0,15]) · see §2.3
- 💡 M03 missing `desc` (drawer empty + weaker copy-prompt) · see §2.5
→ run `docs-cockpit lint` for the full list · `docs-cockpit-author` skill has the schema spec
```

### F — "Frontmatter issues / lint"

When the user asks "what's wrong with frontmatter" / "lint output" / "fix the warnings":

1. Read `issues[]` from state.json (0.9.0+) — has structured `severity`/`field`/`suggestion`/`reference`
2. Group by severity:
   - `error` → blocking (won't render at all) · MUST fix
   - `warn` → user-experience problems · SHOULD fix
   - `hint` → polish · CAN fix later
3. For each issue, surface: which file · what field · what's wrong · suggested fix · reference section
4. Offer: "Want me to hand off to `docs-cockpit-author` and fix these one-by-one, or fix as a batch?"
5. Hand off to `docs-cockpit-author` for actually editing the MD files

## Output format conventions

- **Tables** for multi-row data (3+ modules, blockers, stale list)
- **Prose** for single-answer questions ("How's M07?" → "M07 · Job FSM is in-progress at 45%, in sprint M1.2, blocks M08 and M09, depends on M04 which is done. 2/4 subtasks complete.")
- **Bullet lists** for short enumerations (≤4 items)
- **Always include `lastBuild`** so user knows data freshness: "Based on `docs/state.json` built 2026-05-15 10:30"
- **Always note `warnings[]`** if non-empty — surface frontmatter issues so user can fix

## Failure modes

- **state.json missing** → tell user `/docs-cockpit:build`, don't scan MD as fallback
- **state.json has 0.1.x shape** → tell user to run `docs-cockpit upgrade` (replaces old `docs-cockpit-update` skill)
- **state.json `modules` array empty** → no module MDs have `id` frontmatter; tell user "no modules visible — add `id:` to your module MDs" and offer to hand off to `docs-cockpit-author`
- **`lastBuild` > 7 days** → note staleness: "This data is from 2026-05-01 — may be stale. Run `docs-cockpit build` for fresh state."
- **User asks about content of an MD** → this skill only sees frontmatter (no markdown body in state.json). For body queries, suggest opening the MD directly OR hand off to `docs-cockpit` for build context.
