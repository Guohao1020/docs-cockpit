---
description: Validate frontmatter + body conventions across all project docs (without rebuilding the dashboard)
---

Explicit invocation of `docs-cockpit lint` — check every module / concept MD against the **docs-cockpit-author** schema spec. Reports `error` (won't render at all) · `warn` (renders but UX problems) · `hint` (polish suggestions), each with a concrete fix + reference to the relevant `docs-cockpit-author` section.

## Why this command exists

`docs-cockpit build` writes HTML + emits validation issues. But sometimes you just want to know "is my frontmatter clean?" without rebuilding — e.g. before a commit, in CI, or when iterating on a single MD file. That's `lint`.

## What this slash command does

When user invokes `/docs-cockpit:lint`:

1. Run `docs-cockpit lint` from project root (default config: `docs-cockpit.yaml`)
2. **If exit code 0 + no output** → confirm: "✓ All modules / concepts pass docs-cockpit-author spec."
3. **If exit code 0 with hints** → show hints, mention they're optional polish
4. **If exit code 1 (errors)** → surface the structured output:
   - For each `❌ error` block: file · field · message · suggested fix · `📚 see` reference
   - Group by file (a module with 3 issues groups as one block)
   - Then offer: "Want me to hand off to `docs-cockpit-author` and fix these now, or do you want to review them first?"
5. Always end with the summary line: "X error(s) · Y warning(s) · Z hint(s) · reference: docs-cockpit-author skill"

## Argument handling

- `/docs-cockpit:lint` (no args) → default · human-readable output
- `/docs-cockpit:lint --json` → JSON output (for piping to CI / IDE)
- `/docs-cockpit:lint --strict-warn` → upgrade warnings to errors (CI strict mode)
- `/docs-cockpit:lint <path-to-yaml>` → use a non-default config

## What you (Claude) should do with the output

The validator output is **structured** — each issue has 5 fields you should surface in order:

```
❌ <filename> · <field>: <message>
   💡 fix: <suggestion>
   📚 see: <reference-to-author-skill-section>
```

**Don't paraphrase these into vague advice** — the precision is the point. The user can grep for the field name, look up the reference section, and fix once and forever.

When the user says "yes, fix them":
- Hand off to **`docs-cockpit-author`** skill (DO NOT try to fix from this command)
- That skill is the canonical schema reference — it knows the right values for each field type

## Don't do these

- **Don't run `build` automatically** — lint is read-only by contract. If the user wants to see the rebuilt dashboard, they should run `/docs-cockpit:build` separately
- **Don't silently fix `error`-severity issues** — the suggested `id:` values etc. are project-specific guesses; the user must approve
- **Don't suppress hints** — hint-level issues (no `desc`, no `docs`) directly affect the copy-prompt feature's quality; surface them
- **Don't substitute your own schema** — if you disagree with what the validator reports, the validator wins. The author skill is the spec. If you find an actual bug, that's a docs-cockpit bug; report it, don't paper over it
