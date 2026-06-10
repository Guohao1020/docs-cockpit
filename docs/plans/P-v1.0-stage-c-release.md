---
id: P-V1.0-STAGE-C
type: plan
title: "v1.0 Stage C · 文档重写 + 发布收尾（1.0.0）"
status: planned
sprint: "1.0"
desc: "skill-first pivot 最后一棒：commands/ 清理 + 模板死文案 + CLAUDE.md/README/site 重写 + CHANGELOG + 1.0.0 bump + 发布回归"
owner: harvey
prd_ref: "docs/plans/P-skill-first-pivot.md"
docs:
  - { title: "Stage B plan(已完成 · 末尾含残留清单)", path: "docs/plans/P-v1.0-stage-b-cli-slim.md" }
---

# v1.0 Stage C Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把所有面向人的叙事（commands/ · CLAUDE.md · README 双语 · site）与面向 dashboard 用户的文案（模板 toast/CTA）更新到 v1.0 skill-first 现实，写 CHANGELOG 1.0.0 entry，版本号 bump 四件套，全量发布回归后解除合并约束。

**Architecture:** 顺序「内容清理 → 大叙事重写 → 版本定格 → 回归合并」：Task 1-4 清死引用（commands/模板/module docs/杂项），Task 5-7 重写三大叙事面（内容清理完后写，避免重写时又引用死物），Task 8 CHANGELOG+bump（一切就绪后定格），Task 9 发布回归 + merge 决策。**输入 = Stage B plan 末尾「Stage C 输入 · 残留清单」**（行号级定位 · 本 plan 任务直接引用其行号）。每 task commit 后 pytest + lint 仍须绿。

**Tech Stack:** Markdown 重写 · 模板 JS/i18n 文案手术 · Keep-a-Changelog 格式 · 版本四件套（`docs_cockpit/__init__.py` / `.claude-plugin/plugin.json` / `.claude-plugin/marketplace.json` / `CHANGELOG.md`）。

**已锁边界**（执行者不要重议）：
- `schema.py` 拆分（md_merge.py）、sync-status 去留再议、模板深度重构 → **post-1.0**，不进本 Stage
- `references/sync_status_workflow.md` **保留**为独立文档（sync-status CLI 存活），只修 L46 措辞
- commands/ 决策：**删 2 改 5**（status.md/weekly.md 删——其 skill 已死且路由走 use-docs-cockpit；build.md→render.md；lint/update/migrate/browse 改写）
- dashboard「Copy bundle prompt」CTA 决策：**改为前端拼自然语言 prompt**（选中 subtask 的 id+title 列表 + 一句「请一起实现以下 subtask」），不再写已删 CLI 命令；若 JS 改动超过 ~30 行则降级为隐藏按钮（与 Refine 按钮同款 `display:none`），二选一由实现者按实际代码量定并报告

---

## Task 1: commands/ 清理（删 2 · 改 5）

**Files:**
- Delete: `commands/status.md`（调已删 standup skill）· `commands/weekly.md`（调已删 portfolio skill + CLI）
- Rename+rewrite: `commands/build.md` → `commands/render.md`
- Modify: `commands/lint.md` · `commands/update.md` · `commands/migrate.md` · `commands/browse.md`

- [ ] **Step 1: 删除** — `git rm commands/status.md commands/weekly.md`。状态查询的入口现在是 use-docs-cockpit 路由 → rebuild Phase 1（hook 注入自动生效），不需要 slash 替代。

- [ ] **Step 2: build.md → render.md** — `git mv` 后重写：description 改「Run docs-cockpit render — regenerates docs/index.html + docs/state.json」；正文「Explicit invocation of the docs-cockpit render pipeline」；步骤里命令全部 `docs-cockpit render`；加一行注「`docs-cockpit build` 仍可用（deprecated alias · 1.1 移除）」。

- [ ] **Step 3: lint.md 重写** — 现文全文引 `docs-cockpit-author`（已删）。改法：schema spec 指向 `references/schema.md`；「hand off 给 author skill」改为「fix 流程走 `docs-cockpit-build` skill 的 Phase 5-6（对话决策 + 落地）」；`📚 see:` 的解释段同步（validator 现在输出 schema.md 锚——B-Task 4 已 repoint）。

