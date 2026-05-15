---
name: docs-cockpit-portfolio
description: |
  Produce **multi-project weekly reports** by reading the user's portfolio registry (`~/.docs-cockpit/projects.yaml`) and aggregating across multiple docs-cockpit projects. Compares each project's current `state.json` against a snapshot ~7 days old to compute "what changed this week" (newly done modules, newly blocked, progress jumps, new modules, new frontmatter issues). Composes a single Markdown report with cross-project KPI header + per-project sections + cross-project highlights.

  TRIGGER this skill aggressively for ANY of these — it's the only skill that can answer cross-project questions, so triggering it is almost always right when the user is in "portfolio mode":
  (a) the user asks for a "weekly report" / "周报" / "出周报" / "weekly status" / "this week's update" — especially WITHOUT specifying a project, OR specifying multiple projects;
  (b) the user asks about progress / status across multiple projects ("how are all my projects going", "what's blocked across everything", "项目们最近怎么样", "harvey 这周做了啥");
  (c) the user is in their `~/` or a parent directory (no `docs-cockpit.yaml` in CWD) and asks status questions — they almost certainly want portfolio-level answers, not "scan some unrelated repo";
  (d) the user asks to set up or manage the portfolio ("add this project to my portfolio", "register this for weekly reports", "list my tracked projects", "什么是 portfolio");
  (e) the user explicitly invokes `/docs-cockpit:weekly` or `docs-cockpit portfolio` CLI commands.

  Do NOT trigger for: single-project status questions where the user is clearly in one project's directory or names a specific project ("what's blocked in Sourcery") → that's `docs-cockpit-standup`. Configuring a single project's `docs-cockpit.yaml` → `docs-cockpit` skill. Writing a new plan / RFC / spec → `docs-cockpit-author`. The discriminator: this skill operates on the **portfolio registry**, reads MULTIPLE `state.json` files, and computes week-over-week diffs. If you're only touching one project, hand off to `docs-cockpit-standup`.
---

# docs-cockpit-portfolio (0.10.0+)

> Read the user's portfolio registry. Compose cross-project weekly reports. Compute week-over-week diffs from snapshots.

## Scope · what's in this skill vs the siblings

| Skill | When |
|---|---|
| **`docs-cockpit-portfolio`** (this one) | Multi-project. Reads `~/.docs-cockpit/projects.yaml`. Diffs against snapshots. Composes weekly reports across N projects. |
| **`docs-cockpit-standup`** | Single project. Reads one `state.json`. Narrative answer for "what's blocked / sprint progress / standup" within one project. |
| **`docs-cockpit`** | Setup + maintain a single cockpit. Writes config / runs `build` / `migrate` / `browse` / `upgrade`. |
| **`docs-cockpit-author`** | Writes a single project doc (plan / RFC / spec) per the canonical schema. |

**Discriminator:** does the user want answers spanning >1 project, OR is it ambiguous which project they mean? → this skill. Single named project + clearly in that project's directory → `docs-cockpit-standup`.

When in doubt, run `docs-cockpit portfolio list` first. If it shows ≥2 projects AND the user's question doesn't single one out, this skill is the right answer.

## Data sources

This skill operates on three files/directories under `~/.docs-cockpit/`:

```
~/.docs-cockpit/
├── projects.yaml                  ← registry (managed by `docs-cockpit portfolio` CLI)
└── snapshots/
    ├── <project-name>/
    │   ├── 2026-05-01.json        ← snapshot copies of state.json (taken weekly)
    │   ├── 2026-05-08.json
    │   └── 2026-05-15.json
    └── <other-project>/
```

### Registry schema (`projects.yaml`)

```yaml
projects:
  - name: Sourcery
    state: D:/harvey_work/Sourcery/docs/state.json
    repo:  D:/harvey_work/Sourcery
    tags:  [active, work]
    added: 2026-05-15
  - name: Bastion
    state: D:/shulex_work/bastion/docs/state.json
    repo:  D:/shulex_work/bastion
    tags:  [active, work]
    added: 2026-04-22
```

If the file doesn't exist (no registered projects yet), tell the user: "no portfolio registered yet · run `docs-cockpit portfolio add` in each project directory, then ask me for a weekly report again". Don't try to scan for projects yourself — the registry is the user's curated list.

## Workflow

### Step 1 · Load the registry

```bash
docs-cockpit portfolio list
```

The output shows: project name · tags · last build time (with `⚠️` if >7 days stale). If the user is asking about a weekly report and any project shows `⚠️ stale`, surface it: "Bastion's last build was 12 days ago — its data may be out of date; want me to skip it, include it as-is, or remind you to rebuild?"

### Step 2 · Present numbered list and ask the user to pick

Show the projects as a numbered list with a one-line current-state summary each — enough for the user to recognize which to include:

```
Which projects to include in this week's report?

  1. Sourcery       · 24 modules · 1 done · 5 in-progress · last built 1d ago
  2. Bastion        · 49 modules · 24 done · 11 in-progress · last built 0d ago
  3. internal-tool  · 8 modules · 3 done · 2 in-progress · last built 8d ago ⚠️

Reply with: numbers ("1,3"), names ("Sourcery, Bastion"), or "all" / "active".
```

The user picks via:
- Comma-separated numbers — `1,3`
- Comma-separated names — `Sourcery, Bastion`
- `all` — every project
- `active` (or any tag) — projects with that tag

If the user is silent or says "全部" / "default", treat as `all`.

### Step 3 · For each picked project, load current state + nearest snapshot

