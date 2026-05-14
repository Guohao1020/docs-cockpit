---
name: docs-cockpit-update
description: |
  Upgrade docs-cockpit (both the Python CLI and the Claude Code plugin) when the user is on an older version. Handles `pip install --upgrade git+...` for the CLI, walks the user through restarting Claude Code so the plugin re-fetches, and optionally flips `autoUpdate: true` in their `~/.claude/settings.json` so future updates land automatically.

  TRIGGER this skill when:
  (a) the user explicitly asks to update / upgrade docs-cockpit ("update docs-cockpit", "upgrade docs-cockpit", "升级 docs-cockpit", "把 docs-cockpit 升到最新", "我用的 docs-cockpit 是不是过期了");
  (b) a `docs-cockpit build` run printed a banner like `[!] docs-cockpit X.Y.Z available (current: …)`;
  (c) one of the sibling skills (`docs-cockpit` or `docs-cockpit-status`) refuses to work because the user's local version doesn't have a feature it needs (e.g. `state.json` missing because their CLI predates 0.1.1).

  Do NOT trigger for: initial install ("how do I install docs-cockpit" → that's just README install instructions, not a skill); arbitrary `pip install --upgrade` of other packages; questions about Claude Code itself updating. The discriminator: the user already HAS docs-cockpit installed at some version and we need to move them to a newer version. If they don't have it yet, point them at README install instructions instead.
---

# docs-cockpit-update

> Move the user from version X.Y.Z to latest. Two layers: Python CLI (pip) + Claude Code plugin (settings.json + restart).

## Two layers reminder

docs-cockpit ships in two pieces that update independently:

1. **Python CLI** (`pip install`-managed) — provides `docs-cockpit build` command. Updates via `pip install --upgrade`.
2. **Claude Code plugin** (`~/.claude/settings.json` → `extraKnownMarketplaces`) — provides the SKILL.md files Claude reads. Updates via marketplace re-fetch on Claude Code restart.

Both can be out of date independently. A user might have 0.1.0 CLI + 0.1.2 plugin, or vice versa. **Always check and update both.**

## Workflow

### Step 1 — Check current versions

```bash
# Python CLI version
python -c "import docs_cockpit; print(docs_cockpit.__version__)"
# Or equivalently:
docs-cockpit --version   # if --version flag exists; fallback to the import above
```

For the plugin version, read `~/.claude/plugins/cache/docs-cockpit/.claude-plugin/plugin.json` (path may differ; if not found, ask the user to check via `/plugin` UI in Claude Code, or just plow ahead and update — re-fetching is idempotent).

### Step 2 — Check what's latest on GitHub

```bash
curl -s https://raw.githubusercontent.com/Guohao1020/docs-cockpit/main/.claude-plugin/plugin.json | python -c "import json,sys; print(json.load(sys.stdin)['version'])"
```

If the user is on Windows without curl, use:
```powershell
(Invoke-RestMethod https://raw.githubusercontent.com/Guohao1020/docs-cockpit/main/.claude-plugin/plugin.json).version
```

### Step 3 — Read the CHANGELOG diff before upgrading

```bash
curl -s https://raw.githubusercontent.com/Guohao1020/docs-cockpit/main/CHANGELOG.md
```

Find the section between the user's current version and the latest. Surface 2-3 bullets to the user so they know what they're getting. Example narrative:

> Upgrading you from 0.1.0 → 0.1.2. New since your version:
> - 0.1.1: state.json sidecar output; `docs-cockpit-status` skill (status / standup queries)
> - 0.1.2: in-CLI version check banner; this `docs-cockpit-update` skill

### Step 4 — Upgrade the Python CLI

```bash
pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git
```

Verify:
```bash
python -c "import docs_cockpit; print(docs_cockpit.__version__)"
```

The new version should match what was on GitHub.

### Step 5 — Make the Claude Code plugin auto-update going forward

Edit `~/.claude/settings.json` (Linux/macOS) or `%USERPROFILE%\.claude\settings.json` (Windows). Find the `extraKnownMarketplaces.docs-cockpit` block and add `"autoUpdate": true`:

```json
"docs-cockpit": {
  "source": { "source": "github", "repo": "Guohao1020/docs-cockpit" },
  "autoUpdate": true
}
```

If `autoUpdate: true` is already there, skip this step.

### Step 6 — Trigger the plugin refresh

The plugin layer needs Claude Code to restart for the marketplace to re-fetch:

> Restart Claude Code now (quit and reopen). On startup it'll re-fetch the docs-cockpit marketplace from GitHub, pull the new plugin.json + SKILL.md files, and the new skills become available.

If the user has `/plugin marketplace update docs-cockpit` available (newer Claude Code versions), they can use that instead of a full restart.

### Step 7 — Verify the upgrade landed

After restart, ask the user to run a quick sanity check:

```bash
docs-cockpit build
```

The build should now:
- Show no `[!] docs-cockpit X.Y.Z available` banner (because user is current)
- Write `docs/state.json` next to `docs/index.html` (if user upgraded to ≥0.1.1)
- Print build_time in `[OK]` line

If anything's off, hand back to the user with the specific symptom for diagnosis.

## Common scenarios

### Scenario A: User on 0.1.0, latest is 0.1.2

Full ritual: CHANGELOG diff → pip --upgrade → settings.json autoUpdate → restart Claude Code → verify.

### Scenario B: User has CLI 0.1.2 but plugin still 0.1.0 (or vice versa)

The two layers updated unevenly. Skip whichever is current, do the other.

- **Plugin is behind**: restart Claude Code (with `autoUpdate: true` if you can set it; otherwise it should still re-fetch on restart for most versions).
- **CLI is behind**: `pip install --upgrade ...` ritual only.

### Scenario C: User wants to pin a specific version

```bash
pip install git+https://github.com/Guohao1020/docs-cockpit.git@v0.1.2
```

For the plugin side, edit settings.json:
```json
"docs-cockpit": {
  "source": { "source": "github", "repo": "Guohao1020/docs-cockpit", "ref": "v0.1.2" },
  "autoUpdate": false
}
```

(Only do this if the user explicitly asks for pinning — auto-update is the better default.)

### Scenario D: User is offline / behind GFW / GitHub unreachable

Tell them: "I can't reach GitHub from this environment. To upgrade, you'd need a working route to `github.com`. Workarounds: SSH tunnel / use a clone of the repo on your own infra and change the source in settings.json to point there."

## Failure modes

- **`pip install` fails with permission error** → suggest `pip install --user --upgrade ...` OR `python -m pip install --upgrade ...` from within an active venv.
- **Plugin doesn't update after restart** → `autoUpdate: true` might not be set, or Claude Code version doesn't honor the flag. Fallback: delete `~/.claude/plugins/cache/docs-cockpit/` and restart (forces fresh re-fetch).
- **Version mismatch persists after both updates** → Python may be importing from a stale install. Run `pip show docs-cockpit` to see install location; verify it matches where the new version went.
- **User has multiple Python environments** → ask which environment Claude Code's spawned `docs-cockpit` subprocess uses. Usually system Python or user-site. Update there specifically.

## Don't do these things

- Don't try to update the plugin by editing files under `~/.claude/plugins/cache/` directly — that's the cache and gets blown away. Always update through settings.json + restart.
- Don't run `pip install --upgrade` without showing the user what's changing (CHANGELOG diff). Surprises break trust.
- Don't promise "next time it'll just work" without verifying `autoUpdate: true` actually landed in settings.json.
