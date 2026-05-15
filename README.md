**English** · [中文](README.zh-CN.md)

# docs-cockpit

> Single-file project **dashboard** for module / sprint / progress tracking. Driven by YAML frontmatter in `docs/spec/module/M*.md`. Opens with `file://`. Regenerates on every change.

> **⚠️ 0.2.0 product pivot:** docs-cockpit became a **project module dashboard** instead of a generic MD preview tool. See [CHANGELOG.md](CHANGELOG.md) for the 0.1.x → 0.2.0 migration table.

`docs-cockpit` solves one specific problem: **your project has module specs / concept docs scattered across folders, and you need a single dashboard to see what's in-progress, what's blocked, what's done — without standing up Jira / Notion / Linear.** It scans `docs/spec/module/*.md` + `docs/spec/concept/*.md`, reads YAML frontmatter (id / status / sprint / progress / desc / subtasks), and produces a self-contained `index.html` dashboard.

Highlights:

- **Module Kanban** — 5 status columns; click a card → drawer with desc / status select / progress slider / subtask checklist (localStorage-persisted overrides)
- **Sprint Timeline** — modules grouped by sprint with avg %, sorted by locale
- **Concept Grid** — concept cards at bottom (simpler · just id / title / status / sprint / progress)
- **System Docs Drawer** — curated entries (CLAUDE.md / PRD / DESIGN.md / RFC / memory / roadmap) accessed via topbar button
- **Subtask auto-progress** — `manualProgress: false` → progress derived from `subtasks[*].done` ratio
- **Machine-readable `state.json`** — sidecar JSON next to `index.html` · feeds the sibling status skill for "what's blocked / sprint progress / standup" queries
- **Cross-platform** — pure Python 3.10+ + pyyaml; same YAML on Windows / macOS / Linux
- **Ships as a Claude Code plugin** — three auto-triggered skills (`docs-cockpit` / `docs-cockpit-status` / `docs-cockpit-update`) plus three slash commands (`/docs-cockpit:build` / `:status` / `:update`)

---

## Quickstart — for Claude Code users (60 seconds)

docs-cockpit is **primarily a Claude Code plugin**. Setup is two commands + telling Claude what you want.

```bash
# 1. In Claude Code, register the plugin marketplace
/plugin marketplace add Guohao1020/docs-cockpit

# 2. Install the CLI (Claude invokes it as a subprocess)
pip install git+https://github.com/Guohao1020/docs-cockpit.git

# 3. Restart Claude Code so the plugin loads
```

Then in any project, ask Claude:

> 把 `docs/spec/module/` 下的 md 做成 dashboard

Claude auto-triggers the `docs-cockpit` skill, writes a `docs-cockpit.yaml` for you, runs `docs-cockpit build`, and gives you `docs/index.html` ready to open.

**That's it.** Three commands total, and **Claude handles the config writing + build for you**.

> If you're not a Claude Code user (Codex / Cursor / Gemini / standalone Python), jump to the [Install](#install--by-tool) section.

### What the dashboard looks like

After Claude finishes setup, open `docs/index.html` — you'll see:

- **Topbar** with project brand + last build time + "系统文档" drawer button
- **Hero gauge** with overall % progress
- **KPI strip** — total / done / in-progress / blocked counts
- **Module Kanban** — 5 status columns; click a card → drawer with subtask checklist + progress slider
- **Sprint Timeline** — modules grouped by sprint with avg %
- **Concept Grid** at the bottom

Module cards come from MDs that have YAML frontmatter:

```markdown
---
id: M07
title: Job FSM
status: in-progress
sprint: M1.2
progress: 45
desc: "12 类 FSM 状态机"
subtasks:
  - { title: "核心实体定义", done: true }
  - { title: "字段校验", done: false }
---
```

Full frontmatter reference: [references/frontmatter_conventions.md](references/frontmatter_conventions.md).

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