- [ ] **Step 4: update.md / migrate.md / browse.md 巡检修订** — update.md 提到的「main docs-cockpit skill 处理 upgrade 触发」已不实 → 改「use-docs-cockpit 路由表分流到 CLI `docs-cockpit upgrade`（详见 references/operations.md · upgrade）」；migrate.md 与 browse.md 逐行读一遍，修掉任何 build 命令名 / 死 skill 引用（如无则报告 clean）。

- [ ] **Step 5: 验证 + Commit**

```bash
grep -rn "docs-cockpit-author\|standup\|portfolio\|docs-cockpit build" commands/   # 0 命中（render.md 的 deprecated 注除外）
ls commands/    # browse / lint / migrate / render / update —— 5 个
git add -A && git commit -m "feat(v1.0-C): clean slash commands (delete 2, rename build->render, rewrite 3)"
```

---

## Task 2: 模板死文案手术（index.html.tmpl）

**Files:**
- Modify: `docs_cockpit/templates/index.html.tmpl`（残留清单行号：L281-284 · L2234/L2543/L4519 · L2238/L2547 · L4209/L4248）

- [ ] **Step 1: 死注释删** — L281-284「prompts-refine.js sidecar 保留 · MCP server 仍能消费」整段注释删（两者均已删）。

- [ ] **Step 2: toast 文案修** — `toast.prompt_missing` 三处（L2234/L2543/L4519）：「run `docs-cockpit build`」→「run `docs-cockpit render`」；`toast.refine_missing` 两处（L2238/L2547）：指向永不再产出的 prompts-refine.js → 整条 toast 串删除 + grep 模板确认无 JS 路径还会触发它（Refine 按钮已 `display:none`，其触发函数若仍引用该 toast key，把函数体一并清理为 no-op 或删除——以「删后 render 出的 dashboard 控制台无 JS error」为准）。

- [ ] **Step 3: bundle CTA 改造** — L4209/L4248 现向剪贴板写已删的 `docs-cockpit prompt --bundle <ids>` 命令。按已锁边界改为前端拼自然语言 prompt：

```js
// 改前（大意）：clipboard ← "docs-cockpit prompt --bundle M07-f75501,M11-S1 --copy"
// 改后：clipboard ← 多行文本：
// 请把以下 subtask 作为一个 bundle 一起实现（上下文见各自 anchor）：
// - M07-f75501 · <title>
// - M11-S1 · <title>
// （docs-cockpit-build skill Phase 5-6 流程 · 先预演每个 anchor 再动手）
```

选中项的 id/title 在多选状态里已有（原代码就是从那里拼 id 列表的）。若实测改动超 ~30 行 → 降级方案：按钮 `display:none` + 一行注释，并在报告里说明。

- [ ] **Step 4: 验证 + Commit**

```bash
grep -n "prompt --bundle\|prompts-refine\|docs-cockpit build" docs_cockpit/templates/index.html.tmpl   # 0 命中
py -3.13 -c "import sys; sys.path.insert(0, r'D:\harvey_work\docs-cockpit'); from docs_cockpit.cli import main; main(['render'])"   # 成功
# 用浏览器或 Read 抽查产物 docs/index.html 的 bundle 按钮区 JS 无语法错误（render 成功 + grep 产物无残留即可）
py -3.13 -m pytest tests/ -q 2>&1 | tail -1    # 253 passed（test_dashboard_render 的反向断言应仍过）
git checkout -- docs/ 2>/dev/null || true
git add docs_cockpit/templates/ && git commit -m "fix(v1.0-C): purge dead CLI references from dashboard template"
```

---

## Task 3: module docs 历史化（8 个 + 1 个 reference）

**Files:**
- Modify: `docs/spec/module/{M02-cli,M03-plugin,M05-portfolio,M07-mcp-server,M08-apply-patch,M10-llm-doc-optimizer,M16-multi-subtask-bundle-ux,M17-bundle-prompt-and-skill}.md`
- Modify: `references/sync_status_workflow.md`（仅 L46）

