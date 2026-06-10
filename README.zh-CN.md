[English](README.md) · **中文**

# docs-cockpit

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)
[![CHANGELOG](https://img.shields.io/badge/CHANGELOG-0.14.3-green.svg)](CHANGELOG.md)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#贡献)

> **MIT 协议开源项目 · 欢迎提 Issues + PR。**
> **落地页:** <https://guohao1020.github.io/docs-cockpit/>

给你的 AI 编程助手装一个项目驾驶舱。把任意文件夹里的项目 markdown(模块 / 概念 / 计划 / RFC / 接口规范)聚合成单文件 HTML 的 **Kanban 看板** + **Backlog 跨模块视图** + **树形侧边栏阅读器**,浏览器 `file://` 直接打开。Frontmatter 驱动 · 内置 schema 校验 · 原生 AI 协作。**Claude Code · Cursor · Codex CLI · Continue** 通过 MCP server 直连。

> AI 不再每次问"该用什么 frontmatter" —— docs-cockpit 把规范以 skill 形式打包发布,把校验器内置到 build,把"复制提示词"做成抽屉里的 CTA,让 AI 拿着完整上下文替你写下一份 plan / RFC / spec / module 子任务。多项目用户还能用 portfolio 注册表 + 周快照机制,一条命令出跨项目周报。

### v0.11 → v0.14 时间线(driver-seat 叙事)

| 版本 | 主题 | 一句话 |
|---|---|---|
| **0.11** | driver-seat | Subtask 一等公民 · split-view 二级页面 · Copy prompt 按钮 · author skill §11/§12 |
| **0.12** | 模式 1 接通 | **MCP server**(Claude / Cursor / Codex 直连)· `apply-patch` / `sync-status` / `suggest` 3 个 CLI |
| **0.13** | polish 收尾 | `code_anchors.path_only` clean 字段 · parser 接受 `## §N · 待办` / `### TODO` · `--from-browser` Firefox · CSS specificity audit |
| **0.14** | 批量驾驶舱 | `#/backlog` 跨模块扁平视图 + 时间/版本/状态/搜索 4 维筛选 · 多选 + shift-click 范围 · **`prompt --bundle`** cohesion 评分聚合 prompt |

当前:**`0.14.3` · 17/17 模块 · overall 100%(dogfood)**。完整时间线见 [CHANGELOG.md](CHANGELOG.md)。

## Quickstart

把 docs-cockpit 装到你的 AI 编程助手上:

- **[Claude Code](#claude-code)** ✅ 已就绪
- **Codex CLI · Codex App · Factory Droid · Gemini CLI · OpenCode · Cursor · GitHub Copilot CLI** —— 打包中 · 看板 / 校验器 / 规范本身是 agent-agnostic 的(都是 markdown skill + Python CLI)· 只有"如何把 skill 分发到不同 harness"这一层因 harness 而异

装完后,4 个 skill 会按你跟 agent 的自然语言对话自动触发 —— 不用记任何语法。7 个 slash 命令在你需要显式调用时提供入口。

## 它怎么工作

只要你让 AI 助手跟踪项目进度、写一份 plan、出 standup 或周报、或修 frontmatter 报错,docs-cockpit 的 skill 就自动接管。

3 个 skill 分工明确:`docs-cockpit` 负责**搭建 cockpit**、`docs-cockpit-standup` 负责**从单项目状态出叙事报告**、`docs-cockpit-portfolio` 负责**多项目周报**;文档规范的 SSOT 在 [`references/schema.md`](references/schema.md)。AI 不再每次都重新发明约定 —— **skill 本身就是约定**。

底层,build 步骤从你列出的每个 markdown 文件读 YAML frontmatter · 渲成一张卡 · 写出独立单文件 HTML 看板,`file://` 直接打开 —— 不需要 localhost · 不需要静态站点生成器 · 不需要 JS 框架 · 运行时零网络请求。Sidecar `state.json` 同步携带相同 payload + 结构化的 frontmatter 校验结果 —— standup / portfolio skill 读它出叙事 · CI 读它做不变式检查。

当你让 AI 给某个模块写 plan / spec 时,**docs-cockpit-build** skill 把 schema(必填字段 · status × progress 不变式 · 文件命名 · 跨文档引用规则 · 详见 `references/schema.md`)带给 AI,落盘之前就先对齐。当看板渲染出来,任何"还没关联 docs"的模块都会显示一个复制提示词 CTA —— 在 `Plan` / `RFC` / `Spec` 三个 tab 之间切换 · 看清楚替换好 id / title / status / sprint / desc / body 摘要的整段提示词 · 一键复制粘贴到你的 AI 助手即可。

对多项目用户,**用户级注册表**(`~/.docs-cockpit/projects.yaml`)跨机器跟踪每个项目。每周跑一次 `docs-cockpit portfolio snapshot`(或挂 cron / pre-commit),**portfolio** skill 出一份覆盖所有项目的周报 · 含"本周变化"周差异(新 done / 新 blocker / 进度跳跃 / 新模块)。

## 安装

### Claude Code

```bash
# 在 Claude Code 里
/plugin marketplace add Guohao1020/docs-cockpit
/plugin install docs-cockpit@docs-cockpit
```

这就是全部安装。插件在第一次 build 时会自动检测你机器上是否有 `docs-cockpit` Python runtime · 没有就用 `uv` / `pipx` / `pip`(看你机器上有谁)透明地 bootstrap 一份 —— 你 PATH 上只需要有 Python 3.10+,其他都由插件自己安排。

要用 MCP server(Claude Code / Cursor / Codex CLI 直连 · v0.12+)· 装可选 `[mcp]` extra:

```bash
pip install 'docs-cockpit[mcp]'                       # 或
uv tool install --with mcp docs-cockpit
```

插件 `plugin.json` 自动给 Claude Code 注册 MCP server —— 重启即可在 MCP 工具列表看到三个 endpoint(`cockpit_prompt` / `cockpit_apply_patch` tool + `cockpit://state` resource)。

装完后,你就得到了:

```
/docs-cockpit:build       生成看板 + Backlog + sidecar
/docs-cockpit:browse      生成树形侧边栏 MD 阅读器
/docs-cockpit:migrate     老项目布局迁移
/docs-cockpit:status      standup 风格状态报告(单项目)
/docs-cockpit:weekly      多项目周报(含跨项目周差异)
/docs-cockpit:lint        按 references/schema.md 规范校验 frontmatter
/docs-cockpit:update      升级 docs-cockpit 自身
```

外加 CLI 子命令(终端跑):

```
docs-cockpit build                              → docs/index.html (+ state.json, prompts.js, bundle-meta.js)
docs-cockpit prompt M07 M07-f75501              单 subtask prompt → 剪贴板
docs-cockpit prompt --bundle M07-A,M07-B,M11-X  bundle prompt(v0.14+)· cohesion 评分聚合
docs-cockpit apply-patch <md> < patch.yaml      LLM YAML patch 落回 MD(v0.12+)· dry-run-first + .bak
docs-cockpit sync-status --import overrides.json   dashboard 勾选反向同步到 MD(v0.12+)· 支持 --from-browser firefox
docs-cockpit suggest M07 --strict               LLM 软建议 prompt(v0.12+)· CI 用
docs-cockpit mcp-serve                          stdio MCP server(v0.12+)· 给 Cursor/Codex/Continue 接
docs-cockpit migrate-subtasks <md> --apply      v0.10 → v0.11 subtask schema 升级
docs-cockpit portfolio add / list / snapshot    多项目注册表 + 周快照(v0.10+)
docs-cockpit upgrade                            原子升级 + plugin cache 清空
```

外加 4 个自动触发的 skill(你不需要主动调,AI 自己判断什么时候用):

| Skill | 触发时机 |
|---|---|
| **`docs-cockpit`** | "给这个项目搭个看板" · "重 build cockpit" · "升级 docs-cockpit" |
| **`docs-cockpit-standup`** | "Sourcery 有什么 blocker" · "M1.2 sprint 进度" · "这个项目的 standup" |
| **`docs-cockpit-portfolio`** | "出周报" / "weekly report" · "我所有项目最近咋样" · "把这个项目加进 portfolio" |

### 其他 AI 编程助手

Codex CLI · Codex App · Factory Droid · Gemini CLI · OpenCode · Cursor · GitHub Copilot CLI —— 打包在 roadmap 上。看板 / 校验器 / 规范本身是 agent-agnostic(就是 markdown skill + Python CLI),只是 skill 在不同 harness 上的分发机制不同。

如果你想给某个 harness 打包,欢迎开 issue 或 PR。

## 基本工作流

1. **让 AI 助手搭 cockpit** —— "给这个项目装 docs-cockpit"。Agent 扫一下仓库的文档布局 · 给出配置建议 · 跑第一次 build。老项目里 `docs/plans/` `docs/adrs/` `docs/RFC/` 已经写一堆的情况下,agent 走 migrate 流程 —— 默认 dry-run 把"打算把谁移到哪"先讲清 · 你确认后才 `git mv` + 注入 frontmatter 脚手架。

2. **在对话里写文档** —— "给 M07 写一份执行计划"。Agent 读规范(`references/schema.md`)· 一次性写对 frontmatter · 放到正确路径(`docs/plans/YYYY-MM-DD-<id>-plan.md`),**并且**回去把源模块的 `docs:` 字段加上链接 —— 下次 build 看板就能直接显示这条关联。

3. **重 build 看板** —— "重 build cockpit"。浏览器开 `docs/index.html` · 模块 Kanban 渲染 · 点任意卡片 → 抽屉显示 desc / status / progress 滑块 / 子任务清单 / 关联文档,关联文档支持**抽屉内联 MD 预览**(marked.js 在抽屉里直接渲染 · 不再跳出看 file:// 原文)。

4. **跟踪单项目状态** —— 自然语言问("Sourcery 有什么 blocker" · "M1.2 进度")。`docs-cockpit-standup` skill 读 `state.json` 出表格 / 列表 / 可直接粘贴的 Markdown。**契约上只读** · 永远不改文件。

5. **Commit 前 lint** —— "校验 frontmatter"。每条 issue 都可操作:

   ```
   ❌ M07.md · id: missing required field — module won't appear in dashboard
      💡 fix: add `id: M07` to frontmatter
      📚 references/schema.md · frontmatter schema (required fields)
   ```

   三档 severity:`error`(根本不会渲染)· `warn`(渲染但状态错)· `hint`(锦上添花 · 影响 copy-prompt 上下文质量)。

6. **多项目周报** —— 每个项目目录里跑一次 `docs-cockpit portfolio add` 注册,定时跑 `docs-cockpit portfolio snapshot`(cron / Task Scheduler / pre-commit),然后跟 AI 说"出周报" —— portfolio skill 聚合所有项目 + 算周差异。

7. **升级** —— "升级 docs-cockpit"。一条命令检测后端 · 对比版本 · 拉 CHANGELOG diff · 让你确认 · 跑升级命令 · 如果 plugin SKILL.md 变了原子清 cache + 提示重启。

## 安装后你得到了什么

### 看板功能

- **模块 Kanban** —— 5 列状态 · 点卡片 → split-view 抽屉显示 desc / status 选择器 / progress 滑块 / 子任务清单(每条 subtask 多 anchor 按钮 + Copy prompt)/ 关联文档 · localStorage 持久化 + build-time-aware 自动失效
- **Sprint Timeline** —— 模块按 sprint 分组 + 平均进度
- **Backlog 视图(v0.14+)** —— `#/backlog` hash route · 跨模块扁平 subtask 清单 · 4 维筛选(时间 / 版本 / 状态 / 搜索)· URL state codec · 可分享链接
- **多选 bundle(v0.14+)** —— 每 subtask 一个 checkbox · shift-click 范围选 · "全选当前" · 按状态快速加 · 底部 floating bar 显 cohesion verdict → Copy bundle prompt(CLI 命令)→ 终端跑 `docs-cockpit prompt --bundle <ids>`
- **Refine with AI 按钮(v0.11+)** —— 每 module · 复制 refinement prompt 让 AI 审计 anchor 精度 · caller-aware mode(Claude Code 直接 Edit · 浏览器 LLM 输出 YAML patch)
- **Concept Grid** + **System Docs 抽屉** —— 精挑的系统级文档(CLAUDE.md / PRD / DESIGN / RFC / memory / roadmap)一键直达
- **Body 自动抽取** —— `## 待办` / `## TODO` / `## §N · 待办`(v0.13+)→ subtasks · `## 关联` / `## Related` → `docs:`
- **抽屉内联 MD 预览** —— 点关联文档 / code anchor / doc anchor · marked.js + highlight.js 在右栏渲染 · slice 信息徽章显「📍 Showing lines X-Y of <file>」
- **空 docs · 复制提示词 CTA** —— `Plan` / `RFC` / `Spec` 三个 tab · 提示词原文展示 · 单 Copy 按钮 · 粘贴到你的 AI 助手
- **needs-docs kanban chip** —— active 状态但无 docs 的模块卡片右上挂 amber chip
- **Frontmatter 校验器** —— 结构化 `error` / `warn` / `hint` · 含修法建议 + 规范引用 · 每条都指向 `references/schema.md` 的具体段落
- **双语 UI** —— 顶栏 `[EN] [中]` 切换 · localStorage 持久化
- **树形浏览器**(`browse`) —— 侧边栏镜像目录结构 · 搜索 + 折叠 + 上次查看记忆 · marked.js + highlight.js 渲染

### MCP server(v0.12+)· `docs-cockpit mcp-serve`

Anthropic 官方 `mcp` SDK · stdio transport。三个 endpoint · 任何 MCP-aware 客户端(Claude Code · Cursor · Codex CLI · Continue)都能用:

| Endpoint | 类型 | 干什么 |
|---|---|---|
| `cockpit_prompt(module_id, subtask_id?, template?)` | tool | 渲染单 subtask prompt(等同 `docs-cockpit prompt` CLI) |
| `cockpit_apply_patch(yaml_patch, module_id, apply?)` | tool | LLM YAML patch merge 回 MD · dry-run-first · `.bak` 备份 |
| `cockpit://state` | resource | 完整 `state.json` payload(modules + subtasks + concepts + issues) |

各客户端接线方式因客户端而异 —— 详见 MCP server 模块的 transport 说明。

### Schema 闭环(v0.12+)· 4 个 CLI 配合

- `prompt --bundle`(v0.14)· N subtask 聚合 prompt · `docs/bundle-meta.js` sidecar 预算 pairwise cohesion / conflict
- `apply-patch`(v0.12 · M08)· 解析 LLM YAML 输出 · merge 到 MD frontmatter 或 body checklist · 白名单字段(`status` / `code` / `docs` / `desc`)其它一律 drop
- `sync-status`(v0.12 · M09)· dashboard 勾选反向同步到 MD · Firefox SQLite reader(`--from-browser firefox`)· Chrome stub 指向 Export workflow
- `suggest`(v0.12 · M10)· LLM 软建议 prompt · 4 template(`desc-rewrite` / `subtask-recompose` / `anchor-completeness` / `cross-doc-consistency`)· `--strict` CI 用

### 跨项目 portfolio(0.10.0+)

- **用户级注册表** 在 `~/.docs-cockpit/projects.yaml` —— 用 `docs-cockpit portfolio add/list/remove/tag` 管理
- **周快照** 在 `~/.docs-cockpit/snapshots/<name>/<YYYY-MM-DD>.json` —— 跑 `docs-cockpit portfolio snapshot`(或挂 cron / pre-commit)
- **周报 skill** 出跨项目 Markdown · 七节固定结构:🚀 Wins · 🔥 Blockers · 📋 In flight · 📈 Progress this week · 🆕 Added · 🥶 Stale · ⚠️ Frontmatter issues · 加 cross-project highlights
- **周差异** 从快照算出来:新 done · 新 blocker · 进度跳跃(≥15 点 · 过滤噪音)· 新模块 · sprint move
- **项目挑选器** —— 你说"出周报"时 · portfolio skill 列出注册的所有项目编号清单 + 每个项目当前 KPI 摘要 · 你按编号 / 名字 / `all` / 标签(比如 `active`)挑

### 机器可读 sidecar:`state.json`

每次 build 在 HTML 旁写一份 `docs/state.json`。和看板同一份 payload + 校验器的 `issues[]`。standup / portfolio skill 读它出叙事 · CI 读它做不变式检查。Schema 自 0.2.0 起稳定(只加字段 · 不删字段)。

## 哲学

- **单文件交付** —— `docs/index.html` 完全自包含 · 无 localhost · 无 build pipeline · 无 JS 框架 · 运行时零网络。可以丢进 Slack DM 也可以 commit 进仓库。
- **Frontmatter 即 schema** —— 每个模块都是人类可读、同时 frontmatter 机器可解析的 markdown 文件。没有私有数据库。
- **一套规范统一一切**(`references/schema.md`) —— schema 写在一份 reference 文档里 · AI 和人共享。校验器逐字段引用它。**不再每次写文档都问 AI "frontmatter 该填啥"**。
- **校验可选但要可操作** —— 每条 `❌` 与 `⚠️` 都带 `💡 fix` 和 `📚 see`。输出可 grep · IDE 能消费 · CI 能用。
- **`file://` 优先** —— 不依赖 webserver。浏览器的 file:// 安全模型就是发布目标。
- **原子升级** —— "清 plugin cache" 和 "提示重启" 压在一步里。Ghost state(CLI 升级后 plugin 仍跑老 SKILL.md)就是这条命令在防的。
- **AI 助手原生** —— 为"对话式工作流"设计 · 而不是为"敲命令行"设计。CLI 是 runtime · agent 才是接口。
- **用户级 portfolio** —— 一个用户同时维护多个项目 · 注册表和快照都在 `~/.docs-cockpit/` 下 · 跟任何具体项目仓库解耦 · 也跟 Claude Code 安装路径解耦。

## 参考

### 项目结构

```
your-project/
├── docs-cockpit.yaml              ← 配置(agent 替你写)
├── docs/
│   ├── index.html                 ← BUILD 产物 · 看板
│   ├── browse.html                ← BUILD 产物 · 树形侧边栏阅读器(可选)
│   ├── state.json                 ← BUILD 产物 · 机器可读 payload + issues[]
│   ├── spec/
│   │   ├── module/M01-*.md        ← 模块规范 → Kanban 卡
│   │   └── concept/C01-*.md       ← 概念规范 → Concept Grid
│   ├── plans/2026-MM-DD-<id>-plan.md   ← 执行计划(通过 `docs:` 关联回模块)
│   ├── RFC/<NNN>-*.md             ← 技术决策
│   └── PRD.md                     ← 作为 `system_docs` 条目展示
├── CLAUDE.md                       ← 作为 `system_docs` 条目展示
└── .git/
```

### Frontmatter(看板读的就是这块)

```yaml
---
id: M07                              # 必填 · 没有就被看板丢掉
type: module                         # module | concept | plan | rfc | spec
title: "Job / Task FSM"
status: in-progress                  # not-started | planned | in-progress | blocked | done | deferred
sprint: M1.2
progress: 60                         # 0-100 · 会与 status 做区间一致性校验
desc: "Job 生命周期状态机 · 驱动 worker 调度"
owner: harvey
prd_ref: "§7.4.1"
docs:                                # 链到 plan / RFC / spec
  - { title: "执行计划", path: "docs/plans/2026-05-03-m07-fsm-plan.md" }
depends_on: [M06]
blocks: [M08, M09]
subtasks:                            # 或在 body 写 `## 待办` —— 二选一都可
  - { title: "把 FSM enum 接到 Pydantic", done: true }
  - { title: "worker 从队列拉取下一个状态", done: false }
---

# 模块正文 —— frontmatter 之下随意写
```

完整规范见 [`references/schema.md`](references/schema.md)。规范覆盖 "docs vs subtasks 决策"、文件命名约定、status × progress 不变式、跨文档引用规则。

### 多项目注册表结构

```
~/.docs-cockpit/
├── projects.yaml                   ← 注册表 · `docs-cockpit portfolio add/list/remove/tag` 管理
└── snapshots/
    └── <project-name>/
        └── <YYYY-MM-DD>.json       ← 周快照(state.json 副本 · 用于周差异)
```

路径用 `pathlib.Path.home()` —— Windows `C:\Users\<name>\.docs-cockpit\` · POSIX `~/.docs-cockpit/`。

## 升级

让 agent 升级即可 —— "升级 docs-cockpit"。`docs-cockpit` skill 走整条流:检测后端 · 对比版本 · 显示 CHANGELOG diff · 让你确认 · 跑升级命令 · 如果 plugin SKILL.md 变了原子清 cache + 提示重启。`/docs-cockpit:update` slash 命令是同一流程的显式入口。

## 贡献

这是一个开源项目 —— 任何大小的贡献都欢迎。开发环假定你在改 docs-cockpit 本身(不是单纯使用):

```bash
git clone https://github.com/Guohao1020/docs-cockpit
cd docs-cockpit
pip install -e .              # editable 安装(Python 3.10+)
docs-cockpit build -c docs_cockpit/examples/minimal.yaml --debug
```

**动手前先看 [CLAUDE.md](CLAUDE.md)** —— 涵盖架构、SemVer 约定、语言约定、本仓库容易踩的坑。

新增 skill 时,参考现有四个的写法(`skills/docs-cockpit*/SKILL.md`)—— frontmatter 的 `description` 要"pushy"(宁可过度触发也别欠触发)· body 解释 **why** 而不只列 **what** · 文件命名 + 段落结构对齐 canonical-skill 风格。

涉及实质性改动(新功能 / schema 变更 / breaking change)先开 issue。Bug fix 和文档改进可以直接 PR。

## License

MIT · 见 [LICENSE](LICENSE)。

## 社区

- **落地页:** <https://guohao1020.github.io/docs-cockpit/>
- **Issues:** <https://github.com/Guohao1020/docs-cockpit/issues>
- **Release notes:** [CHANGELOG.md](CHANGELOG.md)
- **贡献者架构文档:** [CLAUDE.md](CLAUDE.md)
- **Sync workflow:** [`references/sync_status_workflow.md`](references/sync_status_workflow.md)
- **Frontmatter 规范 (SSOT):** [`references/schema.md`](references/schema.md)
