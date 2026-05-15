---
name: docs-cockpit
description: |
  Set up and maintain a docs-cockpit — a self-contained single-HTML **dashboard** for project module / sprint / progress tracking. Aggregates a project's `docs/spec/module/*.md` + `docs/spec/concept/*.md` (driven by YAML frontmatter: id / status / sprint / progress / desc / subtasks / docs) into one `file://`-openable page with topbar, hero, KPI strip, module Kanban, Sprint Timeline, Concept Grid, and a "System Docs" drawer (CLAUDE.md / PRD / RFC index / memory / roadmap). Module cards open drawer with desc + status select + progress slider + subtask checklist (localStorage-persisted overrides) + linked-docs inline preview. Each build writes `docs/state.json` for `docs-cockpit-standup` (status narratives) and includes structured `issues[]` (referencing `docs-cockpit-author` for spec). Also handles **upgrading docs-cockpit itself** via `docs-cockpit upgrade` CLI (since 0.7.0).

  TRIGGER this skill when the user wants to (a) bootstrap a docs-cockpit dashboard for a project, (b) extend an existing config to scan new module / concept directories, (c) curate the `system_docs` list (CLAUDE.md / PRD / memory / etc), (d) wire build into pre-commit / CI to keep `docs/index.html` from going stale, (e) debug build issues (0 modules / wrong status / yaml schema errors), (f) **upgrade docs-cockpit itself** (just run `docs-cockpit upgrade` — 0.7.0+ CLI handles backend detection + atomic restart), (g) react to a "new version available" banner in build output. Common phrasings: "把项目做成 dashboard / 项目看板", "build a project progress dashboard", "搞个 module Kanban", "wire frontmatter for sprint tracking", "升级 docs-cockpit", "update docs-cockpit to the latest version".

  Do NOT trigger for: rendering a single MD file to HTML (use marked/pandoc); building a multi-page static site like Sphinx/Docusaurus/MkDocs/GitBook (different toolchain); markdown→PDF; live multi-user kanban with drag-drop (Jira/Linear/Trello). **Also do NOT trigger for**: (a) status questions about an EXISTING cockpit ("what's blocked", "sprint M1.3 progress", "weekly standup", "which modules are stalled") → use `docs-cockpit-standup`; (b) writing a single project doc (plan / RFC / spec / module MD) per the schema → use `docs-cockpit-author`; (c) fixing individual frontmatter `issues[]` reported by lint → use `docs-cockpit-author` per the suggestion + reference of each issue. The discriminator: this skill **WRITES cockpit-level config + runs the build + handles upgrade**. For status interpretation → `docs-cockpit-standup`. For authoring a single doc per the schema → `docs-cockpit-author`.
---

# docs-cockpit (operational skill · 0.9.0+)

> Turn a folder of `docs/spec/module/*.md` into a single-file project Kanban dashboard you can open with `file://`.

## Scope · what's in this skill vs the siblings (0.9.0)

The plugin ships **4 skills** as of 0.10.0 (renamed + reorganized through 0.8→0.10):

**This skill** (`docs-cockpit`) — **writes/edits cockpit-level files + runs CLI**. Setup, extend the `docs-cockpit.yaml` config, curate `system_docs`, run `build` / `migrate` / `browse` / `lint` / `portfolio`, **run `docs-cockpit upgrade`** for self-upgrade. If your action ends with the user's repo gaining or changing a yaml / HTML / hook, or you're invoking the CLI directly, you're in this skill.

**Sibling `docs-cockpit-standup`** — **reads ONE cockpit's state.json**. Answers narrative questions about a SINGLE project's state: "what's blocked", "sprint M1.3 progress", "standup for this project", "which modules are stale". If your action ends with a narrative summary about ONE project and no files change, hand off.

**Sibling `docs-cockpit-portfolio`** (NEW in 0.10.0) — **reads MULTIPLE projects' state.json via the user's portfolio registry**. Composes multi-project weekly reports with week-over-week diffs from snapshots. If the user asks for "周报" / "weekly report" / "across all my projects" / wants to add or manage the registry, hand off.

**Sibling `docs-cockpit-author`** — **writes individual project docs per the unified frontmatter spec**. Plans, RFCs, specs, individual module/concept MDs. The canonical source for frontmatter schema + body conventions + file naming + cross-doc reference rules. If `docs-cockpit lint` reported issues OR the user asks to write a new plan/RFC/spec/module MD, hand off.

## Upgrading docs-cockpit itself (folded in from old `docs-cockpit-update` skill)

When the user says "update docs-cockpit" / "升级 docs-cockpit" / "把 docs-cockpit 升到最新" / "I saw a 'new version available' banner":

```bash
docs-cockpit upgrade
```

