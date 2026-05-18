---
id: DOCS-COCKPIT-V0.11-UI-SPLITVIEW-2026-05-18
type: plan
title: "v0.11 UI 重做 · split-view 驾驶舱 · alpha.6 sub-plan"
status: planned
sprint: "0.11"
owner: harvey
desc: "把 dashboard 从 modal-drawer 体验重做成 split-view 二级页面驾驶舱 · 接 alpha.2 W1 + alpha.3 W3 backend 已经做好的 code_anchors + prompts.js sidecar 数据 · 闭环 v0.11 driver-seat 叙事"
created: 2026-05-18
depends_on:
  - DOCS-COCKPIT-V0.11-PLAN-2026-05-18
  - DOCS-COCKPIT-V0.11-BACKLOG-2026-05-18
docs:
  - { title: "v0.11 driver-seat plan · §6.6 + §6.7", path: "docs/plans/P-v0.11-driver-seat.md" }
  - { title: "v0.11 backlog · §2 P0 A", path: "docs/plans/P-v0.11-remaining-backlog-2026-05-18.md" }
---

# v0.11 UI 重做 · split-view 驾驶舱 · alpha.6 sub-plan

## §0 · 精度边界 · python 解析层 / LLM 语义层(2026-05-18 round-4)

主 plan §0 已 lock:**driver-seat 是 AI 副驾不是精度引擎**。alpha.6 范围:

- ✅ python `_resolve_doc_anchor` **解析层精度** · `path:start-end` / `path#§slug` 语法解析 + heading 位置定位 · 让 AI 输出的 anchor 能渲染
- ✅ frontend 渲染 AI 给的 anchor:滚动 + visual highlight section
- ❌ **不用 python 做语义精度**(不写「猜 subtask 跟 doc 哪段相关」的 regex / 反向 index)
- ❌ **不用 python 做 module-aware highlight**(不写「灰显非相关 section」的 visual filter)

语义精度的两条 AI 路线 留 alpha.7:
- 模式 3 · 升级 `docs-cockpit-author` SKILL.md · 教 Claude 写 MD 时直接产出准确 anchor
- 模式 2 · split-view 加「🤖 Ask AI to refine」按钮 · 走 prompts.js 延伸

见 `docs/plans/P-v0.11-ai-augmented-precision-alpha7-2026-05-18.md`。

## §1 · Dogfood 现状 · 当前 dashboard 长什么样

### §1.1 · 主 dashboard(index.html · 一屏)

```
┌───── topbar ───────────────────────────────────────────────────┐
│ [D] docs-cockpit | DOGFOOD · v0.11 PREP    Last build  Sys EN θ │
└────────────────────────────────────────────────────────────────┘
┌─── hero ───────────────────────────────────────────────────────┐
│ [D]  docs-cockpit                                       94.2%  │
│      YAML-frontmatter 驱动的项目 Kanban · CLI + plugin           │
└────────────────────────────────────────────────────────────────┘
┌─── KPI strip ──────────────────────────────────────────────────┐
│  Total 6  |  Done 4  |  In-progress 2  |  Not-started+Blocked 0│
└────────────────────────────────────────────────────────────────┘
┌─── 模块 KANBAN ────────────────────────────────────────────────┐
│ Not-started 0 │ Planned 0 │ In-progress 2 │ Blocked 0 │ Done 4 │
│               │           │  [M03 Plugin] │           │ [M01]  │
│               │           │  [M04 Author] │           │ [M02]  │
│               │           │               │           │ [M05]  │
│               │           │               │           │ [M06]  │
└────────────────────────────────────────────────────────────────┘
┌─── Sprint timeline ────────────────────────────────────────────┐
│ 0.10  · 2 modules · avg 100%                                    │
│ 0.11  · 4 modules · avg 84%                                     │
└────────────────────────────────────────────────────────────────┘
┌─── Concept grid ───────────────────────────────────────────────┐
│ (empty · 不配)                                                   │
└────────────────────────────────────────────────────────────────┘

[Click System Docs btn 弹 drawer]
[Click module card 弹 drawer]
```

### §1.2 · 当前 Module drawer(modal · 弹出)

