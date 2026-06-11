**English** · [中文](README.zh-CN.md)

# docs-cockpit

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)
[![CHANGELOG](https://img.shields.io/badge/CHANGELOG-1.2.0-green.svg)](CHANGELOG.md)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#contributing)

> **Open-source MIT-licensed project. Issues + PRs welcome.**
> **Landing page:** <https://guohao1020.github.io/docs-cockpit/>

A project cockpit for AI-coding agents. Turn any folder of project markdown files (modules, concepts, plans, RFCs, specs) into a single-HTML **Kanban dashboard** + **Backlog view** + **tree-sidebar reader** you open with `file://`. Frontmatter-driven, schema-validated, AI-agent-native.

> Since v1.0 docs-cockpit is **skill-first**: the cognition — which module links to which doc, which subtask is backed by which plan section — lives in skills your agent reads; the Python CLI is a mechanical renderer. Install the plugin, open any project that has a `docs-cockpit.yaml`, and a SessionStart hook auto-injects a router into your agent's context — it knows how to use the cockpit before you say a word.

### What's new — v1.0 (skill-first pivot)

One sentence drove the pivot: **cognition lives in skills, Python only renders.** Doc association is judgment work — search, read, decide — and encoding it in CLI subcommands produced exactly the failure users reported: links that point nowhere. v1.0 moves all of that judgment into skill workflows that decide each linkage *with you*, in dialogue, under one north-star rule: **a wrong anchor is worse than a missing anchor.**

| v0.x | v1.0 |
|---|---|
| 4 auto-trigger skills with overlapping scopes | **1 entry router + 2 flow skills** — the router is auto-injected at session start |
| Cognition-side CLI subcommands (prompt rendering, LLM suggestions, patch merging, …) | Removed — their judgment moved into the skill workflows |
| MCP server as the agent interface | Removed — **the skill is the agent interface** |
| `docs-cockpit build` | `docs-cockpit render` (the old name was kept as a deprecated alias through 1.0 and removed in 1.1) |

Full rationale: [`docs/plans/P-skill-first-pivot.md`](docs/plans/P-skill-first-pivot.md) · full timeline: [CHANGELOG.md](CHANGELOG.md).

## Quickstart

Give your AI coding agent docs-cockpit:

- **[Claude Code](#claude-code)** ✅ available now
- **Cursor** — the SessionStart router hook ships a Cursor adaptation (`hooks/hooks-cursor.json`); full packaging on the roadmap
- **Codex CLI · Gemini CLI · OpenCode · GitHub Copilot CLI · …** — the dashboard / validator / spec are agent-agnostic (markdown skills + a Python CLI); only the skill-distribution layer differs per harness

Once installed there is nothing to remember: in any docs-cockpit project the router skill is injected automatically at session start, and your agent routes cockpit-related requests to the right workflow on its own. Five slash commands give you explicit invocation surfaces when you want them.

## How it works

**One router, two flow skills, one mechanical CLI.**

When a session starts in a project that has a `docs-cockpit.yaml`, the plugin's SessionStart hook injects the `use-docs-cockpit` router into your agent's context (in every other project the hook stays completely silent). The router's only job is dispatch:

| You want to | Handled by |
|---|---|
| Build the association system 0→1 — set up the cockpit, plan the whole project's specs/plans, wire modules to docs, fill anchor gaps | **`docs-cockpit-build`** skill · 7-phase dialogue workflow: ensure config → discover all docs → reason about linkages → dry-run-verify every anchor → decide each one with you → write anchors + draft missing docs → render |
| Refresh an EXISTING association that drifted — anchors stale after a refactor, specs evolved, links outdated | **`docs-cockpit-rebuild`** skill · 5 phases: read current state → diagnose drift → re-infer → minimal-diff refresh → render + verify |
| Ask status questions — what's blocked, sprint progress, which modules stalled | **`docs-cockpit-rebuild` Phase 1** · reads `state.json`, answers, touches nothing |
| Just regenerate the dashboard HTML | **`docs-cockpit render`** CLI · no association work |

Under the hood, `render` reads YAML frontmatter from every markdown file you list, turns each into a card, and writes a self-contained HTML dashboard you open with `file://` — no localhost, no static-site generator, no JS framework, no network call at runtime. A sidecar `state.json` carries the same payload plus structured validation results — the rebuild skill reads it for status narratives, CI reads it for invariant checks.

The canonical doc spec — required fields, status × progress invariants, anchor syntax, file naming, cross-doc reference rules — lives in [`references/schema.md`](references/schema.md): one file your agent and you both read, and the validator cites it issue-by-issue. The agent doesn't reinvent conventions each time — **the skills are the conventions.**

## Installation

### Claude Code

```bash
# inside Claude Code
/plugin marketplace add Guohao1020/docs-cockpit
/plugin install docs-cockpit@docs-cockpit
```

That's the whole install. The plugin checks for the `docs-cockpit` Python runtime on first render and bootstraps it transparently (via `uv` / `pipx` / `pip` — whichever is on your machine) before doing anything else. Python 3.10+ is the only thing you need on PATH; everything else is handled.

Once installed, the plugin gives you:

```
/docs-cockpit:render      # regenerate dashboard + state.json (explicit invocation)
/docs-cockpit:browse      # generate tree-sidebar MD reader
/docs-cockpit:migrate     # legacy-layout migration
/docs-cockpit:lint        # validate frontmatter against references/schema.md
/docs-cockpit:update      # upgrade docs-cockpit itself
```

And these CLI subcommands (run from terminal):

```
docs-cockpit render        # → docs/index.html (+ state.json, prompts.js)
docs-cockpit lint          # frontmatter + body validation, no render · CI / pre-commit
docs-cockpit init          # scaffold a minimal docs-cockpit.yaml
docs-cockpit migrate       # scattered legacy MDs → canonical layout · dry-run first
docs-cockpit browse        # single-file tree-sidebar MD reader
docs-cockpit sync-status   # dashboard checkbox ticks → back into MD source
docs-cockpit upgrade       # atomic CLI + plugin upgrade (cache clear + restart prompt)
```

Plus 3 skills (you don't invoke these — your agent decides when to use them):

| Skill | Role |
|---|---|
| **`use-docs-cockpit`** | Entry router · auto-injected at session start in any project with a `docs-cockpit.yaml` · routes everything below |
| **`docs-cockpit-build`** | "set up a docs-cockpit" · "wire modules to specs" · "plan the whole project's docs" — 0→1 / whole-project association building, decided with you in dialogue |
| **`docs-cockpit-rebuild`** | "anchors are stale" · "re-sync after refactor" · "what's blocked" — diagnose + refresh an existing association, or just read its state |

### Other AI coding agents

Cursor, Codex CLI, Gemini CLI, OpenCode, GitHub Copilot CLI — packaging is on the roadmap (Cursor already has a hook adaptation in `hooks/hooks-cursor.json`). The dashboard / validator / spec are agent-agnostic — it's markdown skills + a Python CLI; only the skill-distribution layer differs per harness.

If you're packaging docs-cockpit for one of these, open an issue or PR.

## The basic workflow

1. **Tell your agent to set up the cockpit** — "set up docs-cockpit for this project". The build skill's Phase 0 scans your repo's doc layout, writes the config, runs the first render. For legacy projects with `docs/plans/` `docs/adrs/` `docs/RFC/` already in flight, it uses the migrate flow — dry-runs first, shows what moves where, then `git mv`'s + injects frontmatter scaffolds.

2. **Build the association in dialogue** — "wire modules to docs", "plan the whole project's specs". The build skill discovers every doc, proposes module ↔ subtask ↔ doc-section linkages *with evidence*, dry-run-verifies every anchor before writing it, and asks you instead of guessing. Missing plan / spec docs get drafted per `references/schema.md` — correct frontmatter, right location (`docs/plans/YYYY-MM-DD-<id>-plan.md`), `docs:` link wired back to the module.

3. **Render the dashboard** — "regenerate the dashboard" or `docs-cockpit render`. Open `docs/index.html` in your browser. Module Kanban renders, click any card → drawer shows desc / status select / progress slider / subtask checklist / linked docs with **inline MD preview** (marked.js renders the doc inside the drawer — no jumping to file:// raw view).

4. **Track status by asking** — "what's blocked", "how's sprint M1.2". The rebuild skill's Phase 1 reads `state.json` and produces tables / bullet lists / paste-ready Markdown. Pure status queries end there — no files touched.

5. **Refresh after refactors** — "anchors are stale", "spec changed, re-sync the links". The rebuild skill diagnoses drift (lint + dry-run-verify every anchor), re-infers only the broken links, and keeps everything still accurate intact.

6. **Lint before commit** — "check frontmatter". Output is structured, every issue actionable:

   ```
   ❌ M07.md · id: missing required field — module won't appear in dashboard
      💡 fix: add `id: M07` to frontmatter
      📚 references/schema.md · frontmatter schema (required fields)
   ```

   Three severities: `error` (won't render at all), `warn` (renders with broken state), `hint` (polish · improves copy-prompt context).

7. **Upgrade** — "update docs-cockpit". One command detects install backend, compares CLI + plugin layer versions, fetches CHANGELOG diff, asks confirmation, and atomically clears cache + prompts restart if the skill layer changed.

## What's inside

### Dashboard features

- **Module Kanban + KPI strip** — 5 status columns · click a card → split-view drawer with desc / status select / progress slider / subtask checklist (with per-subtask anchor buttons + Copy prompt) / linked docs · localStorage-persisted overrides with build-time-aware invalidation
- **Sprint Timeline** — modules grouped by sprint with avg %
- **Backlog view** — `#/backlog` hash route · flat cross-module subtask list · 4-axis filter (time / sprint / status / search) · URL state codec for shareable links
- **Multi-select bundle** — checkboxes per subtask · shift-click range · "Select all visible" · quick-add by status · floating bar → Copy bundle prompt (a ready-to-paste prompt covering all selected subtasks)
- **Concept Grid** + **System Docs Drawer** — curated entries (CLAUDE.md / PRD / DESIGN / RFC / memory / roadmap) one click away
- **Auto body extraction** — `## 待办` / `## TODO` → subtasks · `## Related` / `## 关联` → `docs:` · checklist lines carry `@code:` / `@docs:` anchors
- **Inline MD preview** — click a linked doc / code anchor / doc anchor · marked.js + highlight.js render in right pane · slice info badge shows `📍 Showing lines X-Y of <file>`
- **Empty-docs Copy-Prompt CTA** — `Plan` / `RFC` / `Spec` tabs · inline prompt preview · one Copy button · paste into your AI agent
- **needs-docs kanban chip** — active modules without docs are flagged on the card
- **Frontmatter validator** — `error` / `warn` / `hint` issues with fix suggestions, every one references a section of `references/schema.md`
- **Bilingual UI** — `[EN] [中]` toggle in topbar · localStorage persists
- **Tree-sidebar MD browser** (via `browse`) — sidebar mirrors directory layout · search + collapse + last-viewed memory · marked.js + highlight.js render

### The skill layer

The plugin ships three skills plus a knowledge layer they read on demand:

- `skills/use-docs-cockpit/` — the entry router, injected at session start by the SessionStart hook (conditionally: only in projects with a `docs-cockpit.yaml`)
- `skills/docs-cockpit-build/` — the 7-phase association-building workflow (also owns cockpit setup + build debugging as its Phase 0)
- `skills/docs-cockpit-rebuild/` — the 5-phase drift-diagnosis + refresh workflow (also answers status questions as its Phase 1)
- `references/schema.md` — frontmatter + anchor field spec (the SSOT every validator issue cites)
- `references/association-method.md` — the 4 atomic association methods (discovery / reasoning / dry-run verification / highlight)
- `references/operations.md` — bootstrap / config / upgrade / troubleshooting runbook

There is no MCP server: since v1.0 the agent interface **is** the skill itself — your agent reads the markdown workflows and runs the same CLI you would. (The v0.12 MCP server was removed in 1.0.)

### Machine-readable sidecar: `state.json`

Every render writes `docs/state.json` next to the HTML. Same payload as the dashboard + structured `issues[]` from the validator. The rebuild skill's Phase 1 reads it for status narratives; CI reads it for invariant checks (`--strict`); any external tool can consume it. Schema is additive-only since 0.2.0 (new fields are added, never removed).

## Philosophy

- **Cognition in skills, Python only renders** — association work is judgment (search, read, decide); the skills do it in dialogue with you, and the CLI stays deterministic. The agent is the interface; the CLI is the runtime.
- **A wrong anchor is worse than a missing anchor** — a missing anchor is an honest gap; a wrong one sends you to irrelevant content and destroys trust in the whole dashboard. The skills dry-run-verify before writing, and ask instead of guessing.
- **Single-file artifacts** — `docs/index.html` is self-contained · no localhost, no build pipeline, no JS framework, no network at runtime. Drop it in a Slack DM or commit it to the repo.
- **Frontmatter as schema** — every module is a markdown file readable by humans AND machine-parseable from the YAML frontmatter. No proprietary database.
- **One spec to rule them all** (`references/schema.md`) — the schema lives in one reference doc that both AI agents and humans read. The validator references it line-by-line. No "ask the AI what frontmatter to use" each time.
- **Validation is opt-in but actionable** — every `❌` and `⚠️` has a `💡 fix` and a `📚 see` reference. Output is greppable, IDE-consumable, and CI-friendly.
- **`file://` first** — works without a webserver. Browsers' file:// security model is the deployment target.
- **Atomic upgrades** — cache-clear + restart prompt happen in one operation. Ghost state (plugin running old SKILL.md after CLI upgraded) is the failure mode this prevents.

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

Body checklists can pin every subtask to evidence — `- [ ] task text @code:src/worker/fsm.py:42-89 @docs:docs/RFC/004.md#§2.1` — and the build / rebuild skills dry-run-verify each anchor before writing it.

Full spec: see [`references/schema.md`](references/schema.md). It defines the "docs vs subtasks" decision rule, anchor syntax, file naming conventions, status × progress invariants, and cross-doc reference rules.

## Updating

Just ask your agent — "update docs-cockpit". The router dispatches upgrade phrasings straight to the `docs-cockpit upgrade` CLI: detect backend, compare versions, show CHANGELOG diff, confirm, run upgrade, atomically clear cache + prompt restart if the skill layer changed. `/docs-cockpit:update` gives you the same flow via explicit slash command.

## Contributing

This is an open-source project — contributions of all sizes are welcome. The dev loop assumes you're working on docs-cockpit itself, not just using it:

```bash
git clone https://github.com/Guohao1020/docs-cockpit
cd docs-cockpit
pip install -e .              # editable install (Python 3.10+)
python -m pytest tests/ -q    # 253-test suite (unit + integration)
docs-cockpit render -c docs_cockpit/examples/minimal.yaml --debug
```

**Read [CLAUDE.md](CLAUDE.md) first** — it covers the architecture, the SemVer convention, the language conventions, and the easy-to-break things in this codebase.

For new skills, follow the conventions in the existing three (`skills/*/SKILL.md`) — frontmatter `description` is "pushy" routing (over-triggers rather than under-triggers, and names the sibling skill that handles the negative case), bodies explain the **why** rather than dictating **what**, file naming + section structure mirrors the canonical-skill style.

Open an issue first for anything substantive (new feature, schema change, breaking change). Bug fixes and docs improvements can come as direct PRs.

## License

MIT — see [LICENSE](LICENSE).

## Community

- **Landing page:** <https://guohao1020.github.io/docs-cockpit/>
- **Issues:** <https://github.com/Guohao1020/docs-cockpit/issues>
- **Release notes:** [CHANGELOG.md](CHANGELOG.md)
- **Architecture overview for contributors:** [CLAUDE.md](CLAUDE.md)
- **Skill-first pivot spec:** [`docs/plans/P-skill-first-pivot.md`](docs/plans/P-skill-first-pivot.md)
- **Sync workflow:** [`references/sync_status_workflow.md`](references/sync_status_workflow.md)
- **Frontmatter spec (SSOT):** [`references/schema.md`](references/schema.md)