Restart Claude Code → plugin auto-fetches from GitHub → 3 skills (`docs-cockpit` / `docs-cockpit-status` / `docs-cockpit-update`) + 3 slash commands (`/docs-cockpit:build` / `:status` / `:update`) become available.

**Auto-update**: add `"autoUpdate": true` to the marketplace entry in `~/.claude/settings.json` (or just ask Claude *"update docs-cockpit"* whenever you want). Plugin layer auto-refreshes on restart; the CLI side still needs an occasional `pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git`.

**If `/plugin` isn't available** (older Claude Code, e.g. PR-review surface): manually merge into `~/.claude/settings.json`:

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

#### What you can ask Claude (skill auto-triggers)

| You say | Claude triggers |
|---|---|
| "把 docs 做成 dashboard" / "bundle docs into a dashboard" | `docs-cockpit` (writes yaml + runs build) |
| "weekly status from docs" / "哪些 module 卡了" / "sprint M1.2 进度" | `docs-cockpit-status` (reads `state.json`, produces narrative) |
| "升级 docs-cockpit" / "update docs-cockpit" | `docs-cockpit-update` (pip + plugin re-fetch + autoUpdate flip) |

Or use the explicit slash commands: `/docs-cockpit:build`, `/docs-cockpit:status weekly`, `/docs-cockpit:update`.

### B. Other vibe-coding tools — manual skill copy

For **Codex / Cursor / Gemini / OpenCode** (or any tool with `~/.claude/skills/`-style skill loading), copy the SKILL.md files manually:

```bash
# Clone the repo somewhere
git clone https://github.com/Guohao1020/docs-cockpit.git ~/.tools/docs-cockpit

# Copy skills into your tool's skill directory
# (substitute <skills-dir> for your tool's path · e.g. ~/.codex/skills/ / ~/.cursor/skills/)
cp -r ~/.tools/docs-cockpit/skills/docs-cockpit         <skills-dir>/
cp -r ~/.tools/docs-cockpit/skills/docs-cockpit-status  <skills-dir>/
cp -r ~/.tools/docs-cockpit/skills/docs-cockpit-update  <skills-dir>/

# Also install the CLI so the skill can invoke it
pip install git+https://github.com/Guohao1020/docs-cockpit.git
```

Restart your tool. The skills should auto-trigger on the same natural-language phrases (Claude-specific path syntax in the skills may need light adaptation).

### C. Standalone Python CLI (no AI tool)

If you just want the CLI and will write `docs-cockpit.yaml` by hand:

```bash
pip install git+https://github.com/Guohao1020/docs-cockpit.git
docs-cockpit init                          # generates a starter yaml
# edit docs-cockpit.yaml
docs-cockpit build                         # default reads ./docs-cockpit.yaml
```

For development / forking, use editable mode:

```bash
git clone https://github.com/Guohao1020/docs-cockpit.git
cd docs-cockpit
pip install -e .
```

