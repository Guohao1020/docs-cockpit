---
id: P-SKILL-FIRST-PIVOT
type: plan
title: "Skill-first pivot · 4 skill → build/rebuild 二元 + 机械渲染核"
status: draft
sprint: "1.0"
desc: "把 docs-cockpit 从「双产物（CLI + plugin）」重定义为「纯 skill 产物 + 极薄机械渲染核」，认知全交 skill，python 只留确定性渲染"
owner: harvey
prd_ref: "本次 brainstorming 对话"
---

# Skill-first pivot · 设计 spec

> 本文是 brainstorming 产出的设计文档（design spec），描述「为什么」与「做什么」，不含实现步骤。
> 实现步骤由 writing-plans 在本 spec 获批后产出。

## §0 · 北极星与动机

### 痛点（用户原话）

> 「模块总是很难关联好任务，任务也无法很好地关联上 spec / plan / rfc 等文档，也没高亮相关片段。需要在 skill 中加入：如何**关联**这些文档、如何**检索**、如何**预演**、如何**推理**。」

### 根因诊断

现有 `docs-cockpit-author`（1225 行）已经覆盖了 schema、anchor 格式、§11 authoring flow、§16.6 verify，但**全部假设「你已经知道该关联哪个文档的哪一段」**（§11 step 1 原话 "read the relevant plan section"）。项目里**没有任何检索/排序/推理的能力**（grep 确认无 `search` / `discover` / `_rank` / `highlight` 函数，commands 目录只有 browse/build/lint/migrate/status/update/weekly）。当没有人明确指路时，agent 无从下手——这正是「关联做得差」的根因。

缺的是**上游认知环节**：面对一个 module / subtask，如何系统地**检索**候选文档、**推理**哪一段相关、落地前**预演**验证指对了、再**高亮**出「为什么相关」。

### 北极星

docs-cockpit 从「**Python CLI + Claude plugin 双产物**」重定义为「**纯 skill 产物 + 极薄机械渲染核**」：

- **认知/方法论 → 全部 skill 化**：检索、推理、预演、关联、高亮、补文档、对话决策、跨文档一致性——这些是 LLM 的活。
- **机械层 → python 保留**：MD 解析、frontmatter 校验、HTML/state.json 渲染——确定性、零认知、可 CI 复用。

此方向是项目自己 north-star 的贯彻而非背离。`author §11` 原文：

> docs-cockpit is the AI's co-pilot · not a precision engine. **Semantic precision comes from LLM · python only handles parsing-layer**（anchor syntax / line numbers / heading slugs）。

`§16.1`：「docs-cockpit 本质上是 skill · python 代码只是辅助」。

**结论**：该删的不是 python，而是所有「承载认知/方法论的 CLI 子命令」；该留的是「纯机械渲染核」。

## §1 · 最终 skill 拓扑（4 → 2）

| 现有 skill | 行数 | 去向 |
|---|---|---|
| `docs-cockpit`（setup/config/build/upgrade） | 413 | setup/config → 并入 `build` 的 Phase 0；bootstrap/upgrade 运维知识 → `references/operations.md`；**skill 间路由 / scope discriminator → `use-docs-cockpit`** |
| `docs-cockpit-author`（schema SSOT + 方法论） | 1225 | schema 规范（§1–§4 字段/命名/anchor 格式）→ `references/schema.md`；方法论（§11/§12/§16.6）→ 拆进 `build` / `rebuild` |
| `docs-cockpit-standup`（读 state.json 出叙事） | 252 | 并入 `rebuild` 的 Phase 1「读现状/诊断」 |
| `docs-cockpit-portfolio`（多项目周报） | 227 | **删除**（连同 `commands/weekly.md`） |

最终是**一个入口元 skill + 两个流程 skill**：

- **`use-docs-cockpit`**（入口/引导/路由元 skill，**默认加载** · 类比 superpowers 的 `using-superpowers`）— 让 agent 一进 session 就知道 docs-cockpit 体系存在并遵循它，路由 build vs rebuild vs `render` CLI。**它是入口不是流程**，故不违背「只留两个流程 skill」。详见 §5.5。
- **`docs-cockpit-build`** — 构建关联体系（0→1 / 全量）。默认覆盖**整个项目**所有 module 的 spec/plan，逐个跟用户对话定夺。
- **`docs-cockpit-rebuild`** — 刷新重建（已有体系，诊断漂移 + 只动失效的关联）。

