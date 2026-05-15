**English** · [中文](README.zh-CN.md)

# docs-cockpit

Turn a folder of project markdown files into a single-HTML **Kanban dashboard** + **tree-sidebar reader** you can open with `file://`. Frontmatter-driven, schema-validated, AI-editor-friendly. Ships as a standalone Python CLI **and** a Claude Code plugin (3 auto-triggered skills + 6 slash commands).

> Build a docs cockpit for any project in one command. Your modules become a Kanban with sprint timeline, KPI bar, and per-module drawer (status / progress / subtasks / linked docs). The frontmatter validator tells you exactly what's missing and how to fix it. The empty-docs CTA generates a ready-to-paste prompt for your AI coding editor (Claude Code, Cursor, Codex, Continue, Aider, …) to write the plan / RFC / spec for you.

## Quickstart

### As a Claude Code plugin (recommended · 60 seconds)

```bash
# inside Claude Code
/plugin marketplace add Guohao1020/docs-cockpit
/plugin install docs-cockpit@docs-cockpit
```

The 3 skills auto-trigger on natural-language requests. The 6 slash commands give you explicit invocation surfaces:

```
/docs-cockpit:build     # generate docs/index.html
/docs-cockpit:browse    # generate docs/browse.html (tree-sidebar MD reader)
/docs-cockpit:migrate   # one-shot legacy-layout migration
/docs-cockpit:status    # narrative standup report from state.json
/docs-cockpit:lint      # validate frontmatter against the author spec
/docs-cockpit:update    # delegate to `docs-cockpit upgrade` CLI
```

### As a standalone CLI (no Claude Code)

Pick the install backend you already use (Python 3.10+ required):

```bash
# uv (recommended · isolates Python version)
uv tool install --python 3.11 git+https://github.com/Guohao1020/docs-cockpit.git

# pip
pip install git+https://github.com/Guohao1020/docs-cockpit.git

# pipx
pipx install git+https://github.com/Guohao1020/docs-cockpit.git
```

Then:

```bash
cd your-project
docs-cockpit init          # writes a minimal docs-cockpit.yaml
docs-cockpit build         # generates docs/index.html + docs/state.json
open docs/index.html
```

## How it works

You point `docs-cockpit` at your project's YAML config and it walks the `modules/` and `concepts/` directories you list. Each markdown file's YAML frontmatter (`id` / `status` / `sprint` / `progress` / `desc` / `subtasks` / `docs:` …) is read and turned into one card. The build serializes everything into a JSON payload, embeds it in an HTML template, and writes a self-contained single file you can open with `file://` — no localhost, no static-site generator, no JS framework, no network call at runtime.

`docs-cockpit build` writes two artifacts side-by-side: `docs/index.html` for humans, `docs/state.json` for tools (skills read it for narrative status answers; CI reads it for invariant checks). The `state.json` also carries `issues[]` from the **frontmatter validator** — every issue points at the exact field, gives a fix suggestion, and references the section of the unified **docs-cockpit-author** spec that defines what's correct.

When a module has no `docs:` linkage yet, the drawer shows a **copy-prompt CTA**: pick `Plan` / `RFC` / `Spec`, see the full prompt rendered inline with your module's id / title / status / sprint / desc / body excerpt all substituted in, then click Copy and paste into your AI coding editor of choice. The prompts reference docs-cockpit-author so the AI writes frontmatter that the dashboard will pick up on the next build.

## The Basic Workflow

1. **Bootstrap** — `docs-cockpit init` or, for legacy projects with `docs/plans/`, `docs/adrs/`, `docs/RFC/` already in flight, `docs-cockpit migrate`. The latter dry-runs first, shows what it'll move where, then `--apply` does `git mv` + injects frontmatter scaffolds.

2. **Author docs** per the **docs-cockpit-author** skill (the canonical schema). Required fields, status enum, status × progress invariants, file naming, the "docs vs subtasks" decision, cross-doc references — all in one place. The author skill auto-triggers when you ask Claude to write a plan / RFC / spec / module-MD.

