# YAML frontmatter 约定(0.2.0)

> docs-cockpit dashboard 的 module / concept 卡片来自 MD 文件顶部的 YAML frontmatter。这份文档列每个字段的语义 + status × progress 治理校验 + 0.2.0 新加的扩展字段。

## 最小 module frontmatter

```markdown
---
id: M07                          # 必填 · 不带 id 不进卡板
title: Job-Task FSM              # 可省 · 缺则用文件名
status: in-progress              # not-started | planned | in-progress | blocked | done | deferred
progress: 45                     # 0-100 · 必须符合 status_progress_ranges
sprint: M1.2                     # 可省 · timeline 按这个分组
---

# M07 · Job-Task FSM(MD body 仍在 · 但 dashboard 不渲染)
```

## 0.2.0 扩展字段(modules · 选填)

```markdown
---
id: M07
title: Job-Task FSM
status: in-progress
sprint: M1.2
progress: 45

# ── 0.2.0 新加 ────────────────────────────────────────
desc: 12 类核心 FSM 状态机 · 含字段校验与跨模型引用约束
docs:
  - { title: "Schema 设计文档", path: "docs/design/schemas.md" }
  - { title: "RFC 003 · 模型边界", path: "docs/RFC/003-model-boundaries.md" }
subtasks:
  - { title: "核心实体定义(12 类)", done: true }
  - { title: "字段校验与 strict 模式", done: true }
  - { title: "序列化与反序列化测试", done: false }
  - { title: "跨模型引用约束", done: false }
manualProgress: false            # 默认 false · 子任务自动算 progress

# ── 治理类(选填)─────────────────────────────────────
owner: harvey
prd_ref: §6.3.7
depends_on: [M04, M06]
blocks: [M08]
updated_at: 2026-05-14
---
```

### 字段语义

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | ✅ | 唯一标识 · 不带 id 的 MD 不进卡板(允许侧边栏继续列出 · 但不计入 Kanban / KPI) |
| `title` | string | ⚠️ | 卡片标题 · 缺省用文件名 |
| `status` | enum | ⚠️ | 必须在 `status_progress_ranges` 表里 |
| `progress` | int 0-100 | ⚠️ | 跟 status 的范围匹配 · 不匹配只 warn 不阻塞 |
| `sprint` | string | ⚠️ | 任意字符串 · timeline 按此分组 · 缺则归 "—" 组 |
| `desc` | string | ✅(展示完整 · 强烈建议) | drawer 里展示的"模块描述" 1-3 句 |
| `docs` | list of `{title, path}` | 可空 | 模块关联的 MD 文档列表 · drawer 里可点开 |
| `subtasks` | list of `{title, done}` | 可空 | 子任务清单 · drawer 里可勾选(localStorage 持久化) |
| `manualProgress` | bool | 可空 | true → 用 `progress` 字段;false → 用子任务完成率算 |

## Concepts 简化字段

Concepts(底部 grid)**不用**扩展字段 · 只读这 5 个:

```markdown
---
id: C03
title: Site Adapter
status: in-progress
sprint: M1.2
progress: 60
---
```

`desc / docs / subtasks` 即使写了也会被忽略 — 概念 grid 只展示 5 字段卡片。

## status × progress 治理

默认 status 词汇 + 允许的 progress 范围(`status_progress_ranges`):

| status | progress 允许 [min, max] | 含义 |
|---|---|---|
| `not-started` | [0, 0] | 完全没开始 |
| `planned` | [0, 15] | sprint 已排期但实际未启动(允许 ≤15 的轻量铺垫) |
| `in-progress` | [5, 95] | 在做 · 排除 0/100 两头 |
| `blocked` | [0, 100] | 任何进度 · 但 status=blocked 比 progress 重要 |
| `done` | [100, 100] | 必须 100% |
| `deferred` | [0, 100] | 暂停 / 推迟 |

不合规会发 build warning(`progress=N out of range [a,b] for status=S`)· 永远**不阻塞** build。

### 自定义 status 词汇

如果你用别的词(`todo` / `wip` / `shipped`),整张表替换:

```yaml
frontmatter:
  status_progress_ranges:
    todo: [0, 0]
    wip: [1, 99]
    shipped: [100, 100]
```

**注意**:前端 Kanban 5 列(`STATUS_ORDER`)硬编码默认这套词。换词汇也要同步改 `templates/index.html.tmpl` 里的 `STATUS_ORDER` / `STATUS_LABEL` / `STATUS_COLOR`。