build / rebuild 共享 `references/`（**reference 不是 skill**，是被引用的规范/方法）：

- `references/schema.md` — frontmatter / anchor 字段规范（不可压缩，约 600 行，从 author §1–§4 降级而来）
- `references/association-method.md` — 检索 / 推理 / 预演 / 高亮 4 原子方法（build/rebuild 共享）
- `references/operations.md` — bootstrap / upgrade / config 运维（从 docs-cockpit 主 skill 降级）

> 设计依据：schema 是「规范」不是「流程」，不该占一个 skill。skill 描述流程，reference 承载规范——这也让 build/rebuild 两个 skill 体积可控（避免重蹈 author 1225 行的覆辙）。

## §2 · CLI 瘦身清单

### 保留（机械层 · 确定性 · 零认知）

| 子命令 | 角色 | 备注 |
|---|---|---|
| `render`（原 `build` 改名） | MD → index.html / state.json 渲染 | `build` 留 deprecated alias 一个 minor 周期，平滑过渡下游 pre-commit |
| `init` | scaffold `docs-cockpit.yaml` | 机械 |
| `browse` | 生成 tree-sidebar 阅读器 HTML | 机械渲染 |
| `lint` | frontmatter / title / anchor 死规则校验 | 规则 ≠ 认知；`§16.7` 已定 lint = render 校验子集 |
| `upgrade` | 自升级（plugin cache + 原子重启） | 运维机械，CLI 还在所以仍需要 |
| `migrate` | 旧 state.json schema 迁移 | 一次性运维机械 |

### 删除（认知层 → 全部变 skill 内的方法）

| 子命令 | 现职责 | 迁往 |
|---|---|---|
| `portfolio`（+ `portfolio.py` 310 行） | 多项目周报 | 删除（用户：不要周报） |
| `suggest` | 软建议（desc/subtask/anchor/一致性） | build/rebuild 内置为方法 |
| `verify` | LLM 二次确认 anchor（4 档 verdict） | rebuild 的「预演/诊断」phase |
| `refine` | anchor 精度升级 | build/rebuild 的「预演」方法 |
| `prompt` / bundle | 渲染 prompt 给 agent | agent 自己就能生成，删 |
| `sprint`（init/check · DoR/DoD） | 敏捷 sprint 规划校验 | build 的「整项目规划」+ lint 死规则保留校验部分 |
| `migrate-subtasks` | v0.10→v0.11 升级 | agent 用 Edit 直接做 |

### 已定删除（原边界模糊项 · review 已定 · 见 §10）

| 项 | 倾向 | 理由 |
|---|---|---|
| MCP server（`cockpit_build` / `cockpit_apply_patch` / `cockpit://state` 等，0.18 新增） | **删除** | 纯 skill 化后 agent 用 Read/Edit/Bash + `render` CLI 即可；MCP 是另一种 agent 接口，与「一切皆 skill」冗余 |
| `sprint` 的 DoR/DoD 死规则校验部分 | 并入 `lint` | DoR/DoD 的「检查」是死规则（trace 到 prd_ref / 有 anchor），保留为 lint category；「规划」是认知，进 build |

## §3 · 命名方案（✅ 已定 · review 通过 · 见 §10）

冲突：CLI 渲染核保留后，skill 名 `docs-cockpit-build` 会跟 CLI `build` + slash `/docs-cockpit:build` 概念撞车（两个完全不同的 build：CLI=渲染，skill=构建关联）。`CLAUDE.md` 已踩过此坑（0.9.0 因 `status` 撞 slash 把 skill 改名 standup）。

**方案**：把 `build` 一词让给 skill（用户心智词），CLI 渲染核改名 `render`。

| 概念 | 名字 | slash |
|---|---|---|
| 机械渲染（MD→HTML） | CLI `docs-cockpit render`（`build` = deprecated alias） | `/docs-cockpit:render` |
| 认知构建关联体系 | skill `docs-cockpit-build` | `/docs-cockpit:build` |
| 认知刷新重建 | skill `docs-cockpit-rebuild` | `/docs-cockpit:rebuild` |

