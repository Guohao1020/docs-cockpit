---
id: P-v0.14
type: plan
title: "v0.14 · Batch driver · Kanban 过滤 + 多子任务批量执行"
status: planned
sprint: "0.14"
progress: 0
desc: "Kanban 升级到「批量执行驾驶舱」· 跨 module 选 subtask · 一次生成 bundle prompt · LLM 推荐哪些任务该一起做"
prd_ref: "用户截图反馈 · Kanban 增加筛选 + 多 subtask 一起跑 + bundle skill 推荐"
docs:
  - { title: "v0.13 plan · DX polish",       path: "docs/plans/P-v0.13-polish-and-edges.md" }
  - { title: "v0.11 driver-seat plan",       path: "docs/plans/P-v0.11-driver-seat.md" }
  - { title: "Author skill · §11 / §13",     path: "skills/docs-cockpit-author/SKILL.md" }
depends_on: [P-v0.13]
---

# Plan · docs-cockpit v0.14 · Batch driver

Generated 2026-05-19 · Status: **PLANNED**

## §0 · 角色定位

v0.11/v0.12/v0.13 把 driver-seat 模式 1/2/3 全部 ship · 单 subtask 闭环完美。但**真实工作里 subtask 经常成组**:

- 「这 3 个 subtask 都改同一个 file」→ 一次跑省 context 加载成本
- 「M07-f75501 + M07-53a63a 都在 mcp_server.py」→ 串行做更省 review 来回
- 「M08-parse + M08-apply 是同一个数据流」→ 一起规划比逐个推更合理

v0.14 升级 driver-seat 体验:**从「单 subtask 闭环」→「subtask 集合闭环」**。

## §1 · Problem Statement

### P1 · Kanban 找不到「我现在要做的那批 subtask」

Kanban 当前只显 module 卡片 + module 级 status / progress · 用户想问的「哪些 subtask 是这周该做的」「哪些跟 file X 相关」「哪些被 block 了」全都得手点进每个 module drawer。

具体痛点:
- **没时间筛选** · 不知道哪个 subtask 是这周改过的 / 这个月新加的
- **没 sprint 筛选** · v0.10/v0.11/v0.12/v0.13/v0.14 module 全堆一起 · 想专注 v0.14 backlog 没快捷
- **没状态筛选** · 想看「所有 blocked subtask」得跑 standup CLI · 不在 UI 里

### P2 · 多 subtask 没法一起跑

用户想做「M07-f75501 + M07-53a63a + M07-fbe944 一次跑 · 一份 prompt 喂 Claude」· 当前必须复制 3 次 prompt(单 subtask 各一次)· 拼接体验差。

需求:
- 选 N 个 subtask(跨 module 也行)
- 一次性 [Copy bundle prompt]
- Prompt 含 N 个 subtask 的完整上下文 + 推荐执行顺序(沿 depends_on)

### P3 · 没人告诉用户「哪些 subtask 该一起跑」

用户当前靠经验判断「这两个 subtask 在一个 file 里 · 应该一起做」。Cockpit 是上下文供给器 · 应该**主动建议** bundle 候选:
- 同 file / 同 plan § 的 subtask cohesion 高
- 改同 file 不同行 = conflict 风险(不该 bundle)
- 链式 depends_on 的 subtask 串行 bundle 比并行更有意义

## §2 · What Makes This Cool

Kanban 从「项目状态展示器」→「批量任务调度台」。落地后驾驶员体验:

```
打开 dashboard · 顶部切到 Backlog 标签
  ↓
看到跨 module 的扁平 subtask 列表 · 每条带 checkbox
  ↓
顶部 filter chip · 点「7 天内」+「sprint 0.14」+「not-started」· 列表收敛
  ↓
勾 4 个 subtask · 底部 floating bar 显「4 selected · ⓘ Bundle 推荐 · [Copy bundle prompt]」
  ↓
ⓘ hover · 看 LLM 推荐结果「✅ 这 4 个同在 mcp_server.py · 一次做省 review · 推荐串行 M07-f75501 → M07-53a63a → M07-fbe944」
  ↓
点 Copy · prompt 进剪贴板 · 含 4 个 subtask + 关联 doc anchor + 推荐顺序 + caller-aware sync 指令
  ↓
粘到 Claude Code · Claude 串行完成 + 自动勾 4 个 checkbox + build · driver-seat 闭环完成
```

