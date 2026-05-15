**English** · [中文](README.zh-CN.md)

# docs-cockpit

> Two single-file HTML views of your project's markdown · driven by YAML config + frontmatter · open with `file://`.
>
> **Dashboard** (Kanban / Sprint Timeline / KPI) for tracked modules · **Browser** (tree sidebar + marked.js render) for raw docs · **EN / 中** language toggle on both.

`docs-cockpit` solves two related problems:

1. **You have module specs with status/progress and need a dashboard** — without standing up Jira / Notion / Linear. → `docs-cockpit build` produces a `docs/index.html` with Module Kanban + Sprint Timeline + KPI bar + drawer-with-subtask-checklist.
2. **You have a folder full of MDs (ADRs, plans, RFCs) and just want to read them in a browser** — without setting up Sphinx / Docusaurus. → `docs-cockpit browse` produces a `docs/browse.html` with a tree-organized file sidebar + marked.js rendering.

## Highlights

- **Module Kanban** — 5 status columns; click a card → drawer with desc / status select / progress slider / **subtask checklist** (localStorage-persisted overrides)
- **Sprint Timeline** — modules grouped by sprint with avg %, locale-sorted
- **Concept Grid** + **System Docs Drawer** — curated entries (CLAUDE.md / PRD / DESIGN / RFC / memory / roadmap) one click away
- **Auto body extraction** (0.4.0+) — `## 待办` / `## TODO` checklists in MD body **automatically** become subtasks · no frontmatter duplication
- **Subtask → auto progress** — `manualProgress: false` derives progress from subtask done-ratio
- **Tree browser** (0.5.0+) — sidebar mirrors actual directory layout · search + collapse + last-viewed memory
- **Bilingual UI** (0.6.0+) — `[EN] [中]` toggle top-right · default EN · localStorage persists
- **`migrate` command** (0.3.0+) — one-shot scan + frontmatter injection + canonical-layout migration for legacy projects (`docs/plans/`, `docs/adrs/`, etc)
- **Machine-readable `state.json`** sidecar — feeds the status skill for "what's blocked / weekly standup" queries · no HTML re-parsing
- **Cross-platform** — pure Python 3.10+ + `pyyaml`; same YAML runs on Windows / macOS / Linux
- **Ships as a Claude Code plugin** — 3 auto-triggered skills + 5 slash commands

---

## Quickstart — for Claude Code users (60 seconds)

docs-cockpit is **primarily a Claude Code plugin**. Setup is two commands + asking Claude.

```bash
# 1. In Claude Code, register the plugin marketplace
/plugin marketplace add Guohao1020/docs-cockpit

# 2. Install the CLI (Claude invokes it as a subprocess)
pip install git+https://github.com/Guohao1020/docs-cockpit.git
# Or for Python <3.10 systems / uv users:
# uv tool install --python 3.11 git+https://github.com/Guohao1020/docs-cockpit.git

# 3. Restart Claude Code so the plugin loads
```

Then in any project, ask Claude one of:

> "Build me a dashboard from `docs/spec/module/`" — or — "Browse all the markdown in this project" — or — "Migrate this legacy doc layout to docs-cockpit"

Claude picks the right skill, writes the config, runs the build. **That's it.**

