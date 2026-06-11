---
id: P-V1.1-HEALTH
type: plan
title: "v1.1 · 全方位体检：九科双模式 + 看板体现 + 一键处方 prompt"
status: done
sprint: "1.1"
desc: "build/rebuild 升格为项目体检：诊断/处方/行动规划三段式，HEALTH.md 新 doc kind 进看板，每条处方一键复制 prompt 丢给 Claude Code"
owner: harvey
prd_ref: "docs/plans/P-skill-first-pivot.md"
---

# v1.1 体检体系 · 设计 spec

> 状态：设计已经三轮对话迭代（v1 五科 → v2 双卷九科+借鉴 gstack/superpowers → v3 行动规划+台账），全部决策用户已确认（§9）。本文是定稿记录。

## §0 · 北极星与三条铁律

每次 build / rebuild = 一次全方位体检。延续 v1.0 north-star（认知交 skill · python 只做确定性渲染 · 错 anchor 比缺 anchor 伤害大），体检新增三条铁律：

1. **Iron Law（superpowers systematic-debugging）**：处方必须带根因 + anchor 定位。查不出根因的不开药，开「进一步检查单」。
2. **Zero-noise（gstack cso）**：快检只报高置信度异常；已接受债务不重复报。体检报告没人看 = 体检失败。
3. **诊断与治疗分离**：体检只产出报告，治疗走 build/rebuild 的对话决策 phase。

## §1 · 九科双卷

**文档卷**（docs-cockpit 本职）：
① 结构科（lint 全量：frontmatter / title 法则 / status×progress）· ② 关联科（anchor 覆盖率 + 4 档 verdict + 死锚）· ③ 新鲜科（git 近期变更 vs anchor 复核状态 · status×commit 活跃度矛盾）· ④ 覆盖科（无 spec 的 module / 无 plan 的 sprint / 孤儿文档 / 0-anchor subtask）· ⑤ 一致科（depends_on/blocks 配对 · subtask×module status · sprint 对齐）

**工程卷**（借鉴 gstack 思路 · 内置检查表为基线，检测到 gstack 时增强）：
⑥ 代码质量科（**包装项目既有工具**：test/type/lint/coverage/dead-code · 缺的标 N/A）· ⑦ 缺陷科（TODO/FIXME/HACK 带 git-blame 年龄 · skip/xfail · 裸 except 吞异常 · 注释掉的代码块）· ⑧ 生产就绪科（硬编码 secret/路径/魔数 · 调试残留 · mock/stub 进生产路径 · 缺错误处理/超时 · 轻量 secrets 扫描）· ⑨ 架构科（深检专属：循环依赖 · God file 行数阈值 · 职责漂移 · 分层违例）

## §2 · 双模式

| | 快检（build/rebuild 自动附带） | 深检（「全面体检/深度体检」明示触发） |
|---|---|---|
| 科室 | ①②④⑥机械 + ⑦⑧高置信 grep | 全九科（⑨深检专属） |
| anchor verdict | >30 锚抽检 | 全量 |
| 报告门槛 | 高置信才报 · 台账条目跳过 | 低置信也报（标置信度）· 台账条目列出但标「已接受」 |

## §3 · 三段式报告 + 五桶行动规划

报告 = **诊断**（总评 A/B/C/D + 九科 ✅⚠️❌）→ **处方**（按伤害排序：错 anchor/真 bug > 生产就绪 > 规范瑕疵）→ **行动规划**（五桶分诊 · 呈用户逐桶确认）：

| 桶 | 落地形式 |
|---|---|
| 立即修 | 当场治（Phase 5-6 对话决策 + Edit） |
| 本 sprint | 处方→subtask（带 @code anchor）挂 module · 同步 sprint-plan in_scope |
| backlog | 起草 plan 文档（docs/plans/P-*.md · 自动进看板） |
| 观察项 | 记复查跟踪清单 · 下次体检重点核 |
| 接受的债 | 入 HEALTH.md 台账 · 快检不再报 · 带复审日期 |

报告结尾自动给**复查节奏建议**（治疗型 / 周期型 / 触发型）。

## §4 · HEALTH.md = 新 doc kind（看板体现的数据底座）

`docs/HEALTH.md` 双重身份：frontmatter = 机器读（render 解析进看板），body = 人读三段式报告。frontmatter schema：

```yaml
---
type: health-report
date: 2026-06-10
mode: quick            # quick | deep
grade: B+              # A/B/C/D ± 修饰
departments:           # 九科结果
  - { id: anchors, name: "关联", verdict: warn, summary: "覆盖率 78% · 抽检 1❌", detail: "..." }
prescriptions:         # 处方（看板渲染 + Copy-prompt 数据源）
  - id: RX-001
    severity: high     # high | medium | low
    bucket: sprint     # now | sprint | backlog | watch | accepted
    title: "M07-S2 锚指向已重构函数"
    root_cause: "fsm.py 重构后原函数移位 88-130"
    anchors: ["sourcery/worker/fsm.py:42-89"]
    fix: "anchor 改指 fsm.py:88-130 · 改后 render 验证"
    module: M07        # 看板联动：处方卡链到 module 卡
accepted_debts:
  - { item: "schema.py God file", reason: "post-1.0 已排期拆分", review: "2026-08" }
next_checkup: "本 sprint 收尾快检 · 30 天深检"
---
（body：三段式人读报告 · 模板见 references/health-check.md）
```

