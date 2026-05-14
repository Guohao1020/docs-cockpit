**English** · [中文](README.zh-CN.md)

# docs-cockpit

> Bundle a project's scattered Markdown into a single-file HTML cockpit — open it with `file://`, regenerate on every change.

`docs-cockpit` solves one specific problem: **your project's docs are scattered everywhere, and there's no single entry point to browse them.** It scans the directories you configure (`docs/PRD/`, `docs/spec/`, `docs/plan/`, `docs/RFC/`, `docs/task/`, root `README.md`, external `~/.claude/plans/...`, session memory, …) and serializes every MD into a self-contained `index.html` — no web server, no build pipeline, just drag-and-drop into a browser.

Highlights:

- **Sidebar nav + doc view** — marked.js + highlight.js client-side rendering, anchor jumps, search box, navigation state persisted via localStorage
- **Optional project kanban** — add YAML frontmatter (`status: in-progress` / `progress: 60` / `sprint: M1.2`) to any MD and you get a KPI bar / module kanban / sprint timeline for free
- **Machine-readable `state.json`** — each build emits a sidecar JSON next to `index.html` so other tools (and the sibling status skill) can answer "what's blocked / sprint progress / standup" without re-parsing the HTML
- **Cross-platform** — pure Python 3.10+ + pyyaml; the same YAML runs on Windows / macOS / Linux
- **Ships as a Claude Code plugin with three skills** — `docs-cockpit` (set up & maintain), `docs-cockpit-status` (read `state.json` and produce status / progress / standup reports), and `docs-cockpit-update` (auto-upgrade when the local CLI is behind GitHub HEAD). All three trigger automatically based on what you ask.

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
  glyph: M

groups:
  - name: Overview
    icon: O
    color: primary
    files:
      - { title: README, path: "{repo}/README.md" }

  - name: Docs
    icon: D
    color: graphite
    scan:
      dir: "{repo}/docs"
      recursive: true
```

Run it and open `docs/index.html` — you should see a sidebar listing every md under `docs/`.

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

This is the recommended path for Claude Code users. Once installed, Claude auto-detects the right sub-skill based on what you ask:

- **`docs-cockpit`** (operational) — triggers on "bundle my docs into a dashboard", "add a new group to my cockpit", "wire pre-commit so HTML stays fresh", "change the cockpit's color scheme", "build is failing"
- **`docs-cockpit-status`** (read-only status) — triggers on "what's blocked", "sprint M1.3 progress", "generate a weekly standup from docs", "which modules haven't moved", "what changed in the cockpit this week"
- **`docs-cockpit-update`** (auto-upgrade) — triggers on "update docs-cockpit", "升级 docs-cockpit", OR automatically when a build prints `[!] docs-cockpit X.Y.Z available (current: ...)`. Handles pip --upgrade + plugin re-fetch in one workflow.

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

## Configuration — three typical project shapes

### Recipe 1 — Simple project with one docs/ directory

```yaml
project: { name: MyLib, glyph: L }

groups:
  - name: Overview
    icon: O
    color: primary
    files:
      - { title: README, path: "{repo}/README.md" }
      - { title: CHANGELOG, path: "{repo}/CHANGELOG.md" }
  - name: Docs
    icon: D
    color: graphite
    scan:
      dir: "{repo}/docs"
      recursive: true
```

Good fit: open-source libraries, internal tools, small doc footprint. Kanban disabled — just sidebar + doc view.

### Recipe 2 — Multi-spec project with kanban

```yaml
project: { name: MyProduct, glyph: P, subtitle: Internal docs }

groups:
  - name: Overview
    icon: O
    color: primary
    files:
      - { title: README, path: "{repo}/README.md" }
      - { title: CHANGELOG, path: "{repo}/CHANGELOG.md" }

  - name: Spec — Concepts
    icon: C
    color: primary-deep
    scan:
      dir: "{repo}/docs/spec/concept"
      title_transform: prefix-dot-titlecase    # C03-foo-bar.md → C03 · Foo Bar

  - name: Spec — Modules
    icon: M
    color: primary
    scan:
      dir: "{repo}/docs/spec/module"
      title_transform: prefix-dot-titlecase

  - name: Plans
    icon: P
    color: graphite
    scan:
      dir: "{repo}/docs/plan"
      recursive: true
      title_transform: path-slash              # roadmap/00-master.md → "roadmap / 00-master"

  - name: Tasks
    icon: T
    color: bloom-coral
    scan:
      dir: "{repo}/docs/task"

  - name: RFCs
    icon: F
    color: storm-deep
    scan:
      dir: "{repo}/docs/RFC"

frontmatter:
  enabled: true
  kanban:
    enabled: true
    kpi_type: module                            # KPI bar only counts module-type cards
    sprint_order: [M0, M1, M2, M3, GA]
```

Good fit: medium-to-large projects with spec / plan / RFC / task buckets. Kanban requires MD files to carry YAML frontmatter:

```markdown
---
id: M07
type: module
title: Job FSM
status: in-progress
progress: 45
sprint: M1.2
---

# M07 — Job FSM ...
```

Full frontmatter field reference in `references/frontmatter_conventions.md`.

### Recipe 3 — Cross-path aggregation, plans living under $HOME

```yaml
project: { name: MyProject, glyph: M }

paths:
  repo: "."
  plans: "{home}/.claude/plans/myproject"      # external path variable

groups:
  - name: Internal docs
    icon: I
    color: primary
    scan:
      dir: "{repo}/docs"
      recursive: true

  - name: External plans
    icon: E
    color: storm-deep
    glob:
      - "{plans}/**/*.md"
```

Good fit: plans / notes you don't want to commit into the project repo but still want centralized in the cockpit. `{home}` is a built-in variable (`$HOME` / `$USERPROFILE`); add any custom variable under `paths:`.

Full config schema in `references/config_reference.md`.

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