```
┌─── 右侧滑出 max-width 960px · 占 ~50% 视口 ────┐
│ M01 · 进行中 · 0.11                  [×]      │
│ Build Engine                                   │
│                                                │
│ 描述                                            │
│ MD frontmatter → state.json + index.html...   │
│                                                │
│ 状态:[未启动][已排期][进行中][阻塞][已完成]      │
│                                                │
│ 进度  85%   ━━━━━━━━━━━━━━━━━━━━ [手动调整]   │
│ 0  25  50  75  100                            │
│                                                │
│ 子任务  9/10 完成                                │
│ [x] v0.10 build_payload + render_html 稳定     │
│ [ ] sidecar 输出 ...                            │
│ ...                                            │
│                                                │
│ 关联文档  4 项                                   │
│ ► v0.11 driver-seat plan          [预览] MD    │
│   v0.11 test plan                  [预览] MD    │
│   Frontmatter conventions          [预览] MD    │
│   Design tokens                    [预览] MD    │
│                                                │
│ [点 预览 → drawer 内整个区域被替换为 MD 渲染 ·   │
│  再点 back 回 module 视图]                       │
└────────────────────────────────────────────────┘
```

### §1.3 · 当前 systemDocs drawer

```
┌─── 顶 bar drawer 弹出 ─────────────────────────┐
│ 系统文档 · MEMORY & GUIDES         [×]         │
│ 项目级文档与记忆                                  │
│                                                │
│ 常驻文档  7 项                                   │
│ ┌────────────────────────────────────────────┐ │
│ │ ◯ CLAUDE.md                              ▸ │ │
│ │   项目级 AI 协作约定 · 架构 / SemVer       │ │
│ │   D:\harvey_work\docs-cockpit\CLAUDE.md   │ │
│ └────────────────────────────────────────────┘ │
│ [...6 more entries · 全是 <a target="_blank">] │
│                                                │
│ [Click · 浏览器新窗口打开 file:// MD raw text · │
│  不 marked 渲染 · 体验割裂]                      │
└────────────────────────────────────────────────┘
```

### §1.4 · alpha.2 / alpha.3 backend 已加但 frontend 没用上的字段

```
state.json::modules[].subtasks[]
  · id          · alpha.5 frontend 用了 (localStorage key) ✅
  · status      · alpha.5 frontend 用了 (display) ✅
  · code        · 用户原始 · 没渲染   ❌
  · code_anchors[]  · alpha.2 算好的 {resolved, preview, vscode_url}  ❌
  · docs        · 用户原始 · 没渲染   ❌

prompts.js sidecar
  · window.__PROMPTS__[subtask.id]   · alpha.3 算好的渲染好 prompt string  ❌
  · 没有「Copy prompt」按钮触发它

systemDocs[]
  · content     · ❌ 根本没生成(systemDocs 没经过 _resolve_and_embed_docs)
```

## §2 · 新驾驶舱设计 · split-view 二级页面

### §2.1 · 路由模型

```
URL hash             page
────────────────────────────────────────────────
(none) / #/         Dashboard 首页(Kanban + Timeline + Concept Grid)
#/module/M01        Module 二级页面 · split-view
#/sysdoc/claude-md  SystemDoc 二级页面 · split-view
#/concept/C01       Concept 二级页面 · split-view(轻量版)
#/?ui=modal         向后兼容 · 强制走老 modal drawer
```

`hashchange` event 监听 · 切 page · 浏览器后退键 work · 复制 URL 分享 work。

### §2.2 · Page 1 · Dashboard 首页(基本不变)

主结构跟 v0.10 一样:topbar + hero + KPI + kanban + sprints + concepts。**只改 click handlers**:

| 元素 | v0.10 行为 | 新行为 |
|---|---|---|
| Module card click | `openModuleDrawer(id)` 弹 modal | `location.hash = '#/module/' + id` |
| System Docs btn click | `openDocsDrawer()` 弹顶 bar drawer | drawer 内每条 row · click → `location.hash = '#/sysdoc/' + id`(drawer 仍弹 · 作为「入口列表」) |
| Concept card click | (没有 modal · 只显示) | `location.hash = '#/concept/' + id` |

System Docs drawer 改:不再是「列表 + 跳新窗口」· 改为「列表 + 跳二级页面」。

### §2.3 · Page 2 · Module 二级页面 · split-view

