---
description: Run docs-cockpit build — regenerates docs/index.html + docs/state.json from the project's docs-cockpit.yaml
---

Explicit invocation of the docs-cockpit build pipeline. Use this when the user wants to force a build immediately without going through natural-language workflow detection.

## Steps

1. **Locate the config.** Look for `docs-cockpit.yaml` in the current working directory. If a path argument was passed after the slash command (`/docs-cockpit:build configs/preview.yaml`), use that path instead.

2. **Bootstrap if missing.** If no config exists, don't fail — hand off to the `docs-cockpit` skill's "Bootstrap a cockpit for a new project" workflow (it'll diagnose the doc layout and write a starter config first).

3. **Run the build.**

   ```bash
   docs-cockpit build -c <config-path>
   # Add --debug if the user explicitly asked to debug
   ```

4. **Surface key output lines:**
   - `[OK] Built <path>` — confirm the HTML wrote
   - `state: <path>` — confirm state.json wrote (≥0.1.1 required)
   - `[WARN] frontmatter: ...` — frontmatter validation warnings
   - `[!] docs-cockpit X.Y.Z available` — version banner; if seen, suggest invoking `/docs-cockpit:update`

5. **Report counts.** Pull the `modules: N | concepts: N | system_docs: N` line and surface it. Also surface the `module status · done=X in-progress=Y ...` line and the `overall progress: N%` line so the user can see at-a-glance summary.

6. **Suggest next move** based on output:
   - All clean → "open `docs/index.html` to verify"
   - Frontmatter warnings → suggest reading `references/frontmatter_conventions.md` for the offending field
   - Version banner → suggest `/docs-cockpit:update`
   - 0 items (no modules / concepts / system_docs visible) → diagnose `paths.repo` and scan paths (usually the cause), suggest `--debug` rerun

## Don't do these

- Don't rewrite the user's yaml without permission. If `docs-cockpit.yaml` has problems, point them at the right group / field to edit, don't silently fix.
- Don't open the HTML in a browser automatically (some users are in remote / headless environments).
- Don't pass `--no-version-check` unless the user explicitly asks — the version banner is a feature.