> 替代方案（未采纳）：skill 用 `docs-cockpit-relate` 语义命名不动 CLI。劣势：偏离用户 build/rebuild 心智。

## §4 · `docs-cockpit-build` skill 设计

**它做什么**：从项目现状出发，构建整个项目的「module ↔ subtask ↔ spec/plan/rfc」关联体系，补齐缺失文档，逐个跟用户对话定夺。
**怎么用**：用户说「把项目文档体系建起来」「关联模块和文档」「规划整个项目的 spec/plan」「给所有 module 补 anchor」。
**依赖**：`references/schema.md`（字段规范）、`references/association-method.md`（4 原子方法）、`references/operations.md`（首次需建 cockpit 时）、CLI `render`（最后渲染）。

### 7 个 phase（默认覆盖整个项目，不是单 module）

| Phase | 名称 | 动作 | 复用原子方法 |
|---|---|---|---|
| 0 | 确保 cockpit 存在 | 检查 `docs-cockpit.yaml`，无则 `init` + bootstrap CLI | （operations.md） |
| 1 | **检索** discovery | 扫全项目 `docs/spec/module`·`concept`·`plans`·`RFC`·`spec`，建「文档全景图」：有哪些 module / spec / plan / rfc、谁关联谁、谁是孤儿 | 检索 |
| 2 | **推理** reasoning | 对每个 module/subtask 推断它**应该**关联哪个文档的哪一段；列出缺口（无 spec 的 module、无 plan 的 sprint、0 anchor 的 subtask） | 推理 |
| 3 | **预演** dry-run | 落地前 Read 每个候选 anchor 的真实片段（目标行/章节），验证它确实支撑——**不瞎猜行号** | 预演 |
| 4 | **高亮** highlight | 对每个关联，文字标出片段里「哪几行/哪句话为什么相关」（引用关键句 + 关联理由） | 高亮 |
| 5 | **对话决策** | 逐个（或批量提议）跟用户确认每个 spec/plan 关联——用户拍板 accept/调整/skip | — |
| 6 | **落地 + 补文档** | 写 anchor 到 MD；为缺失的 spec/plan 起草新文档（吸收 author 写作能力 + schema.md） | — |
| 7 | **渲染** | 调 `docs-cockpit render` 生成 dashboard，验证 0 warning | — |

## §5 · `docs-cockpit-rebuild` skill 设计

**它做什么**：已有关联体系但漂移了（重构后 anchor 失效 / spec 演进 / 关联过时 / 状态不准），诊断 + 只刷新失效的关联。
**怎么用**：用户说「关联乱了重新梳理」「重构后 anchor 都失效了」「spec 改了同步关联」「这个 module 的关联还准不准」。
**依赖**：`references/association-method.md`、`references/schema.md`、`docs/state.json`（读现状）、CLI `render` / `lint`。

### 5 个 phase

| Phase | 名称 | 动作 | 来源 |
|---|---|---|---|
| 1 | **读现状** | 读 `state.json` + MD，叙述当前关联体系状态 | 吸收 standup |
| 2 | **诊断漂移** | 跑 `lint`（死规则）+ 用「预演」方法重新验证所有 anchor（4 档 verdict：accurate/partial/wrong/missing） | 吸收 verify |
| 3 | **重新推理** | 对漂移的关联，重新「检索 + 推理」正确 anchor | 检索+推理 |
| 4 | **刷新落地** | 改 anchor，**保留仍有效的，只动漂移的**（最小 diff） | — |
| 5 | **渲染验证** | `render` + 复查 | — |

**build vs rebuild 的差别**：共享 4 原子方法；build 是全量从无到有 + 对话决策每个；rebuild 是增量诊断 + 只动漂移的、保留有效的。

## §5.5 · `use-docs-cockpit` 入口元 skill + 默认加载机制

