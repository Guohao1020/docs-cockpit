# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`docs-cockpit` is an **open-source MIT-licensed** project that turns YAML-frontmatter-driven markdown into a single-file project Kanban dashboard. It ships as **two artifacts from the same repo**:

1. **A Python CLI** (`docs-cockpit` console script · `pyproject.toml::project.scripts`) installable via pip / uv tool / pipx
2. **A Claude Code plugin** (`.claude-plugin/plugin.json` + `skills/` + `commands/`) installable via `/plugin install docs-cockpit@docs-cockpit`

The plugin's skills reach into the CLI for the actual MD → HTML build — they're not duplicates of each other. The CLI is the runtime; the plugin is the interface layer for AI agents.

Because the project is open-source and used in production on multiple downstream projects (e.g. `D:/harvey_work/Sourcery`, `D:/shulex_work/bastion`), changes here surface as user-visible plugin updates. Treat any change to `skills/*/SKILL.md`, the validator, or the HTML template as a release event — bump the version per the SemVer convention below.

## Common commands

### Local development

```bash
pip install -e .                                          # editable install (Python 3.10+)
docs-cockpit init                                         # scaffold a docs-cockpit.yaml
docs-cockpit build -c docs-cockpit.yaml --debug           # build + verbose
docs-cockpit lint                                         # validate frontmatter (no build)
docs-cockpit portfolio list                               # show user-level multi-project registry
```

### Smoke testing from source (no install needed)

The project has no formal pytest suite. Smoke tests are run by injecting the source directory into `sys.path` and invoking `main()` directly — Python 3.10+ required (system Python 3.9 will fail on type unions):

```bash
py -3.13 -c "import sys; sys.path.insert(0, r'D:\harvey_work\docs-cockpit'); from docs_cockpit.build import main; main(['build', '--config', 'docs-cockpit.yaml'])"
```

The two reference projects used for end-to-end smoke testing are `D:/harvey_work/Sourcery` (24 modules, 11 concepts) and `D:/shulex_work/bastion` (49 modules). Build them after substantive `build.py` / template changes to verify nothing regressed.

### "Lint" in this project

`docs-cockpit lint` is **frontmatter validation against the canonical schema in `references/schema.md`** — NOT Python code linting. There is no ruff / mypy / black configured for this repo's own Python source. If you want code-level linting, add it and document it.

### Release / version bump

A release touches **four files together**:

```
docs_cockpit/__init__.py          # __version__ = "X.Y.Z"
.claude-plugin/plugin.json        # "version": "X.Y.Z"
.claude-plugin/marketplace.json   # "version": "X.Y.Z"
CHANGELOG.md                      # add ## [X.Y.Z] · YYYY-MM-DD section above prior entry
```

After commit + push, users on the plugin can pull the update via `docs-cockpit upgrade` (handles plugin-cache clear + atomic restart prompt).

## SemVer convention

This project deviates from strict SemVer to encode the user-visible blast radius:

- **patch** (`0.7.1`, `0.7.2`) — CLI-only / template-only fix. No SKILL.md changes. Plugin can be updated without restarting Claude Code (just the CLI).
- **minor** (`0.8.0`, `0.9.0`, `0.10.0`) — new feature, new schema field, new CLI subcommand, new skill, or any SKILL.md change. Plugin cache MUST be cleared + Claude Code restarted (the `upgrade` CLI handles this atomically).
- **major** — config schema break (`docs-cockpit.yaml` shape changes incompatibly). None yet.

A change to `skills/*/SKILL.md` is by definition at least minor — those files are loaded into Claude's context, and stale ones cause hard-to-debug routing bugs.

## Architecture · the big picture

### Build pipeline (build.py)

`docs-cockpit build` does this end-to-end:

1. Load `docs-cockpit.yaml` from CWD or `--config` path
2. `_build_vars()` resolves `{repo}` / `{home}` / `{env:X}` / `{main_repo}` path variables
3. `_resolve_group_files()` walks `modules:` / `concepts:` config (supports `files:` / `scan:` / `glob:`)
4. For each MD: `read_md()` → `split_frontmatter()` → `_build_card()`
   - `_build_card()` also calls `_resolve_and_embed_docs()` which reads each linked doc's MD content into the payload (so the drawer can render inline · added 0.7.1) and `extract_subtasks_from_body()` / `extract_docs_from_body()` for body-section fallback (added 0.4.0)
