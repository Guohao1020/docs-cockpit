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

## Quickstart — 60 seconds

In **your project root** (e.g. `D:\projects\myapp\`):

```bash
# 1. Install docs-cockpit (any of the methods below)
pip install git+https://github.com/Guohao1020/docs-cockpit.git

# 2. Generate the minimal config template
docs-cockpit init

# 3. Edit the generated docs-cockpit.yaml — 2-3 lines are usually enough

# 4. Build
docs-cockpit build

# 5. Open
start docs/index.html      # Windows
open  docs/index.html      # macOS
xdg-open docs/index.html   # Linux
```

The minimal template looks roughly like this (`docs-cockpit init` writes it for you):

```yaml
project:
  name: MyProject
  mark: M
  tagline: "项目进度概览"

system_docs:
  - { id: readme, title: README, path: "{repo}/README.md", desc: "项目总览", icon: doc }

modules:
  scan:
    dir: "{repo}/docs/spec/module"
    title_transform: prefix-dot-titlecase

concepts:
  scan:
    dir: "{repo}/docs/spec/concept"
    title_transform: prefix-dot-titlecase
```

Run it and open `docs/index.html` — you should see the topbar, KPI strip, module Kanban (populated from frontmatter), Sprint Timeline, and concept grid. Click a module card to open the drawer with subtask checklist.

For modules to appear as cards, the MDs need YAML frontmatter:

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

## Install — three paths, pick by scenario

### A. Pip install — recommended for "just use it as a tool"

```bash
pip install git+https://github.com/Guohao1020/docs-cockpit.git
```

After installation:
- The `docs-cockpit` command lands on your PATH — run `docs-cockpit build` directly
- Or `python -m docs_cockpit build` — both are equivalent

**Upgrade**: `pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git`

### B. Clone + editable mode — recommended for "I want to fork and tweak the logic"

```bash
git clone https://github.com/Guohao1020/docs-cockpit.git
cd docs-cockpit
pip install -e .
```

`pip install -e .` makes source edits take effect immediately — no reinstall needed.

### C. No install — temporary PYTHONPATH

```bash
git clone https://github.com/Guohao1020/docs-cockpit.git /some/where
# In your own project root:
PYTHONPATH=/some/where python -m docs_cockpit build
```

For trying it once, or if you don't want to touch site-packages.

### D. Install as a Claude Code plugin — let Claude invoke it

This is the recommended path for Claude Code users. The plugin ships two ways to invoke each capability — natural-language **skills** (auto-triggered) AND explicit **slash commands** (typed):

**Skills — auto-triggered when you describe what you want:**

- **`docs-cockpit`** (operational) — triggers on "bundle my docs into a dashboard", "add a new group to my cockpit", "wire pre-commit so HTML stays fresh", "change the cockpit's color scheme", "build is failing"
- **`docs-cockpit-status`** (read-only status) — triggers on "what's blocked", "sprint M1.3 progress", "generate a weekly standup from docs", "which modules haven't moved", "what changed in the cockpit this week"
- **`docs-cockpit-update`** (auto-upgrade) — triggers on "update docs-cockpit", "升级 docs-cockpit", OR automatically when a build prints `[!] docs-cockpit X.Y.Z available (current: ...)`

**Slash commands — explicit invocation with tab-completion:**

- **`/docs-cockpit:build`** — run a build now (optional config path arg)
- **`/docs-cockpit:status [question]`** — quick status query (e.g. `/docs-cockpit:status weekly`, `/docs-cockpit:status sprint M1.2`, `/docs-cockpit:status blockers`)
- **`/docs-cockpit:update`** — explicit upgrade trigger

Use whichever you prefer. Slash commands are faster for power users who remember the names; skills work for everyone else by just saying what you want.

Two install paths depending on your Claude Code version:

**D-1. Via slash command** (newer Claude Code, ~v2.1+):

```
/plugin marketplace add Guohao1020/docs-cockpit
/plugin install docs-cockpit@docs-cockpit
```

If you see `/plugin isn't available in this environment`, your version is too old — use D-2 below (or run `claude --version` and upgrade via `npm install -g @anthropic-ai/claude-code@latest`).

**D-2. Via settings.json** (always works, also the fallback for older Claude Code):

Edit `~/.claude/settings.json` (Linux/macOS) or `%USERPROFILE%\.claude\settings.json` (Windows) and **merge** these two blocks into the existing top-level object (don't replace any other keys):

```json
{
  "extraKnownMarketplaces": {
    "docs-cockpit": {
      "source": { "source": "github", "repo": "Guohao1020/docs-cockpit" }
    }
  },
  "enabledPlugins": {
    "docs-cockpit@docs-cockpit": true
  }
}
```

If `extraKnownMarketplaces` or `enabledPlugins` already exist in your settings, add the new entries **inside** those objects rather than replacing them.

**After either path, restart Claude Code.** On next startup it fetches `Guohao1020/docs-cockpit` from GitHub, parses `.claude-plugin/marketplace.json` + `plugin.json`, and the skill goes live.

**Verify it worked**: ask Claude something like *"bundle the markdown under docs/ into a dashboard"* — it should pick up `docs-cockpit` and start the workflow.

> ⚠️ **You still need `pip install`** (option A above) so the `docs-cockpit` CLI is on PATH — Claude invokes it as a subprocess. Plugin install + pip install is a combination, not an either/or.

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
