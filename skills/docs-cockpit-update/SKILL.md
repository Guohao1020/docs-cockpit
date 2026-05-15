---
name: docs-cockpit-update
description: |
  Upgrade docs-cockpit to the latest version. **0.7.0+ recommendation: just run `docs-cockpit upgrade`** — the CLI auto-detects the install backend (pip / uv / pipx / editable), compares CLI + plugin layer versions independently, runs the right upgrade command, and ONLY clears plugin cache + asks for restart if the plugin SKILL.md actually changed. No more "ghost state" risk from separating cache clear from restart in time.

  TRIGGER this skill when:
  (a) the user explicitly asks to update / upgrade docs-cockpit ("update docs-cockpit", "upgrade docs-cockpit", "升级 docs-cockpit", "把 docs-cockpit 升到最新");
  (b) a `docs-cockpit build` run printed `[!] docs-cockpit X.Y.Z available (current: …)`;
  (c) a sibling skill failed because the user's local version doesn't have a needed feature (e.g. `state.json` missing because their CLI predates 0.1.1, or `/docs-cockpit:upgrade` slash command absent because plugin predates 0.7.0).

  Do NOT trigger for: initial install ("how do I install docs-cockpit" → README install path, not this skill); arbitrary `pip install --upgrade` of other packages; questions about Claude Code itself updating. Discriminator: user already HAS docs-cockpit installed at some version, and wants to be on the latest.
---

# docs-cockpit-update

> One command. `docs-cockpit upgrade` does everything that this skill used to walk through manually — version detection, install backend detection, CLI upgrade, plugin cache decision, atomic restart instruction.

## Primary path (0.7.0+)

Just run the `docs-cockpit upgrade` CLI command (or invoke via `/docs-cockpit:upgrade` slash command):

```bash
docs-cockpit upgrade
```

What it does internally (in this order, all in one process):
1. **Detects** current CLI version (via `__version__`)
2. **Detects** current plugin layer version (reads `~/.claude/plugins/cache/*docs-cockpit*/.claude-plugin/plugin.json`)
3. **Detects** install backend (pip / uv / pipx / editable git clone)
4. **Fetches** latest version from GitHub `raw.githubusercontent.com/.../plugin.json`
5. **Shows** CHANGELOG diff between local and latest
6. **Confirms** with user (unless `--yes`)
7. **Runs** the right CLI upgrade command for the detected backend
8. **Compares** plugin layer version with new remote version:
   - If same: prints "✓ no restart needed" — DONE
   - If different: auto-clears plugin cache, prints **ATOMIC** restart instructions
9. **Verification checklist** (post-restart)

**Flags**:
- `--dry-run` — print plan, change nothing
- `--yes` / `-y` — non-interactive, skip "Proceed?" prompt
- `--no-clear-cache` — skip auto cache clear (let user do manually)
- `--skip-changelog` — skip CHANGELOG fetch (faster on slow networks)

## What this skill does (when invoked)