5. `validate_meta()` emits structured `Issue` objects with `severity / field / message / suggestion / reference` (the reference points to a section of `references/schema.md`)
6. `build_payload()` returns `(payload, issues)` · payload is the JSON structure embedded in HTML; issues are surfaced both to stdout (three-section formatted) and to `state.json::issues[]`
7. `render_html()` does a single `template.replace("__DOCS_JSON__", json)` — the template (`docs_cockpit/templates/index.html.tmpl`) is otherwise static; all rendering is client-side JS
8. Writes `docs/index.html` + `docs/state.json` side-by-side

The `state.json` is the **machine-readable sidecar** consumed by:
- `docs-cockpit-standup` skill (single-project narrative)
- `docs-cockpit-portfolio` skill (cross-project weekly + week-over-week diff via snapshots)
- Any CI / external tool that wants invariant checks

The CLI dispatcher is `main()` in `build.py`. It wires subparsers for: `build`, `init`, `migrate` (from `migrate.py`), `browse` (from `browse.py`), `upgrade` (from `upgrade.py`), `portfolio` (from `portfolio.py`), `lint`. New subcommands are added by writing a module + calling its `add_<name>_parser(sub)` from `main()`.

### The four skills · scope discriminators

The four skills in `skills/` form a deliberate division — each has a description that includes a discriminator paragraph stating when to defer to a sibling:

| Skill | Scope | Reads | Writes |
|---|---|---|---|
| `docs-cockpit` | One cockpit · setup + maintain + upgrade docs-cockpit itself | `docs-cockpit.yaml` | `docs-cockpit.yaml` + HTML + runs CLI |
| `docs-cockpit-standup` | One project · narrative status | `docs/state.json` | nothing |
| `docs-cockpit-portfolio` | Multiple projects · weekly reports + diffs | `~/.docs-cockpit/projects.yaml` + each project's `state.json` + snapshots | `~/.docs-cockpit/snapshots/<name>/<date>.json` (via `portfolio snapshot` CLI) |

`references/schema.md` is the **single source of truth** for the frontmatter schema, body section conventions, file naming, and cross-doc reference rules (it absorbed the former author skill in v1.0). The validator's `Issue.reference` field points at sections of this file (e.g. `📚 references/schema.md · frontmatter schema`). **Do not duplicate the schema elsewhere** — every skill, README section, and CLI message should reference it for canonical definitions.

### Skill design conventions (from skill-creator)

Skills are written following the conventions of the `anthropic-skills:skill-creator` skill that this repo uses for guidance:

- **Frontmatter `description` is pushy** — over-triggers rather than under-triggers · includes both positive trigger phrases ("when the user says…") AND a `Do NOT trigger for…` discriminator paragraph naming the sibling skill that handles the negative case
- **Skill body explains the WHY** — not just rote `MUST`s · `skills/docs-cockpit-build/SKILL.md`'s "## Why this skill exists" paragraph is the canonical example
- **Skill names ≠ slash command names** — in 0.9.0 we renamed `docs-cockpit-status` → `docs-cockpit-standup` precisely because the `/docs-cockpit:status` slash command looked like a duplicate. If you add a new skill, check `commands/` and pick a non-colliding name.

### The bootstrap pattern (plugin without CLI pre-installed)

The plugin is markdown-only — Claude Code's plugin system can't pip-install Python packages on install. So the main skill (`skills/docs-cockpit/SKILL.md`) has a **first-build bootstrap** section: before running any `docs-cockpit <subcommand>`, the skill checks `docs-cockpit --version` and, if missing, runs `uv tool install` / `pipx install` / `pip install --user` in priority order.

Tell the user transparently when this happens ("Installing the docs-cockpit Python toolkit via uv (one-time setup)…") — don't bury the bootstrap in silence.

### Portfolio (multi-project) layout

User-level registry + snapshots live under `~/.docs-cockpit/`:

```
~/.docs-cockpit/
├── projects.yaml                    # registry · managed by `docs-cockpit portfolio` CLI
└── snapshots/
    └── <project-name>/
        └── <YYYY-MM-DD>.json        # weekly state.json copy · for week-over-week diff
```