> Not on Claude Code? See the [Install](#install--by-tool) section for Codex / Cursor / Gemini / OpenCode (manual skill copy).

### What you get

```
docs-cockpit build     →  docs/index.html   (Module Kanban + Sprint + KPI dashboard)
                          docs/state.json   (sidecar JSON for the status skill)

docs-cockpit browse    →  docs/browse.html  (tree-sidebar markdown browser)

docs-cockpit migrate   →  reorganizes legacy layout into docs/spec/module/M{NN}-*.md
                          + writes a tailored docs-cockpit.yaml
```

All HTML files have a `[EN] [中]` toggle in the top-right corner — defaults to English, switches to Chinese on click (localStorage-persisted).

### Module frontmatter (for dashboard cards)

For a module to appear as a Kanban card, the MD needs YAML frontmatter:

```markdown
---
id: M07
title: Job FSM
status: in-progress
sprint: M1.2
progress: 45
desc: "12-class FSM with field validation"
subtasks:
  - { title: "Core entity definitions", done: true }
  - { title: "Field validation", done: false }
---
```

Or — **just write `## TODO` / `## 待办` in the body** with checkbox items, docs-cockpit will auto-extract them as subtasks (0.4.0+):

```markdown
---
id: M07
title: Job FSM
status: in-progress
---

# M07 · Job FSM

## TODO
- [ ] Core entity definitions
- [x] Field validation
- [ ] Cross-model reference constraints
```

Full reference: [references/frontmatter_conventions.md](references/frontmatter_conventions.md).

---

## Install — by tool

### A. Claude Code (recommended)

**One-line plugin install + one-line CLI install + restart.**

```bash
# In Claude Code:
/plugin marketplace add Guohao1020/docs-cockpit

# In your shell:
pip install git+https://github.com/Guohao1020/docs-cockpit.git
```

Restart Claude Code → plugin auto-fetches from GitHub → 3 skills + 5 slash commands appear.

**Auto-update**: add `"autoUpdate": true` to the `extraKnownMarketplaces.docs-cockpit` entry in `~/.claude/settings.json`. Or ask Claude *"update docs-cockpit"* — the update skill walks the whole flow (pip upgrade + plugin cache clear + restart prompt). Cache clearing matters: `autoUpdate: true` alone is unreliable in current Claude Code (0.3.1+ flow handles this).

**If `/plugin` isn't available** (older Claude Code, PR-review surface): manually merge into `~/.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "docs-cockpit": {
      "source": { "source": "github", "repo": "Guohao1020/docs-cockpit" },
      "autoUpdate": true
    }
  },
  "enabledPlugins": {
    "docs-cockpit@docs-cockpit": true
  }
}
```

#### Natural-language triggers (skills auto-fire)

| You say | Claude triggers |
|---|---|
| "Bundle docs into a dashboard" / "Make a project Kanban" | `docs-cockpit` → writes yaml + runs `build` |
| "Browse the markdown in this project" / "Read all our ADRs" | `docs-cockpit` → runs `browse` |
| "Migrate this legacy layout to docs-cockpit" / "我项目用 docs/plans/, 帮我迁" | `docs-cockpit` → runs `migrate` (dry-run first, then `--apply`) |
| "What's blocked" / "Sprint M1.2 progress" / "Weekly standup from docs" | `docs-cockpit-status` → reads `state.json`, narrative output |
| "Update docs-cockpit" / "升级 docs-cockpit" | `docs-cockpit-update` → pip upgrade + plugin cache clear + restart prompt |

#### Explicit slash commands

- `/docs-cockpit:build` — Dashboard build → `docs/index.html` + `docs/state.json`
- `/docs-cockpit:browse [--dir <path>]` — Markdown browser → `docs/browse.html`
- `/docs-cockpit:migrate [--apply]` — Legacy layout migration (dry-run unless `--apply`)
- `/docs-cockpit:status [question]` — Read state.json, answer status / standup query
- `/docs-cockpit:update` — Two-layer upgrade workflow

### B. Other vibe-coding tools — manual skill copy

For **Codex / Cursor / Gemini / OpenCode** (or any tool with `~/.claude/skills/`-style skill loading):

```bash
# Clone the repo somewhere
git clone https://github.com/Guohao1020/docs-cockpit.git ~/.tools/docs-cockpit

# Copy skills into your tool's skill directory
# (substitute <skills-dir> for your tool's path · e.g. ~/.codex/skills/, ~/.cursor/skills/)
cp -r ~/.tools/docs-cockpit/skills/docs-cockpit         <skills-dir>/
cp -r ~/.tools/docs-cockpit/skills/docs-cockpit-status  <skills-dir>/
cp -r ~/.tools/docs-cockpit/skills/docs-cockpit-update  <skills-dir>/

# Install the CLI so the skill can invoke it
pip install git+https://github.com/Guohao1020/docs-cockpit.git
```

Restart your tool. The skills auto-trigger on the same natural-language phrases (Claude-specific path syntax in SKILL.md may need light adaptation).

> **Python ≥ 3.10 required.** Older system default? Use [`uv`](https://docs.astral.sh/uv/): `uv tool install --python 3.11 git+https://github.com/Guohao1020/docs-cockpit.git`.

---

## Configuration (for `docs-cockpit build`)

The dashboard's `docs-cockpit.yaml` has 4 top-level data blocks:

