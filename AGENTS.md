# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## What this repo is

`docs-cockpit` is an **open-source MIT-licensed**, **skill-first** project Kanban: YAML-frontmatter-driven markdown rendered into a single-file dashboard. Since v1.0 the product is a **Codex plugin** — one entry/router skill + two workflow skills + a mechanical render CLI:

- **Skills carry the cognition** — discovery, reasoning about module↔doc associations, dialogue decisions all live in `skills/*/SKILL.md`
- **Python only renders** — the CLI (`docs-cockpit` console script · `pyproject.toml::project.scripts` → `docs_cockpit.build:main`) does deterministic MD → HTML and validation, nothing "smart"
- **North star**: a wrong anchor hurts more than a missing anchor — the build skill prefers asking the user over guessing associations

The full pivot rationale lives in `docs/plans/P-skill-first-pivot.md`. The v0.x four skills (`docs-cockpit` / `docs-cockpit-author` / `docs-cockpit-standup` / `docs-cockpit-portfolio`) and the cognition-side CLI subcommands were **deleted in v1.0** — if you see them referenced anywhere, that reference is stale.

The project is used in production on downstream projects (e.g. `D:/harvey_work/Sourcery`, `D:/shulex_work/bastion`), so changes here surface as user-visible plugin updates. Treat any change to `skills/*/SKILL.md`, the validator, or the HTML template as a release event — bump the version per the SemVer convention below.

## Common commands

### Local development

```bash
pip install -e .                                          # editable install (Python 3.10+)
docs-cockpit init                                         # scaffold a docs-cockpit.yaml
docs-cockpit render -c docs-cockpit.yaml --debug          # render dashboard + verbose
docs-cockpit lint                                         # validate frontmatter (no render)
```

`render` was named `build` in v0.x — the `build` alias was deprecated in 1.0 and removed in 1.1. All docs and skills say `render`.

### Tests

The repo has a real pytest suite — `tests/unit/` + `tests/integration/`, 253 tests:

```bash
py -3.13 -m pytest tests/ -q      # Python 3.10+ required (3.9 fails on type unions)
```

After substantive `build.py` / template changes, also smoke-render the two downstream reference projects: `D:/harvey_work/Sourcery` (24 modules) and `D:/shulex_work/bastion` (49 modules).

### "Lint" in this project

`docs-cockpit lint` is **frontmatter validation against the canonical schema in `references/schema.md`** — NOT Python code linting. There is no ruff / mypy / black configured for this repo's own Python source. If you want code-level linting, add it and document it.

### Release / version bump

A release touches **four files together**:

```
docs_cockpit/__init__.py          # __version__ = "X.Y.Z"
.codex-plugin/plugin.json        # "version": "X.Y.Z"
.agents/plugins/marketplace.json # plugins[].version = "X.Y.Z"
CHANGELOG.md                      # add ## [X.Y.Z] · YYYY-MM-DD section above prior entry
```

When the Codex marketplace bundle under `plugins/docs-cockpit/` is updated, keep
`plugins/docs-cockpit/.codex-plugin/plugin.json` in sync with the root manifest.

After commit + push, users on the plugin pull the update via `docs-cockpit upgrade` (handles plugin-cache clear + atomic restart prompt).

## SemVer convention

This project deviates from strict SemVer to encode the user-visible blast radius:

- **patch** — CLI-only / template-only fix. No SKILL.md changes. Plugin can be updated without restarting Codex (just the CLI).
- **minor** — new feature, new schema field, new CLI subcommand, new skill, or any SKILL.md change. Plugin cache MUST be cleared + Codex restarted (the `upgrade` CLI handles this atomically).
- **major** — config schema break (`docs-cockpit.yaml` shape changes incompatibly). v1.0 is the first: it removed skills and CLI subcommands wholesale.

Two 1.0-era rules:

- A SKILL.md frontmatter `description` is **machine routing** — Codex matches user requests against it. Any change to a description is at least minor, and users must run `docs-cockpit upgrade` (stale cached descriptions cause hard-to-debug routing bugs).
- The deprecated `build` alias was removed in 1.1 — don't reintroduce call sites.

## Architecture · the big picture

### Skill topology (the product)

| Skill | Role |
|---|---|
| `skills/use-docs-cockpit/` | Entry router · 29 lines · injected at SessionStart in docs-cockpit projects, routes to build / rebuild / direct CLI |
| `skills/docs-cockpit-build/` | 7-phase first-association build: Phase 0 ensure cockpit + AGENTS.md idempotent anchor block (three-state self-heal) → discovery → reasoning → dry-run → highlight → dialogue decisions → write anchors + draft missing docs → render. Phases 1–4 follow the 4 atomic methods in `references/association-method.md` |
| `skills/docs-cockpit-rebuild/` | 5-phase refresh of an existing cockpit: read current state (incl. status narrative — a pure status query ends here) → diagnose drift → re-infer → minimal-diff refresh → render + verify |

