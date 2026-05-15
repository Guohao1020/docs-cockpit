---
name: docs-cockpit
description: |
  Set up and maintain a docs-cockpit — a self-contained single-HTML **dashboard** for project module / sprint / progress tracking. Aggregates a project's `docs/spec/module/*.md` + `docs/spec/concept/*.md` (driven by YAML frontmatter: id / status / sprint / progress / desc / subtasks / docs) into one `file://`-openable page with topbar, hero, KPI strip, module Kanban, Sprint Timeline, and Concept Grid. System docs (CLAUDE.md / DESIGN.md / PRD / RFC index / memory / roadmap) appear in a separate "系统文档" drawer. Module cards open drawer with desc + status select + progress slider + subtask checklist (localStorage-persisted overrides). Each build also writes `docs/state.json` for the sibling `docs-cockpit-status` skill.

  TRIGGER this skill when the user wants to (a) bootstrap a docs-cockpit dashboard for a project, (b) extend an existing config to scan new module / concept directories, (c) wire frontmatter status / progress / sprint / desc / docs / subtasks conventions so modules show up as cards, (d) curate the `system_docs` list (CLAUDE.md / PRD / memory / etc), (e) wire build into pre-commit / CI to keep `docs/index.html` from going stale, (f) debug build issues (0 modules / wrong status / frontmatter warnings / yaml schema errors). Common phrasings: "把项目做成 dashboard / 项目看板", "build a project progress dashboard", "搞个 module Kanban", "agg my spec/module mds into one HTML", "wire frontmatter for sprint tracking", or any near-paraphrase that involves SETTING UP or MAINTAINING the cockpit itself.

  Do NOT trigger for: rendering a single MD file to HTML (use marked/pandoc); building a multi-page static site like Sphinx/Docusaurus/MkDocs/GitBook (different toolchain); markdown→PDF; live multi-user kanban with drag-drop (Jira/Linear/Trello); Notion-style collaborative wikis. **Also do NOT trigger for status questions about an EXISTING cockpit** — phrasings like "what's blocked", "sprint M1.3 progress", "weekly standup from the cockpit", "which modules are stalled" go to the SIBLING skill `docs-cockpit-status`. The discriminator: this skill **WRITES** project files (yaml / MD frontmatter / runs build); `docs-cockpit-status` only **READS** `docs/state.json` to interpret status. If the user wants to change the cockpit → this skill. If the user wants to be told what the cockpit currently says → the sibling.
---

# docs-cockpit (operational skill · 0.2.0+)

> Turn a folder of `docs/spec/module/*.md` into a single-file project Kanban dashboard you can open with `file://`.

## Scope · what's in this skill vs the siblings

**This skill** (`docs-cockpit`) — **writes/edits** project files. Setup, extend modules / concepts, wire frontmatter, debug. If your action ends with the user's repo gaining or changing a yaml / MD / HTML / hook, you're in this skill.

**Sibling `docs-cockpit-status`** — **reads only**. Answers questions about an existing cockpit's state: "what's blocked", "sprint M1.3 progress", "weekly standup", "which modules are stale". If your action ends with a narrative summary back to the user and no files change, hand off.

**Sibling `docs-cockpit-update`** — **handles upgrades**. Triggers when the user asks to update / upgrade docs-cockpit, OR when a `docs-cockpit build` run prints a banner like `[!] docs-cockpit X.Y.Z available (current: …)`. **If you see such a banner in build output, surface it to the user and hand off** — don't try to limp along with a stale install.

## What this skill is for

The user has a project with structured docs under `docs/spec/module/M*.md` (and optionally `docs/spec/concept/C*.md`). Each module MD carries YAML frontmatter with `id`, `status`, `sprint`, `progress`, and (in 0.2.0+) `desc`, `docs`, `subtasks`. You produce **ONE** HTML file that gives the user:

