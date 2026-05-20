---
id: M14
type: module
title: "CSS time-bomb audit + UX polish"
status: done
sprint: "0.13"
progress: 100
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

- [x] grep template audit · 4 个 hidden element 全部已有 explicit `[hidden] { display: none; }` override · 无 specificity 隐 bug @code:docs_cockpit/templates/index.html.tmpl
- [x] 评估 global safety net `*[hidden]:not(...)`· 决定**不加**(4 个 element explicit cover · 加 global 性能略损且收益边际)@code:tests/integration/test_dashboard_render.py
- [x] `renderSplitPreviewSubtaskDoc` head 加 `📍 Showing lines X-Y of <file>` slice info badge · HP 蓝 pill 风格 @code:docs_cockpit/templates/index.html.tmpl
- [x] 扫一遍 i18n key 跟 hardcoded fallback · 确认 alpha 期占位文案已清干净 @code:docs_cockpit/templates/index.html.tmpl
- [x] 加轻量集成测试 · 不依赖 playwright 走 string-based 校验关键 DOM 结构 @code:tests/integration/test_dashboard_render.py
- [x] hash route 浏览器级测试推迟到下个 sprint · 当前静态结构已被集成测试 cover @code:tests/integration/test_dashboard_render.py
- [x] CHANGELOG 加 CSS audit 章节 · 走 v0.14.3 patch · 列 4 元素 explicit override 验证 + 评估不加 global safety net 的理由 @docs:CHANGELOG.md
