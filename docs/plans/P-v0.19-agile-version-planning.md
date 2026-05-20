---
id: P-v0.19
type: plan
title: "v0.19 · Agile version planning · sprint-plan 一等公民 + DoR/DoD 校验"
status: in-progress
sprint: "0.19"
progress: 10
desc: "把 PRD/RFC → sprint → subtask 闭环 · 每个版本前自动校验需求对齐 + LLM 参考文档充分性 · 不依赖人记得"
owner: harvey
prd_ref: "Sourcery dogfood 反馈 · M12 sprint=0.7 但没有 V0.7 sprint plan · 散落 spec 串不起来"
docs:
  - { title: "M07 MCP server", path: "docs/spec/module/M07-mcp-server.md" }
  - { title: "Author skill §16 anchor 完整性 SOP", path: "skills/docs-cockpit-author/SKILL.md" }
  - { title: "Scrum Guide 2020", path: "https://scrumguides.org/scrum-guide.html" }
depends_on: []
blocks: []
---

# v0.19 · Agile version planning

## §1 · 用户原话(why this exists)

用户在 Sourcery dogfood 后提的诉求(直引):

> 「根据用户生成的 spec / PRD / plan / RFC 等等文档 · 根据敏捷开发的范式规划出不同的版本 · 每个版本的做任务都有哪些 · 需要落地的 plan 文档都有哪些 · **每个版本开始前都需要校验是否有了充分的需求对齐和大模型参考文档**」

观察:用户已经在 module MD 写 `sprint: "0.7"` · `sprint: "0.18"` · subtask title 也带 `M1.1` / `M1.2 Lane F` 这类 sprint 编号。但**没有任何一个文档描述「sprint 0.7 这个版本到底要做什么 · 做完算什么」**。spec 散在 24 个 module · plan / RFC 各自一份 · 版本视角缺失。

把这个洞填上 = v0.19 主要工作。

## §2 · 敏捷开发 + 版本规划范式(把 Scrum/Kanban 映射到 docs-cockpit)

### §2.1 · 核心概念表(三层模型)

docs-cockpit 现状跟敏捷的对应关系 + v0.19 新增的对应关系:

| 敏捷概念 | 现状(0.18-) | v0.19 引入 |
|---|---|---|
| Product Backlog · 所有想做的事 | 所有 `docs/spec/module/M*.md`(状态 not-started + in-progress)| 不动 |
| Sprint Backlog · 这个 sprint 要做的事 | 隐式 · 看 module.sprint 字段反推 | **显式** · 走 sprint-plan.in_scope[] |
| Increment · 这个 sprint 交付的产物 | 隐式 · CHANGELOG / git tag | **显式** · 走 sprint-plan.goals[] + dod[] |
| User Story · 用户视角的需求 | subtask title(0.16+ 规则:讲用户得到什么)| 不动 |
| Acceptance Criteria · 验收标准 | per-subtask plan MD §4 · 验证(0.16+)| 不动 |
| Definition of Ready (DoR) · 开工前要满足的条件 | 没有 · 全靠人记 | **新** · 走 sprint-plan.dor[] + lint_sprint_readiness |
| Definition of Done (DoD) · 完成的标准 | 没有 · 全靠人记 | **新** · 走 sprint-plan.dod[] + lint_sprint_done |
| Sprint Planning · 开始前规划 | 没有 · sprint 字段一填就开干 | **新** · `docs-cockpit sprint init <version>` scaffold |
| Sprint Review / Demo · 结束后回顾 | 没有 | **新** · sprint-plan.retro 字段 + body §4 验证 |
| Velocity · 速度 | 隐式 · 看 portfolio snapshots | 不动 |
| Carryover · 没做完滚到下个 sprint | 没有 · 直接改 module.sprint 字段 | **新** · sprint-plan.retro.carryover[] |

### §2.2 · 为什么不是「Waterfall + 版本号」

避免误解:v0.19 不是把 docs-cockpit 改成瀑布(写好所有 spec → 一次性 release)· 也不是把每个 release 当 sprint。具体区分:

- **release(版本号 · 0.18.0 / 0.19.0)** · 是给下游用户的 packaging 单位 · 一个 release 含若干 sprint 的产出。SemVer 还是 SemVer。
- **sprint(0.7 / 0.18 / 0.19)** · 是开发节奏单位 · 1-4 周一个 · sprint-plan 描述。
- 一个 release 可以 = 一个 sprint(小项目)· 也可以 = 多个 sprint(大项目分阶段 ship)

