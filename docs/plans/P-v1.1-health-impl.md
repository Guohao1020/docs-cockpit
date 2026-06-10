---
id: P-V1.1-HEALTH-IMPL
type: plan
title: "v1.1 体检体系 · 实施 plan（9 task）"
status: planned
sprint: "1.1"
desc: "P1 落地：health-check reference + HEALTH.md doc kind + render 解析 + 看板健康面板 + Copy-prompt CTA + skill 升格 + alias 移除 + 1.1.0 release"
owner: harvey
prd_ref: "docs/plans/P-v1.1-health-check.md"
docs:
  - { title: "v1.1 设计 spec", path: "docs/plans/P-v1.1-health-check.md" }
---

# v1.1 Health-Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 build/rebuild 升格为全方位体检（九科双模式 · 三段式报告 · 五桶行动规划），体检结果经 `docs/HEALTH.md`（新 doc kind）进看板渲染（健康徽章 + 健康面板 + 处方卡），每条处方一键 Copy prompt 丢给 Claude Code 执行。同车完成 `build` alias 移除（1.1 既有承诺）。版本 1.1.0。

**Architecture:** 数据流 = skill 体检（认知）→ 写 HEALTH.md（frontmatter 结构化 + body 三段式）→ render 解析（机械 · 固定路径探测）→ `state.json::health` + 看板面板 → Copy-prompt（前端拼 · bundle CTA 同款）→ Claude Code 治疗 → rebuild 复查循环。实施顺序「规范 → 校验 → 解析 → 渲染 → skill → alias → dogfood → release」——每层落地后下一层才有依赖物。**python 任务走 TDD**（253 测试基线 · 只增不破），每 task commit 后 pytest + lint 绿。

**Tech Stack:** Markdown（reference + SKILL.md）· Python（schema.py validator + build.py 解析）· 模板 JS/CSS/i18n（健康面板 + CTA）· pytest。

**已锁边界**：P2（gstack 委托 + python 死指标自动统计）/ P3（趋势）不进本 plan；HEALTH.md 固定路径 `docs/HEALTH.md`（不进 config 扫描——与 state.json 同级的约定路径）；处方 prompt 前端拼（不进 prompts.js sidecar——处方数据已在 payload）。

---

## Task 1: `references/health-check.md`（体检方法论 SSOT）

**Files:**
- Create: `references/health-check.md`（目标 250-350 行）
- 参照: spec `docs/plans/P-v1.1-health-check.md` §1-§3、`references/association-method.md`（风格 + 方法 3 引用）

- [ ] **Step 1: 创建文件，章节结构：**
  - `## 九科检查表`——双卷各科一小节：查什么（具体检查项清单）· 怎么查（工具调用：lint 输出解析 / Glob+Grep pattern / git log 命令 / 读 pytest 输出——每项给可执行命令或 grep 正则）· 判定标准（✅⚠️❌ 的量化阈值，如 ⑦缺陷科「TODO 年龄>90 天→⚠️」、⑨「单文件>1000 行→⚠️ · >1500→❌」）。②关联科写「verdict 流程引用 association-method.md 方法 3」不重复
  - `## 双模式`——快检/深检的科室矩阵 + 抽检规则（>30 锚抽 20%·最少 10 条）+ 置信度门（快检：只报「有具体证据定位」的异常；深检：嫌疑也报 + 标置信 高/中/低）
  - `## 三条铁律`——Iron Law（处方必须根因+anchor，否则开检查单）· Zero-noise（台账跳过 + 高置信门）· 诊断治疗分离
  - `## 三段式报告模板`——spec §3 报告终稿格式的逐字模板（含五桶行动规划段 + 复查节奏三型）
  - `## HEALTH.md 写入规范`——frontmatter 字段逐个说明（与 Task 2 将进 schema.md 的规范一致 · 此处写「字段 schema 见 references/schema.md · health-report 节」+ 写入时的注意：处方 id 形如 RX-NNN 稳定递增、module 字段必须是真实存在的 module id、anchors 写入前必须按方法 3 预演过）
  - `## 五桶分诊判据`——每桶的判定规则 + 落地动作（spec §3 表展开）
  - `## 台账机制`——accepted_debts 的写入/跳过/复审规则
- [ ] **Step 2: 自检**——把九科各想象成一条指令执行：每科的「怎么查」是否给到可直接执行的命令/正则/读取目标？阈值是否可判定？
- [ ] **Step 3: Commit** — `feat(v1.1): add references/health-check.md (9-department checkup methodology)`