**它做什么**：作为 docs-cockpit skill 生态的入口/引导/路由器（类比 superpowers 的 `using-superpowers`）。让 agent（Claude / Codex / Cursor）一进 session 就知道：本项目装了 docs-cockpit、它的 north-star 是「一切皆 skill」、何时走哪个 skill。
**怎么用**：不靠用户主动触发——**默认加载**（见下）。
**依赖**：检测项 `docs-cockpit.yaml`；指向 `docs-cockpit-build` / `docs-cockpit-rebuild` / `render` CLI。

### §5.5.1 · skill 内容（薄 · 只做路由）

入口 skill 要**薄**（每 session 注入吃 token），只装路由表，不重复 build/rebuild 的细节：

| agent 想做 | 走 | 触发短语 |
|---|---|---|
| 建/补关联体系、规划整个项目 spec/plan、给 module 补 anchor | `docs-cockpit-build` | 「把文档体系建起来」「关联模块和文档」「规划 spec」 |
| 关联漂移了、重构后 anchor 失效、spec 改了同步 | `docs-cockpit-rebuild` | 「关联乱了重新梳理」「anchor 失效了」 |
| 只想刷新 dashboard HTML | CLI `docs-cockpit render` | 「重新生成 dashboard」 |
| 查状态/进度（无文件改动） | `docs-cockpit-rebuild` 的 Phase 1「读现状」 | 「项目进度怎么样」「哪些卡了」 |

外加一段「north-star」提醒：认知交 skill、python 只做渲染、anchor 精度优先（错 anchor 比缺 anchor 伤害大）。

### §5.5.2 · 默认加载机制（按平台分）

**Claude Code（hook 注入 · 主路径）**

新增 `hooks/hooks.json`（plugin 自动发现，参考 superpowers）：

```jsonc
{ "hooks": { "SessionStart": [{ "matcher": "startup|clear|compact",
  "hooks": [{ "type": "command",
    "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" session-start",
    "async": false }] }] } }
```

- `hooks/run-hook.cmd` — 跨平台 polyglot wrapper（照搬 superpowers：Windows cmd 找 Git-bash 跑、Unix 直接 bash、无 bash 静默 exit 0）。
- `hooks/session-start` — 扩展名-less bash 脚本。**与 superpowers 的关键差异 = 条件注入**：
  1. 检测 cwd（向上找）是否有 `docs-cockpit.yaml`。**没有 → 静默 exit 0，绝不注入**（docs-cockpit 是项目特定的，不污染无关项目）。
  2. 有 → 输出 `use-docs-cockpit` 引导内容到 stdout → Claude Code 注入为 SessionStart additionalContext。

**Codex / Cursor / 其它 agent（AGENTS.md 锚 · 退化路径）**

Codex 不读 Claude Code 的 hooks。机制：

- `docs-cockpit-build` 的 Phase 0（建/确认 cockpit 时）**自动往项目根 `AGENTS.md` 写入一段引导锚点**（幂等 · 已存在则跳过），指向 `use-docs-cockpit`。Codex 约定读 `AGENTS.md`，由此默认加载。
- superpowers 已有 `hooks/hooks-cursor.json` 先例做 Cursor 适配，可照搬。

### §5.5.3 · 拓扑澄清

「只留 build/rebuild 两个流程」不变 —— `use-docs-cockpit` 是**入口元 skill**（路由器），与流程 skill 性质不同，正如 `using-superpowers` 之于 superpowers 技能库。最终 `skills/` 下：`use-docs-cockpit` + `docs-cockpit-build` + `docs-cockpit-rebuild`，外加 `references/`。

## §6 · 4 原子方法（`references/association-method.md`）

build/rebuild 都引用这一份。每个方法给「何时用 + 怎么做 + 反模式」。

1. **检索 discovery** — 用 Glob/Grep 建文档全景 + 候选池。怎么从 module 关键词、sprint、prd_ref 反查候选文档；怎么识别孤儿文档和无文档支撑的 subtask。
2. **推理 reasoning** — 从 subtask 语义匹配到 doc section。建立「证据链」：subtask 讲 X → plan §N 也讲 X → 故关联。强调 actually read（不是 grep 关键词碰运气）。
3. **预演 dry-run** — Read 候选片段，对照 subtask title 验证 4 档 verdict（吸收 §16.6）。错 anchor 比缺 anchor 伤害大——找不到对应 section 必须给 ❌ + TODO，不准瞎猜行号。
4. **高亮 highlight**（skill-only 实现）— agent 在产出/对话里用文字标出「片段第 X–Y 行 / 这句话」为什么支撑这条 subtask。**不是改 template 的渲染高亮**，是推理层的证据呈现，落到 anchor 的精确行范围 + 给用户的关联理由说明。

