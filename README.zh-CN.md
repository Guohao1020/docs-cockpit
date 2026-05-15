[English](README.md) · **中文**

# docs-cockpit

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)
[![CHANGELOG](https://img.shields.io/badge/CHANGELOG-0.10.0-green.svg)](CHANGELOG.md)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#贡献)

> **MIT 协议开源项目 · 欢迎提 Issues + PR。**

给你的 AI 编程助手装一个项目看板。把任意文件夹里的项目 markdown(模块 / 概念 / 计划 / RFC / 接口规范)聚合成单文件 HTML 的 **Kanban 看板** + **树形侧边栏阅读器**,浏览器 `file://` 直接打开。Frontmatter 驱动 · 内置 schema 校验 · 原生 AI 协作。

> AI 不再每次问"该用什么 frontmatter" —— docs-cockpit 把规范以 skill 形式打包发布,把校验器内置到 build,把"复制提示词"做成抽屉里的 CTA,让 AI 拿着完整上下文替你写下一份 plan / RFC / spec。多项目用户还能用 portfolio 注册表 + 周快照机制,一条命令出跨项目周报。

## Quickstart

把 docs-cockpit 装到你的 AI 编程助手上:

- **[Claude Code](#claude-code)** ✅ 已就绪
- **Codex CLI · Codex App · Factory Droid · Gemini CLI · OpenCode · Cursor · GitHub Copilot CLI** —— 打包中 · 看板 / 校验器 / 规范本身是 agent-agnostic 的(都是 markdown skill + Python CLI)· 只有"如何把 skill 分发到不同 harness"这一层因 harness 而异

装完后,4 个 skill 会按你跟 agent 的自然语言对话自动触发 —— 不用记任何语法。7 个 slash 命令在你需要显式调用时提供入口。

## 它怎么工作

只要你让 AI 助手跟踪项目进度、写一份 plan、出 standup 或周报、或修 frontmatter 报错,docs-cockpit 的 skill 就自动接管。

4 个 skill 分工明确:`docs-cockpit` 负责**搭建 cockpit**、`docs-cockpit-author` 负责**按规范写单份项目文档**、`docs-cockpit-standup` 负责**从单项目状态出叙事报告**、`docs-cockpit-portfolio` 负责**多项目周报**。AI 不再每次都重新发明约定 —— **skill 本身就是约定**。

底层,build 步骤从你列出的每个 markdown 文件读 YAML frontmatter · 渲成一张卡 · 写出独立单文件 HTML 看板,`file://` 直接打开 —— 不需要 localhost · 不需要静态站点生成器 · 不需要 JS 框架 · 运行时零网络请求。Sidecar `state.json` 同步携带相同 payload + 结构化的 frontmatter 校验结果 —— standup / portfolio skill 读它出叙事 · CI 读它做不变式检查。

当你让 AI 给某个模块写 plan / spec 时,**author** skill 触发,把 schema(必填字段 · status × progress 不变式 · 文件命名 · 跨文档引用规则)带给 AI,落盘之前就先对齐。当看板渲染出来,任何"还没关联 docs"的模块都会显示一个复制提示词 CTA —— 在 `Plan` / `RFC` / `Spec` 三个 tab 之间切换 · 看清楚替换好 id / title / status / sprint / desc / body 摘要的整段提示词 · 一键复制粘贴到你的 AI 助手即可。

对多项目用户,**用户级注册表**(`~/.docs-cockpit/projects.yaml`)跨机器跟踪每个项目。每周跑一次 `docs-cockpit portfolio snapshot`(或挂 cron / pre-commit),**portfolio** skill 出一份覆盖所有项目的周报 · 含"本周变化"周差异(新 done / 新 blocker / 进度跳跃 / 新模块)。

## 安装

### Claude Code

```bash
# 在 Claude Code 里
/plugin marketplace add Guohao1020/docs-cockpit
/plugin install docs-cockpit@docs-cockpit
```

这就是全部安装。插件在第一次 build 时会自动检测你机器上是否有 `docs-cockpit` Python runtime · 没有就用 `uv` / `pipx` / `pip`(看你机器上有谁)透明地 bootstrap 一份 —— 你 PATH 上只需要有 Python 3.10+,其他都由插件自己安排。

装完后,你就得到了:

```
/docs-cockpit:build       生成看板
/docs-cockpit:browse      生成树形侧边栏 MD 阅读器
/docs-cockpit:migrate     老项目布局迁移
/docs-cockpit:status      standup 风格状态报告(单项目)
/docs-cockpit:weekly      多项目周报(含跨项目周差异)
/docs-cockpit:lint        按 author 规范校验 frontmatter
/docs-cockpit:update      升级 docs-cockpit 自身
```

外加 4 个自动触发的 skill(你不需要主动调,AI 自己判断什么时候用):

| Skill | 触发时机 |
|---|---|
| **`docs-cockpit`** | "给这个项目搭个看板" · "重 build cockpit" · "升级 docs-cockpit" |
| **`docs-cockpit-author`** | "给模块 M07 写一份 plan" · "这个 RFC 该用什么 frontmatter" · 校验器报 issue |
| **`docs-cockpit-standup`** | "Sourcery 有什么 blocker" · "M1.2 sprint 进度" · "这个项目的 standup" |
| **`docs-cockpit-portfolio`** | "出周报" / "weekly report" · "我所有项目最近咋样" · "把这个项目加进 portfolio" |

### 其他 AI 编程助手

Codex CLI · Codex App · Factory Droid · Gemini CLI · OpenCode · Cursor · GitHub Copilot CLI —— 打包在 roadmap 上。看板 / 校验器 / 规范本身是 agent-agnostic(就是 markdown skill + Python CLI),只是 skill 在不同 harness 上的分发机制不同。

如果你想给某个 harness 打包,欢迎开 issue 或 PR。

## 基本工作流

1. **让 AI 助手搭 cockpit** —— "给这个项目装 docs-cockpit"。Agent 扫一下仓库的文档布局 · 给出配置建议 · 跑第一次 build。老项目里 `docs/plans/` `docs/adrs/` `docs/RFC/` 已经写一堆的情况下,agent 走 migrate 流程 —— 默认 dry-run 把"打算把谁移到哪"先讲清 · 你确认后才 `git mv` + 注入 frontmatter 脚手架。

2. **在对话里写文档** —— "给 M07 写一份执行计划"。Agent 触发 `docs-cockpit-author`,读规范 · 一次性写对 frontmatter · 放到正确路径(`docs/plans/YYYY-MM-DD-<id>-plan.md`),**并且**回去把源模块的 `docs:` 字段加上链接 —— 下次 build 看板就能直接显示这条关联。

3. **重 build 看板** —— "重 build cockpit"。浏览器开 `docs/index.html` · 模块 Kanban 渲染 · 点任意卡片 → 抽屉显示 desc / status / progress 滑块 / 子任务清单 / 关联文档,关联文档支持**抽屉内联 MD 预览**(marked.js 在抽屉里直接渲染 · 不再跳出看 file:// 原文)。

4. **跟踪单项目状态** —— 自然语言问("Sourcery 有什么 blocker" · "M1.2 进度")。`docs-cockpit-standup` skill 读 `state.json` 出表格 / 列表 / 可直接粘贴的 Markdown。**契约上只读** · 永远不改文件。

5. **Commit 前 lint** —— "校验 frontmatter"。每条 issue 都可操作:

   ```
   ❌ M07.md · id: missing required field — module won't appear in dashboard
      💡 fix: add `id: M07` to frontmatter
      📚 see: docs-cockpit-author · §2.1 required frontmatter
   ```

   三档 severity:`error`(根本不会渲染)· `warn`(渲染但状态错)· `hint`(锦上添花 · 影响 copy-prompt 上下文质量)。

6. **多项目周报** —— 每个项目目录里跑一次 `docs-cockpit portfolio add` 注册,定时跑 `docs-cockpit portfolio snapshot`(cron / Task Scheduler / pre-commit),然后跟 AI 说"出周报" —— portfolio skill 聚合所有项目 + 算周差异。

7. **升级** —— "升级 docs-cockpit"。一条命令检测后端 · 对比版本 · 拉 CHANGELOG diff · 让你确认 · 跑升级命令 · 如果 plugin SKILL.md 变了原子清 cache + 提示重启。

## 安装后你得到了什么

### 看板功能

- **模块 Kanban** —— 5 列状态 · 点卡片 → 抽屉显示 desc / status 选择器 / progress 滑块 / 子任务清单 / 关联文档 · localStorage 持久化覆盖
- **Sprint Timeline** —— 模块按 sprint 分组 + 平均进度
- **Concept Grid** + **System Docs 抽屉** —— 精挑的系统级文档(CLAUDE.md / PRD / DESIGN / RFC / memory / roadmap)一键直达
- **Body 自动抽取** —— `## 待办` / `## TODO` → subtasks · `## 关联` / `## Related` → `docs:`
- **抽屉内联 MD 预览** —— 点关联文档 · marked.js + highlight.js 在抽屉里直接渲染 · "返回模块" 一键回卡片
- **空 docs · 复制提示词 CTA** —— `Plan` / `RFC` / `Spec` 三个 tab · 提示词原文展示 · 单 Copy 按钮 · 粘贴到你的 AI 助手
- **needs-docs kanban chip** —— active 状态但无 docs 的模块卡片右上挂 amber chip · 一眼看出谁要补
- **Frontmatter 校验器** —— 结构化 `error` / `warn` / `hint` · 含修法建议 + 规范引用 · 每条都指向 `docs-cockpit-author` 的具体段落
- **双语 UI** —— 顶栏 `[EN] [中]` 切换 · 默认 EN · localStorage 持久化
- **树形浏览器**(`browse`) —— 侧边栏镜像目录结构 · 搜索 + 折叠 + 上次查看记忆 · marked.js + highlight.js 渲染

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
- **一套规范统一一切**(`docs-cockpit-author`) —— schema 写在一个 skill 里 · AI 和人共享这份文档。校验器逐字段引用它。**不再每次写文档都问 AI "frontmatter 该填啥"**。
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

完整规范见 `docs-cockpit-author` skill —— 你的 AI 助手在写 plan / RFC / spec / 模块 MD 时会自动加载。规范覆盖 "docs vs subtasks 决策"、文件命名约定、status × progress 不变式、跨文档引用规则。

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

新增 skill 时,参考现有四个的写法(`skills/docs-cockpit*/SKILL.md`)—— frontmatter 的 `description` 要"pushy"(宁可过度触发也别欠触发)· body 解释 **why** 而不只列 **what** · 文件命名 + 段落结构对齐 canonical-skill 风格。`docs-cockpit-author/SKILL.md` 是"docs-cockpit 系列 skill 该长什么样"的参考模板。

涉及实质性改动(新功能 / schema 变更 / breaking change)先开 issue。Bug fix 和文档改进可以直接 PR。

## License

MIT · 见 [LICENSE](LICENSE)。

## 社区

- Issues: <https://github.com/Guohao1020/docs-cockpit/issues>
- Release notes: [CHANGELOG.md](CHANGELOG.md)
- 贡献者架构文档: [CLAUDE.md](CLAUDE.md)
