---
id: M15
type: module
title: "Backlog view + filters · cross-module subtask 扁平视图"
status: not-started
sprint: "0.14"
progress: 0
desc: "新 backlog view · 跨 module 扁平 subtask 列表 · 时间 / sprint / 状态 / 搜索四向 filter · 让用户找到「我现在要做的那批」"
owner: harvey
prd_ref: "v0.14 plan §5.1"
docs:
  - { title: "v0.14 plan · §5.1",          path: "docs/plans/P-v0.14-batch-driver.md" }
  - { title: "Dashboard template",         path: "docs_cockpit/templates/index.html.tmpl" }
  - { title: "Design tokens",              path: "references/design_tokens.md" }
depends_on: []
blocks: [M16]
---

# M15 · Backlog view + filters

## §1 · 范围

新 view · hash route `#/backlog` · 扁平 subtask 列表 + filter bar。Kanban 现在只能看 module 级 progress · backlog 让用户跨 module 找 subtask。

```
┌─ topbar
├─ filter bar (sticky)
│   [Time: All ▼] [Sprint: All ▼] [Status: All ▼] [🔍 search...]   清除
├─ subtask 列表
│   ☐ M07-f75501  cockpit_prompt tool                M07 · 0.12 · done
│   ☐ M11-9adb12  code_anchors path_only             M11 · 0.13 · not-started
│   ☐ M14-...     CSS audit                          M14 · 0.13 · not-started
│   ...(按 sprint desc → module id 排)
└
```

URL state:filters 写 hash query · `#/backlog?sprint=0.14&status=not-started&q=parser` 可分享 / 还原。

## §2 · 关键文件

| 文件 | 角色 |
|---|---|
| `docs_cockpit/templates/index.html.tmpl` · 新 `<section id="backlog-page">` | view 容器 + filter bar + 行渲染 |
| `docs_cockpit/templates/index.html.tmpl` · hash router `parseHash` + `applyRoute` | 加 `#/backlog` kind |
| `docs_cockpit/templates/index.html.tmpl` · JS `renderBacklog(filters)` | 主渲染函数 |
| `docs_cockpit/templates/index.html.tmpl` · JS `_filtersFromHash()` + `_filtersToHash()` | URL state codec |
| `tests/integration/test_backlog_render.py` · pytest-playwright | hash route + filter chain 验证 |

## 3 · 待办

- [ ] hero 下方加「View Backlog」link · 跳 `#/backlog`
- [ ] `<section id="backlog-page" hidden>` 新增容器 + sticky filter bar CSS(0.12.1 学的 `.split-page[hidden]` 显式 override)
- [ ] hash router 支持 `#/backlog` + 解码 `?sprint=...&status=...&q=...` query
- [ ] `renderBacklog(filters)` 跑 4-axis filter chain · 输出 subtask 行 list
- [ ] filter bar 4 控件(Time / Sprint / Status / Search)+ active chip 显示已选 + 「清除全部」按钮
- [ ] 排序 default sprint desc → module id → subtask order · 也支持 by title / by status(下拉切)
- [ ] 每行带 [Copy prompt] 图标 · 复用单 subtask Copy prompt 路径
- [ ] 集成测试 · pytest-playwright 跑 #/backlog?sprint=0.14 · 验只显 v0.14 subtask
