---
id: M14
type: module
title: "CSS time-bomb audit + UX polish"
status: not-started
sprint: "0.13"
progress: 0
desc: "扫光 v0.11/v0.12 留的 CSS specificity 隐 bug + alpha 期占位文案 · 加 [hidden] safety net + subtask doc preview header"
owner: harvey
prd_ref: "v0.13 plan §5.4 · v0.12.1 暴露的 .split-page[hidden] 撞 specificity bug"
docs:
  - { title: "v0.13 plan · §5.4",      path: "docs/plans/P-v0.13-polish-and-edges.md" }
  - { title: "HTML template",          path: "docs_cockpit/templates/index.html.tmpl" }
  - { title: "design tokens reference", path: "references/design_tokens.md" }
depends_on: []
blocks: []
---

# M14 · CSS time-bomb audit + UX polish

## §1 · 范围

v0.12.1 修过的 `.split-page[hidden] { display: none }` specificity bug 暴露一类隐性问题:author CSS 用 `display: grid/flex/block` 自定义 layout + HTML 用 `hidden` 属性切显隐 · UA 的 `[hidden] { display: none }` specificity 同级 winning 失效。可能不止一处。

同时清 v0.11/v0.12 alpha 期遗留:
- `## 上下文 · 子任务` 渲染时多余空行(prompt.py extract_subtasks_from_body 边界 stripping)
- subtask doc anchor 右栏切片预览没显「这是 path:lines 中的哪段」(M14 §3 路径定位标识)
- 可能还有几处 `§4.d` / `(no content)` 之类 alpha 占位文案

## §2 · 关键文件

| 文件 | 角色 |
|---|---|
| `docs_cockpit/templates/index.html.tmpl` | CSS audit · `[hidden]` safety net · 占位文案审查 |
| `docs_cockpit/templates/index.html.tmpl::renderSplitPreviewSubtaskDoc` | header 加 `path:lines` 标识 |
| `tests/integration/test_dashboard_render.py` | **NEW** · pytest-playwright · 验关键元素 visible/hidden 正确 |

## 3 · 待办

- [ ] grep template 所有 `display: (grid|flex|block)` · 列出哪些 element 也用 `hidden` 属性 · 加显式 `[hidden] { display: none; }` per-element rule
- [ ] 加全局 safety net `*[hidden]:not(.<known-exception>) { display: none !important; }`(评估副作用后决定加不加)
- [ ] `renderSplitPreviewSubtaskDoc` head 区加 `<path>:<lines>` 标识行 · 让用户在切片预览里知道这段是原文件哪里
- [ ] 扫 template 所有 `data-i18n` 跟 hardcoded fallback · 同步两边内容(避免 `§4.d will fill...` 这类 alpha 占位再出现)
- [ ] tests/integration/test_dashboard_render.py · pytest-playwright 跑 dashboard root · 验:split-page 不可见 / kanban-section 可见 / export 按钮存在
- [ ] 再跑 #/module/M11 · 验:split-page 可见 / kanban-section 不可见 / Refine + 同步 source 按钮渲染
- [ ] CHANGELOG 加「CSS audit」section · 列扫到的所有 specificity 隐 bug + 修法
