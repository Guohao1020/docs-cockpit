---
id: M04
type: module
title: "Author Skill · Frontmatter Schema SSOT"
status: in-progress
sprint: "0.11"
progress: 80
desc: "docs-cockpit-author/SKILL.md · frontmatter / body 规范的 canonical spec · validator Issue.reference 反向指向"
owner: harvey
prd_ref: "v0.11 driver-seat plan §6.1 §6.2"
docs:
  - { title: "Author SKILL", path: "skills/docs-cockpit-author/SKILL.md" }
  - { title: "Frontmatter conventions", path: "references/frontmatter_conventions.md" }
  - { title: "v0.11 driver-seat plan", path: "docs/plans/P-v0.11-driver-seat.md" }
depends_on: []
blocks: [M01, M02]
---

# M04 · Author Skill · Frontmatter Schema SSOT

## §1 · 范围

`docs-cockpit-author/SKILL.md` 是整个项目 **frontmatter / body 规范的单一真相源(SSOT)**。所有其他 skill / validator / 文档都指回这里 · 不重复定义 schema。

validator 输出的 `Issue.reference` 字段直接指向 SKILL 章节(`📚 see: docs-cockpit-author · §2.4`)· 形成 spec ↔ 实现的闭环。

## §2 · 关键文件

| 文件 | 角色 |
|---|---|
| `skills/docs-cockpit-author/SKILL.md` | 8 sections · §1 概念 / §2 frontmatter / §3 docs vs subtasks / §4 命名 / §5 validator / §6 body / §7 cross-doc / §8 examples |
| `references/frontmatter_conventions.md` | 速查版 · 大段引用 author SKILL |

## 3 · 待办

- [x] §1-§8 frontmatter schema 完整(v0.10)
- [x] docs vs subtasks 决策树 + 双形式(frontmatter / body)
- [x] file naming conventions(module / concept / plan / rfc / spec)
- [x] validator output 解读 + Issue.reference 反向指向
- [ ] §2.4 · subtask 对象 schema 完整定义(`id / title / status / code / docs`)@docs:docs/plans/P-v0.11-driver-seat.md
- [ ] §2.4 · id 算法 `<module-id>-<sha1(title)[:6]>` + title 修改 = id 重算的 trade-off 说明
- [ ] §10 · prompt template 章节 + 4 内置 template 介绍 + ChoiceLoader 寻找顺序
- [ ] §10.2 · context vars stability contract(plan-eng-review 2A · 列 v0.X vars + since-version + 升级守则)
- [ ] `## 3 · 待办` body 内联语法 `@code:path:lines @docs:ref` 文档化