```yaml
project:        { name, mark, tagline, eyebrow, output }
paths:          { repo, ... custom-named vars }
system_docs:    [ { id, title, path, desc, icon } ... ]   # hand-curated drawer entries
modules:        { files / scan / glob }                    # frontmatter-driven dashboard cards
concepts:       { files / scan / glob }                    # simpler grid cards
frontmatter:    { enabled, status_progress_ranges }
```

`docs-cockpit browse` doesn't need any yaml — it scans the project + `~/.claude/{plans,projects}/<project>/` by default. Override with `--dir`.

References:
- [`docs_cockpit/examples/full.yaml`](docs_cockpit/examples/full.yaml) — complete reference config (6 system_docs + module scan + concept scan + frontmatter governance)
- [`docs_cockpit/examples/minimal.yaml`](docs_cockpit/examples/minimal.yaml) — minimal working config
- [`references/config_reference.md`](references/config_reference.md) — every field's semantics and defaults
- [`references/frontmatter_conventions.md`](references/frontmatter_conventions.md) — module / concept frontmatter spec + body fallback rules (`## TODO` → subtasks, etc.)

---

## Daily workflow

### Dashboard build

```bash
docs-cockpit build                          # default reads ./docs-cockpit.yaml
docs-cockpit build -c configs/preview.yaml  # specify config
docs-cockpit build --debug                  # print resolved path variables (debug saver)
```

Each build overwrites `docs/index.html` + `docs/state.json`. `Ctrl+R` in the browser to see new content.

### Markdown browser

```bash
docs-cockpit browse                              # default: project + ~/.claude scan
docs-cockpit browse --dir docs/adrs              # limit to one dir
docs-cockpit browse --output docs/adrs.html      # custom output
docs-cockpit browse --no-claude                  # skip ~/.claude scanning
```

Each run regenerates the HTML — no live watch. After editing MDs, re-run + `Ctrl+R`.

### Legacy project migration

```bash
docs-cockpit migrate                # dry-run · print plan · no file changes
docs-cockpit migrate --apply        # execute · git mv files + inject frontmatter + write yaml
docs-cockpit migrate --apply --keep-originals   # copy instead of move
```

Migrate auto-classifies legacy layouts (`docs/plans/`, `docs/adrs/`, `docs/superpowers/plans/` → modules; `docs/PRD/`, `docs/RFC/`, `docs/architecture/` → system_docs) and generates ID-prefixed frontmatter (`M01-*.md`, `M02-*.md`, ...).

### Wire into git workflow (optional but recommended)

A cockpit is only useful if it stays fresh. Three patterns:

**Pre-commit hook** (zero friction):

```bash
# .git/hooks/pre-commit
#!/bin/bash
if git diff --cached --name-only | grep -E '\.md$|\.yaml$' > /dev/null; then
  docs-cockpit build
  git add docs/index.html docs/state.json
fi
```

**CI check** (strict):

```yaml
# .github/workflows/docs.yml
- run: pip install git+https://github.com/Guohao1020/docs-cockpit.git
- run: docs-cockpit build
- run: git diff --exit-code docs/index.html docs/state.json
```

**CONTRIBUTING convention** (lightest):

> Any PR touching `*.md` must re-run `docs-cockpit build` and commit the regenerated artifacts.

### Commit `docs/index.html` or gitignore it?

**Commit it** — anyone who clones can `start docs/index.html` immediately; good for internal tools / team preview. Makes the `docs/` view on GitHub better too.

**Gitignore it** — keeps the repo lean; everyone has to build locally; good for public projects with binary-averse maintainers.

---

## Upgrade

The `docs-cockpit-update` skill walks the full flow — just ask Claude *"update docs-cockpit"*. Manual steps:

```bash
# 1. Upgrade the CLI
pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git
# Or: uv tool upgrade docs-cockpit

# 2. Force-clear plugin cache (autoUpdate alone is unreliable · 0.3.1 lesson)
rm -rf ~/.claude/plugins/cache/*docs-cockpit*                                # POSIX
# Windows: Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\plugins\cache\*docs-cockpit*"

# 3. Restart Claude Code so it re-fetches the marketplace
```

**Verify the upgrade landed** (post-restart):

- `/plugin` UI shows the new version number for `docs-cockpit`
- Skills list shows 5 slash commands (`/build`, `/browse`, `/migrate`, `/status`, `/update`)
- `docs-cockpit build` doesn't print a `[!] X.Y.Z available` banner

