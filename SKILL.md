---
name: docs-cockpit
description: |
  Generate a self-contained, live HTML cockpit (single `index.html`) that aggregates MANY of a project's Markdown documents — spread across folders like `docs/PRD/`, `docs/spec/`, `docs/plan/`, `docs/RFC/`, `docs/task/`, plus root files (README, CHANGELOG, CLAUDE.md) and external paths (`~/.claude/plans/...`, session memory) — into ONE `file://`-openable preview page with sidebar nav, in-page Markdown rendering (marked.js + highlight.js via CDN), and an optional frontmatter-driven project dashboard (KPI / module kanban / sprint timeline) for documents that carry YAML headers like `status: in-progress`, `progress: 45`, `sprint: M1.2`.

  TRIGGER this skill when the user wants to bundle/aggregate/集中预览 many markdown files into a single navigable HTML page. Common phrasings include "docs dashboard", "文档看板", "项目看板", "doc cockpit", "把 MD 文档汇总成 HTML", "spec/plan/PRD 集中预览", "build docs preview", "实时同步 docs/index.html", "项目进度面板", "把 docs/ 下所有 md 做成 dashboard", "aggregate markdown into one html", "single-file offline preview of my docs", or any near-paraphrase. Also trigger when they want to (a) bootstrap such a page for a new project, (b) add a doc source / group / scan rule to an existing cockpit, (c) wire frontmatter status/progress/sprint into a kanban-by-status view, (d) change design tokens / branding for the cockpit, (e) extract a project-specific `build_docs_html.py` into a reusable tool, or (f) any docs-driven progress board where the source of truth is markdown files with YAML frontmatter.

  Do NOT trigger for: rendering a single MD file to HTML preview (too simple — use marked/pandoc directly); building a multi-page static site like Sphinx, Docusaurus, MkDocs, GitBook (different toolchain entirely); converting markdown to PDF; CI/Pages deployment workflows; live multi-user kanban boards (Jira/Linear/Trello style with drag-drop and websockets); Notion-style collaborative wikis with permissions; generic file-listing scripts; or pure "how-does-X-work" explanations of YAML/markdown/marked.js. The discriminator: many MD files → ONE static HTML file, optionally driven by their YAML frontmatter, openable with `file://`. If the shape isn't that, this isn't the skill.
---

# docs-cockpit

> Turn a folder of Markdown into a single-file project cockpit you can open with `file://`.

## What this skill is for

You're given a project with lots of Markdown documentation scattered across folders (`docs/PRD/`, `docs/spec/`, `docs/plan/`, `docs/RFC/`, `docs/task/`, `~/.claude/plans/`, root `README.md`, etc.). The user wants a **single HTML file** that, when opened in a browser, gives them:

1. A **sidebar** grouping all those MD files by category (Spec, Plan, RFC, …)
2. A **document view** that renders any MD file with marked.js
3. An optional **dashboard view** with KPI cards / kanban / sprint timeline driven by YAML frontmatter inside the MD files (e.g. `status: in-progress`, `progress: 60`, `sprint: M1.2`)
4. **Real-time sync**: when an MD file changes, re-running one build command regenerates the HTML — no service, no DB, just a static file

The whole thing is self-contained — open it from `file://`, no localhost, no build pipeline beyond Python + PyYAML. Markdown rendering happens client-side from a CDN.

## How the pieces fit together

```
project root/
├── docs-cockpit.yaml              ← user-authored config (you help write it)
├── docs/
│   ├── index.html                 ← BUILD ARTIFACT — do not hand-edit
│   ├── PRD/*.md
│   ├── spec/{concept,module}/*.md
│   ├── plan/**/*.md
│   ├── RFC/*.md
│   └── task/*.md
└── (run the build)
    python -m docs_cockpit build --config docs-cockpit.yaml
```

The build:
1. Reads `docs-cockpit.yaml`
2. For each `groups[*]`, resolves files (explicit list, dir scan, or glob)
3. Reads each MD, splits YAML frontmatter, computes mtime, runs frontmatter governance checks
4. Aggregates frontmatter into `cards` (for kanban) + `kpi` (rolled-up metrics) if `frontmatter.kanban.enabled`
5. Serializes `{groups, cards, kpi}` as JSON, embeds inside an HTML template
6. Writes `<output>` (default `docs/index.html`)

