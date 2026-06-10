# Sync Status Workflow · docs-cockpit v0.12+

> Close the loop on **plan §1 缺口 3** — get the subtask checkboxes you ticked in the dashboard back into your source MD where they belong.

## Why this exists

docs-cockpit's dashboard lets you tick subtask checkboxes for instant feedback while working. By default those ticks live in browser `localStorage` — fine for single-session work, problematic over time:

1. **Drift** · MD is the source of truth (CI / git history / other devs all read MD). localStorage drifts away from MD over days.
2. **Lost on browser clear** · clearing cache nukes weeks of dashboard ticks.
3. **No cross-machine sync** · laptop A's localStorage doesn't reach laptop B.

`docs-cockpit sync-status` writes those ticks back to MD so MD stays canonical.

(0.11.3's complementary fix: build-time-aware override invalidation makes the **MD → dashboard** direction work; sync-status closes the **dashboard → MD** direction.)

## The supported workflow (Path 1 · Export JSON)

### Step 1 · Export from dashboard

Open `docs/index.html` · top-right · click the **Export** button (next to System Docs / language toggle). A JSON file downloads:

```
<project-name>-overrides-2026-05-19T15-30-00.json
```

The file is the raw `localStorage["project-kanban-state-v1"]` payload plus an `_exported_at` timestamp.

### Step 2 · Dry-run sync

```bash
docs-cockpit sync-status --import ./Test-overrides-2026-05-19T15-30-00.json
```

Output shows:
- which modules / subtasks would be ticked
- a unified diff per touched MD
- any `⚠ stale subtask ref` warnings (override referencing a subtask that no longer exists in MD)

### Step 3 · Apply

```bash
docs-cockpit sync-status --import overrides.json --apply
```

Writes each touched MD with a `.bak` backup sibling. Standard dry-run-first pattern（原 migrate-subtasks / apply-patch CLI 同款 · 两者 v1.0 已删 · 现用 Edit 直接重写 MD）.

### Step 4 · Commit + rebuild

```bash
git add docs/spec/module/*.md
git commit -m "sync: dashboard ticks → source MD"
docs-cockpit build -c docs-cockpit.yaml
```

The rebuild's 0.11.3 logic then invalidates the now-stale localStorage entries (because the new `build_time` ≠ stored `_built_at`) — the dashboard re-renders from source and the loop closes cleanly.

## Priority rules

`sync-status` is **promotion-only** by default — it ticks done · it does not un-tick:

| localStorage | MD                | Result                        |
|--------------|-------------------|-------------------------------|
| `done = true`  | `not-started`      | MD gets `[x]` (localStorage wins) |
| `done = false` | `done`             | MD stays `[x]` (MD wins · localStorage is "user un-ticked locally · we trust MD") |
| no record    | `done` / `not-done` | MD wins (no override to apply) |
| `done = true`  | subtask missing     | warn + skip (subtask deleted/renamed) |

If you genuinely want to un-tick in MD, edit MD directly. The asymmetry prevents "I forgot I un-ticked that yesterday" from silently downgrading shipped state.

## Cross-machine workflow

For multi-machine workflows (laptop · desktop · CI), establish one of these patterns:

### Pattern A · Manual on demand

Each machine:
1. Work in dashboard · tick checkboxes locally
2. Before context switch · Export overrides → save in `~/Downloads`
3. On the other machine · pull the JSON file → `sync-status --apply` → commit MD
4. Other machine `git pull` → `docs-cockpit build` → dashboard now reflects synced state

### Pattern B · Weekly cadence (recommended for solo developers)

Set a recurring reminder (Friday EOD or Monday AM):
1. From your primary work machine
2. Export overrides
3. `docs-cockpit sync-status --import ./latest-overrides.json --apply`
4. Commit + push
5. Skip on other machines — MD is now ahead, build invalidates their old localStorage automatically

### Pattern C · Pair / team

For teams sharing one project: agree on **MD is canonical · dashboard is scratchpad**. Each dev exports + syncs on their own cadence; conflicts surface in git diff (two devs ticked the same subtask = no conflict; one ticked vs one untickled → MD-wins resolves cleanly).

## Path 2 · Direct browser profile read (v0.13 candidate)

Eventually:

```bash
docs-cockpit sync-status --from-browser chrome --apply
```

Skips the Export-button step by reading `localStorage` directly from the browser profile dir:
- Chrome / Edge → `Local Storage/leveldb`
- Firefox → `webappsstore.sqlite`

**MVP status: stub** — running this prints an error pointing back to Path 1. The leveldb/sqlite readers + cross-platform path resolution are scoped to v0.13. If you need this sooner · open an issue.

## Limitations / trade-offs

- **No module-level sync** — only subtask checkboxes (the `__st__` keys). Module-level dashboard overrides (status select / progress slider override) stay in localStorage and don't write back. Reason: module-level fields are wired through `manualProgress` + frontmatter `status` / `progress`; touching those reliably is more brittle than subtasks.
- **Un-ticking requires MD edit** — see priority rules above. Promotion-only by design.
- **Body checklist vs frontmatter subtasks** — supported on both forms. The merge follows the same logic as `apply-patch` (M08): frontmatter `subtasks:` Form A merges by id; body `## 待办` Form C ticks the checkbox + appends inline annotations.
- **No `.bak` cleanup** — sync-status doesn't garbage-collect old `.bak` files. Add `*.bak` to `.gitignore` if you don't want them committed.

## CLI reference

```
docs-cockpit sync-status [--import <file>] [--from-browser <name>] [--apply] [-c <config>]

Options:
  --import <file>       JSON exported from dashboard
  --from-browser <name> Read directly from browser profile (v0.13 · stub)
                        Choices: chrome | firefox | edge
  --apply               Write back to MD (default: dry-run, print diff only)
  -c, --config <path>   docs-cockpit.yaml path (default: ./docs-cockpit.yaml)

Exit codes:
  0  All overrides synced cleanly · no conflicts
  1  Sync ran but some subtasks conflicted (warn-level · operator review)
  2  Config / input file missing or malformed (CLI args wrong)
```