3. **Build the dashboard** — `docs-cockpit build`. Open `docs/index.html` in the browser. Module Kanban renders, click any card → drawer shows desc / status select / progress slider / subtask checklist / linked docs with **inline MD preview** (marked.js renders the doc inside the drawer · no jumping to file:// raw view).

4. **Track status** by asking Claude natural-language questions ("what's blocked", "sprint M1.2 progress", "give me a weekly standup"). The `docs-cockpit-standup` skill reads `state.json` and produces tables / bullet lists / paste-ready Markdown reports. **Read-only by design** — never edits files.

5. **Lint before commit** — `docs-cockpit lint` runs the validator without rebuilding. Output is structured:

   ```
   ❌ M07.md · id: missing required field — module won't appear in dashboard
      💡 fix: add `id: M07` to frontmatter
      📚 see: docs-cockpit-author · §2.1 required frontmatter
   ```

   Three severities: `error` (won't render at all), `warn` (renders with broken state), `hint` (polish · adds context for the copy-prompt feature). `--json` for IDE / CI consumption, `--strict-warn` to treat warnings as failures.

6. **Upgrade** — `docs-cockpit upgrade`. One command detects your install backend (pip / uv / pipx / editable), compares CLI + plugin layer versions, fetches CHANGELOG diff, asks confirmation, runs the right upgrade command, and if the plugin SKILL.md changed, atomically clears cache + prompts restart. No more "ghost state" from forgetting to restart.

## What's Inside

### Skills (auto-triggered)

| Skill | Purpose | Read or Write |
|---|---|---|
| **`docs-cockpit`** | Setup + maintain the cockpit · run `build` / `migrate` / `browse` / `upgrade` | writes config + HTML + runs CLI |
| **`docs-cockpit-author`** (new in 0.9.0) | Canonical spec for writing a single module / concept / plan / RFC / spec — frontmatter schema, body conventions, file naming, cross-doc refs | writes individual project docs |
| **`docs-cockpit-standup`** (renamed from `-status` in 0.9.0) | Read `state.json` and produce narrative status reports, sprint progress, blockers, weekly standup | read-only |

### Slash commands

```
/docs-cockpit:build       build dashboard from YAML config
/docs-cockpit:browse      generate tree-sidebar MD reader
/docs-cockpit:migrate     migrate legacy layout (docs/plans/, docs/adrs/, …) to canonical
/docs-cockpit:status      narrative status / standup report
/docs-cockpit:lint        validate frontmatter without building
/docs-cockpit:update      delegate to `docs-cockpit upgrade` CLI
```

### CLI subcommands

```
docs-cockpit init         scaffold docs-cockpit.yaml
docs-cockpit build        build single-file dashboard + state.json
docs-cockpit browse       generate tree-sidebar MD reader
docs-cockpit migrate      migrate legacy layout (dry-run first · --apply commits)
docs-cockpit lint         validate frontmatter (--json · --strict-warn)
docs-cockpit upgrade      one-command CLI+plugin upgrade (--dry-run · --yes)
```

### Dashboard features

- **Module Kanban** — 5 status columns · click a card → drawer with desc / status select / progress slider / subtask checklist / linked docs · localStorage-persisted overrides
- **Sprint Timeline** — modules grouped by sprint with avg %
- **Concept Grid** + **System Docs Drawer** — curated entries (CLAUDE.md / PRD / DESIGN / RFC / memory / roadmap) one click away
- **Auto body extraction** — `## 待办` / `## TODO` checklists become subtasks · `## Related` / `## 关联` link-lists become `docs:` · no frontmatter duplication
- **Subtask → auto progress** — `manualProgress: false` derives progress from done-ratio
- **Inline MD preview in drawer** (0.7.1+) — click a linked doc · renders with marked.js + highlight.js inside the drawer · "Back to module" returns to the card view
- **Empty-docs Copy-Prompt CTA** (0.8.0+ · reworked in 0.9.0) — `Plan` / `RFC` / `Spec` tabs · inline prompt preview · one Copy button · paste into Claude Code / Cursor / Codex / Continue / Aider
- **needs-docs kanban chip** — active modules without docs are flagged on the card so you can see at a glance what needs filling in
- **Frontmatter validator** (0.9.0+) — structured `error` / `warn` / `hint` issues with fix suggestions; every issue references a section of `docs-cockpit-author`
- **Bilingual UI** — `[EN] [中]` toggle in topbar · default EN · localStorage persists
- **Tree browser** (`docs-cockpit browse`) — sidebar mirrors actual directory layout · search + collapse + last-viewed memory · marked.js + highlight.js render

### Machine-readable sidecar: `state.json`

Every build writes `docs/state.json` next to the HTML. Same payload as the dashboard + `issues[]` from the validator. The `docs-cockpit-standup` skill reads this for narrative answers; CI reads it for invariant checks. Schema is stable across 0.2.0+ (new fields are added, never removed).

## Philosophy

- **Single-file artifacts** — `docs/index.html` is self-contained · no localhost, no build pipeline, no JS framework, no network at runtime. Drop it in a Slack DM or commit it to the repo.
- **Frontmatter as schema** — every module is a markdown file readable by humans AND machine-parseable from the YAML frontmatter. No proprietary database.
- **One spec to rule them all** (`docs-cockpit-author`) — the schema lives in a skill that both Claude and humans can read. The validator references it line-by-line. No "ask Claude what frontmatter to use" each time.
- **Validation is opt-in but actionable** — every `❌` and `⚠️` has a `💡 fix` and a `📚 see` reference. Output is greppable, IDE-consumable, and CI-friendly.
- **`file://` first** — works without a webserver. Browsers' file:// security model is the deployment target.
- **Atomic upgrades** — `docs-cockpit upgrade` clears plugin cache and prompts restart in one operation. Ghost state (plugin running old SKILL.md after CLI upgraded) is the failure mode this prevents.
- **Cross-platform** — pure Python 3.10+ + `pyyaml`. Same YAML runs on Windows / macOS / Linux.

## Anatomy of a docs-cockpit project

```
your-project/
├── docs-cockpit.yaml              ← config (you write this; `init` scaffolds it)
├── docs/
│   ├── index.html                 ← BUILD ARTIFACT · the dashboard (human-facing)
│   ├── browse.html                ← BUILD ARTIFACT · tree-sidebar reader (optional)
│   ├── state.json                 ← BUILD ARTIFACT · machine-readable payload + issues[]
│   ├── spec/
│   │   ├── module/M01-*.md        ← module specs (frontmatter → Kanban cards)
│   │   └── concept/C01-*.md       ← concept specs (frontmatter → Concept Grid)
│   ├── plans/2026-MM-DD-<id>-plan.md   ← execution plans (linked via `docs:`)
│   ├── RFC/<NNN>-*.md             ← technical decisions
│   └── PRD.md                     ← curated as a `system_docs` entry
├── CLAUDE.md                       ← curated as a `system_docs` entry
└── .git/
```

## Minimal `docs-cockpit.yaml`

```yaml
project:
  name: MyProject
  mark: M                          # one-char wordmark
  tagline: "Module progress + sprint tracking"
  output: docs/index.html

paths:
  repo: "."                        # also: {home}, {env:VAR}, {main_repo} are available

system_docs:
  - { id: claude-md, title: CLAUDE.md, path: "{repo}/CLAUDE.md",  desc: "AI collab conventions", icon: memory }
  - { id: prd,       title: PRD.md,    path: "{repo}/docs/PRD.md", desc: "Product requirements",  icon: doc }

modules:
  scan:
    dir: "{repo}/docs/spec/module"
    title_transform: prefix-dot-titlecase

concepts:
  scan:
    dir: "{repo}/docs/spec/concept"
    title_transform: prefix-dot-titlecase
```

## Frontmatter (the part the dashboard reads)

```yaml
---
id: M07                              # REQUIRED · without this the doc is dropped
type: module                         # module | concept | plan | rfc | spec
title: "Job / Task FSM"
status: in-progress                  # not-started | planned | in-progress | blocked | done | deferred
sprint: M1.2
progress: 60                         # 0-100 · validated against status invariants
desc: "Job lifecycle state machine · drives worker scheduling"
owner: harvey
prd_ref: "§7.4.1"
docs:                                # links to plans / RFCs / specs
  - { title: "Execution plan", path: "docs/plans/2026-05-03-m07-fsm-plan.md" }
depends_on: [M06]
blocks: [M08, M09]
subtasks:                            # OR write `## TODO` in body — both work
  - { title: "wire FSM enum to Pydantic", done: true }
  - { title: "worker pulls next state from queue", done: false }
---

# Module body — anything below frontmatter
```

See the `docs-cockpit-author` skill for the full spec including the "docs vs subtasks" decision, file naming conventions, status × progress invariants, and cross-doc reference rules.

## Updating

```bash
docs-cockpit upgrade
```

That's the whole flow (0.7.0+). Backend detection · version compare · CHANGELOG diff · confirmation · atomic cache-clear + restart prompt if the plugin SKILL.md changed. Add `--dry-run` to see the plan, `--yes` for non-interactive.

## Working with AI coding editors

The empty-docs CTA generates prompts for the most common editors:

- **Claude Code** with **[superpowers](https://github.com/obra/superpowers)** — its `/plan`, `/spec`, `/rfc` skills scaffold; docs-cockpit-author then aligns frontmatter
- **Claude Code** with **gstack** — its plan/spec/rfc generators integrate the same way
- **Cursor / Codex / Continue / Aider** — paste the copied prompt into chat; the editor writes the file

In every case, after the AI writes the file, `docs-cockpit lint` is the source of truth for "is this going to render correctly".

## Contributing

PRs welcome. The dev loop:

```bash
git clone https://github.com/Guohao1020/docs-cockpit
cd docs-cockpit
pip install -e .              # editable install
docs-cockpit build -c docs_cockpit/examples/minimal.yaml --debug
```

For new skills, follow the conventions in the existing three (`skills/docs-cockpit*/SKILL.md`) — frontmatter `description` is "pushy" (over-triggers rather than under-triggers), bodies explain the **why** rather than dictating **what**.

## License

MIT — see [LICENSE](LICENSE).

## Community

- Issues: <https://github.com/Guohao1020/docs-cockpit/issues>
- Release notes: [CHANGELOG.md](CHANGELOG.md)