```
┌─── topbar(常驻 · 加返回按钮)──────────────────────────────────────┐
│ ← Back to Dashboard  |  [D] docs-cockpit  M01 · Build Engine    │
└─────────────────────────────────────────────────────────────────┘
┌─── Left Navigator(38% · min 360px) ─┬─── Right Preview(flex)────┐
│                                       │                            │
│ M01 · 进行中 · 0.11        100%       │ # v0.11 driver-seat plan   │
│ Build Engine                          │                            │
│                                       │ Generated by /office-hours │
│ 描述                                   │ Branch: main · Repo: ...   │
│ MD frontmatter → state.json...        │                            │
│                                       │ ## §1 · Problem Statement  │
│ 状态:5 个 status button             │ docs-cockpit 现状是一个...  │
│                                       │                            │
│ 进度 100% ━━━━━━━━━━━━━━━━━━━━       │ ## §2 · What Makes...     │
│ [手动调整 toggle]                       │ ...                        │
│                                       │                            │
│ 子任务 10/10 完成                       │ (marked.js 渲染 · 完整 MD) │
│ ┌──────────────────────────────────┐  │                            │
│ │ [x] v0.10 build_payload 稳定      │  │ [当前 active doc · 高亮]   │
│ │ [x] frontmatter validator + ...  │  │                            │
│ │ [x] @plan-eng-review 1A · 拆 ... │  │                            │
│ │     📄 docs_cockpit/build.py     │← │ [点 code 图标 → 右栏改   │
│ │     [↗ VS Code]  [📋 Copy prompt]│  │  显示 code preview snippet │
│ │ ...                              │  │  + vscode 深链按钮]        │
│ └──────────────────────────────────┘  │                            │
│                                       │                            │
│ 关联文档 4 项                          │                            │
│ ► v0.11 driver-seat plan      📄     │ ← active (右栏当前显示)     │
│   v0.11 test plan             📄     │                            │
│   Frontmatter conventions     📄     │                            │
│   Design tokens               📄     │                            │
│ [Click 切右栏到这条 doc]               │                            │
│                                       │                            │
│ depends on:                           │                            │
│ blocks: M02                           │                            │
└───────────────────────────────────────┴────────────────────────────┘
```

**关键交互**:
- 默认右栏:渲染第一条 linked doc(0.7.1 已 embed content)
- 点 linked docs list 任意 row → 右栏切到那条 doc(active 高亮 ► 跟随)
- 点 subtask checkbox → toggle done(走 alpha.5 stable id localStorage)
- 点 subtask 的 code 图标 → 右栏渲染 code preview snippet(alpha.2 `code_anchors[].preview`)+ 「↗ Open in VS Code」按钮(`vscode_url`)
- 点 subtask 的 📋 Copy prompt → 取 `window.__PROMPTS__[subtask.id]`(alpha.3 prompts.js) → 复制到剪贴板 + toast(右栏**不切**保持当前预览)
- 点 status select(5 button)→ 写 localStorage + frontend override
- 点 progress slider → 写 localStorage + frontend override
- 点 「← Back to Dashboard」/ 按 Esc → `location.hash = ''`

### §2.4 · Page 2 · SystemDoc 二级页面 · split-view(简化版)

```
┌─── topbar(常驻)────────────────────────────────────────────────┐
│ ← Back to Dashboard  |  System Docs · CLAUDE.md                 │
└──────────────────────────────────────────────────────────────────┘
┌── Left Navigator(38% · min 360px)──┬── Right Preview(flex)─────┐
│                                      │                            │
│ System Docs · 7 项                    │ # CLAUDE.md                │
│ ┌──────────────────────────────────┐ │                            │
│ │ ► CLAUDE.md                      │ │ This file provides...     │
│ │   memory · 项目级 AI 协作约定     │ │                            │
│ │   D:\...\CLAUDE.md                │ │ ## What this repo is       │
│ ├──────────────────────────────────┤ │ ...                        │
│ │   README                          │ │                            │
│ │   doc · 项目总览                  │ │ (marked.js 渲染)            │
│ ├──────────────────────────────────┤ │                            │
│ │   README · 中文                    │ │                            │
│ │ ...                              │ │                            │
│ └──────────────────────────────────┘ │                            │
│                                      │                            │
└──────────────────────────────────────┴────────────────────────────┘
```

**特殊**:
- 左侧不是单 entity 详情 · 是 systemDocs list(同顶 bar drawer 内容但永久显示)
- 右侧渲染当前 active 那条的 content
- 切别的 system_doc:URL 变 `#/sysdoc/<new-id>` · 左 list active 高亮跟随

### §2.5 · Page 2 · Concept 二级页面(轻量版 · 跟 Module 同布局但 fields 少)

Concept 在 docs-cockpit 模型里是 simpler 卡(`{id, title, status, sprint, progress}`)· 没 subtask 没 docs 没 desc 通常。所以二级页面:
- 左 navigator 显示基本 status / progress / sprint
- 右 preview 直接渲染 concept MD body(用 marked.js · 走 0.7.1 embed)

