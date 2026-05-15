---
description: Update docs-cockpit (CLI + plugin) · delegates to `docs-cockpit upgrade` CLI for atomic one-command upgrade
---

Explicit invocation of the docs-cockpit upgrade workflow. **0.7.0+ recommendation**: just run `docs-cockpit upgrade` — the CLI handles everything (backend detection, version comparison, plugin cache decision, atomic restart).

The upgrade trigger phrases are now handled inside the **main `docs-cockpit` skill** (0.9.0 cleanup — the old standalone `docs-cockpit-update` skill was redundant; `docs-cockpit upgrade` CLI is the source of truth). This slash command remains as the explicit invocation surface.

## Primary path · 0.7.0+

```bash
docs-cockpit upgrade
```

That's the whole flow. The CLI:
1. Shows current CLI + plugin layer versions
2. Detects install backend (pip / uv / pipx / editable)
3. Fetches GitHub latest version
4. Shows CHANGELOG diff
5. Asks confirmation
6. Runs the right backend upgrade command
7. Compares plugin version · if changed, auto-clears cache + prints ATOMIC restart instructions; if unchanged, says "no restart needed"

Useful flags:
- `--dry-run` · print plan only · no changes
- `--yes` / `-y` · skip the "Proceed? [Y/n]" prompt
- `--no-clear-cache` · skip auto cache clear (manual control)
- `--skip-changelog` · skip CHANGELOG fetch (faster)

## What this slash command does

When user invokes `/docs-cockpit:update`:

1. Run `docs-cockpit upgrade` (with `--yes` if you want non-interactive · normally let it prompt)
2. Surface the output verbatim to the user
3. If output ends with "ATOMIC NEXT STEP", **emphasize** to the user: quit Claude Code completely in the next 30 seconds. Don't let them defer.
4. If output ends with "✓ no restart needed", confirm: CLI is up to date, plugin didn't need touching, they can keep working.

## Fallback · user on pre-0.7.0

If `docs-cockpit upgrade` errors with "unknown subcommand", the user has <0.7.0 installed. Run the old manual flow:

```bash
# 1. Detect backend
which docs-cockpit              # POSIX
where.exe docs-cockpit          # Windows

# 2. Upgrade CLI (pick one)
pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git
uv tool upgrade docs-cockpit
pipx upgrade docs-cockpit

# 3. ATOMIC · cache clear + IMMEDIATE restart (one operation · no pause)
#    POSIX:
rm -rf ~/.claude/plugins/cache/*docs-cockpit*
#    Windows:
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\plugins\cache\*docs-cockpit*" -ErrorAction SilentlyContinue
#    → then: quit Claude Code immediately, reopen
```

## Ghost state recovery

If user already separated cache clear from restart (the very scenario `docs-cockpit upgrade` exists to prevent):

- Plugin NOT in `Customize → Personal plugins` sidebar
- BUT Directory shows "Docs cockpit" with Uninstall + Manage (treated as installed)
- `/plugin install` says "already installed"

Recovery (in order):

1. **Restart Claude Code** (full quit · 30% chance fixes by itself)
2. **If still wrong**: in Directory → Plugins → Docs cockpit click **Uninstall** → restart → `/plugin marketplace add Guohao1020/docs-cockpit` → `/plugin install docs-cockpit@docs-cockpit` → restart
3. **Nuclear**: manually edit `~/.claude/settings.json` to remove `docs-cockpit` from both `extraKnownMarketplaces` AND `enabledPlugins` → save → restart → re-add marketplace

## Don't do these

- **Don't recommend manual `pip install --upgrade` if `docs-cockpit upgrade` is available** — it handles backend detection + plugin logic automatically; manual is the pre-0.7.0 path
- **Don't separate cache clear from restart in time** — `docs-cockpit upgrade` already presents them atomically. If you must do manual cache clear, put both commands in ONE Bash block with the restart instruction right after.
- **Don't run upgrade without showing CHANGELOG diff first** — `docs-cockpit upgrade` shows it by default. If using `--skip-changelog`, do show CHANGELOG manually before running.
- **Don't claim "upgrade succeeded" until post-restart verification** — `/plugin` UI version + slash command count are the truth.
