---
description: Compose a multi-project weekly report from the user's portfolio registry · pick which projects to include · diff against last week's snapshot
---

Explicit invocation of `docs-cockpit-portfolio` — the multi-project weekly report skill. Use this when the user wants a status report spanning **several** docs-cockpit projects, not just one.

## What this slash command does

When user invokes `/docs-cockpit:weekly`:

1. Run `docs-cockpit portfolio list` to see what's registered
2. If the registry is empty → tell user to register projects first:
   ```
   docs-cockpit portfolio add        # in each project root
   docs-cockpit portfolio snapshot   # to enable week-over-week diff
   ```
3. Otherwise show the user a numbered picker:
   ```
   Which projects to include?
     1. Sourcery · 24 modules · last built 1d ago
     2. Bastion · 49 modules · last built 0d ago
     3. internal-tool · 8 modules · last built 8d ago ⚠️
   Reply: numbers (1,3), names (Sourcery, Bastion), or "all" / "active"
   ```
4. Read each picked project's `state.json` + nearest snapshot from `~/.docs-cockpit/snapshots/<name>/`
5. Compute week-over-week diff (newly done · newly blocked · progress jumps · new modules)
6. Compose the report per the structure defined in `skills/docs-cockpit-portfolio/SKILL.md`

## Argument handling

- `/docs-cockpit:weekly` (no args) → show picker
- `/docs-cockpit:weekly all` → all registered projects
- `/docs-cockpit:weekly active` → all projects tagged `active`
- `/docs-cockpit:weekly Sourcery,Bastion` → those two

## What you (Claude) should do with the output

Surface the report as-is — Markdown, paste-ready into Slack / email / standup notes. **Don't paraphrase**. Users grep their old reports for the exact section headers (🚀 Wins · 🔥 Blockers · 📋 In flight · 📈 Progress this week).

If the registry has projects without a 5-14 day old snapshot, end the output with the snapshot reminder so next week's diff works.

## Don't do these

- **Don't run `docs-cockpit build` for the user** before generating the report — the skill works with whatever state.json currently exists (stale or fresh). If something's stale, surface it; don't silently rebuild.
- **Don't write/edit project files** — this command is read-only on project repos. The only write is to `~/.docs-cockpit/snapshots/` if you also offer to take a fresh snapshot.
- **Don't substitute a single-project report when the user asked for portfolio** — even if only one project ends up picked, follow the portfolio template (with the picker). If the user clearly wants single-project ("what's blocked in Sourcery"), invoke `/docs-cockpit:status` or hand off to `docs-cockpit-standup` instead.
- **Don't invent projects that aren't in the registry** — the registry is the user's curated list. If they want a new project included, run `docs-cockpit portfolio add` first.
