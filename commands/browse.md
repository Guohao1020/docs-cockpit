---
description: Generate a single-file markdown browser HTML — tree sidebar + marked.js render. Scans project docs/ + ~/.claude/{plans,projects} by default
---

Explicit invocation of `docs-cockpit browse` — for when the user just wants to **read** the project's scattered MDs in a tree-organized browser, not see a dashboard.

## When to use

- User says: "我想浏览这个项目的所有文档 / give me an MD reader for this project / 把所有 md 汇总到一个 html 里"
- User wants a sidebar-tree view of `docs/adrs/`, `docs/plans/`, etc.
- The project's docs don't have frontmatter (so `docs-cockpit build` dashboard is empty) but user still wants something readable
- User also wants their `~/.claude/plans/<project>/` notes accessible from the same HTML

## What it does

1. Scans MDs in:
   - **Project root** top-level `*.md` (README, CLAUDE.md, CHANGELOG, etc.)
   - **`<project>/docs/`** recursively
   - **`~/.claude/plans/<project-name>/`** (if exists; skip with `--no-claude`)
   - **`~/.claude/projects/<sanitized-cwd>/memory/`** (if exists)
2. Groups files into "roots" by source (project / claude-plans / claude-memory)
3. Embeds content as JSON in a single HTML file with:
   - Sidebar: nested file tree per root, foldable, with file counts
   - Main: marked.js + highlight.js renders the clicked MD
   - Search: filters file paths (Ctrl+K / `/` to focus)
   - localStorage: remembers last-viewed file + which folders are expanded

## Usage

```bash
# Default · scan project + ~/.claude
docs-cockpit browse

# Specific directory only
docs-cockpit browse --dir docs/adrs --output docs/adrs.html

# Skip ~/.claude scanning
docs-cockpit browse --no-claude

# Override project name (shows in topbar)
docs-cockpit browse --project "Bastion"
```

## Steps

1. **Confirm the use case.** Browse mode is for READING. If user wants the project-progress dashboard (Kanban / KPI), redirect to `/docs-cockpit:build` instead.
2. **Run dry first** (no `--dir`) to see what gets scanned by default:
   ```bash
   docs-cockpit browse --output /tmp/preview.html
   ```
3. **If too much noise**, narrow with `--dir`:
   ```bash
   docs-cockpit browse --dir docs/adrs --dir docs/plans --output docs/browse.html
   ```
4. **Open the HTML** in the user's browser (file://). Show them the path.
5. **Update flow**: tell the user that re-running `docs-cockpit browse` regenerates the HTML — there's no live watch. After editing MDs, re-run the command + `Ctrl+R` in browser.

## Don't do these

- **Don't run on huge repos** (>1000 MD files) without `--dir` narrowing — payload bloats. The browse HTML embeds all MD content inline.
- **Don't conflate with `/docs-cockpit:build`** — build is for the kanban dashboard with frontmatter cards; browse is for raw MD reading. They produce DIFFERENT HTML files at different paths.
- **Don't auto-overwrite `docs/index.html`** — that's reserved for `docs-cockpit build` (the dashboard). Default browse output is `docs/browse.html`, intentionally different.
- **Don't try to make this a live MD editor**. It's read-only. For editing, user opens MDs in their IDE / editor.
