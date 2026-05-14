---
description: Update docs-cockpit (Python CLI + Claude Code plugin) to the latest version on GitHub
---

Explicit invocation of the `docs-cockpit-update` skill's two-layer upgrade workflow.

## Steps

1. **Check current versions.**

   ```bash
   python -c "import docs_cockpit; print(docs_cockpit.__version__)"
   ```

   Save as `LOCAL_VERSION`.

2. **Fetch latest from GitHub.**

   ```bash
   # Cross-platform: try curl, fall back to powershell on Windows
   curl -s https://raw.githubusercontent.com/Guohao1020/docs-cockpit/main/.claude-plugin/plugin.json
   # OR Windows PowerShell:
   # (Invoke-RestMethod https://raw.githubusercontent.com/Guohao1020/docs-cockpit/main/.claude-plugin/plugin.json).version
   ```

   Save as `REMOTE_VERSION`.

3. **Already current?** If `LOCAL_VERSION == REMOTE_VERSION`, tell the user "you're on the latest" and stop.

4. **Show CHANGELOG diff.** Fetch the CHANGELOG, surface the bullet lists for every version between LOCAL and REMOTE so the user knows what's coming.

   ```bash
   curl -s https://raw.githubusercontent.com/Guohao1020/docs-cockpit/main/CHANGELOG.md
   ```

5. **Upgrade Python CLI.** Run:

   ```bash
   pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git
   ```

   Verify:

   ```bash
   python -c "import docs_cockpit; print(docs_cockpit.__version__)"
   ```

   Should now match REMOTE_VERSION.

6. **Wire up plugin auto-update.** Read `~/.claude/settings.json` (Linux/macOS) or `%USERPROFILE%\.claude\settings.json` (Windows). Find the `extraKnownMarketplaces.docs-cockpit` entry. If `"autoUpdate": true` is missing, add it. Don't replace other keys.

7. **Tell the user to restart Claude Code** so the plugin marketplace re-fetches `.claude-plugin/plugin.json` + the updated `SKILL.md` files. After restart, the plugin layer is current.

8. **Suggest verification.** After restart, the user should run `/docs-cockpit:build` once — the build banner should be gone (since they're current now), and `state.json` should output cleanly.

## Failure modes

- **`pip install` permission error** → suggest `pip install --user --upgrade ...`
- **Multiple Python environments** → use `pip show docs-cockpit` to find which one Claude's subprocess uses
- **GitHub unreachable** → tell user network is the blocker, no other fix here
- **settings.json doesn't have docs-cockpit entry** → user added the plugin via a different path; tell them to read README's "Install" section, then come back

## Don't do these

- Don't edit settings.json to add brand-new keys you didn't see before. Only add the `autoUpdate: true` field inside the existing `docs-cockpit` marketplace block.
- Don't run `pip install --upgrade` without showing the CHANGELOG diff first. Surprises break trust.
- Don't claim the upgrade is done before the user restarts Claude Code — they're only half-updated until the plugin layer re-fetches.