Frontend (already inside the template — you don't touch this):
- Loads marked.js + highlight.js from jsdelivr CDN
- Parses the embedded JSON payload
- Renders sidebar, dashboard, and on-click document view
- Persists last-viewed slug + view mode in `localStorage`
- Shows a CDN-failure banner if marked.js doesn't load

## When you arrive at a task

Decide which workflow you're in and skip to that section. Each one calls out which references to consult before writing code.

### Workflow A — Bootstrap a cockpit for a new project

The user has a project with `docs/` full of MD files and no cockpit yet.

1. **Look at the doc layout first.** `ls docs/` and skim a few MD files to spot natural groupings (Spec / Plan / RFC / Task / etc.). Also check for `README.md`, `CHANGELOG.md`, `CLAUDE.md` at root — these usually belong in an "Overview" group.
2. **Ask about frontmatter.** If MD files already have YAML frontmatter with fields like `status` / `progress` / `sprint`, the kanban view will work out of the box. If not, ask the user whether they want kanban enabled — if yes, point them at `references/frontmatter_conventions.md` and offer to seed a few files. If no, just leave `frontmatter.kanban.enabled: false`.
3. **Author `docs-cockpit.yaml`.** Start from `examples/minimal.yaml` and grow. Use `scan:` blocks when a directory has many files; use explicit `files:` when each entry is hand-picked.
4. **Run the build.**
   ```bash
   python -m docs_cockpit build --config docs-cockpit.yaml
   ```
   Open the resulting HTML and verify the sidebar populates and at least one doc renders.
5. **Wire it into the workflow.** Tell the user about the forcing-function pattern: any PR that changes MD must re-run the build and commit the regenerated `docs/index.html` in the same commit. This is what makes the cockpit a real "live" view instead of going stale.

### Workflow B — Add a new doc source to an existing cockpit

User says "I just added `docs/runbook/` with a bunch of MD — show those in the sidebar too" or similar.

1. Open `docs-cockpit.yaml`, find the most similar existing group, and add a new entry under `groups:`.
2. Prefer `scan:` over explicit `files:` whenever the directory will keep growing — saves the user from re-editing the config every time they add a doc.
3. Re-run the build. Done.

### Workflow C — Just rebuild after MD changes

This is the daily-driver path. One command, no config edits:

```bash
python -m docs_cockpit build --config docs-cockpit.yaml
```

The build is idempotent and fast (no network during build — CDN only loads when a human opens the HTML). If the user has a pre-commit hook or CI step, plug this command into it.

### Workflow D — Customize design / branding

User wants to change the primary color, swap the wordmark glyph, replace the footer columns, or theme the page to match a different design system.

1. Read `references/design_tokens.md` to see which tokens are exposed via the `design:` block in the config.
2. Edit `docs-cockpit.yaml`. Anything not overridden falls back to the built-in HP-style defaults (clean white canvas + blue primary + ink sidebar).
3. For deeper changes (new section in the dashboard, custom card layouts), the template lives at `docs_cockpit/templates/index.html.tmpl`. Edit it directly. Keep the `__BUILD_TIME__` / `__DOCS_JSON__` / `__PROJECT_*__` placeholders intact — the renderer substitutes those.

## Quick config reference

```yaml
project:
  name: MyProject
  subtitle: Docs preview
  glyph: M                                # single char in the wordmark square
  description: One-line tagline for footer
  output: docs/index.html                 # relative to config file

paths:
  repo: "."                               # default; everything resolves from here
  # Auto-available: {home}, {env:VAR}, {main_repo} (worktree-aware)

groups:
  - name: Overview
    icon: O
    color: primary
    files:
      - {title: README, path: "{repo}/README.md"}
      - {title: CHANGELOG, path: "{repo}/CHANGELOG.md"}

  - name: Spec · Modules
    icon: "6"
    color: primary
    scan:
      dir: "{repo}/docs/spec/module"
      title_transform: prefix-dot-titlecase   # M01-foo-bar → M01 · Foo Bar

  - name: Plans
    icon: P
    color: graphite
    scan:
      dir: "{repo}/docs/plan"
      recursive: true                     # nested dirs included
      title_transform: path-slash         # subdir / stem

  - name: External roadmap
    icon: R
    color: storm-deep
    glob:
      - "{home}/.claude/plans/myproject/**/*.md"

frontmatter:
  enabled: true                           # parse YAML frontmatter
  kanban:
    enabled: true                         # show dashboard view
    card_types: [module, concept, task]   # only these `type:` values become cards
    kpi_type: module                      # KPI summary aggregates this type
    sprint_order: [M0, M1, M2, M3, GA]    # order for the timeline; unknowns sort last

design:                                    # all optional — see references/design_tokens.md
  primary: "#024ad8"
  primary_deep: "#0e3191"
  # ... or leave the whole block out for HP-style defaults
```

Full reference with every option: see `references/config_reference.md`.

## Frontmatter conventions (only if kanban enabled)

Each MD file that should appear as a kanban card needs YAML frontmatter at the top:

```markdown
---
id: M07
type: module
title: Job-Task FSM
status: in-progress     # not-started | planned | in-progress | blocked | done | deferred
progress: 45            # 0-100; must match status range (see frontmatter_conventions.md)
sprint: M1.2
prd_ref: §6.3.7
owner: harvey
depends_on: [M04, M06]
blocks: [M08]
updated_at: 2026-05-14
---

# document body…
```

Files without an `id` field are still indexed in the sidebar but don't appear as cards. This is intentional — README, governance docs, design system pages aren't "trackable work items".

Status / progress mismatches surface as build warnings (e.g. `progress=80 out of range [0,15] for status=planned`) but never block the build — partial truth is better than no truth.

Full schema and rationale: see `references/frontmatter_conventions.md`.

## Common failure modes (and what they mean)

- **`[WARN] 0 docs exist`** → all paths in the config resolved to nonexistent files. Almost always a `paths.repo` mismatch or you ran the build from a worktree without `{main_repo}` resolution. Run with `--debug` to print every resolved path.
- **Sidebar shows `missing` chips next to entries** → the doc was listed but the file isn't there. Either delete the entry from the config or create the file. Missing docs render a friendly placeholder inside the document view; they don't crash the build.
- **CDN failure banner in the rendered HTML** → user is offline or behind a firewall that blocks jsdelivr. Document view falls back to raw `<pre>` MD. For an offline-first deployment, see `references/design_tokens.md` → "Offline / vendored mode".
- **Frontmatter warnings spamming the console** → the `status` ⇄ `progress` ranges are tighter than the user's actual usage. Either fix the MD files or relax the ranges under `frontmatter.status_progress_ranges` in the config.
- **YAML config rejects with `unknown key`** → the config loader uses strict matching. Typo in a key, or a feature that's not implemented yet. Check spelling against `references/config_reference.md`.

## References — read these when…

- **`references/config_reference.md`** — when authoring or extending the YAML config, especially the `groups` / `frontmatter` / `design` blocks. Open this any time you're about to write more than a single `scan:` entry.
- **`references/frontmatter_conventions.md`** — when enabling kanban for the first time, or when the user asks why a doc didn't show up as a card. Includes the status / progress validation table.
- **`references/design_tokens.md`** — when the user wants brand/theme changes, or when something looks wrong in the rendered HTML. Lists every CSS variable the template exposes, the default color tokens, and how to vendor marked.js / highlight.js for offline mode.

## Examples — clone-and-edit starting points

- **`examples/minimal.yaml`** — smallest workable config: one group, a couple of files, no kanban. Good for "I have a tiny `docs/` and just want a sidebar".
- **`examples/full.yaml`** — comprehensive reference config: 10 groups, mix of explicit files + dir scans + globs into `~/.claude/plans/`, kanban enabled with PRD-driven module statuses. Reference this when you're scaling a real project up.

## The forcing function (worth surfacing to the user)

The cockpit is only useful if it stays fresh. The pattern that's been battle-tested:

> Any PR that touches MD files must re-run `python -m docs_cockpit build` and commit the regenerated HTML in the same commit. PRs without this update don't merge.

This isn't enforced by the skill — it's a team convention. But if the user asks "how do I make sure people don't forget", suggest one of:

- A `pre-commit` hook that runs the build and stages the HTML
- A CI step that runs the build and fails if `docs/index.html` is dirty
- A simple paragraph in CONTRIBUTING.md / CLAUDE.md spelling out the rule

The lowest-friction starting point is option 3.