如果 concept 没 docs:右栏显示 concept MD body 本身。

### §2.6 · 响应式

```
viewport         layout
────────────────────────────────────────────────────────
≥ 1024px        左 navigator + 右 preview 并列 grid
768-1023px      左 navigator collapsible dropdown · 右 preview 全宽
< 768px         stacked 单列 · 左在上 · 右在下 · 点 doc list 滚到 preview
```

**移动端**:不优化 · graceful degrade · 是桌面侧驾驶舱工具(plan §6.6 已 lock)。

### §2.7 · 向后兼容

- `?ui=modal` URL query 保留原 modal drawer 体验
- 用户 v0.10 的书签 / muscle memory 不破
- 默认走新 split-view · 老体验需要 explicit opt-in

## §3 · Backend 改动(plan §6.7)

只一处:`build.py::build_payload` 给 systemDocs 接 `_resolve_and_embed_docs`(0.7.1 module 已经接了)· 输出 systemDocs[].content / mtime / exists。

```python
# 0.11.0-alpha.6:systemDocs 也 embed content · 让 split-view 右栏渲染
sys_docs_raw = _build_system_docs(config.get("system_docs"), vars_)
# Wrap as docs list for _resolve_and_embed_docs 复用
sys_with_content = _resolve_and_embed_docs(
    [{"title": d["title"], "path": d["path"]} for d in sys_docs_raw],
    pathlib.Path(vars_["repo"]) / "<virtual>",  # fake module path
    pathlib.Path(vars_["repo"]),
    vars_,
)
# Merge 回 sys_docs_raw
for d, c in zip(sys_docs_raw, sys_with_content):
    d["content"] = c["content"]
    d["mtime"] = c["mtime"]
    d["exists"] = c["exists"]
```

单 doc content hard cap 50KB(plan §6.7 防 memory dir 撑爆)· `_MAX_EMBED_BYTES` 已经是 100KB · system_docs 用更紧的 50KB cap。

## §4 · 实施分块 · 5 个 commit chain

按风险递增 · 每块独立 commit · 任意一块出问题能 revert:

### §4.a · Backend systemDocs embed(plan §6.7)

工程量:**2-3 小时**
- `build.py::build_payload` 加 systemDocs `_resolve_and_embed_docs` 调用
- 50KB hard cap helper
- Unit test 覆盖 systemDocs content embed
- 验证:`state.json::systemDocs[0].content` 非空

风险:低 · 只动 build_payload · 不破任何前端

### §4.b · Hash router + topbar 「← Back」按钮

工程量:**3-4 小时**
- 加 `window.location.hash` 监听 + 解析 router
- `_currentPage = parseHash()` · 返 `{kind: 'dashboard' | 'module' | 'sysdoc' | 'concept', id?: string}`
- 顶 topbar 加「← Back to Dashboard」按钮(URL 不在 dashboard 时显示)
- Esc 键 listener · 触发 `location.hash = ''`
- `?ui=modal` query 检测 · 走旧 modal flow

风险:中 · 加路由层 · 跟现有 modal handler 共存

### §4.c · Split layout CSS + 左 navigator

工程量:**4-5 小时**
- 新 CSS class `.split-page` / `.split-nav` / `.split-preview`
- `display: grid; grid-template-columns: minmax(360px, 38%) 1fr`
- 媒体查询 < 1024 / < 768
- 左 navigator 复用现 `.drawer-body` 内容但去掉 max-width · 加 `.split-nav` 包

风险:中 · CSS 大改 · 影响视觉

### §4.d · 右 preview + linked docs 切换 + code anchor 渲染

工程量:**5-6 小时**
- 右 preview 区 marked.js 渲染 doc content
- 左 navigator linked docs list · click → 切右栏 active
- subtask code 图标 · click → 右栏渲染 code preview + vscode 深链按钮
- subtask Copy prompt button · click → `window.__PROMPTS__[id]` + execCommand fallback(0.10.1 已 ship)

风险:中 · 接 alpha.2 / alpha.3 已有 backend 数据 · 但渲染逻辑新

### §4.e · 测试 + alpha.6 release

工程量:**3-4 小时**
- `tests/e2e/test_split_view.py` Playwright 测:
  - dashboard → 点 module card → URL `#/module/M01`
  - 左 navigator 显示 subtasks + linked docs
  - 右 preview 默认渲染第一条 doc
  - 点 linked docs 切右栏
  - Esc / Back 返 dashboard
  - `?ui=modal` 走 modal flow
