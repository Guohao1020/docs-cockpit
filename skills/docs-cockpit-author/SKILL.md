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

### §3.1 · subtasks format (v0.11 object schema · 向后兼容 v0.10)

v0.10 用 `list[str]` · v0.11 升到 object schema with `id / title / status / code / docs`. The string form keeps working — validator treats a bare string as `{title: <string>}` and generates the rest. Three equivalent forms:

**Form A · frontmatter object array (v0.11 · 最高精度 · 支持 code/docs anchor):**
```yaml
subtasks:
  - id: M09-S1                                       # optional · auto-derived from title if missing
    title: "wire FSM enum to Pydantic"
    status: done                                     # not-started | in-progress | done | blocked
    code: sourcery/worker/fsm.py:42-89               # single anchor · or list for multi-file
    docs:
      - docs/spec/module/M09-browser-cluster.md#§2.1
      - docs/RFC/RFC-004-fsm-redesign.md:128-180
  - title: "worker pulls next state from queue"      # bare title also fine · id auto-derived
    status: not-started
```

**Form B · frontmatter v0.10 legacy (string list):**
```yaml
subtasks:
  - "wire FSM enum to Pydantic"                      # treated as {title, done:false, id:auto}
  - "worker pulls next state from queue"
```

The validator emits a `hint` on string form and points to `docs-cockpit migrate-subtasks` (one-shot upgrade · see end of this section).

**Form C · body section with inline annotations (v0.11.0-alpha.2 · diff-friendly · what this repo uses for its own modules):**
```markdown
## 3 · 待办

- [x] wire FSM enum to Pydantic @code:sourcery/worker/fsm.py:42-89 @docs:docs/spec/module/M09.md#§2.1
- [ ] worker pulls next state from queue @code:sourcery/worker/main.py:120-180 @docs:docs/RFC/RFC-004.md:128-180
```

**Accepted heading forms** (since 0.14.3 · parser regex was tightened up):

| Form | Example | Notes |
|---|---|---|
| Plain | `## 待办` / `## TODO` / `## Subtasks` / `## 任务` | bare keyword |
| Number-prefixed | `## 3 · 待办` / `## 4. TODO` / `## 3 - Tasks` | digit + optional `·` / `.` / `-` separator |
| **§-prefixed** | `## §4 · 待办` / `## §3.2 · 任务` | for plan / RFC style heading numbering(0.14.3 加 · M08/M09/M10 dogfood 反馈) |
| **3rd-level+** | `### 待办` / `#### TODO` | any heading `##` through `######` |
| Tab-separated | `##\t待办` / `## §4\t待办` | tab works · `\s+` regex |
| Case-insensitive | `## todo` / `## Subtask` | `re.IGNORECASE` |

**Reject** the form `##待办` (no space between `##` and keyword) and `# 待办` (h1 too thin). Also reject random text like `regular text TODO` — must be a heading line.

The build's `extract_subtasks_from_body()` (in `schema.py`) does:

1. find a section matching one of the heading regexes
2. for each `- [x]` / `- [ ]` line: extract checkbox state → `done` boolean
3. run two regex sweeps over the rest of the line:
   - `@code:(\S+)` → all hits become `code` (single string if 1 hit, list if 2+)
   - `@docs:(\S+)` → same for `docs`
4. `title` = original line text minus all `@code:...` / `@docs:...` annotations, whitespace-collapsed

So `@code:` and `@docs:` can stack any number of times on one line · don't put spaces inside the anchor (`\S+` ends at whitespace).

**Frontmatter wins**: if both frontmatter `subtasks:` and body `## 待办` exist, frontmatter overrides — body is ignored. So pick one form per doc and stick to it.

### §3.1.1 · id algorithm + the title-is-identity tradeoff

When you write Form A or Form B without an explicit `id:`, the build auto-assigns:

```
id = <module-id> + "-" + sha1(title.strip())[:6]
```

Example · module M03, subtask title `"First-build bootstrap(uv tool / pipx / pip --user 优先级)"` → `M03-3bc28b`.