The SessionStart hook (`hooks/session-start`, wired by `hooks/hooks.json`) injects the router skill's body **conditionally**: it probes up to 6 directory levels for `docs-cockpit.yaml` and silently exits in non-cockpit projects. The script emits one of three JSON shapes depending on the detected platform: Codex → `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "..."}}` (nested); Cursor → `{"additional_context": "..."}` (snake_case top-level); Copilot CLI and unknown platforms → `{"additionalContext": "..."}` (SDK-standard top-level). `hooks/hooks-cursor.json` wires the same script under the Cursor hook protocol.

`references/` is the knowledge layer the skills read on demand:

- `schema.md` — **the frontmatter field-spec SSOT** · validator `Issue.reference` points at its sections · do not duplicate the schema anywhere else
- `association-method.md` — the 4 atomic association methods used by build Phases 1–4
- `operations.md` — bootstrap / config / upgrade / troubleshooting (read by build Phase 0)
- `config_reference.md` / `design_tokens.md` / `frontmatter_conventions.md` / `sync_status_workflow.md`

### Skill design conventions

- **Frontmatter `description` is pushy** — over-triggers rather than under-triggers · includes positive trigger phrases AND a discriminator naming the sibling skill that handles the negative case (build vs rebuild)
- **Skill body explains the WHY** — not just rote `MUST`s · `skills/docs-cockpit-build/SKILL.md`'s "## Why this skill exists" is the canonical example
- **Skill names ≠ slash command names** — check `commands/` before naming a new skill (a 0.9.0 rename was forced by exactly this collision; both parties of that collision are deleted now, the rule survives)

### Render pipeline (CLI)

The dispatcher is `main()` in `docs_cockpit/cli.py` (`build.py` re-exports it so the `build:main` entry point keeps working). Subcommands: `render` / `lint` / `init` / `migrate` / `browse` / `sync-status` / `upgrade` (the deprecated `build` alias was removed in 1.1). New subcommands are added by writing a `cmd_<name>(args)` function in a new module + wiring an inline `sub.add_parser(...)` block with `set_defaults(func=cmd_<name>)` in `cli.py::main()` — there is no `add_<name>_parser()` convention in this codebase. The v0.x cognition-side subcommands (`prompt` / `suggest` / `verify` / `sprint` / `migrate-subtasks` / `apply-patch` / `apply-body-patch` / `mcp-serve` + the MCP server) are gone — their judgment moved into the skills.

`docs-cockpit render` end-to-end:

1. Load `docs-cockpit.yaml` from CWD or `--config` path
2. `_build_vars()` resolves `{repo}` / `{home}` / `{env:X}` / `{main_repo}` path variables
3. `_resolve_group_files()` walks `modules:` / `concepts:` config (supports `files:` / `scan:` / `glob:`)
4. For each MD: `read_md()` → `split_frontmatter()` → `_build_card()` (build.py) — which calls `paths.py::_resolve_and_embed_docs()` (inlines linked-doc content for the drawer) and `schema.py::extract_subtasks_from_body()` / `extract_docs_from_body()` for body-section fallback
5. `schema.py::validate_meta()` emits structured `Issue` objects with `severity / field / message / suggestion / reference` (reference points to a `references/schema.md` section)
6. `build_payload()` returns `(payload, issues)` · issues surface to stdout and `state.json::issues[]`
7. `render_html()` does a single `template.replace("__DOCS_JSON__", json)` — `templates/index.html.tmpl` is otherwise static; all rendering is client-side JS
8. Writes `docs/index.html` + `docs/state.json` side-by-side · `state.json` is the machine-readable sidecar for the rebuild skill's status reading and any CI invariant checks

Module placement facts that differ from where you'd guess:

