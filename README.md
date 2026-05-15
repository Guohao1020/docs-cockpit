**English** · [中文](README.zh-CN.md)

# docs-cockpit

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)
[![CHANGELOG](https://img.shields.io/badge/CHANGELOG-0.10.0-green.svg)](CHANGELOG.md)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#contributing)

> **Open-source MIT-licensed project. Issues + PRs welcome.**

A project dashboard for your AI coding agent. Turn any folder of project markdown files (modules, concepts, plans, RFCs, specs) into a single-HTML **Kanban dashboard** + **tree-sidebar reader** you open with `file://`. Frontmatter-driven, schema-validated, AI-agent-native.

> Your AI agent stops asking "what frontmatter should I use?" — docs-cockpit ships the canonical spec as a skill, the validator that enforces it, and a copy-prompt CTA that hands AI the right context to write the next plan / RFC / spec for you. Multi-project users get a portfolio registry + weekly snapshot diff so one command produces a cross-project weekly report.

## Quickstart

Give your AI coding agent docs-cockpit:

- **[Claude Code](#claude-code)** ✅ available now
- **Codex CLI · Codex App · Factory Droid · Gemini CLI · OpenCode · Cursor · GitHub Copilot CLI** — packaging coming · the schema / validator / spec are agent-agnostic, only the skill-distribution layer differs

Once installed, the 4 skills auto-trigger when you talk to your agent — there's nothing to remember, no syntax to learn. The 7 slash commands give you explicit invocation surfaces when you want them.

## How it works

The moment you ask your AI agent to track a project's progress, write a plan, generate a standup or weekly report, or fix frontmatter issues, docs-cockpit's skills auto-trigger.

There's a skill for **setting up the cockpit** (`docs-cockpit`), a skill for **writing individual project docs to the canonical spec** (`docs-cockpit-author`), a skill for **reading one project's state to answer status questions** (`docs-cockpit-standup`), and a skill for **producing cross-project weekly reports** (`docs-cockpit-portfolio`). The AI agent doesn't reinvent conventions each time — the skills _are_ the conventions.

Under the hood, the build step reads YAML frontmatter from every markdown file you list, turns each into a card, and writes a self-contained HTML dashboard you can open with `file://` — no localhost, no static-site generator, no JS framework, no network call at runtime. A sidecar `state.json` carries the same payload plus structured frontmatter validation results, which the standup / portfolio skills read for narrative answers and CI reads for invariant checks.

When you ask your AI to write a plan or spec for a module, the **author** skill triggers and walks the AI through the schema (required fields, status × progress invariants, file naming, cross-doc references) before any code touches disk. When the dashboard renders, modules with no `docs:` linkage show a copy-prompt CTA — pick `Plan` / `RFC` / `Spec`, see the full prompt rendered inline with your module's id / title / status / sprint / desc / body excerpt all substituted in, then click Copy and paste into your AI agent of choice.

For multi-project users, a **user-level registry** (`~/.docs-cockpit/projects.yaml`) tracks every project across your machine. Run `docs-cockpit portfolio snapshot` weekly (or via cron / pre-commit), and the **portfolio** skill composes one weekly report aggregating all of them with week-over-week diff (newly done · newly blocked · progress jumps · new modules).

## Installation

### Claude Code

```bash
# inside Claude Code
/plugin marketplace add Guohao1020/docs-cockpit
/plugin install docs-cockpit@docs-cockpit
```

That's the whole install. The plugin will check for the `docs-cockpit` Python runtime on first build and bootstrap it transparently (via `uv` / `pipx` / `pip` — whichever is on your machine) before doing anything else. Python 3.10+ is the only thing you need on PATH; everything else is handled.

Once installed, the plugin gives you:

```
/docs-cockpit:build       # generate dashboard
/docs-cockpit:browse      # generate tree-sidebar MD reader
/docs-cockpit:migrate     # legacy-layout migration
/docs-cockpit:status      # standup-style status report (single project)
/docs-cockpit:weekly      # multi-project weekly report (cross-project diff)
/docs-cockpit:lint        # validate frontmatter against the author spec
/docs-cockpit:update      # upgrade docs-cockpit itself
```

Plus 4 auto-triggered skills (you don't invoke these — your agent decides when to use them):

| Skill | When it triggers |
|---|---|
| **`docs-cockpit`** | "Set up a dashboard for this project" · "rebuild the cockpit" · "update docs-cockpit" |
| **`docs-cockpit-author`** | "Write a plan for module M07" · "what frontmatter should this RFC have" · validator emitted issues |
| **`docs-cockpit-standup`** | "What's blocked in Sourcery" · "sprint M1.2 progress" · "standup for this project" |
| **`docs-cockpit-portfolio`** | "Weekly report" / "周报" · "how are all my projects going" · "add this project to my portfolio" |

### Other AI coding agents

Codex CLI, Codex App, Factory Droid, Gemini CLI, OpenCode, Cursor, GitHub Copilot CLI — packaging is on the roadmap. The dashboard / validator / spec are agent-agnostic (it's just markdown skills + a Python CLI); only the skill-distribution layer differs per harness.

If you're packaging docs-cockpit for one of these, open an issue or PR.

## The basic workflow

1. **Tell your AI agent to set up the cockpit** — "set up docs-cockpit for this project". The agent scans your repo's doc layout, suggests a config, runs the first build. For legacy projects with `docs/plans/` `docs/adrs/` `docs/RFC/` already in flight, the agent uses the migrate flow — dry-runs first, shows what it'll move where, then `git mv`'s + injects frontmatter scaffolds.

2. **Author docs in conversation** — "write an execution plan for M07". The agent triggers `docs-cockpit-author`, reads the canonical schema, writes the frontmatter correctly the first time, drops the file in the right location (`docs/plans/YYYY-MM-DD-<id>-plan.md`), AND updates the source module's `docs:` link so the dashboard picks it up.

3. **Build the dashboard** — "rebuild the cockpit". Open `docs/index.html` in your browser. Module Kanban renders, click any card → drawer shows desc / status select / progress slider / subtask checklist / linked docs with **inline MD preview** (marked.js renders the doc inside the drawer · no jumping to file:// raw view).

4. **Track status** by asking — "what's blocked", "how's sprint M1.2". The `docs-cockpit-standup` skill reads `state.json` and produces tables / bullet lists / paste-ready Markdown. Read-only by design — never edits files.

5. **Lint before commit** — "check frontmatter". Output is structured, every issue actionable:

   ```
   ❌ M07.md · id: missing required field — module won't appear in dashboard
      💡 fix: add `id: M07` to frontmatter
      📚 see: docs-cockpit-author · §2.1 required frontmatter
   ```

   Three severities: `error` (won't render at all), `warn` (renders with broken state), `hint` (polish · improves copy-prompt context).

6. **Multi-project weekly report** — register each project once (`docs-cockpit portfolio add` in each repo), schedule weekly snapshots (`docs-cockpit portfolio snapshot` via cron / Task Scheduler / pre-commit), then ask your AI for "weekly report" — the portfolio skill aggregates across all your projects with week-over-week diff.

7. **Upgrade** — "update docs-cockpit". One command detects install backend, compares CLI + plugin layer versions, fetches CHANGELOG diff, asks confirmation, and atomically clears cache + prompts restart if the plugin SKILL.md changed.

## What's Inside

### Dashboard features

- **Module Kanban** — 5 status columns · click a card → drawer with desc / status select / progress slider / subtask checklist / linked docs · localStorage-persisted overrides
- **Sprint Timeline** — modules grouped by sprint with avg %
- **Concept Grid** + **System Docs Drawer** — curated entries (CLAUDE.md / PRD / DESIGN / RFC / memory / roadmap) one click away
- **Auto body extraction** — `## 待办` / `## TODO` → subtasks · `## Related` / `## 关联` → `docs:`
- **Inline MD preview in drawer** — click a linked doc · marked.js + highlight.js render inside the drawer · "Back to module" returns to the card view
- **Empty-docs Copy-Prompt CTA** — `Plan` / `RFC` / `Spec` tabs · inline prompt preview · one Copy button · paste into your AI agent
- **needs-docs kanban chip** — active modules without docs are flagged on the card
- **Frontmatter validator** — `error` / `warn` / `hint` issues with fix suggestions, every one references a section of `docs-cockpit-author`
- **Bilingual UI** — `[EN] [中]` toggle in topbar · default EN · localStorage persists
- **Tree-sidebar MD browser** (via `browse`) — sidebar mirrors directory layout · search + collapse + last-viewed memory · marked.js + highlight.js render

### Cross-project portfolio (0.10.0+)

- **User-level registry** at `~/.docs-cockpit/projects.yaml` — managed via `docs-cockpit portfolio add/list/remove/tag`
- **Weekly snapshots** at `~/.docs-cockpit/snapshots/<name>/<YYYY-MM-DD>.json` — run `docs-cockpit portfolio snapshot` (or cron / pre-commit)
- **Weekly report skill** composes cross-project Markdown with sections: 🚀 Wins · 🔥 Blockers · 📋 In flight · 📈 Progress this week · 🆕 Added · 🥶 Stale · ⚠️ Frontmatter issues · plus cross-project highlights
- **Week-over-week diff** computed from snapshots: newly done · newly blocked · progress jumps (≥15 points) · new modules · sprint moves
- **Project picker** — when you ask for a weekly report, the portfolio skill shows a numbered list of registered projects + each project's current KPI summary; you pick by numbers / names / `all` / tag (e.g. `active`)

### Machine-readable sidecar: `state.json`

Every build writes `docs/state.json` next to the HTML. Same payload as the dashboard + `issues[]` from the validator. The standup / portfolio skills read this for narrative answers; CI reads it for invariant checks. Schema is stable across 0.2.0+ (new fields are added, never removed).

## Philosophy

- **Single-file artifacts** — `docs/index.html` is self-contained · no localhost, no build pipeline, no JS framework, no network at runtime. Drop it in a Slack DM or commit it to the repo.
- **Frontmatter as schema** — every module is a markdown file readable by humans AND machine-parseable from the YAML frontmatter. No proprietary database.
- **One spec to rule them all** (`docs-cockpit-author`) — the schema lives in a skill that both AI agents and humans can read. The validator references it line-by-line. No "ask Claude what frontmatter to use" each time.
- **Validation is opt-in but actionable** — every `❌` and `⚠️` has a `💡 fix` and a `📚 see` reference. Output is greppable, IDE-consumable, and CI-friendly.
- **`file://` first** — works without a webserver. Browsers' file:// security model is the deployment target.
- **Atomic upgrades** — cache-clear + restart prompt happen in one operation. Ghost state (plugin running old SKILL.md after CLI upgraded) is the failure mode this prevents.
- **AI-agent native** — designed for the AI-conversation workflow, not the CLI workflow. The CLI is the runtime; the agent is the interface.
- **User-level portfolio** — one user maintains many projects; the registry and snapshots live under `~/.docs-cockpit/` so they're decoupled from any single repo and from Claude Code's install path.

## Reference

### Anatomy of a docs-cockpit project

```
your-project/
├── docs-cockpit.yaml              ← config (your agent writes this for you)
├── docs/
│   ├── index.html                 ← BUILD ARTIFACT · the dashboard
│   ├── browse.html                ← BUILD ARTIFACT · tree-sidebar reader (optional)
│   ├── state.json                 ← BUILD ARTIFACT · machine-readable payload + issues[]
│   ├── spec/
│   │   ├── module/M01-*.md        ← module specs → Kanban cards
│   │   └── concept/C01-*.md       ← concept specs → Concept Grid
│   ├── plans/2026-MM-DD-<id>-plan.md   ← execution plans (linked via `docs:`)
│   ├── RFC/<NNN>-*.md             ← technical decisions
│   └── PRD.md                     ← curated as a `system_docs` entry
├── CLAUDE.md                       ← curated as a `system_docs` entry
└── .git/
```

### Frontmatter (what the dashboard reads)

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

Full spec: see the `docs-cockpit-author` skill (loaded automatically when your AI agent is writing a plan / RFC / spec / module-MD). The skill defines the "docs vs subtasks" decision rule, file naming conventions, status × progress invariants, and cross-doc reference rules.

### Multi-project registry layout

```
~/.docs-cockpit/
├── projects.yaml                   ← registry · `docs-cockpit portfolio add/list/remove/tag`
└── snapshots/
    └── <project-name>/
        └── <YYYY-MM-DD>.json       ← weekly state.json copy (for week-over-week diff)
```

Path uses `pathlib.Path.home()` — Windows `C:\Users\<name>\.docs-cockpit\` · POSIX `~/.docs-cockpit/`.

## Updating

Just ask your agent — "update docs-cockpit". The `docs-cockpit` skill walks through the upgrade flow: detect backend, compare versions, show CHANGELOG diff, confirm, run upgrade command, atomically clear cache + prompt restart if the plugin SKILL.md changed. `/docs-cockpit:update` gives you the same flow via explicit slash command.

## Contributing

This is an open-source project — contributions of all sizes are welcome. The dev loop assumes you're working on docs-cockpit itself, not just using it:

```bash
git clone https://github.com/Guohao1020/docs-cockpit
cd docs-cockpit
pip install -e .              # editable install (Python 3.10+)
docs-cockpit build -c docs_cockpit/examples/minimal.yaml --debug
```

**Read [CLAUDE.md](CLAUDE.md) first** — it covers the architecture, the SemVer convention, the language conventions, and the easy-to-break things in this codebase.

For new skills, follow the conventions in the existing four (`skills/docs-cockpit*/SKILL.md`) — frontmatter `description` is "pushy" (over-triggers rather than under-triggers), bodies explain the **why** rather than dictating **what**, file naming + section structure mirrors the canonical-skill style. The `docs-cockpit-author/SKILL.md` is the reference template for "this is how a docs-cockpit skill is structured".

Open an issue first for anything substantive (new feature, schema change, breaking change). Bug fixes and docs improvements can come as direct PRs.

## License

MIT — see [LICENSE](LICENSE).

## Community

- Issues: <https://github.com/Guohao1020/docs-cockpit/issues>
- Release notes: [CHANGELOG.md](CHANGELOG.md)
- Architecture overview for contributors: [CLAUDE.md](CLAUDE.md)
