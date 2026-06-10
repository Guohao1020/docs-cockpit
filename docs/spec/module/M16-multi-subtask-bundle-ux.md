---
id: M16
type: module
title: "Multi-subtask bundle selection · backlog UX"
status: done
sprint: "0.14"
progress: 100
desc: "Backlog 行加 checkbox · 跨 module 多选 · floating bar 弹「N selected · Bundle 推荐 · Copy bundle prompt」"
owner: harvey
prd_ref: "v0.14 plan §5.2"
docs:
  - { title: "v0.14 plan · §5.2",       path: "docs/plans/P-v0.14-batch-driver.md" }
  - { title: "M15 backlog view",        path: "docs/spec/module/M15-backlog-view-filters.md" }
  - { title: "subtask 格式(原 author §3.1)",     path: "references/schema.md" }
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

ⓘ tooltip · 显 M17 build-time 算好的 cohesion / conflict score(M16 只读不算)。(v1.0 注:M17 sidecar 已删 · verdict 走 fallback 文案 · Copy 按钮改为前端拼自然语言 bundle prompt)

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

- [x] Backlog 每行 checkbox + data-st-key · click `_toggleBundleSelection(stKey, checked)` @code:docs_cockpit/templates/index.html.tmpl
- [x] localStorage `BUNDLE_SELECTION_KEY` · 跟 0.11.3 build-time invalidation 一致(build 切就 reset)@code:docs_cockpit/templates/index.html.tmpl
- [x] `<aside id="bundle-bar" hidden>` · fixed bottom · HP 蓝 [Copy bundle prompt] 按钮 + outline [Clear] @code:docs_cockpit/templates/index.html.tmpl
- [x] `_renderBundleBar()` · N≥1 显 / 走 `window.__BUNDLE_META__` 算 cohesion verdict 显在 verdict span @code:docs_cockpit/templates/index.html.tmpl
- [x] [Clear] 清 selection · re-render backlog 清 checked 状态 @code:docs_cockpit/templates/index.html.tmpl
- [x] [Copy bundle prompt] · v1.0 改为前端拼自然语言 bundle prompt(选中 subtask 的 id+title 列表)直接进剪贴板 · 原 MVP 复制 CLI 命令(该 CLI v1.0 已删) @code:docs_cockpit/templates/index.html.tmpl
- [x] i18n EN/中 · bundle.copy / bundle.clear / bundle.prompt_head / bundle.prompt_tail / toast.bundle_prompt_copied(原 toast.bundle_cli_copied · v1.0 随 Copy 行为改) @code:docs_cockpit/templates/index.html.tmpl
- [x] [Copy bundle prompt] 状态 · 当 `window.__BUNDLE_META__` 没加载 verdict span 显 fallback message @code:docs_cockpit/templates/index.html.tmpl