Sourcery 的命名 `M1.1` / `M1.2 Lane F` / `M1.5.c` 已经是 sprint 编号 + lane(并行流)· 用户已经在跑敏捷 · 只是缺工具支持。docs-cockpit 这次补这个工具。

### §2.3 · 跟「per-subtask plan MD(§16.3)」的层级

0.16 引入 per-subtask plan MD(`docs/plans/M<NN>/S<NN>-*.md`)· 0.19 引入 per-sprint plan MD(`docs/plans/V<x.y>-*.md`)· 层级:

```
docs/plans/
├── V0.18.md                          ← sprint plan (0.19+ NEW · 本 release 引入)
├── V0.19.md                          ← sprint plan
├── V0.20.md                          ← sprint plan
├── P-v0.18-driver-seat.md            ← release plan / RFC(沿用 P-* 命名)
├── P-v0.19-agile-version-planning.md ← 本文件 · release plan
├── M07/                              ← per-module dir (0.16+)
│   ├── S01-implement-mcp-stdio.md    ← per-subtask plan (0.16+)
│   └── S02-wire-cockpit-prompt.md
└── M11/
    └── ...
```

| 层 | 粒度 | doc type | 答的问题 |
|---|---|---|---|
| `P-v<release>-*.md` | release · 跨多 sprint | `plan` | 这个 release 要解决什么大问题 |
| `V<x.y>.md` | sprint · 1-4 周 | `sprint-plan`(新)| 这 1-4 周交付什么 user-visible 产物 |
| `M<NN>-*.md` | 模块 · 多 sprint 渐进 | `module` | 这个模块累计 ship 哪些能力 |
| `M<NN>/S<NN>-*.md` | 单子任务 · 几小时-几天 | `subtask-plan`(0.16+)| 这条 subtask 具体怎么做 |

每层加一层 traceability · sprint-plan 显式列 `in_scope: [module: M07, subtasks: [...]]` · 自动接到下层。

## §3 · sprint-plan 文档 schema(核心契约)

新 doc type · `type: sprint-plan` · 文件命名 `docs/plans/V<x.y>.md`(可加 slug:`V0.19-agile.md`)。

```yaml
---
id: V0.19                          # 必填 · 跟 module.sprint 字段值对齐("0.19" 跟 "V0.19" 双向兼容)
type: sprint-plan                  # 必填 · 新 doc type
title: "Sprint 0.19 · agile version planning + sprint-plan first-class"
status: in-progress                # 必填 · planned | in-progress | done | blocked
window: "2026-05-21 → 2026-06-04"  # 必填 · ISO 日期范围 · 1-4 周
progress: 10                       # 0-100 · 自动 = (in_scope 里 done subtask 数 / 总数)

# §2.1 表里说的 user-visible 产物 · 至少 1 条 · 描述完用户能干什么
goals:
  - "用户能写 V<x.y>.md sprint plan · docs-cockpit 识别并验"
  - "lint 自动校验需求对齐 + LLM 参考文档充分性 · 不再靠人记"

# §2.1 表里说的 sprint backlog · 显式列哪些 module / subtask 算在这个 sprint
in_scope:
  - module: M01           # 必填 module id
    subtasks: [M01-a1b2c3, M01-d4e5f6]  # 可选 · 不填 = 整个 module 都在
  - module: M02
    subtasks: []          # 空 list 跟不填 同义

out_of_scope:             # 显式 NOT in sprint · 防 scope creep
  - "MCP cockpit_sprint_readiness tool · 留 v0.19.1"
  - "LLM-driven sprint composition · 留 v0.19.2"

prd_refs:                 # 需求对齐 · DoR 校验 #1 · 至少 1 条
  - { section: "§6.3", title: "资源池统一抽象", path: "docs/PRD/Sourcery_PRD_V1.0.docx" }
  - { section: "RFC-002 §4", title: "ResourcePool 设计", path: "docs/RFC/002-resource-pool-design.md" }

docs:                     # LLM 参考文档 · DoR 校验 #2 · 大模型执行前必读的 ref
  - { title: "Author skill §17 · agile workflow", path: "skills/docs-cockpit-author/SKILL.md" }

dor:                      # Definition of Ready · sprint 开干前要满足的条件
  - "每个 in_scope subtask 有 prd_ref 或 @docs anchor 指向 PRD/RFC section"
  - "每个 in_scope subtask 有 @code 或 @docs anchor(LLM 拉得到上下文)"
  - "复杂 subtask 有独立 plan MD(per §16.3)"
  - "linked PRD/RFC 文件存在 + 可读"

dod:                      # Definition of Done · sprint 结束的验收
  - "所有 in_scope subtask status=done"
  - "lint 0 error / 0 warning(对本 sprint 涉及的 module)"
  - "CHANGELOG 加 entry"
  - "demo 跑通(本 sprint 至少 1 个 goal 现场演示)"

# sprint 结束后填(retro 一节 · 给下个 sprint 复盘用)
retro:
  what_worked: ""         # 哪些做法成功 · 下个 sprint 保留
  what_didnt: ""          # 哪些做法翻车 · 下个 sprint 改
  carryover: []           # 没做完滚到下个 sprint 的 subtask id list
---

# Sprint 0.19 plan

## §1 · 用户得到什么(详写 goals)

(每个 goal 一段话讲清用户体验 · 不超过 200 字)

## §2 · 跟上 sprint 的衔接

(上个 sprint 的 carryover · 跟本 sprint 的依赖关系)

## §3 · 风险 + 假设

(已知 risks · 团队 assumptions · 哪些前提如果不成立 · 半路要重新规划)

## §4 · 验证 · 谁来跑 demo

(每个 goal 怎么验 · 谁来 sign-off · 哪些自动化 · 哪些手动 / 跨人)

## §5 · Retro(sprint 结束填)

(what worked · what didn't · carryover 详细解释)
```

