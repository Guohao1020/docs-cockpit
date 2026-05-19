---
id: M16
type: module
title: "Multi-subtask bundle selection · backlog UX"
status: not-started
sprint: "0.14"
progress: 0
desc: "Backlog 行加 checkbox · 跨 module 多选 · floating bar 弹「N selected · Bundle 推荐 · Copy bundle prompt」"
owner: harvey
prd_ref: "v0.14 plan §5.2"
docs:
  - { title: "v0.14 plan · §5.2",       path: "docs/plans/P-v0.14-batch-driver.md" }
  - { title: "M15 backlog view",        path: "docs/spec/module/M15-backlog-view-filters.md" }
  - { title: "Author skill · §3.1",     path: "skills/docs-cockpit-author/SKILL.md" }
depends_on: [M15]
blocks: [M17]
---

# M16 · Multi-subtask bundle selection

## §1 · 范围

在 M15 backlog view 之上 · 让用户跨 module 勾选 N 个 subtask · 底部 floating bar 提供 bundle 操作。Bundle prompt 的真生成走 M17 · 本 module 只做 UX + selection state。

```
┌─ backlog page(M15)
│   ☑ M07-f75501  ...
│   ☐ M07-53a63a  ...
│   ☑ M07-fbe944  ...
│   ☑ M11-9adb12  ...
└─ floating bar (bottom · sticky · 仅 N≥1 显)
    ┌─────────────────────────────────────────────────┐
    │ 3 selected · ⓘ Bundle 推荐 · [Copy bundle prompt] [Clear] │
    └─────────────────────────────────────────────────┘
```

ⓘ tooltip · 显 M17 build-time 算好的 cohesion / conflict score(M16 只读不算)。

## §2 · 关键文件

| 文件 | 角色 |
|---|---|
| `docs_cockpit/templates/index.html.tmpl` · `BUNDLE_SELECTION_KEY` localStorage | selection state(`Set<subtask_id>` 序列化) |
| `docs_cockpit/templates/index.html.tmpl` · `<aside id="bundle-bar">` | floating action bar |
| `docs_cockpit/templates/index.html.tmpl` · `toggleBundleSelection(stKey)` | toggle handler |
| `docs_cockpit/templates/index.html.tmpl` · `renderBundleBar()` | 更新 N / 按钮状态 |
| `docs_cockpit/templates/index.html.tmpl` · CSS `.bundle-bar` · sticky bottom · HP 蓝主色 | 视觉风格跟 Refine 按钮一致 |
| `tests/integration/test_bundle_select.py` · pytest-playwright | toggle + clear + N display |

## 3 · 待办

- [ ] Backlog 每行渲染 checkbox + `data-bundle-key="<subtask.id>"` · click toggle selection
- [ ] localStorage `BUNDLE_SELECTION_KEY` 存 `Set<subtask_id>` JSON · 跟 0.11.3 build-time invalidation 一致(build 切就 reset)
- [ ] `<aside id="bundle-bar" hidden>` 容器 · sticky bottom · HP 蓝填色按钮
- [ ] `renderBundleBar()` · N≥1 显 / N==0 hidden · 显「N selected」+ ⓘ + [Copy bundle prompt] + [Clear]
- [ ] [Clear] 清 selection + hide bar
- [ ] [Copy bundle prompt] · 调 `window.__BUNDLE_PROMPTS__[bundle-hash]`(M17 sidecar)· 走 clipboard fallback
- [ ] 键盘 · 上下 arrow 移焦点 / Space toggle / Esc clear · accessibility
- [ ] [Copy bundle prompt] 按钮 disabled 状态 · 当 sidecar 没对应 hash 时(用户挑了奇怪组合 · sidecar 没预算)· tooltip 提示「run docs-cockpit build to refresh bundle sidecar」
