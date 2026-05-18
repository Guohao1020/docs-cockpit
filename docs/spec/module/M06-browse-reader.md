---
id: M06
type: module
title: "Browse Reader · Tree-sidebar Doc Browser"
status: done
sprint: "0.10"
progress: 100
desc: "docs/browse.html 单文件文档浏览器 · 左 tree sidebar + marked.js 渲染 · 不依赖 server"
owner: harvey
prd_ref: "browse skill"
docs:
  - { title: "browse command", path: "commands/browse.md" }
depends_on: [M01]
blocks: []
---

# M06 · Browse Reader · Tree-sidebar Doc Browser

## §1 · 范围

`docs-cockpit browse` 生成 `docs/browse.html` · 单文件 + tree sidebar + marked.js 客户端渲染 · 不需要 server · file:// 可直接打开。是 cockpit 的姐妹工具(cockpit 是 Kanban · browse 是文件浏览器)。

## §2 · 关键文件

| 文件 | 角色 |
|---|---|
| `docs_cockpit/browse.py` | 扫描目录树 · 嵌入 marked.js · 输出单 HTML |
| `docs_cockpit/templates/browse.html.tmpl` | HTML 模板 · 左 tree + 右 marked.js render |
| `commands/browse.md` | slash command 入口 |

## 3 · 待办

- [x] browse.html.tmpl 渲染 tree
- [x] marked.js 集成 + GFM
- [x] tree filter / search
- [x] file:// 兼容(不走 fetch · MD 内容内联)