This is deterministic and stable **across builds** as long as the title doesn't change. The dashboard, prompts.js sidecar, and localStorage all key off this id — so changing the title:

- **breaks the localStorage override** (user's manual status flip on this subtask is lost)
- **rotates the id in `state.json::issues[].field`** (validator/CI tooling sees this as a different subtask)
- **invalidates any external reference** to the old id (e.g. a PR description that links to `#/module/M03?st=M03-3bc28b`)

**Rule of thumb · title is identity**:
- Small wording tweak ("ok" → "OK") · usually fine · id rotates · accept the storage loss
- Substantive rewrite (`"补 BrowserVendor abstraction"` → `"Lane A · BrowserVendor abstraction + LocalPlaywrightVendor"`) · explicitly pin the original id with `id: M09-S1` so storage / tooling keeps pointing at the right subtask
- Splitting one subtask into two · the new ones get new ids by design · don't try to preserve

You can always upgrade later: leave id auto-derived for new subtasks, only pin `id:` when you know you'll be rewording.

### §3.1.2 · code anchor format

The `code:` field on a subtask is parsed by `paths.py::_resolve_code_anchor`. Accepted shapes:

| Shape | Example | Meaning |
|---|---|---|
| `<path>` | `sourcery/worker/fsm.py` | whole file · preview = first ~40 lines |
| `<path>:<line>` | `sourcery/worker/fsm.py:42` | single line · preview = ±20 lines around it |
| `<path>:<start>-<end>` | `sourcery/worker/fsm.py:42-89` | line range · preview = exactly those lines |
| `[<anchor1>, <anchor2>, ...]` | `["worker/a.py:10-30", "worker/b.py:100-150"]` | multi-anchor · drawer renders N chevron buttons |

Path resolution is the **three-step fallback** (same as `docs:`): absolute → relative to source MD → relative to repo root. Stale anchors render with a `⚠ stale code anchor` warning in the preview pane (but don't fail the build · severity = warn).

The drawer surfaces a `vscode://file/<abs>:<line>` deep-link button on each anchor — clicking opens the file in VS Code at the right line.

**Resolved `code_anchors[]` entry shape** (after build · the payload your template / downstream tooling sees):

| Field | Type | Meaning | Use this when... |
|---|---|---|---|
| `path` | str | **raw user input** including any `:lines` suffix · e.g. `"worker/x.py:42-89"` | you want to display the user's literal anchor string (e.g. CLI output) |
| `path_only` | str (0.14.3+) | **clean path** without `:lines` · e.g. `"worker/x.py"` | building file references in templates · merging with `lines` separately · cross-anchor dedup |
| `lines` | str \| null | line range `"42-89"` / `"42"` / null | display "lines X-Y" badges · jump-to-line in editors |
| `resolved` | str | absolute path · empty if file not found | open / read the file from disk |
| `exists` | bool | file exists on disk | gate render(stale anchor warning) |
| `preview` | str | code snippet (truncated to 800 chars) | drawer code-preview pane |
| `vscode_url` | str | `vscode://file/<abs>:<line>` deep link | "Open in VS Code" button |
| `warning` | str | "" if ok · else stale / out-of-range / binary message | render `⚠` badge |

**Template rule of thumb**: use `{{ ca.path_only }}{% if ca.lines %}:{{ ca.lines }}{% endif %}` instead of `{{ ca.path }}:{{ ca.lines }}` — `path` already contains `:lines` if user wrote them, so double-appending produces `worker/x.py:42-89:42-89`. The 4 built-in `prompts/*.md.j2` and `suggest/bundle-recommendation.md.j2` templates do this since 0.14.3.

### §3.1.3 · docs anchor format (subtask level)

The subtask-level `docs:` field is a **list of strings** (not `{title, path}` dicts like module-level `docs:`). Parsed by `paths.py::_resolve_subtask_doc_anchor` (added 0.11.0-alpha.8). Accepted shapes:

| Shape | Example | Behavior |
|---|---|---|
| `<path>` | `docs/spec/module/M09.md` | whole file rendered in right pane (frontmatter stripped) |
| `<path>:<lines>` | `CLAUDE.md:88-100` | slice lines 88-100 (1-indexed · inclusive both ends · raw file lines · not stripping frontmatter) |
| `<path>:<line>` | `docs/plans/p.md:367` | slice single line |
| `<path>#<heading>` | `docs/plans/p.md#§6.2` | find first `## *<heading>*` line (substring match, case-insensitive) → slice from there to next same-or-higher heading |

The build pre-slices the content into `subtask.doc_anchors[i].content` at build time · the dashboard's right pane just runs `marked.parse(content)`. This avoids the unreliable "render the whole doc and try to highlight line 88-100 in the resulting HTML" problem — slicing happens on the source markdown before rendering.

100 KB hard cap per anchor (same as module-level docs).

**Resolved `doc_anchors[]` entry shape** (after build):

| Field | Type | Meaning |
|---|---|---|
| `raw` | str | **raw user input** including `:lines` / `#heading` · e.g. `"plan.md#§6.2"` |
| `raw_with_anchor` | str (0.14.3+) | alias of `raw` · 命名跟 `code_anchors[].path` 对称(都是 raw 串)· future-proof for v0.X+ deprecation of `raw` |
| `path` | str | **clean path** without anchor · e.g. `"plan.md"` |
| `lines` | str \| null | `"88-100"` / `"88"` / null(只 path / heading 时) |
| `heading` | str \| null | `"§6.2"` · null when lines-style or whole-file |
| `title` | str | heading 匹配上时取找到的 heading 文本(`"§6.2 · W3 Prompt scaffolding"`) |
| `resolved` | str | absolute path |
| `exists` | bool | file exists |
| `content` | str | sliced markdown text(100KB cap) |
| `mtime` | str \| null | `"YYYY-MM-DD HH:MM"` |
| `warning` | str | "" / `path not found` / `heading not found` |

**Template rule of thumb**: 对称命名 · `doc_anchors[].raw` ≡ `code_anchors[].path`(都是 raw 串)· `doc_anchors[].path` ≡ `code_anchors[].path_only`(都是 clean 路径)。0.14.3+ 加了 `raw_with_anchor` alias 让命名对称 · 未来 minor 可 deprecate `raw` 单字段。

### §3.1.4 · One-shot v0.10 → v0.11 migration

If your existing module MDs have `subtasks: list[str]`, run:

```bash
docs-cockpit migrate-subtasks docs/spec/module/M07-fsm.md            # dry-run · print diff · no file change
docs-cockpit migrate-subtasks docs/spec/module/M07-fsm.md --apply    # write back · generate .bak
```

The migrator:
- converts string → `{id, title, done, status}` (auto-derives id · maps `done: true` → `status: done`)
- preserves any existing object-form entries unchanged
- does NOT touch `code:` / `docs:` (that's net-new precision work you do per subtask — the `/docs-cockpit:refine` workflow does that)

Always show the user the dry-run output first · then `--apply`.

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

## §10 · prompt template chapter (0.11.0-alpha.3)

Prompt scaffolding (W3) renders module + subtask + linked docs + code anchor as a copy-pasteable prompt for Claude / Cursor / Codex.

### §10.1 · Built-in templates

4 templates live in `docs_cockpit/templates/prompts/`:

| name | purpose |
|---|---|
| `generic.md.j2` | default · works for any subtask |
| `feature.md.j2` | implementing new feature subtask |
| `fix.md.j2` | bug fix subtask · emphasizes root cause + regression test |
| `refactor.md.j2` | behavior-preserving change · Beck make-the-change-easy principle |

User can override by writing `docs/prompts/<name>.md.j2` in their repo · `ChoiceLoader` resolution order:
1. `<repo>/docs/prompts/<name>.md.j2` (user override)
2. `docs_cockpit/templates/prompts/<name>.md.j2` (built-in)

Template selection precedence (when rendering):
1. CLI flag `docs-cockpit prompt M01 M01-S1 --template <name>`
2. subtask frontmatter `prompt: <name>`
3. module frontmatter `prompt_kind: <name>` (must be in `{feature, fix, refactor}`)
4. fallback `generic`

### §10.2 · Context vars stability contract

Templates receive 5 context vars (v0.11):

| var | type | description |
|---|---|---|
| `module` | dict | module's full frontmatter + body |
| `subtask` | dict | the specific subtask · contains `code_anchors[]` (alpha.2) |
| `linked_docs` | list[dict] | each `{title, path, summary}` · summary is doc body hard-capped at 2000 chars |
| `repo_root` | str | absolute path |
| `current_branch` | str \| None | lazy git rev-parse · None when git unavailable (CI / tarball) |

**Backward-compat rules for future minor versions**:

- **No-remove / no-rename** of existing vars in any minor release. Deprecate first (emit warning) · keep at least two minor cycles · remove only in major.
- **New vars must be guarded** in built-in templates · use `{{ new_var | default('') }}` or `{% if new_var %}...{% endif %}` so user templates that pre-date the new var still render fine.
- **SandboxedEnvironment configured with `Undefined`** (not `StrictUndefined`) · references to undefined vars render empty string · graceful degrade.

When v0.12 / v0.13 add new vars · update this section with the `since-version` tag.

## §11 · Writing module MD with AI assistance (0.11.0-alpha.7 · 模式 3)

The driver-seat plan locks in v0.11 §0:**docs-cockpit is the AI's co-pilot · not a self-contained precision engine**. Semantic precision comes from LLM · python only handles parsing-layer (anchor syntax / line numbers / heading slugs).

This section teaches Claude / Codex / Cursor **how to produce high-precision module MD** at write-time · so users don't need to manually figure out which plan section a subtask should anchor to.

### §11.1 · The standard authoring flow

When a user says **"帮我写 M07 build worker module · plan 在 driver-seat plan §6 · 代码在 sourcery/worker/"** or similar request to write / refine a module · follow this flow:

1. **Read the relevant plan / RFC / spec body** (NOT grep · actually read · understand what each section says)
   - User typically references a sprint plan / driver-seat plan / module-related RFC
   - Map out each section's intent before drafting subtasks
2. **Cross-reference to decompose subtasks**
   - Each subtask should map to a specific plan section / RFC decision
   - Use the plan's terminology in `subtask.title` · keep semantic alignment
   - Don't invent subtasks the plan didn't sanction · if you see a gap · flag it instead of silently filling
3. **Fill precise `code:` anchors**
   - Actually read the repo · find the file + function + line range the subtask will touch
   - Output `code: docs_cockpit/build.py:42-89` (with line range) · NOT `code: docs_cockpit/` (whole directory · unhelpful)
   - If multiple files involved · use list: `code: [a.py:10-30, b.py:50]`
   - If code doesn't exist yet (new file) · use just `code: docs_cockpit/new_module.py` (no lines · marks intent)
4. **Fill precise `docs:` anchors**
   - Use `docs/plans/x.md#§6.1` (heading anchor) or `docs/plans/x.md:120-180` (line range) to point to specific plan section
   - NOT just `docs/plans/x.md` (whole doc · user has to find the relevant part)
   - Multi-reference is fine: `docs: ['plan.md#§6.1', 'rfc-003.md', 'spec.md#§2']`
5. **Cross-subtask consistency self-check**
   - Adjacent subtasks have dependency hints in title ("Lane A 完成后做 Lane B")
   - Same plan section referenced by multiple subtasks · check if over-fragmented (merge if so)
   - subtask `status` × module-level `status` alignment (alpha.4 validator catches this · pre-empt)

### §11.2 · Example · good vs bad

**Bad** (low precision · validator passes but driver-seat experience is "open a 600-line doc · find it yourself"):

```yaml
subtasks:
  - title: "build worker"
    code: "sourcery/worker/"
    docs: "docs/plans/driver-seat.md"
```

**Good** (high precision · drive-seat right preview goes straight to the relevant section + code snippet):

```yaml
subtasks:
  - id: M07-S1
    title: "BrowserVendor abstraction · Lane A"
    status: in-progress
    code: "sourcery/worker/browser_vendor.py:42-89"
    docs: ["docs/plans/driver-seat.md#§6.1", "docs/RFC/004-browser-vendor.md"]
  - id: M07-S2
    title: "LocalPlaywrightVendor impl · Lane B (depends on Lane A)"
    status: not-started
    code: "sourcery/worker/local_playwright_vendor.py"
    docs: "docs/plans/driver-seat.md#§6.2"
```

### §11.3 · When in doubt · output a draft + ask

If you can't find a clear plan section for a subtask · don't fabricate an anchor. Two acceptable patterns:

1. Output the subtask without `docs:` · let the validator emit hint「无文档支撑」· user adds later
2. Add a TODO comment: `# TODO: anchor this subtask once plan §X clarifies` · so the user knows you couldn't resolve

Better honest gap than wrong anchor that breaks user trust in the dashboard.

## §12 · Cross-module / cross-doc consistency self-check (0.11.0-alpha.7)

After producing or refining a module · run this checklist:

### §12.1 · Doc backref check

If a single plan / RFC is referenced by multiple modules · check that their anchors don't overlap pointlessly:

- M01 references `plan.md#§6.1` (W1 数据层 section)
- M02 references `plan.md#§6.2` (W3 prompt section)
- M03 references `plan.md` (no anchor · only valid if M03 is about the plan's overall narrative)

If two modules anchor to the same section · ask: are they really doing the same work? If yes · merge them. If no · find more specific anchors for each.

### §12.2 · Module dependency closure

If you set `depends_on: [M02]` on M01 · then M02 should have `blocks: [M01]` (or vice versa). Validator doesn't enforce this yet but the author skill should produce consistent pairs.

### §12.3 · subtask status × module status

If you mark `status: done` on a module · all subtasks should also be `done` (or at least the same). alpha.4 cross-field validator catches this · but pre-empt:

- 9 subtasks done + 1 not-started · module status should be `in-progress` not `done`
- If user explicitly wants `done` despite incomplete subtasks · question it (might be wrong)

### §12.4 · Sprint alignment

All subtasks should belong to the same sprint as the module · or be explicitly deferred. Mixed-sprint subtasks usually means the module needs splitting.

## §13 · How to consume `docs-cockpit suggest` output (0.12.0+ · M10)

`docs-cockpit suggest [module_id]` outputs **soft-recommendation prompts** for AI to act on — different from `docs-cockpit lint` which outputs **hard validation errors**. The 4 built-in templates (`desc-rewrite` / `subtask-recompose` / `anchor-completeness` / `cross-doc-consistency`) all emit prompts following the same caller-aware pattern as Refine and Copy prompt.

### §13.1 · The 5-step flow (matches §11)

When you receive a `docs-cockpit suggest` output (one or more concatenated prompts):

1. **Read each prompt's `## 问题诊断` / `## 诊断` section** — understand what the heuristic flagged
2. **Read the linked docs the prompt references** — use the `Read` tool · don't ask the user to paste
3. **Decide which suggestions to take** — not all triggered suggestions are worth acting on (e.g. `subtask-recompose` for a stable module that just happens to have 16 subtasks)
4. **Apply changes directly** (if you have `Edit` / `Write` tools) — edit the source MD · don't output patches for the user to copy
5. **Re-build** — run `docs-cockpit build` to verify · re-run `docs-cockpit suggest <module>` to confirm the trigger no longer fires

### §13.2 · Per-template guidance

- **`desc-rewrite`** · output a 1-line concrete `desc:` (<100 chars) · edit frontmatter directly · prefer specifics over abstractions
- **`subtask-recompose`** · if >15 subtasks · propose merging adjacent ones OR splitting the module into sibling modules (M0X-a / M0X-b) · if <3 · split each into 2-3 finer subtasks aligned to plan sections
- **`anchor-completeness`** · for each subtask missing `@code:` / `@docs:` · Read the relevant plan section + repo · pin to `path:start-end` / `path#§N.M` · don't guess line numbers
- **`cross-doc-consistency`** · run all 4 §12 checks · report `clean` per check OR specific fixes per issue · never silently skip a check

### §13.3 · `--strict` mode (CI integration)

```bash
docs-cockpit suggest --all --strict
```

Exits 1 if any module triggers any suggestion. Useful as a CI quality gate — alongside `docs-cockpit lint --strict` which catches hard schema errors. Together they form the "no MD ships without both passing" workflow.

### §13.4 · Custom suggest templates

Drop `docs/suggest/<name>.md.j2` in the user repo · the `ChoiceLoader` picks them up before the built-in `templates/suggest/*.md.j2`. Same `SandboxedEnvironment` rules as `prompt` / `refine` templates (no `os` / no `import` · only Jinja built-ins).

Context vars available to suggest templates:
- `module` · the full module dict from state.json
- `linked_docs` · list[{title, path, summary}] · summary capped at 2000 chars
- `repo_root` · str
- `thresholds` · dict with `desc_min_chars` / `subtasks_max` / `subtasks_min`


## §14 · Bundle heuristics (0.14.0+ · M17 batch driver)

When the user wants to **run multiple subtasks together** (via `docs-cockpit prompt --bundle <ids>` or the dashboard's Backlog multi-select), help them decide which subtasks bundle well. The cockpit precomputes pairwise cohesion / conflict scores into `docs/bundle-meta.js`; this section is the rubric.

### §14.1 · Cohesion · 4 维(高 = 一起做有意义)

- **+3 · Same module** — sibling subtasks share the same plan / RFC / context · they're already related work
- **+2 · Same code file** (`code_anchors[].path_only` overlap) — edits to one will touch the other · do them together to keep diff coherent
- **+1 · Same doc anchor path** (`doc_anchors[].path` overlap) — referencing the same spec / plan section · context loads once
- **+2 · depends_on chain** (A's module depends_on B's module, or vice versa) — sequential bundle · upstream first

### §14.2 · Conflict · 4 维(高 = 别一起做)

- **+5 · Same file, overlapping line ranges** — merge conflict guaranteed · split or refactor first
- **+1 · Cross-sprint** (different `module.sprint`) — usually means different release timing · review separately
- **+1 · Cross-owner** (different `module.owner`) — coordination cost · async-friendly to split
- **+1 · Reverse blocking** (A blocks B but bundled in wrong order) — sequencing matters

### §14.3 · Recommended execution order

When a bundle is approved, order subtasks by:
1. **depends_on chain · upstream first** — if M07.blocks=[M08] and both in bundle, M07 subtasks come first
2. **Same file together** — minimize editor context switches · cluster by `code_anchors.path_only`
3. **Free order otherwise** — alphabetical / by id for determinism

The `docs_cockpit/bundle.py::recommended_order` function implements this · `render_bundle_prompt` outputs the result.

### §14.4 · How to use the recommendation skill

```bash
# Soft recommendation · LLM checks one module's bundle candidates
docs-cockpit suggest M07 --template bundle-recommendation

# Hard bundle execution · CLI renders prompt for selected subtasks
docs-cockpit prompt --bundle M07-f75501,M07-53a63a,M11-S1 --copy
```

When responding to a `bundle-recommendation` prompt, output:
1. A pairwise cohesion table (or top 10 if N is large)
2. 1-3 **positive bundle recommendations** with execution order + ready-to-run CLI command
3. 1 **negative example** ("don't bundle these") with the conflict reason

### §14.5 · Anti-patterns

- ❌ Bundling 10+ subtasks at once — Claude's attention degrades · the bundle prompt itself becomes a wall of text · split into 2-3 bundles of 3-5 subtasks each
- ❌ Bundling across sprints just because cohesion is high — usually means the sprint boundary is wrong · fix the sprint assignment first
- ❌ Bundling a `done` subtask with `not-started` ones — skip done subtasks · they're noise in the prompt
- ❌ Ignoring conflict warnings · `⚠ same file lines overlap` means merge conflict guaranteed
