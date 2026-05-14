---
name: docs-cockpit-status
description: |
  Read an existing docs-cockpit's `docs/state.json` and answer interpretive questions about project status. Doesn't write or run anything — just reads structured frontmatter data (id / type / status / progress / sprint / owner / depends_on / blocks / updated_at) and produces narrative summaries: blockers, sprint completion %, stale docs, weekly diffs, standup reports.

  TRIGGER this skill when the user asks status / health / progress questions about a project that already has docs-cockpit set up. Common phrasings: "what's blocked", "what's blocked in <project>", "sprint M1.3 progress", "how's the project going", "weekly status from docs", "generate a standup report", "which modules haven't moved", "which RFCs are still planned", "show me sprint M1.X cards", "what changed in the cockpit this week", "项目进度怎么样", "哪些模块卡了", "M1.2 sprint 还差啥", "给我一份周报". Also trigger for status diffs over time if historical state.json snapshots exist ("what's different since last week").

  Do NOT trigger for: setting up a cockpit when no state.json exists (→ sibling `docs-cockpit`); changing config / yaml / MD files (writing files → `docs-cockpit`); rendering or building (→ `docs-cockpit`); questions about a project that doesn't have docs-cockpit installed (state.json doesn't exist — answer with the source MDs directly or suggest installing docs-cockpit first). The discriminator: `docs/state.json` (or a custom path equivalent) **exists** AND the user wants **narrative output with no file changes** → this skill. Anything that writes a yaml / MD / HTML / hook → the sibling.
---

# docs-cockpit-status

> Read the cockpit. Tell the user what's going on. No file writes — narrative only.

## Scope · what's in this skill vs the sibling

**This skill** (`docs-cockpit-status`) — **reads only**. Answers questions about a cockpit's current state. Outputs are tables, prose, bullet lists. **No project files change.**

**Sibling skill** (`docs-cockpit`) — **writes/edits**. Setup, add doc sources, build, frontmatter wiring, design tweaks, debug. If the user wants to *change* the cockpit, hand off.

If the user shifts mid-conversation from "what's going on" → "fix this", hand off explicitly: *"That's a setup/maintenance change — switching to the `docs-cockpit` skill for that."*

## Data source: `docs/state.json`

Every `docs-cockpit build` writes `<output_dir>/state.json` next to `index.html`. That's your primary input.

### Where to find it

- Default: `<project_root>/docs/state.json`
- Custom: if `project.output` in `docs-cockpit.yaml` is e.g. `site/foo.html`, state.json is at `site/state.json` (sibling of the HTML)
- Always read the **most recent** state.json — its `build_time` is in the JSON

### If state.json doesn't exist

Three possible causes — diagnose before answering anything:

1. **Cockpit was never built** → tell the user "I don't see `docs/state.json`. Run `docs-cockpit build` and try again." Don't try to scan MD files manually as a fallback — that's the operational skill's job.
2. **Cockpit was built with an old docs-cockpit version** (pre-state.json output) → tell the user to `pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git` then rebuild.
3. **`project.output` is in an unusual place** → check `docs-cockpit.yaml` for the output path, look at that directory.

### State.json schema (top-level)

```json
{
  "project": { "name": "...", "subtitle": "...", "glyph": "...", "description": "..." },
  "build_time": "2026-05-14 22:30",
  "groups": [
    {
      "group": "Spec · Modules",
      "icon": "M",
      "color": "primary",
      "items": [
        {
          "slug": "m07-job-fsm",
          "title": "M07 · Job FSM",
          "path": "/abs/path/to/M07-job-fsm.md",
          "mtime": "2026-05-14 12:00:00",
          "exists": true,
          "size": 4521,
          "meta": { ...YAML frontmatter as parsed... }
        }
      ]
    }
  ],
  "cards": [
    {
      "id": "M07",
      "type": "module",
      "title": "Job FSM",
      "status": "in-progress",         // not-started | planned | in-progress | blocked | done | deferred
      "progress": 45,                  // 0-100
      "sprint": "M1.2",
      "prd_ref": "§6.3.7",
      "owner": "harvey",
      "depends_on": ["M04", "M06"],
      "blocks": ["M08"],
      "updated_at": "2026-05-14",
      "slug": "m07-job-fsm",
      "group": "Spec · Modules"
    }
  ],
  "kpi": {
    "kpi_type": "module",
    "total_modules": 24,
    "done": 5,
    "in_progress": 8,
    "blocked": 2,
    "planned": 7,
    "not_started": 2,
    "deferred": 0,
    "overall_progress": 32.1
  },
  "sprint_order": ["M0", "M1.1", "M1.2", "M2", "M3", "GA"],
  "kanban_enabled": true,
  "warnings": ["progress=80 out of range [0,15] for status=planned · /path/foo.md"]
}
```

`cards` and `kpi` are only populated if `frontmatter.kanban.enabled: true` in the project's config. If `kanban_enabled: false`, you only have `groups[*].items[*]` to work with — fall back to mtime-based "what's been touched recently" answers.

## Workflow

### 1. Locate and load state.json

```python
# Always start here. Read the file via your Read tool.
# Don't shell out to jq or anything fancy — it's just JSON.
```

### 2. Decide which slice answers the question

| User asks about | Read from |
|---|---|
| Blocking / blockers | `cards` where `status == "blocked"` + `cards[*].blocks` graph |
| Sprint progress | `cards` filtered by `sprint == X` + sum `progress` |
| Stale docs | `groups[*].items[*].mtime` |
| Overall health | `kpi` |
| What changed | Compare two state.json snapshots over time |
| Specific module/RFC by id | `cards` filtered by `id` |
| Owner workload | `cards` grouped by `owner` |