## §3 · Constraints

- **不能破 v0.11/v0.12/v0.13 单 subtask 闭环** · Bundle 是叠加路径 · 老 Copy prompt 按钮 / Refine 按钮全部保留
- **Backlog 是叠加 view · 不取代 Kanban** · Kanban 主页保留 · Backlog 走 tab / hash route(`#/backlog`)
- **Bundle prompt 是聚合 prompt · 不是 N 个 prompt 拼接** · 共享上下文(同 module 一次给 / 同 doc 一次嵌)只列一次 · 子任务清单分别说明
- **LLM bundle 推荐是建议 · 不强制** · 用户选哪些 cockpit 不阻拦 · 只在 UI 标 cohesion 分 + conflict 警告
- **跨平台 / file:// 友好** · 跟现有 dashboard 一致 · 无 server / 无 framework

## §4 · Approaches Considered

### Approach A · 扩 Kanban 卡片内联 subtask checkbox(原地展开)
每个 module 卡片下加 mini checklist · 用户在卡片上直接勾。
- ✅ 不引新 view · UX 简单
- ❌ 卡片高度爆炸(M03 有 7 subtask · 卡片高 10x)· Kanban 全 hero 视觉破坏
- ❌ 跨 module 跨 sprint 多选 UX 拙劣

### Approach B · 新 Backlog view + multi-select + bundle prompt ✅ CHOSEN
专门一个扁平 view · checkbox 跨 module · floating bar + bundle prompt CLI。
- ✅ 单 subtask 视图清晰 · 跟 module Kanban 互补
- ✅ filter / sort 可独立设计 · 不污染 Kanban
- ✅ Bundle prompt 是新 prompt template · 不动单 subtask 路径

### Approach C · 全功能(Backlog + 拖拽 reorder + 优先级 column + 拼调度面板)
- ❌ 工程量翻 3 倍 · 多数功能 (拖拽 reorder / 优先级) 用户没要求
- ❌ 复杂 UI 跟 v0.10 起约定的「single-file HTML · 无 framework」冲突

## §5 · Recommended Approach (B · 3 module)

### §5.1 · M15 · Backlog view + filters

**新 view** · hash route `#/backlog` · 通过 topbar tab 或 hero 下方 link 进入。

**Layout**:
```
┌─ topbar(老)
├─ filter bar
│   [Time: All ▼] [Sprint: All ▼] [Status: All ▼] [🔍 search...]
│   active filter chips:  [7d ✕] [sprint 0.14 ✕] [not-started ✕]   清除全部
├─ subtask 列表(扁平 · 跨 module)
│   ☐ M07-f75501 · cockpit_prompt tool · M07 (done)
│   ☐ M08-29373a · parse_patch · M08 (done)
│   ☑ M11-9adb12 · code_anchors path_only · M11 (not-started)  ← 当前选中
│   ...
└─ (M16 加 floating select bar 在底部)
```

**Filter dimensions**:
- **Time**:All / 7d / 30d / custom range(基于 module `mtime` 或 git blame · MVP 用 mtime)
- **Sprint**:multi-select dropdown · 从 state.json 自动 enum(0.10 / 0.11 / 0.12 / 0.13 / 0.14)
- **Status**:multi-select · 复用 5 个 enum(not-started / planned / in-progress / blocked / done)
- **Search**:对 subtask.title 走 substring 匹配(不考虑 fuzzy)

**Sort**:
- 默认 · sprint desc → module id → subtask order
- 也可 by title / by status

**URL state**:filters 编码到 hash query · `#/backlog?sprint=0.14&status=not-started&q=parser` 可分享 URL · 直接还原视图。

### §5.2 · M16 · Multi-subtask batch selection + UX

**Selection state**:`Set<subtask_id>` · localStorage 持久(同 build 内 · 跟 0.11.3 build-time invalidation 一致)。