For each project:

1. Read current `state.json` (the path from registry)
2. Look in `~/.docs-cockpit/snapshots/<project-name>/` for the most recent snapshot whose date is **≥ 5 days old AND ≤ 14 days old**. This is "what was the state ~1 week ago". The 5-14 day band tolerates inconsistent snapshot cadence — exact 7 days isn't always available.
3. If no snapshot in that band exists, note it: "no week-old snapshot for X yet · this is the first weekly · run `docs-cockpit portfolio snapshot` weekly to enable diff next time". For first-week projects, the section just shows current state (no diff).

### Step 4 · Compute the diff (when both snapshots available)

For each project where both current state and a prior snapshot exist, compare `modules[]` by `id` and emit:

| Change kind | How to compute |
|---|---|
| **Newly done** | `status` was anything else → now `done` |
| **Newly blocked** | `status` was anything else → now `blocked` |
| **Newly added** | `id` not in prior snapshot, in current |
| **Removed** | `id` in prior, not in current |
| **Progress jumps** | `|current.progress - prior.progress| ≥ 15` AND not newly-done (which is its own bucket) |
| **Sprint move** | `sprint` field changed |
| **Subtask shifts** | Count `subtasks[*].done` changed by ≥ 2 between snapshots |

The 15-point progress threshold filters noise — a module ticking from 60→62 isn't "this week's news".

### Step 5 · Compose the report

Use this exact structure (humans will skim it):

```markdown
# 周报 · <YYYY-MM-DD> · <N> projects

**Aggregate**: <total-modules> modules across <N> projects · <total-done> done · <total-in-progress> in-progress · <total-blocked> blocked · overall progress <weighted-avg>%

---

## <Project Name 1>

**Last build**: <date> (<age>d ago) · **Sprint**: <current-sprint(s)> · **Progress**: <overall>%

### 🚀 Wins this week
- <Newly-done modules with their previous status/progress shown>

### 🔥 Blockers
- <status=blocked modules · plus blocks/depends_on graph if revealing>

### 📋 In flight
- <in-progress modules with current progress>

### 📈 Progress this week
- <progress jumps · "M07 30%→55%" style>

### 🆕 Added this week
- <new modules added since last snapshot>

### 🥶 Stale (>30d untouched)
- <modules whose mtime is >30 days old · skip if empty>

### ⚠️ Frontmatter issues
- <count of error/warn/hint from state.json `issues[]` · point at lint for detail>

---

## <Project Name 2>
... (same structure)

---

## Cross-project highlights

- <patterns spanning projects · e.g. "Both Sourcery and Bastion shipped 2 modules this week">
- <dependencies between projects if user has annotated them via tags · skip if not obvious>
- <suggested focus for next week based on blockers · 1-2 bullets max>
```

Match emoji + section headers exactly · users grep their old reports for these.

### Step 6 · When done

End the report with a footer:

```
---
_Generated by docs-cockpit-portfolio · diff window: <oldest-snapshot-date> → today · run `docs-cockpit portfolio snapshot` weekly to keep diffs accurate._
```

If the user has any project without a snapshot, add a hint to that footer:
```
_Tip: run `docs-cockpit portfolio snapshot` to capture today's state and enable week-over-week diff next time._
```

## Edge cases

- **No portfolio yet** → tell user the registry is empty; suggest `docs-cockpit portfolio add` in each project root after `docs-cockpit build`. Do NOT try to scan filesystem yourself.
- **All snapshots missing for a project** → include the project's current-state section but skip the diff section · note it inline.
- **Snapshot exists but state.json is stale (>14d since last build)** → warn in that project's section: "data is from <date> · last 14 days of activity not visible · run `docs-cockpit build` to refresh".
- **User asks "show me only blockers across projects"** → use the same workflow but skip non-blocker sections in the output. Customize, don't force the full template.
- **User asks for a single project after the picker** → hand off to `docs-cockpit-standup` (don't run the multi-project flow with N=1).
- **Project paths reference UNC / WSL / cross-mount** — the registry stores absolute paths; respect them as-is. If `state.json` can't be read, surface the path error verbatim.

## Tooling interop

The portfolio CLI commands are the source of truth — `docs-cockpit portfolio add/list/remove/tag/snapshot`. Read `~/.docs-cockpit/projects.yaml` directly if you need to introspect; write via the CLI to avoid corrupting the file format.

When the user asks to add/remove/tag projects, prefer the CLI commands over hand-editing the YAML — the CLI normalizes paths, validates state.json presence, and uses `yaml.safe_dump` so formatting stays consistent.

## Quick examples

**Example 1** — "出本周周报":

1. Run `docs-cockpit portfolio list`
2. Show numbered picker
3. User picks `all`
4. For each project, load state.json + nearest snapshot
5. Compose report per template
6. Note if any project lacks snapshot

**Example 2** — "what's blocked across everything":

1. Run `docs-cockpit portfolio list`
2. Skip the picker (treat as `all` since user asked "everything")
3. For each project, filter `modules[]` to `status=blocked`
4. Output a compact table: Project / Module / Sprint / Blocks / Depends-on
5. Skip the weekly diff (user didn't ask for "this week")

**Example 3** — "add this project to my portfolio" while in a project directory:

1. Recognize the user wants `docs-cockpit portfolio add`
2. Run that command in the current directory
3. Show the result (or error: "no state.json yet — run `docs-cockpit build` first")
4. Confirm with `docs-cockpit portfolio list` afterwards