- `extract_subtasks_from_body` / `lint_sprint_readiness` / `load_sprint_plans` / the md-merge functions (`apply_to_md`, `compute_diff`) all live in **`schema.py`** (consolidated there in v1.0 · a post-1.0 split into `md_merge.py` is planned)
- `_resolve_doc_path` / `_resolve_and_embed_docs` live in **`paths.py`**
- `prompt.py` survives in trimmed form: it only produces the `docs/prompts.js` sidecar (data source for the dashboard's Copy-prompt CTA) — this is why the `jinja2` dependency is still in `pyproject.toml`

### The bootstrap pattern (plugin without CLI pre-installed)

The plugin is markdown-only — Codex's plugin system can't pip-install Python packages on install. So `references/operations.md` (read by `docs-cockpit-build` Phase 0) carries the **first-build bootstrap**: before running any `docs-cockpit <subcommand>`, check `docs-cockpit --version` and, if missing, run `uv tool install` / `pipx install` / `pip install --user` in priority order. Tell the user transparently when this happens — don't bury the bootstrap in silence.

## Language conventions in this repo

This repo follows the global `~/.Codex/AGENTS.md` language layering with one specific sub-override:

- **Python code comments**: 中文 prose · English technical terms (matches global rule)
- **`skills/*/SKILL.md` body**: **English** — these are cross-locale docs read by AI agents on machines in any locale; English provides stable trigger matching. Trigger phrases inside the description can include Chinese phrases for matching Chinese user inputs.
- **`commands/*.md`**: English (slash command docs · same reasoning as SKILL.md)
- **CHANGELOG.md entries**: English subject line under `### Added`/`### Changed`/etc · 中文 prose for the descriptions (matches global "human-collaboration prose → 中文")
- **README.md / README.zh-CN.md**: bilingual siblings · keep them in sync structurally · EN is primary
- **Commit subjects + PR titles**: English (machine-faced · grep-able)
- **Commit bodies + PR bodies**: 中文 (human-collaboration prose)

## Easy-to-break things (project-specific gotchas)

- **`hooks/*` must be LF** — `hooks/session-start` is a bash script; CRLF makes it die with `$'\r': command not found`. `.gitattributes` locks `hooks/* text eol=lf` — don't remove that line, and don't let an editor re-save these files with CRLF.
- **SessionStart injection is conditional** — no `docs-cockpit.yaml` within 6 parent levels → the hook silently exits. If injection "doesn't work" in a test project, check for the yaml before debugging the hook.
- **HTML template tokens**: `templates/index.html.tmpl` has exactly one placeholder, `__DOCS_JSON__`. `render_html` calls `str.replace(..., count=1)`, so only the **first** occurrence is substituted — if the same literal appears earlier in the template (e.g. in a JS comment or string), it hijacks the replacement and the real placeholder is left verbatim. Avoid `__DOCS_JSON__` anywhere in template content other than the single intended placeholder.
- **`references/schema.md` ↔ `schema.py::validate_meta()` pairing**: any change to the schema spec MUST be paired with a matching validator update (and vice versa). They drift apart silently — users get warned about things the spec says are fine, or the reverse.
- **Frontmatter validator severity routing**: a `severity: error` means "the dashboard literally won't render this doc". Don't downgrade an error to warn without checking the build still produces something meaningful — errors are read by CI via `--strict` to fail builds.
- **HTML comments count toward subtask-title anchor detection** — `schema.py::extract_subtasks_from_body()` does not strip `<!-- … -->` from checklist lines, so comment text lands in the subtask title and is scanned by the anchor-ref lint. Don't write `.md` / `§N` / line-number tokens inside comments on checklist lines.
- **State.json schema**: additive-only since 0.2.0 (fields added, never removed). External tools depend on `modules[*]` having stable fields; `warnings[]` is retained for backward compat alongside `issues[]`.
- **`docs:` path resolution**: `paths.py::_resolve_doc_path()` uses a three-step fallback (absolute → relative to source MD → relative to repo root). Don't simplify — the fallback exists to fix a real 0.7.0 bug (`docs/docs/foo.md` doubling).
- **Plugin marketplace cache + ghost state**: changing a SKILL.md and pushing is not enough — users must run `docs-cockpit upgrade` (clears the cache atomically). Don't tell users to just "restart Codex" — that doesn't clear the cache and produces ghost state.
- **Windows path separators**: in `state.json` paths are stored as-is (`D:\\harvey_work\\...`). Templates and JS handle both via `replace(/\\/g, '/')` at the use site — don't normalize at the build layer.

## Where to look first when working on a change

| Change kind | Start here |
|---|---|
| New CLI subcommand | `docs_cockpit/cli.py::main()` (argparse wiring) + new module if substantial |
| New render feature | `docs_cockpit/build.py::cmd_build` and `build_payload` |
| Skill workflow change | `skills/<name>/SKILL.md` — remember: frontmatter `description` = routing, body = workflow; description changes are at least minor |
| Hook injection behavior | `hooks/session-start` (+ `hooks/hooks.json` for Codex, `hooks/hooks-cursor.json` for Cursor) |
| New slash command | `commands/<name>.md` |
| New frontmatter field | `docs_cockpit/build.py::_build_card()` + `docs_cockpit/schema.py::validate_meta()` + `references/schema.md` |
| HTML / drawer / dashboard UI | `docs_cockpit/templates/index.html.tmpl` (~4700 lines · most of the work is CSS + the JS at the bottom) |
| Tree-sidebar reader UI | `docs_cockpit/templates/browse.html.tmpl` |
| Schema spec / authoring conventions | `references/schema.md` (the canonical source) |
| Association reasoning rules | `references/association-method.md` |

## References (in-repo)

- `docs/plans/P-skill-first-pivot.md` — the v1.0 pivot spec (why skill-first · what was deleted and why)
- `references/schema.md` — frontmatter & anchor field spec (the canonical SSOT)
- `references/association-method.md` — the 4 atomic module↔doc association methods
- `references/operations.md` — bootstrap / config / upgrade / troubleshooting runbook
- `references/config_reference.md` — full `docs-cockpit.yaml` field reference
- `references/frontmatter_conventions.md` — frontmatter governance (supplements `references/schema.md`)
- `references/design_tokens.md` — HTML template design system
- `CHANGELOG.md` — every release entry has a "Why" section explaining the user-visible motivation; read it before changing related code
