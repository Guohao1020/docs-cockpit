---
description: Read docs/state.json and answer a status / progress / standup question about the project
---

Explicit invocation of the `docs-cockpit-status` skill. Use this when the user wants project status quickly — without typing out "what's blocked" or "give me a weekly status report".

## Argument handling

The user can pass their question as the argument after the command:

- `/docs-cockpit:status` (no args) → ask: *"What do you want to know? Options: blockers / sprint progress / weekly status / stale docs / recent changes."*
- `/docs-cockpit:status what's blocked` → answer blockers
- `/docs-cockpit:status sprint M1.2` → sprint progress
- `/docs-cockpit:status weekly` → generate standup report
- `/docs-cockpit:status stale` → docs not touched in >30d

## Steps

1. **Find state.json.** Look for `docs/state.json` first. If `project.output` in `docs-cockpit.yaml` is set, derive the state.json location from there (sibling of the HTML).

2. **Handle missing state.json:**
   - If state.json doesn't exist → tell user `/docs-cockpit:build` first
   - If state.json was created by docs-cockpit <0.1.1 (no `cards` array even when kanban enabled) → suggest `/docs-cockpit:update` first
   - If state.json `build_time` > 7 days ago → warn the data may be stale, but still answer

3. **Parse the question + read the right slice.** Match the table in `skills/docs-cockpit-status/SKILL.md`:

   | Question shape | Read |
   |---|---|
   | blockers | `cards` where status==blocked, plus `blocks` / `depends_on` graph |
   | sprint X | `cards` where sprint==X, group by status, sum progress |
   | stale | `groups[*].items[*]` by mtime |
   | weekly / standup | `kpi` + recently-updated cards + warnings |
   | overall health | `kpi` |
   | by id | `cards` filtered by `id` |

4. **Compose output.** Match the format conventions in the status skill:
   - Multi-row → markdown table
   - Single answer → 1-2 prose sentences
   - Short enum → bullet list
   - Always include `build_time` so user knows data freshness
   - If `kanban_enabled: false`, degrade to file-listing mode, note the limitation

## Don't do these

- Don't write/edit any project files. This command is read-only by contract.
- Don't run `docs-cockpit build` automatically — if state.json is missing, ask the user to run `/docs-cockpit:build` first (separation of concerns).
- Don't fabricate cards or status that aren't in state.json. If something's not there, say "not visible in current cockpit data".