---

## Task 2: health-report doc kind（schema 规范 + validator · TDD）

**Files:**
- Modify: `references/schema.md`（新 H2 `## health-report schema` + TOC +1）
- Modify: `docs_cockpit/schema.py`（新函数 `validate_health_report(meta) -> list[Issue]`）
- Test: `tests/unit/test_schema.py`（新增 TestValidateHealthReport）

- [ ] **Step 1: schema.md 新节**——spec §4 的 frontmatter 字段表：必填 `type: health-report` / `date`（ISO）/ `mode`（quick|deep）/ `grade`（A|B|C|D 可带 +/-）/ `departments[]`（每项 id/name/verdict∈{pass,warn,fail}/summary）；可选 `prescriptions[]`（id/severity∈{high,medium,low}/bucket∈{now,sprint,backlog,watch,accepted}/title/root_cause/anchors[]/fix/module）/ `accepted_debts[]`（item/reason/review）/ `next_checkup`。TOC 同步。
- [ ] **Step 2: 先写失败测试**——TestValidateHealthReport：合法 frontmatter → 0 issue；缺 grade → error；mode 非法值 → error；prescription 缺 root_cause → warn（Iron Law 的死规则面）；bucket 非法 → warn；module 字段引用不存在的 module id → warn（需传入已知 module ids 集合）。跑确认 FAIL（函数不存在）。
- [ ] **Step 3: 实现 `validate_health_report`**——风格对齐 `validate_sprint_plan`（schema.py:438 附近）：Issue 带 `category="health-report"`、`reference="references/schema.md · health-report schema"`。
- [ ] **Step 4: pytest 全绿（253+新增） + Commit** — `feat(v1.1): health-report doc kind schema + validator`

---

## Task 3: render 解析 HEALTH.md → state.json::health（TDD）

**Files:**
- Modify: `docs_cockpit/build.py`（`build_payload` 内固定路径探测 `docs/HEALTH.md`）
- Test: `tests/unit/test_schema.py` 或新 `tests/integration/test_health_render.py`

- [ ] **Step 1: 先写失败测试**——fixture 项目放一份合法 HEALTH.md → `build_payload` 返回的 payload 含 `health` 顶层 key（grade/mode/date/departments/prescriptions/accepted_debts/next_checkup/body 原文透传）；HEALTH.md 不存在 → payload 无 `health` key（或 null——选 null，模板判空简单）；HEALTH.md frontmatter 非法 → issues[] 含 health-report 类 issue 且 health 仍尽力解析（degraded 不阻断渲染——体检报告坏了不能拖垮整个看板）。
- [ ] **Step 2: 实现**——`build_payload` 末段：`health_path = repo_root / "docs" / "HEALTH.md"`，存在则 `read_md + split_frontmatter + validate_health_report`（module ids 集合传入做 module 引用校验），结果进 payload["health"]，issues 并入主 issues 流。**state.json additive-only 兼容**：新增顶层 key 合规。
- [ ] **Step 3: pytest 全绿 + 本仓 render 烟测（无 HEALTH.md 时行为不变） + Commit** — `feat(v1.1): parse docs/HEALTH.md into state.json health key`

---

## Task 4: 看板健康面板（徽章 + 三段式面板 + 处方卡）

**Files:**
- Modify: `docs_cockpit/templates/index.html.tmpl`（~4700 行 · CSS + JS + i18n）
- Test: `tests/integration/test_dashboard_render.py`（新增断言）

- [ ] **Step 1: 健康徽章**——topbar/KPI 区（与现有 KPI strip 同排）：`health.grade` 显示为色块徽章（A=绿 B=蓝 C=橙 D=红 · 用 design_tokens 现有色板），副文本 `mode + date`。`health` 为 null 时整组 DOM 不渲染（向后兼容——老项目无 HEALTH.md 看板零变化）。
- [ ] **Step 2: 健康面板**——点徽章开 drawer（复用现有 drawer 机制）：(a) 九科行——name + verdict 三色点 + summary；(b) 处方卡列表——severity 色条 + bucket 标签 tab 过滤（全部/立即修/本sprint/backlog/观察/已接受）+ title + root_cause + anchors（复用现有 code-anchor 链样式）+ module 反链（点击关 drawer 开对应 module 卡）；(c) 行动规划区——`next_checkup` + accepted_debts 折叠表。body 原文经 marked 渲染在「完整报告」折叠区。
- [ ] **Step 3: i18n**——新 key 全部 EN/中成对（`health.badge_title` / `health.dept_*` / `health.bucket_*` / `health.copy_rx` / `health.copy_bucket` 等），跟现有 i18n 结构。
- [ ] **Step 4: 测试 + 验证**——test_dashboard_render 新增：fixture 含 HEALTH.md → 产物含徽章 DOM + 处方卡 + 无 JS 引用悬空；fixture 无 HEALTH.md → 产物不含健康 DOM。`render` 本仓烟测 + 产物人工抽查（Read 产物徽章区段）。
- [ ] **Step 5: Commit** — `feat(v1.1): dashboard health badge + 3-section health panel`