**Python ≥ 3.10** required. If your system default is Python 3.9 or older, use [`uv`](https://docs.astral.sh/uv/):

```bash
uv tool install --python 3.11 git+https://github.com/Guohao1020/docs-cockpit.git
```

---

## Configuration

The 0.2.0 schema has 4 top-level blocks:

```yaml
project:        { name, mark, tagline, eyebrow, output }
paths:          { repo, ... custom-named vars }
system_docs:    [ { id, title, path, desc, icon } ... ]   # hand-curated drawer entries
modules:        { files / scan / glob }                    # frontmatter-driven dashboard cards
concepts:       { files / scan / glob }                    # simpler grid cards
frontmatter:    { enabled, status_progress_ranges }
```

See [`examples/full.yaml`](examples/full.yaml) for a complete reference config (6 system_docs + module scan + concept scan + frontmatter governance). See [`references/config_reference.md`](references/config_reference.md) for every field's semantics and defaults. See [`references/frontmatter_conventions.md`](references/frontmatter_conventions.md) for the module / concept frontmatter spec (status × progress validation, subtask auto-progress derivation, etc.).

---

## Daily workflow

### 1. Run build

```bash
docs-cockpit build                          # default reads ./docs-cockpit.yaml
docs-cockpit build -c configs/preview.yaml  # specify config
docs-cockpit build --debug                  # print resolved path variables (a lifesaver when debugging)
```

### 2. Browse

Each build overwrites `docs/index.html` (or whatever `project.output` points to). `Ctrl+R` in the browser to see new content.

### 3. Wire into your git workflow (optional but strongly recommended)

A cockpit is only useful if it stays fresh. Three patterns:

**Pattern a — pre-commit hook** (zero friction):

```bash
# .git/hooks/pre-commit
#!/bin/bash
if git diff --cached --name-only | grep -E '\.md$|\.yaml$' > /dev/null; then
  docs-cockpit build
  git add docs/index.html
fi
```

**Pattern b — CI check** (strict):

```yaml
# .github/workflows/docs.yml
- run: pip install git+https://github.com/Guohao1020/docs-cockpit.git
- run: docs-cockpit build
- run: git diff --exit-code docs/index.html
  # If docs/index.html is stale → CI fails → PR can't merge until rebuilt
```

**Pattern c — CONTRIBUTING convention** (lightest):

> Any PR touching `*.md` must re-run `docs-cockpit build` and commit the regenerated `docs/index.html`.

### 4. Commit `docs/index.html` or gitignore it?

**Commit it**: anyone who clones can `start docs/index.html` immediately — good for internal tools / team preview.
**Gitignore it**: keeps the repo lean — but everyone has to build locally — good for public projects.

Recommendation: commit it. Makes the `docs/` view on GitHub better too.

---

## Upgrade

```bash
# From GitHub
pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git

# Clone mode (development)
cd docs-cockpit && git pull
```

Will an upgrade break your config?
- `0.1.x` patch releases: 100% backward-compatible
- `0.x → 1.0`: may break — the CHANGELOG will list migration paths
- Adding new fields to your config won't break older versions; unknown fields are silently ignored

---

## Troubleshooting — common issues

| Symptom | Likely cause | Fix |
|---|---|---|
| `[WARN] 0 docs exist` | `paths.repo` is wrong | Delete the entire `paths` block — default is the config file's directory |
| Sidebar full of `missing` chips | Path variables didn't resolve | `docs-cockpit build --debug` to inspect the vars dict |
| Red banner at top of browser | CDN can't reach marked.js | Intranet users: see `references/design_tokens.md` "Offline mode" |
| Kanban empty / cards missing | Missing `id` in frontmatter / `kanban.enabled: false` | See `references/frontmatter_conventions.md` |
| YAML unknown-key error | Typo — config schema is strict | Check spelling in `references/config_reference.md` |

Deeper debugging in the "Common failure modes" section at the end of `SKILL.md`.

---

## Documentation index

- **`skills/docs-cockpit/SKILL.md`** — operational skill · setup + maintain workflows + which reference to read for each step
- **`skills/docs-cockpit-status/SKILL.md`** — status-reading skill · how to interpret `docs/state.json` for blockers / sprint progress / standup reports
- **`skills/docs-cockpit-update/SKILL.md`** — auto-upgrade skill · CLI + plugin two-layer upgrade workflow
- **`commands/build.md` / `status.md` / `update.md`** — slash command definitions for `/docs-cockpit:build|status|update`
- **`references/config_reference.md`** — full field schema for `docs-cockpit.yaml` · essential
- **`references/frontmatter_conventions.md`** — YAML frontmatter conventions + status × progress validation
- **`references/design_tokens.md`** — CSS tokens, brand colors, fonts, dark mode, offline vendoring
- **`examples/minimal.yaml`** — minimal working config
- **`examples/full.yaml`** — comprehensive reference · 10 groups + kanban
- **`CHANGELOG.md`** — release history
- **`README.zh-CN.md`** — 中文 README

> Note: the SKILL.md and `references/*.md` files are currently Chinese-first. The README is the only fully translated surface; deep reference docs assume bilingual readers or future translation contributions.

---

## License

MIT