- 4 文件 version bump 0.11.0-alpha.5 → 0.11.0-alpha.6
- CHANGELOG 写完整 alpha.6 section
- dogfood docs-cockpit 自身 · 截图对比 alpha.5 vs alpha.6

风险:低 · 收尾 · CC+gstack 加速 OK

**总工程量:~2-3 工作日 CC+gstack · 或 ~1.5-2 周 human**

## §5 · 不动的东西

- HTML 仍是单文件 · 不引入 SPA framework(React / Vue / Svelte)
- state.json schema 不变(只加 systemDocs content 字段)
- 老 modal drawer 代码保留 · `?ui=modal` 切回去
- subtask schema / code anchor / prompt scaffolding · alpha.2/3 已 stable
- prompts.js sidecar 格式 / window.__PROMPTS__ 不变

## §6 · 验收点

### §6.1 · 功能验收(必须全过)

- [ ] 点 dashboard 任意 in-progress module → URL `#/module/<id>` · 切到 split-view
- [ ] 二级页面右栏默认渲染第一条 linked doc(marked.js)
- [ ] 点左 navigator 另一条 linked doc → 右栏切 + active 跟随
- [ ] 点 subtask code 图标 → 右栏渲染 code preview + vscode 深链
- [ ] 点 subtask Copy prompt → 复制成功 + toast
- [ ] 「← Back」/ Esc → 回 dashboard
- [ ] 点 System Docs btn → drawer 显示 · 点某条 → 切到 sysdoc split-view
- [ ] sysdoc split-view 右栏 marked.js 渲染 CLAUDE.md / README 等内容(不再新窗口)
- [ ] `?ui=modal` URL · 跑老 modal drawer flow
- [ ] 复制 URL `#/module/M01` 给别人 · 打开直接到那个 module split-view

### §6.2 · 数据一致性验收(alpha.4/5 教训)

- [ ] subtask checkbox · localStorage key 仍用 alpha.5 stable id
- [ ] status 改 · localStorage override 在 split-view 跟 modal 都生效
- [ ] alpha.4 cross-field validator(status × subtasks)输出 issue 在 split-view 也能看到

### §6.3 · 性能 / 体积 验收

- [ ] 主 `index.html` 体积:alpha.5 411KB → alpha.6 估算 ≤ 500KB(+22%)· plan §8 -20% budget 内
- [ ] `state.json` 增加 systemDocs content(7 个 × ~5-10KB)· ~50KB · OK
- [ ] HTML 首次渲染 < 200ms(viewport ≥ 1024px)
- [ ] 切 module split-view → 切回 dashboard:无 reload · 无白屏

### §6.4 · 响应式验收

- [ ] 1920px wide:左右双列舒服
- [ ] 1024px (boundary):双列 · 不破
- [ ] 768-1023px:左变 collapsible · 右全宽
- [ ] < 768px:stacked 单列 · 移动端 readable

### §6.5 · 向后兼容验收

- [ ] 老用户 `?ui=modal` 仍能用 modal drawer
- [ ] 0.10 时代手工勾的 localStorage 状态(alpha.5 已经做 cleanup)· alpha.6 升级后仍工作
- [ ] 老 module / concept / sysdoc YAML 不需要改

## §7 · 风险 + Mitigations

| 风险 | Mitigation |
|---|---|
| HTML template 改 400-500 行 · 容易破现有 modal 渲染 | `?ui=modal` 保留老 path · 走老代码 · 不删 |
| 移动端 < 768px 体验差 | graceful degrade 一栏 · plan §6.6 明确不是 priority |
| systemDocs content embed 加 50KB payload | hard cap 50KB / doc + alpha.6 单文件 HTML 仍 < 500KB |
| 用户 muscle memory 习惯 modal · split-view 不适应 | `?ui=modal` opt-in 老体验 · CHANGELOG 显眼说明 |
| split-view 大改后 alpha.6 引入 regression | 跑全套 Playwright e2e + dogfood docs-cockpit 自身一次 |

## §8 · 开始信号

user 已选 §2 A(UI split-view)· 现在等:

- [ ] 本 spec 你 review 一遍 · 有要改的告诉我
- [ ] 确认后我开 alpha.6 · 按 §4 a→e 5 块顺序推

每块独立 commit · 完成后 surface · 你能在任意一块叫停。

---

**Status:** planned · 等用户 confirm 后启动 alpha.6
