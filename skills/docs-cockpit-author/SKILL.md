---
name: docs-cockpit-author
description: |
  Write project docs (module / concept / plan / RFC / spec) that the docs-cockpit dashboard can render correctly. This skill is the **canonical spec** for the frontmatter schema, body section conventions, file naming, and cross-doc references that every doc in a docs-cockpit project must follow. If you skip the spec, the dashboard either drops the doc silently (no `id` → invisible) or renders it with broken state (wrong status × progress, missing `docs:` linkage, empty drawer).

  TRIGGER this skill aggressively · use it WHENEVER any of these happen — don't wait for the user to name the skill:
  (a) the user asks to write / draft / create / scaffold a plan / RFC / spec / module-MD / concept-MD for a project that has docs-cockpit installed (i.e. has `docs-cockpit.yaml`);
  (b) the user pastes a frontmatter snippet and asks "is this right" / "怎么写 frontmatter" / "为什么这条没出现在看板上";
  (c) `docs-cockpit build` printed `❌` / `⚠️` / `💡` lines (the structured validation output) — surface them to the user and walk through the fix;
  (d) `docs-cockpit lint` output was non-empty;
  (e) the user copied a "Plan / RFC / Spec prompt" from a docs-cockpit dashboard's empty-docs CTA and asked you to execute it;
  (f) the user says any of: "怎么让 module 显示在看板上", "为什么我的 plan 没被识别", "frontmatter 该填什么", "docs-cockpit 的文档规范是什么", "how do I link a plan to a module", "what fields are required", "what's the status enum", "add subtasks to this module";
  (g) you are about to write a docs/{plans,RFC,spec,memory}/*.md file in a docs-cockpit project — read this skill first so the frontmatter & body conform.

  Do NOT trigger for: docs-cockpit setup (use `docs-cockpit` skill instead — that one writes `docs-cockpit.yaml` and runs build); status / standup reports from an existing cockpit (use `docs-cockpit-standup`); upgrading docs-cockpit itself (use `docs-cockpit upgrade` CLI). The discriminator: this skill is about **writing a single project doc that the dashboard will pick up** — the OUTPUT of this skill is a markdown file. If the user wants to scan/aggregate/configure the dashboard → use `docs-cockpit`. If the user wants narrative status interpretation → use `docs-cockpit-standup`.
---

# docs-cockpit-author

**The unified spec for writing docs that the docs-cockpit dashboard understands.**

The dashboard reads YAML frontmatter and body sections from each markdown file. If the schema doesn't match, the doc either silently disappears (no `id`), renders with wrong state, or shows the empty-docs warning chip. This skill is what you check against **before** writing any project doc.

## Why this skill exists

The cockpit has been around for 8 months and we kept changing conventions ad-hoc. Result: in one real project (Sourcery, ~24 modules), 19 modules had no `docs:` linkage, 24 had no `desc:`, and `## TODO` vs `## 待办` vs `## Subtasks` were used interchangeably with no validation. Humans couldn't follow it either. This skill fixes that by:

1. **Writing the spec down** in one place so Claude and humans agree
2. **Making the validator strict and actionable** — every issue points to a section in this skill
3. **Refusing to write a doc that doesn't conform** without first asking the user to confirm the deviation

If the validator (`docs-cockpit lint` / `build`) emits `❌ … see: docs-cockpit-author · §N`, that `§N` is a section below. Quote it back to the user.

## §1 · The five doc kinds

Every markdown file in a docs-cockpit project is one of:

| Kind | Location | YAML `type` | Purpose |
|---|---|---|---|
| **module** | `docs/spec/module/MNN-*.md` | `module` | A code-level unit of work · gets a Kanban card |
| **concept** | `docs/spec/concept/CNN-*.md` | `concept` | A shared abstraction · gets a Concept Grid tile |
| **plan** | `docs/plans/YYYY-MM-DD-<id>-plan.md` | `plan` | Time-boxed execution plan for a module |
| **rfc** | `docs/RFC/NNN-<slug>.md` | `rfc` | Technical decision · compares options |
| **spec** | `docs/spec/<id>-spec.md` | `spec` | Formal interface contract (API · data model) |

`memory` and `roadmap` are also valid `type` values for system-level docs (e.g. `CLAUDE.md`, `docs/ROADMAP.md`) that appear in the "System Docs" drawer · they don't get individual cards.

**Picking a kind:** ask yourself "what does this doc do for the project?"
- "It's a thing being built" → **module**
- "It's an idea/pattern shared by multiple modules" → **concept**
- "It says how/when we'll build it" → **plan**
- "It explains why we chose approach A over B" → **rfc**
- "It defines the contract other code must obey" → **spec**

Don't pick "plan" if you mean "spec". Don't pick "module" if you mean "concept". The validator can't catch this mismatch, but the dashboard groups by kind, so picking wrong puts the doc in the wrong place.

## §2 · Frontmatter schema

Every doc starts with a YAML frontmatter block:

```yaml
---
id: M07
type: module
title: "Job / Task FSM"
status: in-progress
sprint: M1.2
progress: 60
desc: "Job lifecycle state machine · drives worker scheduling"
owner: harvey
prd_ref: "§7.4.1"
docs:
  - { title: "Execution plan", path: "docs/plans/2026-05-03-m07-fsm-plan.md" }
  - { title: "FSM spec", path: "docs/spec/m07-fsm-spec.md" }
depends_on: [M06]
blocks: [M08, M09]
---
```

### §2.1 · Required fields

**`id`** — REQUIRED. Without it the doc is silently dropped from the dashboard (the build only counts entries with `id`).

- Convention: `M01`-`M99` for modules · `C01`-`C99` for concepts · `RFC-001` for RFCs · `<MODULE-ID>-PLAN-<date>` for plans · `<MODULE-ID>-SPEC` for specs
- MUST be unique across all docs (validator does NOT enforce this yet, but the dashboard will collide silently)
- NEVER use placeholder ids containing `XX` or ending in `XXX` — the validator emits a warning and the entry is skipped

### §2.2 · status enum

**`status`** — RECOMMENDED. Without it the dashboard treats the module as `not-started`. Pick exactly one:

| value | meaning | progress range |
|---|---|---|
| `not-started` | not in flight · nobody's looked at it | `0` only |
| `planned` | scoped + sprint-assigned but not started | `0`-`15` |
| `in-progress` | being actively worked on | `5`-`95` |
| `blocked` | started but stuck on dependency / decision | `0`-`100` |
| `done` | merged + verified | `100` only |
| `deferred` | intentionally pushed to a later sprint | `0`-`100` |

The validator (`§2.3`) enforces the progress range per status.

### §2.3 · status × progress invariants

**`progress`** is an integer 0-100. The validator emits a `warn` if it's out of the band defined for the current status:

```
status=done       → progress must be 100
status=not-started → progress must be 0
status=planned    → progress in [0, 15]   (scoping ≠ doing)
status=in-progress → progress in [5, 95]   (5 = some commit landed · 95 = needs final review)
```

When out of range, either move `status` forward or bring `progress` back to the band. Pick whichever describes reality.

### §2.4 · doc type enum

**`type`** — optional but recommended. One of: `module`, `concept`, `plan`, `rfc`, `spec`, `memory`, `roadmap`. The validator warns on unknown values.

This affects nothing in the dashboard rendering today, but the author skill uses it to pick the right body template, and lint will eventually use it to validate kind-specific fields (e.g. `rfc` needs `status: draft|reviewing|accepted|superseded`).

### §2.5 · Recommended fields

- **`title`** — display name in the Kanban card. Defaults to filename stem if missing — usually fine but won't be pretty
- **`sprint`** — string · e.g. `M1.2` · drives the Sprint Timeline grouping. Without it the Sprint view shows "unscheduled"
- **`desc`** — one-line description shown in the drawer. **Without `desc`, the copy-prompt feature gets weaker context** because it falls back to a body excerpt. Validator emits a `hint` if missing
- **`owner`** — string · just a name · surfaces in the drawer

### §2.6 · Cross-doc reference fields

**`docs`** — list of `{title, path}` linking to plans / RFCs / specs that elaborate this module. Path is **relative to the repo root** (NOT relative to the source file). The build resolver tries absolute → relative-to-source → relative-to-repo so older patterns still work.

```yaml
docs:
  - { title: "RFC-002 · ResourcePool",       path: "docs/RFC/002-resource-pool.md" }
  - { title: "Round 3 plan · build sequence", path: "docs/plans/round-3-build-house.md" }
```

If you don't fill `docs:` in frontmatter, the body fallback (§4) takes over.

**`depends_on`** / **`blocks`** — lists of other module ids. Currently informational (not rendered yet) but the author skill writes them so dependency graph features can be added later.

**`prd_ref`** — string · the PRD section reference that motivates this doc · e.g. `"§7.4.2 + §9.2"`. Surfaces in the drawer.

## §3 · The "docs vs subtasks" decision

This is where people get confused. Two related but different concepts:

| Concept | Lives where | Used for | Captured by |
|---|---|---|---|
| **subtasks** | `subtasks:` frontmatter list OR `## TODO` / `## 待办` body section | Granular work items WITHIN this doc · drives progress auto-calc | Drawer checklist |
| **docs** | `docs:` frontmatter list OR `## Related` / `## 关联` body section | Links to OTHER docs that elaborate / depend on this | Drawer "Linked Docs" list |

**Rule of thumb:**
- Sub-bullets of work you'll do yourself → `subtasks`
- References to other markdown files that describe details → `docs`

If you're tempted to put a "see also" link in `subtasks:`, it's `docs:`. If you're tempted to put a checkbox in `docs:`, it's `subtasks:`.

### §3.1 · subtasks format

Two equivalent forms (pick one per doc, don't mix):

**Form A · frontmatter (precise control):**
```yaml
subtasks:
  - { title: "wire FSM enum to Pydantic", done: true }
  - { title: "worker pulls next state from queue", done: false }
```

**Form B · body section (more readable in raw MD):**
```markdown
## TODO

- [x] wire FSM enum to Pydantic
- [ ] worker pulls next state from queue
```

Or `## 待办` for Chinese projects. The build auto-extracts `- [ ]` / `- [x]` checkboxes from sections matching `## TODO` / `## 待办` / `## Subtasks` / `## 任务`.

**Frontmatter wins**: if both forms are present, frontmatter `subtasks:` overrides body extraction.

### §3.2 · docs format

Similar two forms:

**Form A · frontmatter (precise · with titles):**
```yaml
docs:
  - { title: "Execution plan", path: "docs/plans/2026-05-03-m07-fsm-plan.md" }
```

**Form B · body section:**
```markdown
## Related

- [Execution plan](docs/plans/2026-05-03-m07-fsm-plan.md)
- [FSM spec](docs/spec/m07-fsm-spec.md)
```

Or `## 关联` / `## 参考` / `## Links` for Chinese / shorter. The build auto-extracts markdown links from these sections.

## §4 · File naming conventions

| Kind | Pattern | Example |
|---|---|---|
| module | `docs/spec/module/M<NN>-<kebab-slug>.md` | `M07-job-task-fsm.md` |
| concept | `docs/spec/concept/C<NN>-<kebab-slug>.md` | `C03-data-schema.md` |
| plan | `docs/plans/<YYYY-MM-DD>-<module-id-lower>-plan.md` | `2026-05-03-m07-fsm-plan.md` |
| rfc | `docs/RFC/<NNN>-<kebab-slug>.md` | `002-resource-pool.md` |
| spec | `docs/spec/<id-lower>-spec.md` | `m07-fsm-spec.md` |

- `<NN>` is two digits zero-padded for the first 99 (`01`, `02`, ..., `99`), then unpadded (`100`, `101`, ...)
- `<kebab-slug>` is lowercase, hyphen-separated, no spaces, no special chars
- Module ids in filenames are lowercase (`m07-...`) but the `id:` field stays uppercase (`M07`)
- Plan filenames lead with date for chronological sort

## §5 · Validation flow (when build emits issues)

When `docs-cockpit build` or `docs-cockpit lint` prints output like:

```
❌ M07-job-task-fsm.md · id: missing required field — module/concept won't appear in dashboard
   💡 fix: add `id: M01-...` to frontmatter
   📚 see: docs-cockpit-author · §2.1 required frontmatter
```

You (Claude) should:

1. **Read each `❌` and `⚠️`** — explain to the user what each one means in plain words
2. **Look up the referenced section** (e.g. `§2.1`) in this skill and quote the relevant paragraph
3. **Propose the exact fix** (the `💡 fix:` line is a starting point but often needs project-specific values)
4. **ASK THE USER for confirmation** before editing their docs en masse — especially for `error` severity. Say something like:

   > "I see 3 errors and 5 warnings in your modules. The errors mean those modules won't appear on the dashboard at all. Should I fix them with the suggested defaults, or do you want to review each one?"

5. **Hint-level issues** (💡) can usually be fixed in batch without asking (e.g. adding empty `desc:` placeholders) but flag the batch in advance.

**Never** silently fix `error` issues. The user's `id:` choice (e.g. `M07` vs `M-FSM-07`) is project-specific; you can suggest but must confirm.

## §6 · Working with the dashboard's copy-prompt CTA

The dashboard shows a "Copy Plan/RFC/Spec prompt" panel on any active module that has no `docs:` linkage. When the user pastes one of those prompts to you (or to another AI editor):

1. **Read this skill first** — the prompts reference frontmatter fields and body sections defined here
2. **Pick the matching file location** from §4
3. **Write the frontmatter strictly per §2** — particularly `type`, `status`, the linkage back to the source module via `blocks: [...]` for RFCs, etc.
4. **After writing, update the source module's frontmatter** to add the link in `docs:` (the prompts include this reminder · don't forget it)
5. **Run `docs-cockpit lint` to verify** — if it's still emitting issues you missed something

## §7 · Tooling interop

This skill is designed to be compatible with other doc-authoring tools the user might have:

- **superpowers** (Claude Code plugin) — has `/plan`, `/spec`, `/rfc` slash commands that scaffold similar files. If superpowers is installed, defer to its commands for the scaffold step, then post-process to align frontmatter with §2
- **gstack** — has its own plan/spec/rfc generators. Same pattern: use gstack for scaffolding, then conform to §2
- **Cursor / Codex / Continue / Aider** — no scaffolding tools, but the cockpit's copy-prompt provides a complete prompt; paste it into chat and the editor writes the file

In all cases, the source-of-truth for "is this doc going to render correctly" is `docs-cockpit lint`. After any scaffolding tool, run it.

## §8 · Anti-patterns (don't do these)

- ❌ Putting checkboxes (`- [ ]`) in `docs:` — they're for subtasks
- ❌ Putting file links (`[text](path.md)`) in `subtasks:` — those are for `docs:`
- ❌ Using `progress: "75%"` (string with `%`) — must be integer 0-100
- ❌ Mixing `## TODO` and `## 待办` in the same project — pick one
- ❌ Filenames with spaces, capital letters in slug, or non-ASCII — break URLs
- ❌ `id:` placeholders containing `XX` or ending `XXX` left in committed files — the build skips them
- ❌ `docs:` paths relative to the source MD file's directory — must be repo-root-relative (build resolver tries fallbacks but it's fragile)
- ❌ Writing a `plan` doc but using `type: rfc` (or vice versa) — pick the kind that matches what the doc DOES

## §9 · Quick reference card

When asked to scaffold a new doc, output this minimal valid frontmatter as starting point, then fill body per §3:

**module:**
```yaml
---
id: MNN
type: module
title: "<one-line title>"
status: planned
sprint: M<X.Y>
progress: 0
desc: "<one-line description · drives drawer + copy-prompt context>"
owner:
prd_ref:
docs: []
depends_on: []
blocks: []
---
```

**plan:**
```yaml
---
id: <MODULE-ID>-PLAN-<YYYY-MM-DD>
type: plan
title: "<module-title> · execution plan"
status: planned
sprint: <inherit from module>
owner:
prd_ref:
---
```

**rfc:**
```yaml
---
id: RFC-<NNN>
type: rfc
title: "<one-line decision title>"
status: draft         # draft → reviewing → accepted → superseded
sprint: <if applicable>
prd_ref:
owner:
depends_on: []
blocks: [<source-module-id>]
---
```

**spec:**
```yaml
---
id: <MODULE-ID>-SPEC
type: spec
title: "<module-title> · interface spec"
status: draft
sprint: <inherit from module>
owner:
depends_on: []
---
```

After scaffolding, **always** add to the source module's frontmatter:
```yaml
docs:
  - { title: "<short label>", path: "docs/<plans|RFC|spec>/<the-file-you-just-wrote>" }
```

This is the cross-link the dashboard needs to render the connection.