### 3. Compose narrative output

**No file writes.** Reply directly to the user. Match the output shape to the question shape (see "Output format" below).

## Common question patterns

### A — "What's blocked?"

1. Read state.json
2. Filter `cards` → `status == "blocked"`
3. For each, also pull `blocks` (what this card is gating) and `depends_on` (what's gating this card)
4. Output as a table:

```markdown
| Card | Sprint | Blocks | Depends on |
|---|---|---|---|
| M07 · Job FSM | M1.2 | M08, M09 | M04 (✓ done) |
| RFC-002 · ResourcePool | M1.3 | M11 | — |
```

If 0 blockers: "Nothing's blocked right now. Total cards: N (done=X, in-progress=Y, planned=Z)."

### B — "Sprint M1.X progress"

1. Filter `cards` → `sprint == X`
2. Group by `status`, count each
3. Sum `progress` / count for an overall %
4. Output:

```markdown
**Sprint M1.2** · 3/8 done · 45% overall

- ✅ Done: M04, M05, M06
- 🔄 In progress: M07 (45%), M08 (20%)
- ⏳ Planned: M09, M10
- 🚫 Blocked: M11

Next moves: M07 is closest to done · M11 needs the resource-pool RFC decision before it can move.
```

If the sprint doesn't exist in `sprint_order`: tell the user, list known sprints.

### C — "What's stale / what hasn't been touched?"

1. Read `groups[*].items[*]` 
2. Filter by `mtime` older than threshold (default: 30 days, but ask the user if unsure)
3. Output as a table, oldest first:

```markdown
| Doc | Group | Last touched |
|---|---|---|
| docs/spec/concept/C03-site-adapter.md | Spec · Concepts | 2026-02-14 (90d ago) |
| docs/RFC/001-tech-stack.md | RFCs | 2026-03-01 (74d ago) |
```

Stale ≠ broken. Just surfacing for the user to triage.

### D — "Weekly diff / what changed this week?"

Requires two state.json snapshots. Options for getting the prior snapshot:

- User keeps a `docs/state-archive/<date>.json` per week (their setup)
- User has git history of `docs/state.json` — `git show HEAD~7:docs/state.json` to get last-week's
- If neither: tell the user "I'd need a previous state.json to diff against. Either commit `docs/state.json` weekly and I can `git show HEAD~7:docs/state.json`, or save snapshots under `docs/state-archive/`."

If two snapshots are available:
1. Diff `cards` by `id` — find new cards, removed cards, changed status, changed progress
2. Output as 4 sections:

```markdown
**Diff: 2026-05-07 → 2026-05-14**

🆕 New cards (2): M12 · Webhook FSM (planned), RFC-004 · Retry strategy (planned)
✅ Newly done (1): M05 · Login flow (was in-progress 80%)
📈 Progress (3): M07 30% → 45%, M08 0% → 20%, M11 planned → blocked
🚫 Newly blocked (1): M11 · Quota enforcer (was planned)
```

### E — "Generate a standup / weekly report"

Combine A + B + C + D into a paste-ready Markdown block. Default structure (override if user has a template):

```markdown
## Sprint M1.2 weekly status · 2026-05-14

**KPI bar**: 24 modules · 5 done · 8 in-progress · 2 blocked · 7 planned · 32% overall progress

### 🚀 This week's wins
- M05 · Login flow shipped (was in-progress 80% last week)
- M07 · Job FSM now at 45% (was 30%)

### 🔥 Blockers
- M11 · Quota enforcer (gated on RFC-002 decision)

### 📋 In flight this sprint
- M07 (45%), M08 (20%)

### 🥶 Stale (>30 days no edit)
- C03 · Site Adapter (2026-02-14, 90d)
- RFC-001 · Tech stack (2026-03-01, 74d)

### ⚠️ Frontmatter warnings (2)
- M09 has progress=80 but status=planned (range allows 0-15)
- RFC-003 missing `updated_at`
```

## Output format conventions

- **Tables for multi-row data** (3+ cards, multiple blockers, stale list)
- **Prose for single-answer questions** ("How's M07?" → "M07 · Job FSM is in-progress at 45%, in sprint M1.2, blocks M08 and M09, depends on M04 which is done.")
- **Bullet lists for short enumerations** (≤4 items)
- **Always include build_time** at the top or bottom: "Based on `docs/state.json` built 2026-05-14 22:30" — so the user knows how fresh the answer is
- **Always note kanban-disabled mode** if `kanban_enabled: false`: "(kanban not enabled in this project's config — answer based on mtime + filenames only)"

## Failure modes

- **state.json missing** → tell user to run `docs-cockpit build`, don't fall back to MD scanning
- **state.json present but kanban_enabled: false** → degrade gracefully to file-listing answers (group structure + mtime), skip card/KPI questions, suggest enabling kanban (hand off to `docs-cockpit`)
- **state.json present but cards array empty** → kanban is enabled but no MD files have `id` frontmatter; tell the user "kanban is on but no docs are wired up as cards. Add `id: M01` (or similar) to the docs you want to track."
- **state.json present but build_time is suspiciously old** (>7 days) → note it: "This data is from 2026-05-01 — it may be stale. Run `docs-cockpit build` if you want today's state."
- **user asks about something not in state.json** (e.g. content of an MD) → tell them this skill only sees frontmatter; for content questions hand off to a regular Read of the source MD file