**UX flow**:
- Backlog 每行左侧 checkbox · 点 toggle selection
- N ≥ 1 时 · 底部 floating action bar 弹出:`「N selected · ⓘ Bundle 推荐 [Copy bundle prompt] [Clear]」`
- ⓘ hover · tooltip 显 LLM 推荐(从 M17 build-time 算好的 bundle scoring)
- [Copy bundle prompt] · 调 `window.__BUNDLE_PROMPTS__[selection-hash]` · 复制到剪贴板
- [Clear] · 清 selection state

**键盘**:
- 上下 arrow · 移焦点
- Space · toggle 焦点行 selection
- Esc · clear

### §5.3 · M17 · Bundle prompt + recommendation skill

**Bundle prompt template**(`docs_cockpit/templates/prompts/bundle.md.j2` · 新):
- 输入:N subtasks across M modules
- 输出:聚合 prompt
  - 共享 module 上下文一次给(同 module N subtask 共用一个 module-meta 段)
  - subtask 清单按推荐顺序列出(沿 depends_on chain · 或同 file 串行)
  - 所有引用的 linked doc / code anchor 去重 · 一次给
  - caller-aware sync 段:**N 个 subtask 都要勾完才报告**

**Bundle CLI**:
```bash
docs-cockpit prompt --bundle M07-f75501,M07-53a63a,M11-9adb12
docs-cockpit prompt --bundle M07-f75501,M07-53a63a --copy
```

**Bundle recommendation skill**(author skill §14 + suggest template `bundle-recommendation.md.j2`):
- author skill §14 · 4 个 cohesion 维度:同 module / 同 file / 同 plan § / depends_on chain
- 4 个 conflict 维度:同 file 不同行 / 跨 sprint / 跨 owner / blocking 关系反向
- `docs-cockpit suggest --bundle-candidates [M07]` · LLM 检查这个 module 哪些 subtask 适合 bundle · 输出建议表
- Frontend `ⓘ Bundle 推荐` tooltip · 从 build-time 算好的 scoring 直读

**Build-time scoring**(轻量启发式 · 不调 LLM):
- 每对 subtask 之间算 cohesion score:
  - 同 module +3
  - 同 code 文件路径 +2
  - 同 doc anchor +1
  - depends_on 链 +2
- conflict score:
  - 同 file 不同 lines · 但 lines 重叠 +5(red flag)
- frontend 用 scoring 给推荐 hint · 也支持手动绕过

## §6 · Distribution Plan

- alpha.1 · M15 Backlog view + filters · 无 selection 也能用(单 subtask 浏览)
- alpha.2 · M16 multi-select + floating bar · 不带 bundle prompt(只 Copy IDs)
- alpha.3 · M17 bundle prompt + recommendation skill · 完整闭环
- 0.14.0 · 4 文件 version bump + CHANGELOG + push tag

## §7 · Success Criteria

- 3 modules 全部 done · 100%
- 198 + ~40 new tests · 全过
- 跨 sprint + 跨 module 选 5 subtask · Copy bundle prompt · 粘 Claude Code · Claude 串行完成 5 个并自动勾 5 个 checkbox + 1 次 build(driver-seat 闭环)
- Bundle recommendation 给出至少 80% 用户「这俩该一起做」直觉一致的建议(dogfood Sourcery 验证)

## §8 · Open Questions

- Backlog view 是 topbar tab(同级 dashboard / Backlog)还是 hero 下方 link?MVP 走 hash route `#/backlog` · UI 决定下放 alpha.1 实施时定
- Bundle prompt 长度上限?N=10 subtask 时 prompt 可能 30KB+ · 是否需要 summary mode?MVP 不截 · v0.15 候选
- Cohesion scoring 是否走 LLM augment?MVP 启发式 · v0.15 接 Claude API(模式 1)augment

## §9 · Out of scope · 留 v0.15+

- 跨 project portfolio backlog(M05 portfolio · 当前 single-project)
- Backlog 拖拽 reorder · 优先级 column
- 实时协作(多用户同时勾选)
- Bundle 执行 progress tracking · live diff watch