逐文件动作（残留清单的行号定位 · 历史锚做法沿用 B-Task 11 先例：`@docs:CHANGELOG.md#<version>` · 先验证 heading substring 唯一命中）：

- [ ] **Step 1: M05 / M17 模块整体历史化**（特性已删但曾 ship）— 保 `status: done`；frontmatter `docs:` 指向已删文件的链接换 `CHANGELOG.md#0.10.0`（M05）/ `#0.14.0`（M17）；subtask 的 `@code:`/`@docs:` 死锚同样换历史锚；desc 加「（v1.0 已移除 · 历史模块）」后缀。
- [ ] **Step 2: M02 desc 更新至 v1.0 CLI 面**（render/lint/init/migrate/browse/sync-status/upgrade）；L32/L43 portfolio 子命令树与关键文件行删或加删除线注；L49 `@code:docs_cockpit/portfolio.py` → CHANGELOG 历史锚。
- [ ] **Step 3: M03 skill 目录树更新**（L32-33 → use-docs-cockpit + build + rebuild 三件套）。
- [ ] **Step 4: M07 残余 stale 锚收尾**（L43 `@code:cli.py:200-215` 等指向已删代码的行号锚 → `CHANGELOG.md#0.12.0`）+ L22/L33 叙事补「已随 v1.0 删」注。
- [ ] **Step 5: M08 L64 / M10 全文 / M16 L57 措辞历史化**（「已删」注 + M10 §1 用法块指 `CHANGELOG.md#0.12.0`；M16 的 bundle CTA 描述与 Task 2 的新行为对齐）。
- [ ] **Step 6: sync_status_workflow.md L46** — migrate-subtasks 措辞改「（原 migrate-subtasks CLI · v1.0 已删 · 现用 Edit 直接重写）」。
- [ ] **Step 7: 验证 + Commit**

```bash
py -3.13 -c "... main(['lint'])"     # exit 0 · 0 warning（历史锚都真实存在）
py -3.13 -c "... main(['render'])"   # 成功
git checkout -- docs/index.html docs/state.json docs/prompts.js 2>/dev/null || true
git add docs/spec/ references/sync_status_workflow.md && git commit -m "docs(v1.0-C): historize module docs for removed features with CHANGELOG anchors"
```

---

## Task 4: 杂项 polish（5 处一行级）

**Files:**
- Modify: `docs_cockpit/build.py` L263（「standup / portfolio 可消费」→「给 rebuild skill / CI 读」）· L652（「给 docs-cockpit-standup skill 读」→ 同款现状措辞）
- Modify: `tests/unit/test_aliases.py` L10（docstring 引已删 skill → 改「给 rebuild skill 区分 alias 条目」）
- Modify: `tests/integration/test_dashboard_render.py` L8/L11（docstring 把 bundle-meta.js 写成正向覆盖 → 改「反向断言：防 ghost 引用」）
- Modify: `docs_cockpit/schema.py` 模块 docstring「无 fs 依赖」陈述（与搬入的 `load_sprint_plans` 矛盾——B-Task 3 质量审查 P2）→ 改「除 v1.0 搬入的 load_sprint_plans / md-merge 函数外无 fs 依赖」

- [ ] **Step 1: 5 处改完 → pytest 253 passed → Commit**

```bash
git add docs_cockpit/ tests/ && git commit -m "polish(v1.0-C): fix stale comments and docstrings referencing removed features"
```

---

## Task 5: CLAUDE.md 重写（170 行 → v1.0 现实）

**Files:**
- Modify: `CLAUDE.md`（整体重写 · 保留仍然成立的段落）