---

## Task 5: Copy-prompt CTA（处方单条 + 桶级批量 · 前端拼）

**Files:**
- Modify: `docs_cockpit/templates/index.html.tmpl`（Task 4 的处方卡上加按钮 + 拼接函数）

- [ ] **Step 1: 单条处方 Copy**——每张处方卡 Copy 按钮，剪贴板内容（前端拼 · `copyBundlePrompt` 同款机制）：

```
请解决以下 docs-cockpit 体检处方（{date} · {mode}检）：
【{severity}】{title}
根因：{root_cause}
位置：{anchors 逐行}
建议修法：{fix}
所属模块：{module}（如有）
完成后跑 `docs-cockpit render` 验证，并更新 docs/HEALTH.md 中该处方状态。
```

- [ ] **Step 2: 桶级批量 Copy**——bucket tab 上「复制本桶全部」按钮：头部一句「请按顺序解决以下 N 条体检处方（按伤害排序）：」+ 各条同上格式拼接 + 同款收尾指令。
- [ ] **Step 3: i18n EN/中成对** + toast（`health.rx_copied`）。
- [ ] **Step 4: 验证**——render 后产物 grep 拼接函数无残留旧引用；浏览器思维走查拼出的 prompt 文本（含换行转义正确——参考 bundle CTA 的 `\n` 处理）；pytest 绿。
- [ ] **Step 5: Commit** — `feat(v1.1): one-click prescription prompt copy (single + bucket)`

---

## Task 6: skill 升格（build / rebuild / router）

**Files:**
- Modify: `skills/docs-cockpit-build/SKILL.md`（frontmatter description + Phase 1-3/5 升格）
- Modify: `skills/docs-cockpit-rebuild/SKILL.md`（frontmatter description + Phase 1-2 升格）
- Modify: `skills/use-docs-cockpit/SKILL.md`（路由表 +1 行 · 仍 <60 行）

- [ ] **Step 1: build 升格**——Phase 1-3 的检查产出按 `references/health-check.md` 汇总为「入院体检」：新增 Phase 4.5 说明（不改 phase 编号——在 Phase 5 开头加「呈体检报告：先写 docs/HEALTH.md（frontmatter 按 references/schema.md health-report 节）→ 呈三段式报告 → 五桶逐桶对话确认 → 已确认的进 Phase 5 既有决策流」）。**五桶落地规则写明（处方→subtask 闭环 · 决策 #3）**：「本 sprint」桶 → Phase 6 写成带 `@code:` anchor 的 subtask 挂入处方 `module` 字段对应的 module（无归属则与用户确认建「健康债」module）；「backlog」桶 → 起草 plan 文档（命名按 schema.md 文件命名约定）；「接受」桶 → 写入 HEALTH.md `accepted_debts`。description 追加触发短语：「体检」「健康检查」摸排类（但 build 只在 0→1 场景接体检——已有体系的体检归 rebuild，Do-NOT 加分流）。
- [ ] **Step 2: rebuild 升格**——Phase 1-2 标准化为「复查」报告（同款 HEALTH.md 写入 + 三段式 + 五桶）；**新增触发场景**：「体检一下/全面体检/health check」→ Phase 1-2 出报告即止（与「纯状态查询止于 Phase 1」同款终点语义——深检关键词触发深检模式）。description TRIGGER 追加「体检」「健康检查」"health check" "checkup"。
- [ ] **Step 3: router +1 行**——「项目体检/健康检查 → docs-cockpit-rebuild（已有体系）· 触发例「体检一下」"run a health check"」。行数仍 <60。
- [ ] **Step 4: 触发自检**——「体检一下」唯一落 rebuild；「把项目搭起来顺便体检」落 build；与既有六类查询零冲突。grep 三 skill 引用 `references/health-check.md` 路径可达。
- [ ] **Step 5: Commit** — `feat(v1.1): upgrade build/rebuild to full checkup flow + router entry`（description 变更 = minor 的核心依据）