1. Run `docs-cockpit upgrade --skip-changelog` (skip the fetch if you've already shown CHANGELOG context) — OR run it with full flags if the user wants to see the CHANGELOG diff
2. Surface the output to the user as-is
3. If the command's last output mentions "ATOMIC NEXT STEP", emphasize to the user: **quit Claude Code COMPLETELY in the next 30 seconds**. Don't let them defer.
4. If the command says "✓ no restart needed", confirm with the user: their CLI is current, plugin didn't need touching, they can keep working.

## Fallback path (if `docs-cockpit upgrade` doesn't exist · user is pre-0.7.0)

If `docs-cockpit upgrade` errors with "unknown subcommand", the user has docs-cockpit <0.7.0 installed. Use the legacy manual flow:

### Step F1 — Check versions

```bash
python -c "import docs_cockpit; print(docs_cockpit.__version__)"

# remote:
curl -s https://raw.githubusercontent.com/Guohao1020/docs-cockpit/main/.claude-plugin/plugin.json
```

### Step F2 — Detect install backend, upgrade CLI

```bash
# Find the binary first:
which docs-cockpit          # POSIX
where.exe docs-cockpit      # Windows

# pip:    pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git
# uv:     uv tool upgrade docs-cockpit
# pipx:   pipx upgrade docs-cockpit
# Python < 3.10: uv tool install --python 3.11 --force git+https://github.com/Guohao1020/docs-cockpit.git
```

### Step F3 — Plugin cache + restart (ATOMIC)

> ⚠️ HARD RULE: cache clear and restart must happen as ONE atomic operation. See "Ghost state recovery" if you've already separated them in time.

Once the user agrees, present these as ONE instruction (not two separate steps):

> Run these two commands together, no pause:
>
> 1. (POSIX) `rm -rf ~/.claude/plugins/cache/*docs-cockpit*`
>    (Windows) `Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\plugins\cache\*docs-cockpit*" -ErrorAction SilentlyContinue`
> 2. Quit Claude Code completely and reopen.

### Step F4 — Verify

After restart:
- `/plugin` UI shows the new version for `docs-cockpit`
- A new slash command appears in the Skills list — `/docs-cockpit:upgrade` is the 0.7.0 marker
- `docs-cockpit upgrade` (the new command!) now reports "✓ Already up to date"

## Ghost state recovery

**Symptom**: After running cache clear (but not immediately restarting), the user sees:
- Plugin NOT in `Customize → Personal plugins` sidebar
- BUT `Directory → Plugins` shows "Docs cockpit" with Uninstall + Manage buttons (treated as installed)
- `/plugin install` reports "already installed"

**Why**: Claude Code's plugin state has two surfaces (in-memory sidebar vs settings.json registry). Clearing disk cache without an immediate restart makes them diverge. Sidebar shows "no plugin"; Directory shows "installed".

**Recovery (try in this order)**:

1. **Restart Claude Code first** (full quit). State often re-reconciles from disk on startup. ~30% chance fixes by itself.

2. **If still wrong after restart**: in `Directory → Plugins → Docs cockpit` click **Uninstall**. Restart again. Then `/plugin marketplace add Guohao1020/docs-cockpit` + `/plugin install docs-cockpit@docs-cockpit` + restart.

3. **Nuclear**: manually edit `~/.claude/settings.json` (Windows: `%USERPROFILE%\.claude\settings.json`):
   - Remove the `docs-cockpit` entry from `extraKnownMarketplaces`
   - Remove the `"docs-cockpit@docs-cockpit": true` entry from `enabledPlugins`
   - Save. Restart Claude Code (state is now clean). Then re-add marketplace fresh.

**Prevent**: ALWAYS use `docs-cockpit upgrade` (0.7.0+). The CLI handles cache clear + restart prompt as one atomic operation. Don't go back to manual cache-clear-then-restart unless absolutely necessary.

## Versioning convention (since 0.7.0)

This convention determines whether `docs-cockpit upgrade` needs to clear cache + ask for restart:

| Bump | What changes | Plugin restart? |
|---|---|---|
| **patch** (0.x.Y → 0.x.Y+1) | CLI code only (build.py / browse.py / etc.) · no SKILL.md or commands/ changes | No |
| **minor** (0.X → 0.X+1) | Plugin SKILL.md / commands/ changed · new features visible to user | Yes |
| **major** (X → X+1) | Breaking config schema · users need to migrate yaml | Yes + migrate |

`docs-cockpit upgrade` decides automatically by comparing local plugin.json version with remote.

## Failure modes

- **`docs-cockpit upgrade` not found** → user is on <0.7.0 · use fallback path above
- **`docs-cockpit upgrade` fails to fetch GitHub** → network / GFW · check `curl https://raw.githubusercontent.com/Guohao1020/docs-cockpit/main/.claude-plugin/plugin.json` manually
- **`pip install` fails with "requires-python: >=3.10"** → switch to uv: `uv tool install --python 3.11 --force git+...`
- **Plugin version still shows old after restart** → ghost state (see recovery above) or DNS / cache TTL · wait 5 min and try again
- **`uv tool list` shows old version, but `__version__` import shows new** → uv tool list is cached metadata · trust `__version__` import

## Don't do these things

- **Don't recommend manual `pip install --upgrade` if `docs-cockpit upgrade` is available** — the CLI command handles backend detection + plugin layer decision; manual pip is the pre-0.7.0 path.
- **Don't separate cache clear from restart in time** — if for some reason you must clear cache manually, present cache-clear + restart as ONE atomic instruction (in the same Bash code block, with the restart step right after). Don't say "first clear cache, then later restart".
- **Don't run `pip install --upgrade` without showing the user what's changing** (CHANGELOG diff) — surprises break trust. `docs-cockpit upgrade` already shows this; if going manual, fetch CHANGELOG yourself.
- **Don't claim the upgrade is done before verification** — `docs-cockpit upgrade` ends with a clear "✓ done" or "ATOMIC restart" message. Wait for user confirmation post-restart before celebrating.
