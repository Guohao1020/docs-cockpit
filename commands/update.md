---
description: Update docs-cockpit (Python CLI + Claude Code plugin) to the latest version on GitHub
---

Explicit invocation of the `docs-cockpit-update` skill's two-layer upgrade workflow. **Key gotcha**: Claude Code's plugin `autoUpdate: true` is unreliable in practice — restart alone often doesn't refresh the plugin layer. This workflow **proactively clears the plugin cache** before restart to force a fresh fetch.

## Steps

1. **Check current versions.**

   ```bash
   python -c "import docs_cockpit; print(docs_cockpit.__version__)" 2>/dev/null
   # If that fails, find install backend:
   which docs-cockpit                # POSIX
   where.exe docs-cockpit            # Windows
   ```

   Save CLI version as `LOCAL_VERSION`.

2. **Fetch latest from GitHub.**

   ```bash
   curl -s https://raw.githubusercontent.com/Guohao1020/docs-cockpit/main/.claude-plugin/plugin.json
   ```

   Save as `REMOTE_VERSION`.

3. **Already current?** If `LOCAL_VERSION == REMOTE_VERSION` AND plugin layer is current (check `/plugin` UI), tell user "you're on the latest" and stop.

4. **Show CHANGELOG diff.** Fetch the CHANGELOG, surface every version between LOCAL and REMOTE so the user knows what's coming.

   ```bash
   curl -s https://raw.githubusercontent.com/Guohao1020/docs-cockpit/main/CHANGELOG.md
   ```

5. **Upgrade Python CLI** (auto-detect backend):

   ```bash
   # Detect install backend:
   #   ~/.local/bin/docs-cockpit (with uv nearby) → uv tool
   #   <python>/Scripts/docs-cockpit.exe → pip
   #   Python < 3.10 default → must use uv (pip path will fail)

   # pip:    pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git
   # uv:     uv tool upgrade docs-cockpit
   # pipx:   pipx upgrade docs-cockpit
   # fallback (when Python < 3.10):
   #         uv tool install --python 3.11 --force git+https://github.com/Guohao1020/docs-cockpit.git
   ```

   Verify CLI:
   ```bash
   docs-cockpit build --help      # should not error
   ```

6. **Wire up plugin `autoUpdate: true`.** Edit `~/.claude/settings.json` (or `%USERPROFILE%\.claude\settings.json` on Windows). Find `extraKnownMarketplaces.docs-cockpit`. If `"autoUpdate": true` is missing, add it.

7+8. **Force-clear the plugin cache, THEN restart Claude Code — as ONE atomic step.**

   ⚠️ **HARD RULE**: cache clear and restart must happen together (in this order, no pause between). If the user clears cache then doesn't restart, Claude Code enters a **ghost state** — plugin shows as "installed" in Directory but disappears from the sidebar, and reinstall fails. See "Ghost state recovery" below.

   **Right way to phrase to the user**:

   > Run these two commands in order, no pause in between:
   >
   > 1. (POSIX) `rm -rf ~/.claude/plugins/cache/*docs-cockpit*`
   >    (Windows) `Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\plugins\cache\*docs-cockpit*" -ErrorAction SilentlyContinue`
   > 2. Quit Claude Code completely (the whole app, not just the chat window). Reopen.

   If unsure of the cache path:
   ```bash
   find ~/.claude -type d -name "*docs-cockpit*" 2>/dev/null      # POSIX
   Get-ChildItem "$env:USERPROFILE\.claude" -Recurse -Directory -Name | Select-String "docs-cockpit"   # Windows
   ```

   If `/plugin marketplace update docs-cockpit` slash command is available (newer Claude Code), prefer that — no cache clear, no ghost state risk.

9. **Suggest verification (USER ACTION post-restart).** Tell the user explicitly what to check:
   - In `/plugin` UI, version should be `REMOTE_VERSION`
   - Skills list should show 4 slash commands including `/docs-cockpit:migrate` (signals plugin is at 0.3.0+)
   - `docs-cockpit build` shouldn't print the `[!] X.Y.Z available` banner

   **If version still shows the old number after restart**, run the slash-command fallback:
   ```
   /plugin marketplace remove docs-cockpit
   /plugin marketplace add Guohao1020/docs-cockpit
   /plugin install docs-cockpit@docs-cockpit
   ```

## Failure modes

- **Python 3.9 system default · pip path fails with "requires-python: >=3.10"** → switch to uv: `uv tool install --python 3.11 --force git+https://github.com/Guohao1020/docs-cockpit.git`
- **`pip install` permission error** → use `pip install --user --upgrade ...` OR switch to uv tool
- **Plugin layer still shows old version after Step 8 restart** → run the `/plugin marketplace remove + add` fallback from Step 9
- **Multiple Python environments** → CLI binary's shebang points to its Python; `which docs-cockpit` then `head -1` that file (POSIX) or check `where.exe` output (Windows)
- **GitHub unreachable** → tell user network is the blocker, no fix here

## Ghost state recovery

If the user already separated cache clear from restart and is now stuck:

- Plugin NOT in `Customize → Personal plugins` sidebar
- BUT Directory shows "Docs cockpit" with Uninstall + Manage buttons (treated as installed)
- `/plugin install` says "already installed"

Recovery (in order):

1. **Restart Claude Code first** (full quit). State often re-reconciles on startup.
2. **If still wrong**: in `Directory → Plugins → Docs cockpit` click **Uninstall**. Restart again. Then `/plugin marketplace add Guohao1020/docs-cockpit` + `/plugin install docs-cockpit@docs-cockpit`.
3. **Nuclear**: edit `~/.claude/settings.json` (Windows: `%USERPROFILE%\.claude\settings.json`), remove the `docs-cockpit` entries from both `extraKnownMarketplaces` and `enabledPlugins`. Save. Restart. Re-add marketplace fresh.

## Don't do these

- **Don't separate cache clear from restart in time** — Step 7+8 is ONE atomic action. If user pauses between, they get ghost state. See above.
- **Don't edit settings.json to add brand-new keys** you didn't see before. Only add `autoUpdate: true` inside the existing `docs-cockpit` marketplace block (unless executing the nuclear recovery in "Ghost state recovery" above).
- **Don't run `pip install --upgrade` without showing the CHANGELOG diff first** — surprises break trust.
- **Don't claim the upgrade succeeded** until the user has restarted AND verified via the `/plugin` UI or a new slash command being visible. CLI upgrade alone is not enough.