Path handling uses `pathlib.Path.home()` for cross-platform (Windows `C:\Users\<name>\` · POSIX `/home/<name>/`). Always write the registry via the CLI (`portfolio add/list/remove/tag`) not by hand-editing — the CLI normalizes paths and uses `yaml.safe_dump` for consistent formatting.

## Language conventions in this repo

This repo follows the global `~/.claude/CLAUDE.md` language layering with one specific sub-override:

- **Python code comments**: 中文 prose · English technical terms (matches global rule)
- **`skills/*/SKILL.md` body**: **English** — these are cross-locale docs read by AI agents on machines in any locale; English provides stable trigger matching. Trigger phrases inside the description can include Chinese phrases for matching Chinese user inputs.
- **`commands/*.md`**: English (slash command docs · same reasoning as SKILL.md)
- **CHANGELOG.md entries**: English subject line under `### Added`/`### Changed`/etc · 中文 prose for the descriptions (matches global "human-collaboration prose → 中文")
- **README.md / README.zh-CN.md**: bilingual siblings · keep them in sync structurally · EN is primary
- **Commit subjects + PR titles**: English (machine-faced · grep-able)
- **Commit bodies + PR bodies**: 中文 (human-collaboration prose)

## Easy-to-break things (project-specific gotchas)

- **HTML template tokens**: `templates/index.html.tmpl` has exactly one placeholder, `__DOCS_JSON__`. Any JS string literal that happens to contain `__DOCS_JSON__` will be silently replaced on build. Avoid that string in template content other than as the intended placeholder.
- **Frontmatter validator severity routing**: A `severity: error` means "the dashboard literally won't render this doc". Don't downgrade an error to warn without thinking about whether the build still produces something meaningful — error issues are read by CI scripts via `--strict` to fail builds.
- **`references/schema.md` schema changes**: any change to the frontmatter schema section MUST be paired with a matching update to `docs_cockpit/schema.py::validate_meta()`. The validator and the spec drift apart silently if you forget — users get warned about things the spec says are fine, or vice versa.
- **State.json schema**: stable since 0.2.0 (only added fields, never removed). External tools depend on `modules[*]` having stable fields. The 0.9.0 `issues[]` addition is opt-in; `warnings[]` was retained for backward compat.
- **`docs:` path resolution**: implemented in `_resolve_doc_path()` with three-step fallback (absolute → relative to source MD → relative to repo root). Don't simplify this — the three-step fallback exists specifically to fix a real bug from 0.7.0 (`docs/docs/foo.md` doubling).
- **Plugin marketplace cache + ghost state**: changing a SKILL.md and pushing alone is not enough — users must run `docs-cockpit upgrade` (which clears the cache atomically). Don't tell users to just "restart Claude Code" — that doesn't clear the cache and produces ghost state.
- **Windows path separators in tests**: when smoke-testing on Windows, paths print with backslashes; in `state.json` they're stored as-is (so `D:\\harvey_work\\...`). Templates and JS handle both via `replace(/\\/g, '/')` at the use site — don't normalize at the build layer.

## Where to look first when working on a change

| Change kind | Start here |
|---|---|
| New CLI subcommand | `docs_cockpit/build.py::main()` (argparse wiring) + new module if substantial |
| New build feature | `docs_cockpit/build.py::cmd_build` and `build_payload` |
| New skill | `skills/<name>/SKILL.md` + update sibling skills' "Scope" sections to mention the new one |
| New slash command | `commands/<name>.md` |
| New frontmatter field | `docs_cockpit/build.py::_build_card()` + `validate_meta()` + `references/schema.md` |
| HTML / drawer / dashboard UI | `docs_cockpit/templates/index.html.tmpl` (~2000 lines · most of the work is CSS + the JS at the bottom) |
| Tree-sidebar reader UI | `docs_cockpit/templates/browse.html.tmpl` |
| Multi-project / portfolio | `docs_cockpit/portfolio.py` + `skills/docs-cockpit-portfolio/SKILL.md` |
| Schema spec / authoring conventions | `references/schema.md` (the canonical source) |

## References (in-repo)

- `references/config_reference.md` — full `docs-cockpit.yaml` field reference
- `references/schema.md` — frontmatter & anchor field spec (the canonical SSOT)
- `references/frontmatter_conventions.md` — frontmatter governance (supplements `references/schema.md`)
- `references/design_tokens.md` — HTML template design system
- `CHANGELOG.md` — every release entry has a "Why" section explaining the user-visible motivation; read it before changing related code