## §4 · 校验门(lint_sprint_readiness)

新 lint category · 两类(都是 warn 级 · 不阻塞 build):

### §4.1 · sprint-schema(sprint-plan 自身 schema 校验)

`validate_sprint_plan(meta) -> list[Issue]` · 走 build 时跟 module 一样的校验路径:

- `id` 必填 · 形如 `V0.19` 或 `0.19`(自动规整)
- `status` ∈ {planned, in-progress, done, blocked}
- `window` 必填 · ISO date range 格式
- `goals` 必填 · list · 不能空 · 每个元素 string
- `in_scope` 必填 · list · 每个元素必须有 `module` 字段
- `dor` `dod` 至少各有 1 条(可以是 free-form string)

### §4.2 · sprint-readiness(DoR 校验 · 用户 #1 + #2 诉求)

`lint_sprint_readiness(modules, sprint_plans) -> list[Issue]` · 对每个 status=planned 或 in-progress 的 sprint-plan 跑:

**需求对齐(用户诉求 #1)**:

- `sprint-readiness-no-prd-anchor` · in_scope subtask 既无 prd_ref · 也无 @docs anchor 指向 prd_refs[].path · 报 warn
- `sprint-readiness-prd-path-missing` · sprint-plan.prd_refs[].path 文件找不到 · 报 warn

**LLM 参考文档(用户诉求 #2)**:

- `sprint-readiness-no-code-or-docs-anchor` · in_scope subtask 既无 @code 也无 @docs · LLM 执行时没 context · 报 warn
- `sprint-readiness-docs-anchor-broken` · in_scope subtask 的 @docs anchor 指向的文件不存在 · 报 warn

**Schema 链路完整性**:

- `sprint-readiness-module-missing` · in_scope.module 在 state.json 里找不到 · 报 warn
- `sprint-readiness-subtask-missing` · in_scope.subtasks[] 在对应 module 里找不到该 id · 报 warn

每条 Issue · `category="sprint-readiness"` · `reference="docs-cockpit-author · §17"` · suggestion 给具体 fix 命令。

### §4.3 · 默认 opt-in · 不影响老项目

old project(没有 sprint-plan)· lint_sprint_readiness 跳过 · 不报警。

新项目要启用走 `docs-cockpit.yaml`:

```yaml
project:
  enforce_sprint_plans: true   # 默认 false · true 时 lint_sprint_readiness 跑严格模式
                               # · 用 module.sprint 但没对应 sprint-plan 也报 warn
```

## §5 · CLI 接口

```bash
# 新建 sprint plan · 默认从模板 scaffold + 从 state.json 反查该 sprint 下哪些 module
docs-cockpit sprint init 0.20
docs-cockpit sprint init 0.20 --window "2026-06-05 → 2026-06-19"
docs-cockpit sprint init 0.20 --slug "mcp-readiness-tool"  # 文件命名 V0.20-mcp-readiness-tool.md

# 校验 DoR · 输出 issue 报告 · CI 用 --strict 阻断
docs-cockpit sprint check 0.19
docs-cockpit sprint check 0.19 --strict     # warn 升 error · exit 1
docs-cockpit sprint check --all             # 跑所有 status=planned/in-progress 的 sprint

# 列所有 sprint plan + 状态
docs-cockpit sprint list
docs-cockpit sprint list --status in-progress
```

## §6 · MCP tool(留 v0.19.1)

不在 v0.19.0 范围 · 设计 freeze:

```jsonc
// tool: cockpit_sprint_readiness
{ "sprint_id": "0.19", "strict": false }
// returns
{
  "ok": true, "sprint_id": "V0.19", "status": "in-progress",
  "issues": [...],         // 同 cmd_sprint_check 输出 schema
  "dor_passed": 4, "dor_total": 4,
  "in_scope_total": 12, "in_scope_done": 3,
}
```

副驾闭环:用户开 sprint 前 · LLM 自己调 cockpit_sprint_readiness · 看不过就帮用户补 anchor / 写 plan · 写完再调 cockpit_build 验。

## §7 · 跟现有功能的关系(不破不动)

| 现有功能 | 是否动 |
|---|---|
| module.sprint(string)| 不动 · 0.19 反查它找 sprint-plan |
| validate_meta(frontmatter schema)| 加 sprint-plan 一档 doc type · 老 doc types 不动 |
| lint_subtask_titles / lint_subtask_anchors | 不动 · sprint-readiness 是新 category 复用 Issue.category 机制 |
| docs-cockpit lint / build | lint_sprint_readiness 进 lint pipeline · 默认 opt-in 不报警 |
| MCP cockpit_build / cockpit_apply_*_patch | 不动 · v0.19.1 加 cockpit_sprint_readiness |
| dashboard | 不动 · v0.19.x 加 sprint timeline column overhaul |

## §8 · 实施 checklist(v0.19.0 MVP)

- [ ] schema.py · sprint-plan 进 VALID_DOC_TYPES · validate_sprint_plan + lint_sprint_readiness 实现 @code:docs_cockpit/schema.py @docs:docs/plans/P-v0.19-agile-version-planning.md#§3 @docs:docs/plans/P-v0.19-agile-version-planning.md#§4
- [ ] sprint.py 新 module · cmd_sprint_init + cmd_sprint_check + cmd_sprint_list 三 subcommand @code:docs_cockpit/sprint.py @docs:docs/plans/P-v0.19-agile-version-planning.md#§5
- [ ] templates/sprint-plan.md.j2 scaffold · cmd_sprint_init 用它 · 用户 init 后填表 @code:docs_cockpit/templates/sprint-plan.md.j2
- [ ] cli.py wire `sprint` subparser 跟 3 个 subcommand · build.py 串 lint_sprint_readiness 进 build_payload @code:docs_cockpit/cli.py @code:docs_cockpit/build.py
- [ ] author skill §17 整理 agile workflow + DoR/DoD 表 + 4 件 tool routing 跟 sprint 命令的关系 @code:skills/docs-cockpit-author/SKILL.md
- [ ] dogfood · 自己写 docs/plans/V0.18.md(已 ship)+ docs/plans/V0.19.md(本 release)· 跑 sprint check 验 · 0 warning @code:docs/plans/V0.18.md @code:docs/plans/V0.19.md
- [ ] CHANGELOG entry + 0.18→0.19 bump + commit + push @docs:CHANGELOG.md

## §9 · 留给 v0.19.x 的事

- v0.19.1 · MCP `cockpit_sprint_readiness` tool(§6)
- v0.19.2 · LLM-driven sprint composer · `docs-cockpit sprint plan <version>` · 读 PRD/RFC/backlog 输出 proposed in_scope[]
- v0.19.3 · dashboard sprint timeline 重做 · 把 sprint-plan goals + dor/dod 渲染进时间线
- v0.20 · roadmap 老 backlog 继续(gap #4 title hash strip / gap #5 sprint sort)
