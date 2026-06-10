<!-- 规范 SSOT · 原 docs-cockpit-author §1-§4/§16.2 · Stage B 后 author 删除，本文成唯一来源 -->

# docs-cockpit · frontmatter & anchor 字段规范

build / rebuild skill 共享的字段规范 SSOT。

## 目录

1. [五种 doc kind](#五种-doc-kind)
2. [frontmatter schema](#frontmatter-schema)
3. [cross-doc 字段](#cross-doc-字段)
4. [subtasks vs docs 决策](#subtasks-vs-docs-决策)
5. [subtask 格式](#subtask-格式)
6. [code anchor 格式](#code-anchor-格式)
7. [doc anchor 格式](#doc-anchor-格式)
8. [文件命名约定](#文件命名约定)
9. [subtask title 4 法则](#subtask-title-4-法则)

---

## 五种 doc kind

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

---

## frontmatter schema

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

### Required fields

**`id`** — REQUIRED. Without it the doc is silently dropped from the dashboard (the build only counts entries with `id`).

- Convention: `M01`-`M99` for modules · `C01`-`C99` for concepts · `RFC-001` for RFCs · `<MODULE-ID>-PLAN-<date>` for plans · `<MODULE-ID>-SPEC` for specs
- MUST be unique across all docs (validator does NOT enforce this yet, but the dashboard will collide silently)
- NEVER use placeholder ids containing `XX` or ending in `XXX` — the validator emits a warning and the entry is skipped

### status enum

**`status`** — RECOMMENDED. Without it the dashboard treats the module as `not-started`. Pick exactly one:

| value | meaning | progress range |
|---|---|---|
| `not-started` | not in flight · nobody's looked at it | `0` only |
| `planned` | scoped + sprint-assigned but not started | `0`-`15` |
| `in-progress` | being actively worked on | `5`-`95` |
| `blocked` | started but stuck on dependency / decision | `0`-`100` |
| `done` | merged + verified | `100` only |
| `deferred` | intentionally pushed to a later sprint | `0`-`100` |

### status × progress invariants

**`progress`** is an integer 0-100. The validator emits a `warn` if it's out of the band defined for the current status:

```
status=done       → progress must be 100
status=not-started → progress must be 0
status=planned    → progress in [0, 15]   (scoping ≠ doing)
status=in-progress → progress in [5, 95]   (5 = some commit landed · 95 = needs final review)
```

When out of range, either move `status` forward or bring `progress` back to the band. Pick whichever describes reality.

### doc type enum

**`type`** — optional but recommended. One of: `module`, `concept`, `plan`, `rfc`, `spec`, `memory`, `roadmap`. The validator warns on unknown values.

This affects nothing in the dashboard rendering today, but the author skill uses it to pick the right body template, and lint will eventually use it to validate kind-specific fields (e.g. `rfc` needs `status: draft|reviewing|accepted|superseded`).

### Recommended fields

- **`title`** — display name in the Kanban card. Defaults to filename stem if missing — usually fine but won't be pretty
- **`sprint`** — string · e.g. `M1.2` · drives the Sprint Timeline grouping. Without it the Sprint view shows "unscheduled"
- **`desc`** — one-line description shown in the drawer. **Without `desc`, the copy-prompt feature gets weaker context** because it falls back to a body excerpt. Validator emits a `hint` if missing
- **`owner`** — string · just a name · surfaces in the drawer

---

## cross-doc 字段

**`docs`** — list of `{title, path}` linking to plans / RFCs / specs that elaborate this module. Path is **relative to the repo root** (NOT relative to the source file). The build resolver tries absolute → relative-to-source → relative-to-repo so older patterns still work.

```yaml
docs:
  - { title: "RFC-002 · ResourcePool",       path: "docs/RFC/002-resource-pool.md" }
  - { title: "Round 3 plan · build sequence", path: "docs/plans/round-3-build-house.md" }
```

If you don't fill `docs:` in frontmatter, the body fallback takes over.

**`depends_on`** / **`blocks`** — lists of other module ids. Currently informational (not rendered yet) but the author skill writes them so dependency graph features can be added later.

**`prd_ref`** — string · the PRD section reference that motivates this doc · e.g. `"§7.4.2 + §9.2"`. Surfaces in the drawer.

### docs body fallback（两种形式）

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

---

## subtasks vs docs 决策

This is where people get confused. Two related but different concepts:

| Concept | Lives where | Used for | Captured by |
|---|---|---|---|
| **subtasks** | `subtasks:` frontmatter list OR `## TODO` / `## 待办` body section | Granular work items WITHIN this doc · drives progress auto-calc | Drawer checklist |
| **docs** | `docs:` frontmatter list OR `## Related` / `## 关联` body section | Links to OTHER docs that elaborate / depend on this | Drawer "Linked Docs" list |

**Rule of thumb:**
- Sub-bullets of work you'll do yourself → `subtasks`
- References to other markdown files that describe details → `docs`

If you're tempted to put a "see also" link in `subtasks:`, it's `docs:`. If you're tempted to put a checkbox in `docs:`, it's `subtasks:`.

---

## subtask 格式

> **0.16.0 · title style rules are MANDATORY** — see subtask title 4 法则 below. Quick recap: one sentence requirement (not code logic) · single language matching `project.doc_language` · NO `§N.M` / file paths / line numbers / function names in title (those go to `code:` / `docs:` fields). Violations surface as `doc-lang-mix` / `title-has-anchor` warnings at build time.

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

The validator emits a `hint` on string form and points to `docs-cockpit migrate-subtasks` (one-shot upgrade：`docs-cockpit migrate-subtasks <file>` dry-run 打印 diff · 加 `--apply` 写回并生成 .bak · 自动把 string 转 {id, title, done, status} 且不动已有 object 条目).

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

### subtask id 算法 + title-is-identity 权衡

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

---

## code anchor 格式

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

---

## doc anchor 格式

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

---

## 文件命名约定

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

---

## subtask title 4 法则

When you write a subtask title:

**法则 1 · One sentence in user-need language · NOT code language**

```
✅ 「实现资源池的借/还机制 · 失败自动冷却 + 超时回收」     ← what the user gets
❌ 「ResourcePool[T] · COOLDOWN(5 失败 → 300s 冷却 / 25min 超时)+ EWMA 评分」  ← code-name dump
```

**法则 2 · Single language matching project.doc_language**

The project's `docs-cockpit.yaml::project.doc_language` lock applies to all subtask titles. Tech tokens (`API`, `MCP`, `CLI`, `JSON`, `SDK`, etc.) are whitelist-OK · they're cross-lingual.

```
zh-CN project · ✅ 「实现 MCP server 的 stdio 接入」          ← 中文主体 + 白名单 'MCP'
zh-CN project · ❌ 「实现 MCP server 的 stdio 接入 with SDK choice」  ← 'with' / 'choice' 非白名单
en project    · ✅ "Implement stdio adapter for the MCP server"
en project    · ❌ "Implement stdio adapter 给 MCP server 接入"        ← CJK 在 en project
```

**法则 3 · NO anchor info in title · 走 `code:` / `docs:` 字段**

These belong in `code_anchors[]` / `doc_anchors[]`, NEVER in title:

- `§3.1` / `§4.6 / §4.7 / §4.8` heading numbers
- `DATA_SCHEMA.md` / `account_proxy.py` file paths
- `:42-89` line ranges
- `ResourcePool[T]` / `lazyAccountProxy()` function / class identifiers

```
✅ title: 「同步 vendor 池的字段定义」
   docs:  ["docs/DATA_SCHEMA.md#§3.1", "docs/DATA_SCHEMA.md#§3.2"]
   code:  ["sourcery/resources/vendor_pool.py"]

❌ title: 「M1.2 Lane F · DATA_SCHEMA.md §3.1 / §3.2 行同步 + §4.6 / §4.7 / §4.8 ...」
```

**法则 4 · 一句话讲需求逻辑 · 不讲实施步骤**

```
✅ 「让 dashboard 在多 sprint 时显示 sprint 筛选下拉」        ← 用户得到的能力
❌ 「在 index.html.tmpl 加 `<select id='backlog-filter-sprint'>` 渲染 sprint 选项」  ← 实施细节
```

实施细节属于 per-subtask plan MD body · 不是 title。