1. **Topbar** with project brand + last build time + "系统文档" drawer button
2. **Hero** with project name + tagline + overall % gauge
3. **KPI strip** — total modules / done / in-progress+planned / not-started+blocked
4. **Module Kanban** — 5 status columns; click a card → drawer with desc / status / progress slider / subtask checklist
5. **Sprint Timeline** — modules grouped by sprint with avg %
6. **Concept Grid** — concept cards at bottom (simpler · just id/title/status/sprint/progress)
7. **System Docs Drawer** — curated list (CLAUDE.md / PRD / memory / etc) accessed via topbar button

The whole thing is self-contained — open it from `file://`, no localhost, no build pipeline beyond Python + PyYAML. Markdown rendering via marked.js / highlight.js is **not used in 0.2.0** (modules don't show MD body — they show structured frontmatter data in drawers).

## How the pieces fit together

```
project root/
├── docs-cockpit.yaml              ← user-authored config (you help write it)
├── docs/
│   ├── index.html                 ← BUILD ARTIFACT — human-facing dashboard
│   ├── state.json                 ← BUILD ARTIFACT — machine-readable, read by docs-cockpit-status
│   ├── spec/
│   │   ├── module/M*.md           ← modules (frontmatter-driven cards)
│   │   └── concept/C*.md          ← concepts (simpler cards)
│   ├── PRD.md / PRD/*.md          ← system docs (curated · not auto-scanned)
│   └── RFC/                        ← typically a system_docs entry pointing here
├── CLAUDE.md                       ← typically a system_docs entry
└── (run the build)
    docs-cockpit build              # or python -m docs_cockpit build
```

The build:
1. Reads `docs-cockpit.yaml`
2. **system_docs**: pass-through with path-variable expansion (no MD scanning)
3. **modules / concepts**: scan/glob/files → read each MD → extract frontmatter → build cards
4. Serializes `{project, systemDocs, modules, concepts}` as JSON, embeds in HTML template
5. Writes `<output>` (default `docs/index.html`) — human-facing
6. Writes `<output_dir>/state.json` — same payload + warnings, for `docs-cockpit-status` to read

## When you arrive at a task

Decide which workflow you're in and skip to that section.

### Workflow A — Bootstrap a cockpit for a new project

1. **Look at the doc layout.** `ls docs/` and skim a few MD files. Identify:
   - **modules** (typically `docs/spec/module/` or similar)
   - **concepts** (typically `docs/spec/concept/`)
   - **system docs to surface** (CLAUDE.md, README, PRD, DESIGN.md, RFC index, memory dir, roadmap dir)
2. **Check frontmatter.** Do the module MDs already have `id` + `status` + `sprint` + `progress`? If yes, cards will populate automatically. If no, point user at `references/frontmatter_conventions.md` and offer to seed a few files.
3. **Author `docs-cockpit.yaml`.** Start from `docs_cockpit/examples/minimal.yaml` and grow. Use `scan:` blocks for module/concept dirs; hand-list `system_docs:` entries.
4. **Run the build.**
   ```bash
   docs-cockpit build --config docs-cockpit.yaml
   ```
   Open the resulting HTML. Verify modules appear in Kanban, concept grid populates, system docs drawer shows the curated entries.
5. **Wire it into the workflow.** Tell the user about the forcing-function pattern: PR-touching-MD must re-run `docs-cockpit build` and commit the regenerated HTML. This is what keeps the dashboard "live".

### Workflow B — Extend / migrate a config

User says "add new modules from `docs/spec/m2/`" or "this is 0.1.x · migrate to 0.2.0":

1. **For new scan paths**: append a glob/scan to existing `modules:` or `concepts:` block.
2. **For 0.1.x → 0.2.0 migration**: see migration table in `references/config_reference.md`:
   - `project.glyph` → `project.mark`
   - `groups[] (with type: module)` → top-level `modules:`
   - `groups[] (with type: concept)` → top-level `concepts:`
   - `groups[] (other)` → flatten into `system_docs:` (need `{id, title, path, desc, icon}` per entry)
   - `frontmatter.kanban.*` → mostly removed in 0.2.0
3. Re-run build, verify.

### Workflow C — Just rebuild after MD changes

```bash
docs-cockpit build --config docs-cockpit.yaml
```

Idempotent. Plug into pre-commit or CI to keep `docs/index.html` and `docs/state.json` fresh.

### Workflow D — Add subtasks / desc / docs links to a module

User says "M07 needs subtasks" or "fill in the desc for these modules":

1. Open the MD file (e.g. `docs/spec/module/M07-job-fsm.md`)
2. Edit the frontmatter to add:
   ```yaml
   desc: "12 类 FSM · 含字段校验"
   docs:
     - { title: "Schema 设计文档", path: "docs/design/schemas.md" }
   subtasks:
     - { title: "核心实体定义", done: true }
     - { title: "字段校验", done: false }
   manualProgress: false        # auto-derive progress from subtasks
   ```
3. Re-run build. Subtask completion ratio auto-populates the progress bar.

## Quick config reference

```yaml
project:
  name: MyProject
  mark: M                          # single-char wordmark
  tagline: "项目进度概览"            # hero subtitle
  eyebrow: "DASHBOARD"             # hero topline
  output: docs/index.html

paths:
  repo: "."
  # Auto-available: {home}, {env:VAR}, {main_repo} (worktree-aware)

system_docs:
  - id: claude-md
    title: CLAUDE.md
    path: "{repo}/CLAUDE.md"
    desc: 项目根级 AI 协作约定
    icon: memory                   # memory | design | plan | doc
  - id: prd
    title: PRD.md
    path: "{repo}/docs/PRD.md"
    desc: 产品需求文档
    icon: doc

modules:
  scan:
    dir: "{repo}/docs/spec/module"
    title_transform: prefix-dot-titlecase

concepts:
  scan:
    dir: "{repo}/docs/spec/concept"
    title_transform: prefix-dot-titlecase

frontmatter:
  enabled: true
  status_progress_ranges:
    not-started: [0, 0]
    planned: [0, 15]
    in-progress: [5, 95]
    blocked: [0, 100]
    done: [100, 100]
    deferred: [0, 100]
```

Full reference: `references/config_reference.md`. Frontmatter field reference: `references/frontmatter_conventions.md`.

## Common failure modes

- **`[WARN] 0 items` after build** → all paths resolved to nonexistent files. Almost always `paths.repo` wrong or scan dir typo. Run with `--debug` to print resolved vars.
- **Modules don't appear in Kanban** → MD missing `id:` in frontmatter, OR id is a template placeholder like `MXX` (those are skipped by design).
- **`progress=80 out of range [0,15] for status=planned`** → status / progress mismatch. Either fix the MD or relax the ranges under `frontmatter.status_progress_ranges`.
- **Subtask toggles don't persist** → that's localStorage. Open the SAME `file://` URL again (re-opening with a fresh path won't carry overrides).
- **CDN font fails (no Inter loaded)** → marked.js/highlight.js are no longer used in 0.2.0; only Google Fonts loads externally. If user wants fully offline, suggest vendoring Inter + JetBrains Mono fonts (future feature).

## References — read these when…

- **`references/config_reference.md`** — when authoring or extending the YAML config. Open any time you're about to write more than a single `scan:` entry.
- **`references/frontmatter_conventions.md`** — when wiring module frontmatter, especially desc / docs / subtasks fields (new in 0.2.0). Includes status / progress validation table + subtask auto-progress calculation.

## Examples — clone-and-edit starting points

- **`docs_cockpit/examples/minimal.yaml`** — smallest workable 0.2.0 config: project + 1 system_doc + modules scan. Good starting point.
- **`docs_cockpit/examples/full.yaml`** — comprehensive reference config: full project meta + multi-entry system_docs + modules + concepts + frontmatter governance. (Bundled inside the package so `docs-cockpit init` finds it post-pip-install.)

## The forcing function (worth surfacing to the user)

The cockpit is only useful if it stays fresh. Pattern:

> Any PR touching a module MD must re-run `docs-cockpit build` and commit the regenerated `docs/index.html` + `docs/state.json`.

If user asks how to enforce: pre-commit hook OR CI step OR CONTRIBUTING line — see README "Daily workflow" section for templates.
