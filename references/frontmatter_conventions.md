# Frontmatter conventions · 给文档加 YAML 头

> 读这份文档的时机:用户想启用 kanban,但 MD 文档现在没有 frontmatter;或者一个文档加了 frontmatter 但没出现在看板里,需要排错;或者要扩展新字段。

## 为什么要 frontmatter

如果你只想要"很多 MD 文件 → 一个 HTML 预览页",不需要 frontmatter — 配置里把 `frontmatter.kanban.enabled` 留成 false 就行,所有文档照常进侧边栏。

但**项目进度看板**(KPI / 模块 Kanban / Sprint Timeline)需要从文档身上读出"这是什么类型的 work item、当前状态、做了百分之多少、属于哪个 sprint"。这些元数据没法从正文里靠 LLM 推断 — 必须显式写。Frontmatter 就是放这些字段的地方。

## 标准字段

每个想进看板的 MD 文档头部:

```markdown
---
id: M07
type: module
title: Job-Task FSM
status: in-progress
progress: 45
sprint: M1.2
prd_ref: §6.3.7
owner: harvey
depends_on: [M04, M06]
blocks: [M08]
updated_at: 2026-05-14
---

# Job-Task FSM

(正文 ...)
```

### 字段语义

| 字段 | 必需? | 类型 | 说明 |
|------|------|------|------|
| `id` | **是** · 没 id 不进看板 | str | 唯一识别符 · 用于 depends_on / blocks 引用 |
| `type` | 强烈建议 | str | `module` / `concept` / `task` / `rfc` / 自定义。`kanban.card_types` 与 `kanban.kpi_type` 都按这个分 |
| `title` | 可选 | str | 看板卡上显示。不写就用从文件名解析的标题 |
| `status` | 是(看板用) | str | 见 status 词汇表 |
| `progress` | 是(看板用) | int 0-100 | 必须落在对应 status 的区间内 |
| `sprint` | 可选 | str | Sprint timeline 用 · 例 `M1.2` / `Q4` |
| `prd_ref` | 可选 | str | PRD 章节回溯 · 例 `§6.3.7` |
| `owner` | 可选 | str | 负责人 · 当前只展示,未来可能加 owner filter |
| `depends_on` | 可选 | list[str] | id 列表 · 当前只展示,未来 DAG 视图会用 |
| `blocks` | 可选 | list[str] | id 列表(反向依赖)|
| `updated_at` | 可选 | date | YAML date 类型会被自动转 ISO 字符串 |

### status 词汇表 + 区间

默认值(可在配置里覆盖):

| status | progress 区间 | 含义 |
|--------|--------------|------|
| `not-started` | `[0, 0]` | 完全未启动 · 只是占位 |
| `planned` | `[0, 15]` | 已排期 · 文档骨架可能在,但未真正开工 |
| `in-progress` | `[5, 95]` | 真在做 · progress 反映完成度 |
| `blocked` | `[0, 100]` | 因外部依赖卡住 · progress 保留卡住前的值 |
| `done` | `[100, 100]` | 完成 · 必须 100 才能写 done |
| `deferred` | `[0, 100]` | 推迟到更晚 sprint · 类似 blocked 但是主动决策 |

**区间是闭区间**(`[lo, hi]` 含两端)。违反会打 warning 但不 fail build。

### 为什么 `planned` 上限到 15?

允许 sprint 启动前的小量铺垫(scaffold / 调研笔记落地后但实际工作未开始)。如果你想更严,改成 `[0, 0]`。

## ID 命名约定

一种典型约定:

- `M01` ~ `M24` — modules(对应 PRD 里的模块清单)
- `C01` ~ `C11` — concepts(核心概念)
- `T-<scope>` — tasks(`T-M1.1.3-login-cookies`)
- `RFC-001` ~ — RFCs

可以用任何约定。但有两个坑:

1. **占位 ID**: 含 `XX` 的 ID(`MXX`)和 `XXX` 结尾的 ID(`RFC-XXX`)会被 build 自动过滤掉 — 这是 template 文件常用模式,防止模板 stub 被错误算进看板
2. **跨文档 unique**: build 不强制 · 但前端 Kanban 卡的 hover 跳转用 slug(文件名 slugify)· id 重复不冲突,只是看上去有歧义

## 文件没出现在看板里 · 排错清单

按概率排序:

1. **`frontmatter.kanban.enabled` 没开** · 配置 `false` 或不写就走文档视图。
2. **没有 `id` 字段** · 没有 id 就不是 trackable work item · 故意只进侧边栏。
3. **`type` 不在 `card_types` 列表里** · 配置里若设了 `card_types: [module]`,而文档是 `type: rfc`,就不进卡。
4. **`type` 不等于 `kpi_type`** · 文档进了 cards 但不进 KPI / Kanban / Timeline(只在 Concept Grid 区显示)。
5. **YAML 解析失败** · 头部第一行不是 `---`,或 yaml 语法错(比如 string 里有 colon 没引号)。build 会静默把 frontmatter 当空字典,文档照常进侧边栏但不进看板。用 `--debug` 看不到这种,得肉眼检查 MD 头。
6. **`progress` 不是 int** · 写成 `"45%"` / `45.0` 会变成 string / float · 看板能渲染但 progress bar 会出 NaN。永远写成 `progress: 45` 不带引号不带 %。

## 给一个文档加 frontmatter · 推荐工作流

如果项目还没有 frontmatter 约定,从 1-2 个高价值文档开始(比如目前 in-progress 的模块):

1. 在文档最顶上插入:

   ```markdown
   ---
   id: M07
   type: module
   title: Job-Task FSM
   status: in-progress
   progress: 30
   sprint: M1.2
   ---
   ```

2. 跑 build,看看出现在 Kanban 的哪一列:

   ```bash
   python -m docs_cockpit build
   ```

3. 调 status / progress 直到看板反映真实。
4. 给其他模块文档复制相同模式。

**不要一次给所有文档加** · 先把约定跑通 + 用户接受了再批量上,否则改约定时要回头改一堆文档。

## 扩展新字段

只需要在 `meta` 上加 key,build 时会原样进 `payload.cards[*].meta`。但前端 template 不会自动渲染未知字段。

要把新字段渲染出来:

1. 在 `docs_cockpit/templates/index.html.tmpl` 里找到 `renderModuleCard` / `renderDashboard`,加 HTML 段
2. 重跑 build

这是 template 直接改的场景 — 当前没法纯 YAML 配置扩 UI。

## 模板:给新文档复制粘贴

### Module(常用)

```markdown
---
id: M__
type: module
title: __
status: not-started
progress: 0
sprint: TBD
prd_ref: §_._._
owner: __
depends_on: []
blocks: []
updated_at: __
---

# __

## 目标

## 范围

## 接口

## 进度

## 风险
```

### Task

```markdown
---
id: T-__
type: task
title: __
status: planned
progress: 0
sprint: __
owner: __
---

# T-__ · __

## DOD

## 步骤

## 链接
```

### Concept

```markdown
---
id: C__
type: concept
title: __
status: planned
progress: 0
prd_ref: §5.__
---

# C__ · __
```