## Subtasks → 自动 progress

`manualProgress: false`(或不写)时,build **不读** `progress` 字段 · 改为按子任务完成率算:

```
progress = round(已完成 subtask 数 / 总 subtask 数 × 100)
```

子任务全空时降级到 `progress` 字段值。

`manualProgress: true` 时:用 `progress` 字段。dashboard drawer 里 toggle 可切换 · 切完写 localStorage 覆盖(用户在浏览器里调 · 不动 MD)。

## localStorage 覆盖机制(0.2.0 新加)

用户在 dashboard 里点 status / 拖 progress / 勾 subtask · **覆盖**写 `localStorage[project-kanban-state-v1]`:

```json
{
  "M07": { "status": "blocked", "progress": 30, "manualProgress": true },
  "M07__st0": true,
  "M07__st1": false
}
```

**source of truth 仍是 MD frontmatter** · 覆盖只是浏览端展示层 · 重 build 不会丢 MD 的真实值。如果用户要把 dashboard 上的覆盖**落回** MD · 暂无自动同步 · 手工改 frontmatter 即可。

(后续 roadmap:`docs-cockpit sync-overrides` 命令把 localStorage 落回 MD frontmatter。)

## 跳过模板占位 id

如果你的 MD 是从模板复制来的 · id 还没填(写成 `MXX` / `CXXX` 等),build 会**跳过这条**不报错。避免模板半成品污染 dashboard。

## Body fallback · 0.4.0 起

如果你的 module MD **frontmatter 没有 `subtasks` 或 `docs` 字段** · 但 **body 里有相应内容** · 0.4.0 起 build 会**自动从 body 提取**:

### subtasks 抽取规则

找 H2 section 标题匹配以下任一(大小写不敏感)`:

- `## 待办` · `## TODO` · `## To-do` · `## Subtasks` · `## Tasks` · `## 任务`
- 允许前面带数字编号 · 如 `## 3 · 待办`

在该 section 下 · 每行 `- [x]` 或 `- [ ]` 的 checklist 项目就是一个 subtask:

```markdown
## 3 · 待办

- [ ] 与 PRD 对照,标记偏离之处
- [x] 在 Sprint 启动时建立 spec 框架
- [ ] 关联 RFC / plan / task
```

→ 提取出 3 个 subtasks · 已完成的一个标 `done: true`。section 在下一个 `## H2` / `### H3` / `---` 分隔线处终止。

### docs 抽取规则

找 H2 section 标题匹配:

- `## 关联` · `## 关联文档` · `## Related` · `## Related docs` · `## Docs` · `## See also` · `## 参考` · `## 链接`

抽 markdown link `[title](path)` 为 docs:

```markdown
## 关联文档

- [Schema 设计文档](docs/design/schemas.md)
- [RFC 003 · 模型边界](docs/RFC/003-model-boundaries.md)
```

→ 提取 2 个 docs。锚点链接(`#section`)跳过。

### 优先级

**frontmatter > body**。如果 frontmatter 已经写了 `subtasks: [...]` · body 抽取**不再触发** · frontmatter 接管。想精控就显式写 frontmatter。

### `desc` 不参与 body 提取

只 `subtasks` / `docs` 走 body fallback。`desc` 字段始终只看 frontmatter · 因为 body 的首段往往是引用块 / metadata 行 · 不靠谱。想要 desc 显式写 frontmatter。

### 配合 `docs-cockpit migrate`

`docs-cockpit migrate --apply` 在迁移 MD 文件时 · 也会跑同样的 body 提取 · 把 subtasks / docs **写进** frontmatter。这样:

- 迁移后 frontmatter 是 source of truth
- 用户在 dashboard drawer 上 toggle 子任务 · 将来可以(roadmap)同步回 frontmatter
- body 的 `## 待办` checklist 仍然存在 · 但 dashboard 不再读它(因为 frontmatter 接管了)

## ID 命名约定

一种典型约定:

- `M01` ~ `M24` — modules
- `C01` ~ `C11` — concepts
- `T-<scope>` — tasks(如 `T-M1.1.3-login-cookies`)
- `RFC-001` ~ — RFCs

可以用任何约定。注意两点:
- id 在整个项目要**全局唯一** · 重复会被前端去重(后出现的覆盖)
- 不要在 id 里塞空格 / 中文 / 特殊字符 · 简单 ASCII 字母 + 数字 + dash 最稳