**If version still shows old**, run the fallback:

```
/plugin marketplace remove docs-cockpit
/plugin marketplace add Guohao1020/docs-cockpit
/plugin install docs-cockpit@docs-cockpit
```

Will an upgrade break your config?
- `0.x.y` patch / minor releases: backward-compatible unless CHANGELOG says otherwise
- `0.x → 1.0`: migration paths listed in CHANGELOG when relevant
- Unknown fields are silently ignored — adding new fields to your config is safe

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

---

## Troubleshooting — common issues

| Symptom | Likely cause | Fix |
|---|---|---|
| `[WARN] 0 items` after build | `paths.repo` wrong OR no MDs match modules/concepts paths | `docs-cockpit build --debug` to inspect the vars dict |
| Modules don't appear as Kanban cards | MD missing `id:` frontmatter, OR id is template placeholder (`MXX`) | Add `id: M07` etc. · See `references/frontmatter_conventions.md` |
| Subtask drawer empty even though MD has `## TODO` | MD body section header doesn't match — must be `## 待办` / `## TODO` / `## Subtasks` / `## Tasks` (with optional number prefix) | See body extraction rules in `references/frontmatter_conventions.md` |
| Red banner at top of browser | CDN can't reach marked.js / highlight.js | Intranet users: vendor the JS locally — open issue, this is on roadmap |
| YAML unknown-key error | Typo — config schema is strict | Check spelling in `references/config_reference.md` |
| Plugin version doesn't update after restart | Plugin cache stale, `autoUpdate` flaky | Force-clear cache: see Upgrade section step 2 above |
| `pip install` fails with "requires-python: >=3.10" | System Python too old | Switch to `uv tool install --python 3.11 git+...` |

Deeper debugging in the "Common failure modes" section at the end of `skills/docs-cockpit/SKILL.md`.

---

## Documentation index

### Skills (Claude auto-trigger)
- [`skills/docs-cockpit/SKILL.md`](skills/docs-cockpit/SKILL.md) — operational skill (setup / build / browse / migrate workflows)
- [`skills/docs-cockpit-status/SKILL.md`](skills/docs-cockpit-status/SKILL.md) — status-reading skill (interpret `state.json` for standups)
- [`skills/docs-cockpit-update/SKILL.md`](skills/docs-cockpit-update/SKILL.md) — auto-upgrade skill (CLI + plugin two-layer)

### Slash commands
- [`commands/build.md`](commands/build.md) — `/docs-cockpit:build`
- [`commands/browse.md`](commands/browse.md) — `/docs-cockpit:browse`
- [`commands/migrate.md`](commands/migrate.md) — `/docs-cockpit:migrate`
- [`commands/status.md`](commands/status.md) — `/docs-cockpit:status`
- [`commands/update.md`](commands/update.md) — `/docs-cockpit:update`

### Reference docs
- [`references/config_reference.md`](references/config_reference.md) — full `docs-cockpit.yaml` field schema
- [`references/frontmatter_conventions.md`](references/frontmatter_conventions.md) — frontmatter spec + body extraction rules
- [`references/design_tokens.md`](references/design_tokens.md) — CSS tokens, brand colors, fonts, dark mode

### Examples (bundled into pip wheel)
- [`docs_cockpit/examples/minimal.yaml`](docs_cockpit/examples/minimal.yaml) — minimal working config
- [`docs_cockpit/examples/full.yaml`](docs_cockpit/examples/full.yaml) — comprehensive reference

### Code
- `docs_cockpit/build.py` — dashboard build + state.json + body extraction
- `docs_cockpit/browse.py` — markdown browser
- `docs_cockpit/migrate.py` — legacy layout migration
- `docs_cockpit/templates/index.html.tmpl` — dashboard template (with i18n)
- `docs_cockpit/templates/browse.html.tmpl` — browser template (with i18n)

### Meta
- [`CHANGELOG.md`](CHANGELOG.md) — release history with migration notes per version
- [`README.zh-CN.md`](README.zh-CN.md) — 中文 README

> Note: the SKILL.md and `references/*.md` files are still Chinese-first. README and the generated HTML have full EN/ZH parity (with the topbar toggle).

---

## License

MIT
