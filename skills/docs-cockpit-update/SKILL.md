---
name: docs-cockpit-update
description: |
  Upgrade docs-cockpit (both the Python CLI and the Claude Code plugin) when the user is on an older version. Auto-detects the CLI install backend (pip / uv tool / etc) and uses the right upgrade command. **Proactively clears the plugin cache** before restart so the plugin layer reliably picks up the new version (not just relying on Claude Code's `autoUpdate` which can be flaky). Flips `autoUpdate: true` in `~/.claude/settings.json` if not already set.

  TRIGGER this skill when:
  (a) the user explicitly asks to update / upgrade docs-cockpit ("update docs-cockpit", "upgrade docs-cockpit", "升级 docs-cockpit", "把 docs-cockpit 升到最新", "我用的 docs-cockpit 是不是过期了");
  (b) a `docs-cockpit build` run printed a banner like `[!] docs-cockpit X.Y.Z available (current: …)`;
  (c) one of the sibling skills (`docs-cockpit` or `docs-cockpit-status`) refuses to work because the user's local version doesn't have a feature it needs (e.g. `state.json` missing because their CLI predates 0.1.1, or `/docs-cockpit:migrate` not available because plugin predates 0.3.0).

  Do NOT trigger for: initial install ("how do I install docs-cockpit" → that's just README install instructions, not a skill); arbitrary `pip install --upgrade` of other packages; questions about Claude Code itself updating. The discriminator: the user already HAS docs-cockpit installed at some version and we need to move them to a newer version. If they don't have it yet, point them at README install instructions instead.
---

# docs-cockpit-update

> Move the user from version X.Y.Z to latest. Two layers: Python CLI (pip / uv tool / etc) + Claude Code plugin (settings.json + cache clear + restart).

## Two layers reminder

docs-cockpit ships in two pieces that update independently:

1. **Python CLI** — provides the `docs-cockpit` command. Installed via `pip install`, `uv tool install`, or similar. Updates require running the same backend's upgrade command.
2. **Claude Code plugin** (`~/.claude/settings.json` → `extraKnownMarketplaces`) — provides the SKILL.md + commands files Claude reads. Updates via marketplace re-fetch on Claude Code restart, **but `autoUpdate: true` is not always reliable** — sometimes the local plugin cache stays stale even with autoUpdate on. **The fix is to actively clear the plugin cache before restart**.

Both can be out of date independently. **Always check and update both.**

## Workflow

### Step 1 — Check current versions

CLI version (try multiple methods, since installer varies):

```bash
# Method 1 · import (works if docs_cockpit is importable from CWD or installed)
python -c "import docs_cockpit; print(docs_cockpit.__version__)" 2>/dev/null

# Method 2 · docs-cockpit CLI doesn't have --version yet · skip if no_module above

# Method 3 · find install backend
which docs-cockpit                # POSIX
where.exe docs-cockpit            # Windows · check this path; uv tool puts at ~/.local/bin/

# If still unknown, run:
docs-cockpit build --help         # confirms CLI is alive even if version unknown
```

Plugin version: read `~/.claude/plugins/cache/<some-dir-containing-docs-cockpit>/.claude-plugin/plugin.json`. Path naming varies — try `ls ~/.claude/plugins/cache/ | grep docs-cockpit` to find it. Or just plow ahead — re-fetching is idempotent.

### Step 2 — Check what's latest on GitHub

```bash
# POSIX:
curl -s https://raw.githubusercontent.com/Guohao1020/docs-cockpit/main/.claude-plugin/plugin.json | python -c "import json,sys; print(json.load(sys.stdin)['version'])"
```

```powershell
# Windows PowerShell:
(Invoke-RestMethod https://raw.githubusercontent.com/Guohao1020/docs-cockpit/main/.claude-plugin/plugin.json).version
```

### Step 3 — Read the CHANGELOG diff before upgrading

```bash
curl -s https://raw.githubusercontent.com/Guohao1020/docs-cockpit/main/CHANGELOG.md
```

Find the section between the user's current version and the latest. Surface 2-3 bullets so they know what they're getting. Example narrative:

> Upgrading you from 0.2.0 → 0.3.0. New since your version:
> - 0.2.1: bundled examples · `docs-cockpit init` now works after pip install
> - 0.3.0: `docs-cockpit migrate` CLI + `/docs-cockpit:migrate` slash command — one-shot bootstrap for legacy projects

### Step 4 — Upgrade the Python CLI (auto-detect backend)

**Detect which backend installed the CLI**, then use that backend's upgrade command. Don't blindly assume pip — many users install via uv tool, especially on Windows with Python 3.9 system default (which can't run docs-cockpit ≥ 0.3.0 anyway).

Detection logic:

```bash
# 1. Check Python version first · 0.3.0+ requires Python >= 3.10
python --version       # if shows 3.9 or older, pip path will fail

# 2. Find which binary is on PATH
which docs-cockpit                     # POSIX
where.exe docs-cockpit                 # Windows

# 3. Inspect the path:
#    - ~/.local/bin/docs-cockpit (with nearby uv.exe / python3.12.exe) → uv tool
#    - <python>/Scripts/docs-cockpit.exe or site-packages → pip
#    - /usr/local/bin/docs-cockpit on macOS → could be either
```

**Use the matching upgrade command**:

```bash
# pip-installed:
pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git

# uv-tool-installed:
uv tool upgrade docs-cockpit

# pipx-installed:
pipx upgrade docs-cockpit

# If pip's Python is < 3.10, switch to uv (works regardless of system Python):
uv tool install --python 3.11 --force git+https://github.com/Guohao1020/docs-cockpit.git
```

Verify by running:

```bash
docs-cockpit build --help    # should not error
# OR
python -c "import docs_cockpit; print(docs_cockpit.__version__)"
```

### Step 5 — Ensure plugin `autoUpdate: true`

Edit `~/.claude/settings.json` (Linux/macOS) or `%USERPROFILE%\.claude\settings.json` (Windows). Find the `extraKnownMarketplaces.docs-cockpit` block and add `"autoUpdate": true`:

```json
"docs-cockpit": {
  "source": { "source": "github", "repo": "Guohao1020/docs-cockpit" },
  "autoUpdate": true
}
```

If `autoUpdate: true` is already there, skip this step.

### Step 6 — Force-refresh the plugin cache (critical!)

**Don't rely on autoUpdate alone** — it sometimes doesn't actually fetch the new version even after restart. Proactively clear the local plugin cache so Claude Code is FORCED to re-clone from GitHub on next startup.

```bash
# POSIX (Linux/macOS):
rm -rf ~/.claude/plugins/cache/docs-cockpit* 2>/dev/null || true
rm -rf ~/.claude/plugins/cache/*docs-cockpit* 2>/dev/null || true

# Windows PowerShell:
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\plugins\cache\docs-cockpit*" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\plugins\cache\*docs-cockpit*" -ErrorAction SilentlyContinue
```

If the cache directory layout is unfamiliar, use:
```bash
# POSIX:
find ~/.claude -type d -name "*docs-cockpit*" 2>/dev/null
# Windows:
Get-ChildItem "$env:USERPROFILE\.claude" -Recurse -Directory -Name | Select-String "docs-cockpit"
```
… and delete what shows up.

### Step 7 — Restart Claude Code

Now that the cache is empty, restart Claude Code so it re-fetches the marketplace from GitHub:

> **Please quit Claude Code completely and reopen it.** Cache was cleared, so on startup it must pull the fresh `.claude-plugin/marketplace.json` + `plugin.json` + SKILL.md + commands from GitHub.

If user has `/plugin marketplace update docs-cockpit` available (newer Claude Code versions), they can use that *instead* of clearing cache + restarting — but cache clear is more reliable.

### Step 8 — Verify the upgrade landed (USER ACTION after restart)

Tell the user explicitly what to check **after they restart**:

1. **Open `/plugin` UI** (or the Customize panel from the gear icon). Find `docs-cockpit` and check:
   - **Version** should be the new one (e.g. `0.3.0`)
   - **Skills section** should list the right number of slash commands (`/build`, `/status`, `/update`, `/migrate` for 0.3.0+)
   - If `/docs-cockpit:migrate` is listed → plugin is at 0.3.0 ✓
2. **Run a sanity build**:
   ```bash
   docs-cockpit build
   ```
   Output should have no `[!] docs-cockpit X.Y.Z available` banner.

**If after restart the plugin version is STILL the old number**, the cache clear didn't catch the right path. Run this fallback:

```
# In Claude Code:
/plugin marketplace remove docs-cockpit
/plugin marketplace add Guohao1020/docs-cockpit
/plugin install docs-cockpit@docs-cockpit
```

This explicitly tells Claude Code's plugin manager to drop and re-add the marketplace, guaranteeing a fresh fetch.

## Common scenarios

### Scenario A: User on 0.2.0, latest is 0.3.0

Full ritual: CHANGELOG diff → upgrade CLI (auto-detect backend, fall back to uv if pip's Python too old) → settings.json autoUpdate → clear plugin cache → restart → verify.

### Scenario B: CLI is current but plugin is behind (common!)

`autoUpdate: true` didn't actually update plugin even after restart. **Skip CLI step**, go straight to:
1. Clear plugin cache (Step 6)
2. Restart
3. Verify version bumped

If still behind, use the `/plugin marketplace remove + add` fallback.

### Scenario C: User wants to pin a specific version

```bash
# CLI:
uv tool install --python 3.11 --force git+https://github.com/Guohao1020/docs-cockpit.git@v0.3.0
# or:
pip install git+https://github.com/Guohao1020/docs-cockpit.git@v0.3.0
```

For the plugin side, edit settings.json:
```json
"docs-cockpit": {
  "source": { "source": "github", "repo": "Guohao1020/docs-cockpit", "ref": "v0.3.0" },
  "autoUpdate": false
}
```

(Only do this if the user explicitly asks for pinning — auto-update is the better default.)

### Scenario D: User is offline / behind GFW / GitHub unreachable

Tell them: "I can't reach GitHub from this environment. To upgrade, you'd need a working route to `github.com`. Workarounds: SSH tunnel / use a clone of the repo on your own infra and change the source in settings.json to point there."

## Failure modes

- **`pip install` fails because Python < 3.10** → switch to uv: `uv tool install --python 3.11 --force git+https://github.com/Guohao1020/docs-cockpit.git`. Do NOT try to install Python 3.10+ system-wide — uv handles its own Python.
- **`pip install` fails with permission error** → suggest `pip install --user --upgrade ...` OR use uv tool instead.
- **Plugin version doesn't change after restart** (the issue this skill is built to handle!) → cache clear (Step 6) wasn't aggressive enough or path was wrong. Use the `/plugin marketplace remove + add` slash-command fallback in Step 8.
- **Version mismatch between import and CLI binary** → multiple Python environments. Run `which python` and `which docs-cockpit` to see which interpreter the CLI binary uses. Usually the CLI binary's shebang points to the right Python.
- **uv tool list shows old version but CLI works as new version** → `__version__` in `__init__.py` may be out of sync with pyproject.toml dynamic version. Trust `--version`-style import check over `uv tool list`.

## Don't do these things

- **Don't try to update the plugin by editing files under `~/.claude/plugins/cache/` directly** — that's the cache and gets blown away. The fresh content comes from GitHub on next fetch.
- **Don't run `pip install --upgrade` without showing the user what's changing (CHANGELOG diff)** — surprises break trust.
- **Don't promise "next time autoUpdate will just work"** without doing Step 6 (cache clear) — autoUpdate is unreliable. Cache clear is what actually forces the re-fetch.
- **Don't skip the verification** in Step 8 — if you don't tell the user what to check post-restart, they don't know if it worked. The new slash command (`/docs-cockpit:migrate` for 0.3.0) is the easiest "did the plugin update" signal.