- [ ] **Step 1: 重写**。必改清单（残留清单 + Stage B 期间发现的陈旧信息）：
  - 「What this repo is」：双产物叙事 → **skill-first**（1 入口 + 2 流程 skill + 机械 render CLI + references/ + hooks 条件注入）；版本叙事改 1.0
  - Common commands：`build` → `render`（注 alias）；删 `portfolio list` 示例（L25）；**修正「no formal pytest suite」**——tests/ 真实存在（253 个），smoke 段改为「`py -3.13 -m pytest tests/ -q` + 下游 Sourcery/bastion render 烟测」
  - Release 四件套段保留（仍成立）；SemVer 段补 1.0 规则（`build` alias 1.1 移除）
  - Architecture：build pipeline 段改 render 叙事；**修正 `extract_subtasks_from_body` 位置（在 schema.py 非 build.py）**；dispatcher 段改 cli.py（main 在 cli.py · build:main 是 re-export）；**「The four skills」表整体替换**为 1+2 拓扑表（use-docs-cockpit 路由 · build 7-phase · rebuild 5-phase + references/ 三件 + hooks 注入机制）；标注 schema 的 SSOT = `references/schema.md`
  - Skill design conventions 段：skill-creator 引用保留 · 0.9.0 命名史加「（相关 skill v1.0 已删）」
  - portfolio registry 章节（L120/L126）删；where-to-look 表更新（删 portfolio 行 · author schema 行改指 references/schema.md · 加 hooks/ 行）
  - 「Easy-to-break things」逐条核：模板 token / state.json schema / docs: 三步回退 / ghost state 仍成立保留；author 配对维护条改「schema.md ↔ validate_meta 配对维护」；新增「hooks/* 必须 LF（.gitattributes 锁）」「SKILL.md frontmatter description 是机器路由——改动按 minor 处理」
  - 语言约定段保留（仍成立）
- [ ] **Step 2: 自检** — grep 新文 `portfolio|standup|author skill|docs-cockpit build`（除历史注）0 命中；行数 ±30% 内（不灌水）。
- [ ] **Step 3: Commit** — `docs(v1.0-C): rewrite CLAUDE.md for skill-first architecture`

---

## Task 6: README.md + README.zh-CN.md 双语重写

**Files:**
- Modify: `README.md` + `README.zh-CN.md`（各 287 行 · 结构镜像同步）

- [ ] **Step 1: EN 重写**。必改（残留清单行号）：L39-43/L102-103/L119/L131 四技能叙事 → 1 入口 + 2 流程（含 SessionStart 自动注入卖点——这是 v1.0 的新用户体验）；L86-93 CLI cheat-sheet → 7 个存活子命令（render 主 · build 注 deprecated）；L153-159 MCP 章节删（替以一段「v1.0 起 agent 接口即 skill——无需 MCP」）；L172-178 + L247 portfolio 章节/目录树删；L182/L193 state.json 消费者 → 「rebuild skill Phase 1 / CI / 外部工具」。安装段、dashboard 特性段、screenshots 等仍成立的保留。
- [ ] **Step 2: zh-CN 镜像同步**（结构一致 · 行号对齐不强求但 section 一一对应）。
- [ ] **Step 3: 自检** — 两文件 section 数一致；grep 死引用 0；`docs-cockpit render` 是主命令名。
- [ ] **Step 4: Commit** — `docs(v1.0-C): rewrite bilingual README for skill-first v1.0`

---

## Task 7: site/index.html 营销页（4 处）

**Files:**
- Modify: `site/index.html`（991 行 · 残留清单：L546/548 author 叙事 · L633-634 prompt 特性卡 · L764 v0.14 引语 portfolio · L852/857 hint 文案）

- [ ] **Step 1: 4 处文案更新** — author skill 叙事 → build skill + references/schema.md；「Subtask 一键复制 prompt」特性卡与现状对齐（prompts.js sidecar 仍在 · CLI prompt 已删——文案不再提 CLI）；v0.14 引语是历史时间线内容→加「（v1.0 已并入 skill）」注或措辞调整；hint 文案对齐。**不做整页重设计**（营销页改版是 post-1.0 的事——只消灭失实）。
- [ ] **Step 2: 自检** — grep site/ `docs-cockpit-author|portfolio|prompt --bundle` 0 失实命中（历史时间线条目带"已删"注的除外）。
- [ ] **Step 3: Commit** — `docs(v1.0-C): update site copy for v1.0 skill-first reality`

---

## Task 8: CHANGELOG 1.0.0 + 版本 bump 四件套

**Files:**
- Modify: `CHANGELOG.md`（顶部加 `## [1.0.0] · <执行日>` 节）
- Modify: `docs_cockpit/__init__.py`（`__version__ = "1.0.0"`）
- Modify: `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json`（version → 1.0.0）

- [ ] **Step 1: CHANGELOG entry**（Keep-a-Changelog 风格 · 与 0.19.0 节同款结构：Why 段含用户原话 + Added/Changed/Removed/Breaking）。骨架：
  - **Why**：引用 north-star 原话「我们项目本质上是 skill · python 代码只是辅助…」+ skill-first pivot 一段叙事（spec 文档 `docs/plans/P-skill-first-pivot.md` 链接）
  - **Breaking**：CLI `build`→`render`（alias 至 1.1）；删 8 认知子命令清单；删 MCP server（plugin.json mcpServers 移除）；删 4 旧 skill（docs-cockpit / author / standup / portfolio）→ 新 3 skill；删 portfolio CLI + weekly
  - **Added**：use-docs-cockpit 入口 + SessionStart 条件注入（hooks/）；docs-cockpit-build 7-phase；docs-cockpit-rebuild 5-phase；references/ 三件（schema SSOT / 4 原子方法 / operations）；hooks-cursor.json
  - **Migration**：下游 pre-commit `docs-cockpit build` → `docs-cockpit render`（alias 兜底到 1.1）；插件用户 `docs-cockpit upgrade`（会清 cache + 重启提示）；MCP 用户 → skill 流程替代说明
- [ ] **Step 2: bump 三处版本号** + 核对四件套一致：

```bash
grep -rn "0\.19\.0\|1\.0\.0" docs_cockpit/__init__.py .claude-plugin/plugin.json .claude-plugin/marketplace.json CHANGELOG.md | head -10
```
- [ ] **Step 3: Commit** — `release(v1.0.0): skill-first pivot · 1 entry + 2 flow skills + mechanical render core`（与历史 release commit 风格一致）

---

## Task 9: 发布全量回归 + merge 准备

- [ ] **Step 1: 全套绿灯** — pytest 253 passed；lint exit 0 · 0 warn；render 本仓成功；`docs-cockpit build`（alias）中文警告正常。
- [ ] **Step 2: hooks 双 smoke**（Claude Code 路 + Cursor 路 + /tmp 静默路 · Stage A/B 的命令复跑）。
- [ ] **Step 3: 下游烟测** — Sourcery + bastion 各跑 `render`（新名验证 · 之前烟测走的 alias）+ 跑后 `git checkout -- docs/` 还原。
- [ ] **Step 4: 终扫** — 残留 grep 全 pattern 复跑（Stage B Task 11 的命令 + `commands/` 现已入扫描）——除 CHANGELOG/docs/plans/有意历史注外 **0 命中**；版本四件套均 1.0.0；`git log --oneline main..HEAD` 总览。
- [ ] **Step 5: 更新 Stage C plan 自身 status** — 本文件 frontmatter `status: planned` → `done`（dogfood）。
- [ ] **Step 6: Commit + merge 决策** — 收尾 commit 后，用 superpowers:finishing-a-development-branch 流程向用户呈现选项（merge to main / PR / 其它）——**merge 本身需用户确认**（这是 1.0.0 发布动作 · 推送即对插件用户可见）。

---

## Stage C 完成定义（DoD）

- [ ] commands/ = browse/lint/migrate/render/update 五件 · 零死引用
- [ ] 模板/site/README×2/CLAUDE.md 零失实叙事（grep 终扫 0 命中）
- [ ] module docs 历史化 · lint 0 error 0 warn
- [ ] CHANGELOG 1.0.0 entry + 版本四件套一致
- [ ] pytest 253 passed · hooks 三路 smoke · 双下游 render 烟测
- [ ] merge 决策已呈现给用户（merge 本身不在 DoD——属用户决定）

**post-1.0 债务（本 Stage 明确不做 · 移交 backlog）**：schema.py 拆 md_merge.py；sync-status 去留再议；site 整页改版；模板深度重构（死 JS 路径清理）；`build` alias 在 1.1 移除。