---

## Task 7: `build` alias 移除（1.1 既有承诺 · breaking）

**Files:**
- Modify: `docs_cockpit/cli.py`（删 build parser + `_cmd_build_deprecated` wrapper）
- Modify: 全部「deprecated alias 注」：`CLAUDE.md` · `README.md`+`README.zh-CN.md`（badge 区 cheat-sheet + pivot 对照表行改措辞「1.1 已移除」）· `skills/docs-cockpit-build/SKILL.md` P7 注 · `skills/docs-cockpit-rebuild/SKILL.md` P5 注 · `commands/render.md` 注
- Test: `tests/integration/test_dashboard_render.py:31` 等 fixture 若走 `build` alias → 改 `render`

- [ ] **Step 1: 删 cli.py alias**——`main(['build'])` 之后应报 invalid choice。先 grep tests/ 里 `"build"` 调用改 `"render"`。
- [ ] **Step 2: 文档注清理**——上列各处 alias 注改为「`build` alias removed in 1.1（renamed in 1.0）」或直接删注（按上下文）。CHANGELOG 历史不动。
- [ ] **Step 3: 验证**——pytest 全绿；`main(['build'])` invalid choice；grep 全仓 `deprecated alias`（除 CHANGELOG/docs/plans）0 残留。**提醒用户**：下游 Sourcery/bastion 的 pre-commit 若仍用 `docs-cockpit build` 将在升级后断——报告里必须显著标注。
- [ ] **Step 4: Commit** — `feat(v1.1)!: remove deprecated build alias (scheduled removal)`

---

## Task 8: Dogfood 自体检（产出本仓第一份 HEALTH.md）

**Files:**
- Create: `docs/HEALTH.md`（真实深检产物 · 不是 fixture）

- [ ] **Step 1: 对本仓执行一次真实深检**——严格按 `references/health-check.md` 九科走（这同时是 reference 可执行性的实战验证）：①lint ②anchor 全量 verdict ③git log 近期 vs anchor ④缺口 ⑤一致性 ⑥pytest/coverage ⑦TODO 年龄+裸 except ⑧硬编码/调试残留 ⑨God file（schema.py ~1490 行是已知病例——应进台账：理由「post-1.0 已排期拆 md_merge.py」）。
- [ ] **Step 2: 写 docs/HEALTH.md**——frontmatter 过 `validate_health_report` 0 error；body 三段式按模板。
- [ ] **Step 3: render + 看板验证**——徽章/面板/处方卡/Copy 按钮在产物中齐备（Read 产物抽查 + grep）；`state.json::health` 字段齐。**HEALTH.md 与渲染产物的 git 处理**：HEALTH.md 入库（它是文档不是产物）；docs/index.html 等照旧 ignored。
- [ ] **Step 4: 报告可执行性回评**——作为第一个照 health-check.md 跑全科的 agent，记录哪科指引模糊（同 Stage A dogfood 模式），轻微问题直接回修 reference。
- [ ] **Step 5: Commit** — `docs(v1.1): first real self-checkup HEALTH.md (dogfood)`

---

## Task 9: CHANGELOG 1.1.0 + 版本四件套 + 发布回归

**Files:**
- Modify: `CHANGELOG.md`（1.1.0 entry：Why（体检需求原话）/ Added（九科/HEALTH.md doc kind/健康面板/Copy-prompt/台账）/ **Breaking（build alias 移除 + 迁移指引）**）
- Modify: `docs_cockpit/__init__.py` + `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` → 1.1.0
- 回归：pytest 全绿 · lint 0/0 · 本仓+Sourcery+bastion `render` 烟测 · hooks 三路 smoke · 触发路由抽查（体检/建关联/查状态/纯渲染） · grep 终扫
- plan status：本 plan + spec 标 done

- [ ] **Step 1-3: entry + bump + 回归 + Commit** — `release(v1.1.0): full project checkup · HEALTH.md doc kind · dashboard health panel · build alias removed`

---

## DoD

- [ ] 九科 reference 可执行（dogfood 实战验证过）· HEALTH.md schema/validator/render/面板/CTA 全链路通
- [ ] 本仓有真实 HEALTH.md 且看板可见健康面板 · Copy prompt 拼出可直接执行的文本
- [ ] `docs-cockpit build` invalid choice（alias 移除）· 下游迁移提醒已显著标注
- [ ] pytest 全绿（253 + 新增）· lint 0/0 · 版本四件套 1.1.0
- [ ] merge 决策呈用户
