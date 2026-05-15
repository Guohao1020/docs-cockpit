---
description: One-shot migrate an existing project's scattered MDs (docs/plans/, docs/adrs/, etc.) into docs-cockpit's canonical docs/spec/module/ layout, with auto-generated frontmatter and yaml
---

Explicit invocation of `docs-cockpit migrate` — for projects that **don't already** have `docs/spec/module/*.md` with frontmatter. Use this on legacy / bastion-style repos with scattered `docs/plans/`, `docs/adrs/`, `docs/PRD/`, etc.

## When to use

- User says: "迁移这个项目到 docs-cockpit / 帮我用 docs-cockpit 跑起来 / set up dashboard for this legacy project"
- `docs-cockpit build` reports `[WARN] 0 items` because the project layout doesn't match defaults
- The `docs-cockpit` skill's bootstrap workflow detects a non-canonical layout (e.g. `docs/plans/` + `docs/adrs/` instead of `docs/spec/module/`)

## What it does

1. **Scans** the project for MDs in known dirs:
   - `docs/spec/module/`, `docs/plans/`, `docs/tasks/`, `docs/adrs/`, `docs/superpowers/{plans,specs}/` → **modules**
   - `docs/spec/concept/`, `docs/concepts/` → **concepts**
   - Root: README / CLAUDE.md / AGENTS.md / GEMINI.md / PROGRESS.md / CHANGELOG.md / PRE-LAUNCH-CHECKLIST.md / dogfood-onboarding.md / DESIGN.md → **system_docs** (each as own entry)
   - Dirs: `docs/PRD/`, `docs/RFC/`, `docs/architecture/`, `docs/DESIGN/`, `docs/audits/`, `docs/review/` → **system_docs** (each as whole-dir entry)
2. **Assigns IDs** (`M01`, `M02`, ... for modules; `C01`, ... for concepts)
3. **Generates frontmatter** for each module/concept:
   - `id` (new), `title` (from H1 or filename), `status: not-started`, `sprint: M0`, `progress: 0` as defaults
   - Existing frontmatter fields are **preserved** (don't override user's `status`/`progress` if already set)
4. **Physically moves** files to `docs/spec/module/M{NN}-{slug}.md` / `docs/spec/concept/C{NN}-{slug}.md`
   - Uses `git mv` to preserve git history (falls back to plain rename if not in git)
   - `--keep-originals` to copy instead of move (preserves `docs/plans/` etc.)
5. **Writes `docs-cockpit.yaml`** with project + paths + system_docs + modules/concepts + frontmatter blocks

## Steps when user invokes /docs-cockpit:migrate

1. **Always start with dry-run.** Run `docs-cockpit migrate` (no `--apply` flag) and show the user the plan output. Highlight:
   - Number of modules / concepts / system_docs detected
   - First 5-10 module file moves so they see the rename pattern
   - Whether `docs-cockpit.yaml` will be overwritten
2. **Wait for explicit user confirmation.** Don't auto-apply. The migration physically moves files.
3. **On confirmation, run with `--apply`** (or `--apply --keep-originals` if user prefers to keep originals).
4. **After apply succeeds, run `docs-cockpit build`** automatically to verify the dashboard generates correctly.
5. **Report:** counts of files moved + dashboard render status + any warnings.

## Flags

| Flag | Effect |
|---|---|
| (none) | Dry-run · prints plan · no file changes |
| `--apply` | Execute migration (`git mv` files, inject frontmatter, write yaml) |
| `--keep-originals` | Copy not move (originals stay at `docs/plans/`, etc.) |
| `--repo <path>` | Migrate a different repo (default: cwd) |

## Don't do these

- **Never run `--apply` without showing the dry-run first.** Migration physically moves user files — they must see the plan.
- **Don't migrate twice.** If the project already has `docs/spec/module/*.md` with frontmatter, the migration becomes a no-op (`dst.exists()` → skip). Tell the user "already migrated, run `docs-cockpit:build` directly".
- **Don't run on dirty git repos** without warning. If `git status` shows uncommitted work, ask user to commit first — migration touches many files.
- **Don't migrate INTO the docs-cockpit repo itself.** It's not the right shape (no `docs/plans/` etc.). Use `init` instead.

## After migration

- User opens `docs/index.html` → sees dashboard with N modules (all `not-started`, `progress: 0` initially)
- User edits MD frontmatter to update statuses, fills in `desc` / `subtasks` / `docs` per module
- Re-runs `docs-cockpit build` to update dashboard

This skill ends after a successful migration. Further work (frontmatter filling, design tweaks, kanban polish) handed off to the operational `docs-cockpit` skill.