That's the whole flow (0.7.0+). The CLI:
1. Detects backend (pip / uv / pipx / editable)
2. Compares CLI + plugin layer versions independently
3. Shows CHANGELOG diff
4. Asks confirmation
5. Runs the right upgrade command
6. Compares plugin SKILL.md hash · if changed, atomic cache-clear + ATOMIC restart prompt; else "no restart needed"

Useful flags: `--dry-run` · `--yes` · `--no-clear-cache` · `--skip-changelog`. If the user is on pre-0.7.0 and gets "unknown subcommand: upgrade", fall back to manual: `pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git` (or `uv tool upgrade` / `pipx upgrade`), then clear `~/.claude/plugins/cache/*docs-cockpit*` and restart Claude Code in **one atomic operation** (the ghost-state hazard otherwise).

**Related CLI · `docs-cockpit browse`** — when the user wants to **just read** the project's scattered MD files (no dashboard), use `docs-cockpit browse` (or `/docs-cockpit:browse`) instead. It generates a separate `docs/browse.html` with a tree-organized file browser + marked.js rendering. Use when:
- User asks to "browse / 浏览 / 预览 / 读" project docs
- Project has no `docs/spec/module/*.md` frontmatter (so dashboard would be empty) but user still wants something readable
- `docs/adrs/`, `docs/plans/`, scattered MD without frontmatter

The dashboard (`docs/index.html` from `build`) and the browser (`docs/browse.html` from `browse`) co-exist — different files, different purposes.

## First-build bootstrap (0.9.0+ · transparent CLI install)

The plugin ships markdown skills, but the actual MD → HTML build is done by the `docs-cockpit` Python CLI. The plugin assumes the user has Python 3.10+ on PATH but does NOT assume the CLI is already installed. Before invoking ANY `docs-cockpit <subcommand>` for the first time, run this preflight:

```bash
# Detect: is docs-cockpit CLI installed?
docs-cockpit --version 2>/dev/null || echo "MISSING"
```

If the output contains `MISSING`, the CLI isn't installed. Bootstrap in this priority order (pick the FIRST one that succeeds):

```bash
# 1. uv (best · isolates Python version · won't clash with system Python 3.9)
command -v uv >/dev/null && uv tool install --python 3.11 git+https://github.com/Guohao1020/docs-cockpit.git

# 2. pipx (good · isolated venv per tool)
command -v pipx >/dev/null && pipx install git+https://github.com/Guohao1020/docs-cockpit.git

# 3. pip --user (fallback · user-site · doesn't need sudo)
python3 -m pip install --user git+https://github.com/Guohao1020/docs-cockpit.git

# 4. pip (last resort · only if user explicitly OK'd it · may need sudo on system Python)
pip install git+https://github.com/Guohao1020/docs-cockpit.git
```

Tell the user briefly what you're doing — "Installing the docs-cockpit Python toolkit via uv (one-time setup)…" — don't bury this in silence. After the install, verify with `docs-cockpit --version` and proceed.

**Why bootstrap is in the skill, not the marketplace plugin spec**: Claude Code's plugin system doesn't yet ship a post-install hook that can pip-install Python packages. The skill is the workaround — first-build invocation runs the bootstrap once, then subsequent builds skip it (CLI is already on PATH).

If bootstrap fails (no Python, network blocked, write-protected /usr), surface the error verbatim and ask the user how they want to proceed (install Python? change install method? abort?). Don't paper over it — the rest of docs-cockpit won't work without the CLI.

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

**Decide first**: does the project already have `docs/spec/module/M*.md` with frontmatter (canonical layout) or NOT?

**A.1 · Project already in canonical layout** (or close):
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

**A.2 · Project uses non-canonical layout** (e.g. `docs/plans/`, `docs/adrs/`, `docs/superpowers/plans/`, scattered PRDs, no frontmatter):

This is the **common case for legacy projects**. Use the `migrate` workflow instead of hand-writing yaml:

```bash
docs-cockpit migrate                # dry-run · prints plan · no file changes
docs-cockpit migrate --apply        # execute · git mv files + inject frontmatter + write yaml
```

The migrate command:
- Auto-detects: `docs/plans/` / `docs/adrs/` / `docs/superpowers/plans/` etc → modules; `docs/PRD/` / `docs/RFC/` etc → system_docs
- Generates IDs (M01..MN) and frontmatter (id / title from H1 / status: not-started / sprint: M0)
- `git mv`'s files into `docs/spec/module/M{NN}-{slug}.md` (preserves git history)
- Writes a tailored `docs-cockpit.yaml`
- Use `--keep-originals` to copy instead of move

After migrate, you're in the A.1 state — run `docs-cockpit build` and iterate on frontmatter (status, progress, subtasks) per module.

**Always show the user the dry-run output first**, get explicit confirmation, THEN run `--apply`. Migration physically moves files.

See `commands/migrate.md` for the full slash-command spec.

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