## §7 · 三阶段实施路线（一份 spec · 内部分阶段 plan）

用户要求「全部三阶段一次做完」——即一份 master spec 覆盖全部；实现时 plan 内部分阶段执行：

- **Stage A · 新建 skill + references + 入口加载（核心方法论 + 默认加载）**
  写 `use-docs-cockpit`（入口元 skill）+ `docs-cockpit-build` + `docs-cockpit-rebuild` 三个 skill + 3 个 references；新增 `hooks/`（`hooks.json` + 跨平台 `run-hook.cmd` + 条件注入的 `session-start`）。流程 skill **新旧并存、零破坏**；hooks 是**新增**默认加载能力（条件注入 · 仅在有 `docs-cockpit.yaml` 的项目生效）。先让方法论 + 入口可 dogfood。
- **Stage B · CLI 瘦身 + skill 归并**
  CLI：删认知子命令、`build`→`render`（保 alias）、删 `portfolio.py`、MCP（待定）。skill：删 portfolio、standup 并入 rebuild、author schema 降 reference、docs-cockpit 主 skill 降 operations.md。更新所有触发 description + 交叉引用。
- **Stage C · 收尾**
  `CLAUDE.md` 重写（「four skills」→「two skills + references」、build pipeline 段更新为 render）、`README` / `README.zh-CN` 双语同步、`commands/` 清理（删 weekly.md、build→render）、`CHANGELOG`、版本号 bump。

## §8 · 版本号与 breaking 影响（✅ 已定 · review 通过 · 见 §10）

删公开 skill（portfolio）+ 删 CLI 子命令 + `build`→`render` 改名 = 对下游（`Sourcery` / `bastion` 的 pre-commit / CI 调 `docs-cockpit build`）**breaking**。

项目 SemVer convention 里「major」原定义是 config schema break——本次不是 config schema break，但**是项目身份重定义**（双产物 → 纯 skill + 渲染核）。

**✅ 已定**：破例标 **`1.0.0`**（major）——这一刀重定义了项目是什么，值得 major。`build`→`render` deprecated alias + 迁移说明降低下游冲击。

## §9 · 风险与回滚

- **下游断裂** — `build`→`render` 改名：靠 deprecated alias（保留一个 minor 周期 + 调用时打 warning）兜底。Stage A 新旧并存确保任何时点都可回退。
- **author 1225 行内容迁移丢失** — schema 降 reference 时逐节核对；§11/§16.6 方法论拆进 build/rebuild 时保留原 worked example。迁移前 `git tag` 锚点。
- **触发路由回归** — 4 skill → 2 skill，description 重写后需验证「写文档」「查状态」「建关联」「刷新」四类输入正确路由。Stage B 后用真实 query 回归。
- **MCP 删除影响** — 若下游已接 MCP server，删除是 breaking；列入 §10 待确认，不在 Stage A 动。

## §10 · 决策记录（✅ 全部 review 通过 · 2026-06-10）

| # | 议题 | 决策 |
|---|---|---|
| 1 | 命名（§3） | CLI `build`→`render`（`build` 留 deprecated alias 一周期）；skill 用 `docs-cockpit-build` / `docs-cockpit-rebuild` |
| 2 | 版本号（§8） | 破例 **`1.0.0`**（major · 项目身份重定义） |
| 3 | MCP server（§2） | **删除**（随认知 CLI 一起；纯 skill 化后 agent 用 Read/Edit/Bash + `render` 即可，冗余） |
| 4 | spec 归属 | 保留在 `docs/plans/`（dogfood 进自身 dashboard） |
| 5 | Codex 默认加载（§5.5.2） | `build` Phase 0 幂等写项目 `AGENTS.md` 引导锚点 |
| 6 | SessionStart 注入开关 | 默认开（条件注入已克制）· 不额外做开关 |
