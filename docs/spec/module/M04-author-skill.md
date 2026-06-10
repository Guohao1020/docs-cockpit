---
id: M04
type: module
title: "Author Skill · Frontmatter Schema SSOT"
status: done
sprint: "0.11"
progress: 100
desc: "原 author skill · frontmatter / body 规范的 canonical spec · v1.0 收编进 references/schema.md · validator Issue.reference 反向指向"
owner: harvey
prd_ref: "v0.11 driver-seat plan §6.1 §6.2"
docs:
  - { title: "字段规范 SSOT(v1.0 收编)", path: "references/schema.md" }
  - { title: "Frontmatter conventions", path: "references/frontmatter_conventions.md" }
  - { title: "v0.11 driver-seat plan", path: "docs/plans/P-v0.11-driver-seat.md" }
depends_on: []
blocks: [M01, M02]
---

# M04 · Author Skill · Frontmatter Schema SSOT

## §1 · 范围

原 author skill 的 SKILL.md 曾是整个项目 **frontmatter / body 规范的单一真相源(SSOT)**;v1.0 起规范收编进 `references/schema.md` · 所有 skill / validator / 文档指回那里 · 不重复定义 schema。

validator 输出的 `Issue.reference` 字段直接指向规范章节(`📚 references/schema.md · frontmatter schema`)· 形成 spec ↔ 实现的闭环。

## §2 · 关键文件

| 文件 | 角色 |
|---|---|
| `references/schema.md`(原 author SKILL · v1.0 收编) | §1 概念 / §2 frontmatter / §3 docs vs subtasks / §4 命名 等规范章节 |
| `references/frontmatter_conventions.md` | 速查版 · 大段引用 author SKILL |

## 3 · 待办

- [x] 写齐 frontmatter schema 完整规范 · 给所有后续模块当真相源 @docs:references/schema.md
- [x] 把 docs 与 subtasks 的边界讲清 · 给用户写文档时不再混淆 @docs:references/schema.md
- [x] 锁定五种文档类型的命名规则 · 让 AI 写新文档时落点统一 @docs:references/schema.md
- [x] 校验器输出格式标准化 · 每条问题都能追溯到规范段落 @code:docs_cockpit/schema.py:478-541
- [x] 把 subtask 升为对象 schema · 让每条子任务能独立追踪 @code:docs_cockpit/schema.py:421-475 @docs:references/schema.md
- [x] 给 subtask id 加稳定生成算法 · 重命名 title 时讲清 trade-off @code:docs_cockpit/schema.py:398-419 @docs:references/schema.md
- [x] 加 prompt template 规范章节 · 四种内置 template 各自适用场景写清 @code:docs_cockpit/prompt.py:130-237
- [x] 给 prompt context 变量定 stability contract · 让自定义 template 升级时不破 @code:docs_cockpit/prompt.py:239-310
- [x] body 内联 anchor 语法文档化 · 让 AI 在 checklist 里就能挂代码跟文档锚 @code:docs_cockpit/schema.py:185-223 @docs:references/schema.md