- schema 规范进 `references/schema.md` 新节；`schema.py::validate_health_report` 校验（错 frontmatter = 看板渲染不了体检——必须有 validator）
- **写入者是 skill**（体检认知产物）；**解析者是 render**（机械）——职责分界与 module MD 完全同构

## §5 · 看板体现（用户确认的硬需求）

1. **健康徽章**：hero/KPI 区显示总评等级（grade → 颜色映射），点击展开健康面板
2. **健康面板**（抽屉或区块）：三段式完整呈现——九科三色行 → 处方卡列表（按桶过滤 tab）→ 行动桶 + 复查建议 + 台账折叠区
3. **处方卡**：severity 色条 + 桶标签 + 根因摘要 + anchor 链（复用 code anchor 预览）+ module 反链（点击跳对应 module 卡）
4. **一键复制 prompt**（用户确认的硬需求）：
   - 每条处方卡一个 Copy 按钮——**前端拼自然语言 prompt**（bundle CTA 同款机制 · C-Task 2 已有先例），内容 = 处方 title + 根因 + anchor + 建议修法 + 「完成后跑 docs-cockpit render 验证」收尾指令，丢给 Claude Code 即可直接执行
   - 行动桶级批量 Copy——整桶处方拼成一个 bundle prompt
   - i18n EN/中 成对（现有机制）

## §6 · 数据流闭环

```
skill 体检（build Phase 1-3 / rebuild Phase 1-2 升格）
  → 写/更新 docs/HEALTH.md（frontmatter + 三段式 body）
  → docs-cockpit render 解析 → state.json::health + 看板健康面板
  → 用户在看板点 Copy prompt → 丢给 Claude Code 治疗
  → 治疗完 rebuild 复查 → HEALTH.md 更新 → render → 循环
```

体检触发面：build（入院基线 · Phase 5 决策前呈报告）· rebuild（复查 · Phase 2 末呈报告）· 「体检一下/health check」（rebuild Phase 1-2 出报告即止）——router +1 行。

## §7 · 实施切分

- **P1（= 1.1.0 本体 · 本 spec 的实施范围）**：references/health-check.md + schema（spec 节 + validator + 测试）+ render 解析 + 看板健康面板 + Copy-prompt CTA + skill 升格 + router + 台账机制 + dogfood（给本仓自己跑出第一份 HEALTH.md）。**同车**：`build` alias 移除（1.1 的既有承诺 · 含全部文档注清理）。
- **P2**：gstack 检测增强（health/cso/qa-only 委托）· 死指标 python 自动统计（render 时算覆盖率等与 HEALTH.md 对照）
- **P3**：体检历史快照 + 趋势对比 + dashboard 趋势线

版本语义：新 doc kind + SKILL.md 变更 + 模板大改 = **1.1.0（minor）**，用户须 `docs-cockpit upgrade`。

## §8 · 与既有体系的关系

- lint 仍是死规则门禁（CI --strict 不变）；体检是诊断叙事层，引用 lint 输出作①结构科数据
- 体检不新增 CLI 子命令（north-star：认知交 skill）；render 只新增 HEALTH.md 解析（机械）
- references/health-check.md 与 association-method.md 平级——前者是「查什么」，后者是「怎么核 anchor」（②关联科引用方法 3）

## §9 · 决策记录（全部已确认 · 2026-06-10）

| # | 决策 | 结论 |
|---|---|---|
| 1 | 报告载体 | 对话输出 + HEALTH.md 持久化（摘要+台账+结构化数据）+ **看板渲染**（用户追加硬需求） |
| 2 | 工程卷路线 | 内置检查表基线 + gstack 检测增强（P2） |
| 3 | 处方→subtask 闭环 | P1 做 |
| 4 | 评分制 | A/B/C/D 等级 + 九科三色 |
| 5 | 安全深度 | 轻量并入⑧ · 完整审计 P2 委托 gstack cso |
| 6 | 死指标进 python | P2（P1 由 skill 写入 HEALTH.md · render 仅解析） |
| 7 | 趋势 | P3（HEALTH.md 摘要打底） |
| 8 | CI 门禁 | 不做 |
| 9 | **看板体现**（追加） | 健康徽章 + 三段式健康面板 + 处方卡 · HEALTH.md 新 doc kind 走既有渲染管线 |
| 10 | **一键 Copy prompt**（追加） | 每条处方 + 桶级批量 · 前端拼（bundle CTA 同款）· 丢给 Claude Code 直接执行 |
