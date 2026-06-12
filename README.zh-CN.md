[English](README.md) · **中文**

# docs-cockpit

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)
[![CHANGELOG](https://img.shields.io/badge/CHANGELOG-1.3.0-green.svg)](CHANGELOG.md)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#贡献)

> **MIT 协议开源项目 · 欢迎提 Issues + PR。**
> **落地页:** <https://guohao1020.github.io/docs-cockpit/>

给你的 AI 编程助手装一个项目驾驶舱。把任意文件夹里的项目 markdown(模块 / 概念 / 计划 / RFC / 接口规范)聚合成单文件 HTML 的 **Kanban 看板** + **Backlog 跨模块视图** + **树形侧边栏阅读器**,浏览器 `file://` 直接打开。Frontmatter 驱动 · 内置 schema 校验 · 原生 AI 协作。

> 自 v1.0 起 docs-cockpit 是 **skill-first** 的:认知 —— 哪个模块该关联哪份文档、哪条子任务背后是 plan 的哪一节 —— 全部住在 agent 直接阅读的 skill 里;Python CLI 只是一个机械渲染器。装上 plugin,打开任何带 `docs-cockpit.yaml` 的项目,SessionStart hook 自动把路由注入 agent 上下文 —— 你还没开口,它就已经知道怎么用这套驾驶舱了。

### v1.0 新在哪(skill-first pivot)

整次重构由一句话驱动:**认知在 skill,Python 只渲染。** 文档关联是判断性工作 —— 搜索、阅读、决策 —— 把它编码进 CLI 子命令,产出的正是用户报告过的失败模式:链接指向不存在的内容。v1.0 把这部分判断全部搬进 skill 工作流,每条关联都在对话里*和你一起*决定,并遵循一条北极星原则:**错误的 anchor 比缺失的 anchor 更糟。**

| v0.x | v1.0 |
|---|---|
| 4 个职责交叠的自动触发 skill | **1 个入口路由 + 2 个流程 skill** —— 路由在会话启动时自动注入 |
| 认知侧 CLI 子命令(prompt 渲染、LLM 建议、patch 合并等) | 已删除 —— 它们的判断职责搬进了 skill 工作流 |
| MCP server 作为 agent 接口 | 已删除 —— **skill 本身就是 agent 接口** |
| `docs-cockpit build` | `docs-cockpit render`(旧名在 1.0 保留为废弃别名 · 1.1 已移除) |

完整动机见 [`docs/plans/P-skill-first-pivot.md`](docs/plans/P-skill-first-pivot.md) · 完整时间线见 [CHANGELOG.md](CHANGELOG.md)。

## Quickstart

把 docs-cockpit 装到你的 AI 编程助手上:

- **[Claude Code](#claude-code)** ✅ 已就绪
- **[Codex](#codex)** ✅ 已通过 Codex marketplace 安装方式支持
- **Cursor** —— SessionStart 路由 hook 已带 Cursor 适配(`hooks/hooks-cursor.json`);完整打包在 roadmap 上
- **Gemini CLI · OpenCode · GitHub Copilot CLI · …** —— 看板 / 校验器 / 规范仍是 agent-agnostic 的(markdown skill + Python CLI);分发层因 harness 而异

装完后不需要记任何东西:在 docs-cockpit 项目里,路由 skill 会在会话启动时自动注入,agent 自己把驾驶舱相关的请求分发到正确的工作流。5 个 slash 命令在你想显式调用时提供入口。

## 它怎么工作

**一个路由 · 两个流程 skill · 一个机械 CLI。**

在带 `docs-cockpit.yaml` 的项目里启动会话时,plugin 的 SessionStart hook 把 `use-docs-cockpit` 路由注入 agent 上下文(在其他任何项目里,hook 保持完全静默)。路由只做一件事:分发。

| 你想做的 | 谁来接 |
|---|---|
| 0→1 建立关联体系 —— 搭 cockpit、规划全项目 spec/plan、把模块接到文档、补 anchor 缺口 | **`docs-cockpit-build`** skill · 7-phase 对话式工作流:确保配置 → 发现全部文档 → 推理关联 → dry-run 验证每个 anchor → 每条都和你一起决定 → 写 anchor + 起草缺失文档 → 渲染 |
| 刷新已经漂移的既有关联 —— 重构后 anchor 失效、spec 演进、链接过期 | **`docs-cockpit-rebuild`** skill · 5 phase:读当前状态 → 诊断漂移 → 重新推理 → 最小 diff 刷新 → 渲染 + 验证 |
| 问状态 —— 哪些卡了、sprint 进度、哪些模块停滞 | **`docs-cockpit-rebuild` Phase 1** · 读 `state.json` 回答,不动任何文件 |
| 只重新生成看板 HTML | **`docs-cockpit render`** CLI · 不做任何关联工作 |

底层,`render` 从你列出的每个 markdown 文件读 YAML frontmatter,把每份渲成一张卡,写出独立单文件 HTML 看板,`file://` 直接打开 —— 不需要 localhost、不需要静态站点生成器、不需要 JS 框架、运行时零网络请求。Sidecar `state.json` 携带相同 payload + 结构化校验结果 —— rebuild skill 读它出状态叙事,CI 读它做不变式检查。

文档规范的 SSOT —— 必填字段、status × progress 不变式、anchor 语法、文件命名、跨文档引用规则 —— 在 [`references/schema.md`](references/schema.md):agent 和人共读一份文件,校验器逐条 issue 引用它。AI 不再每次重新发明约定 —— **skill 本身就是约定。**

## 安装

### Codex

```bash
# 在 Codex CLI 里
codex plugin marketplace add Guohao1020/docs-cockpit
```

然后打开 Codex 插件目录,选择 `docs-cockpit` marketplace,安装 `docs-cockpit` 插件。在 Codex app 里,添加 marketplace 后从 **Plugins** 页面安装。

### Claude Code

```bash
# 在 Claude Code 里
/plugin marketplace add Guohao1020/docs-cockpit
/plugin install docs-cockpit@docs-cockpit
```

这就是全部安装。插件在第一次 render 时会自动检测你机器上是否有 `docs-cockpit` Python runtime,没有就用 `uv` / `pipx` / `pip`(看你机器上有谁)透明地 bootstrap 一份 —— 你 PATH 上只需要有 Python 3.10+,其他都由插件自己安排。

装完后,你就得到了:

```
/docs-cockpit:render      # 重新生成看板 + state.json(显式调用)
/docs-cockpit:browse      # 生成树形侧边栏 MD 阅读器
/docs-cockpit:migrate     # 老项目布局迁移
/docs-cockpit:lint        # 按 references/schema.md 规范校验 frontmatter
/docs-cockpit:update      # 升级 docs-cockpit 自身
```

外加 CLI 子命令(终端跑):

```
docs-cockpit render        # → docs/index.html (+ state.json, prompts.js)
docs-cockpit lint          # frontmatter + body 校验 · 不渲染 · CI / pre-commit 用
docs-cockpit init          # 生成最小可用 docs-cockpit.yaml
docs-cockpit migrate       # 散落的老 MD → canonical 布局 · 默认 dry-run
docs-cockpit browse        # 单文件树形侧边栏 MD 阅读器
docs-cockpit sync-status   # dashboard 勾选反向写回 MD 源文件
docs-cockpit upgrade       # 原子升级 CLI + plugin(清 cache + 提示重启)
```

外加 3 个 skill(你不需要主动调,agent 自己判断什么时候用):

| Skill | 角色 |
|---|---|
| **`use-docs-cockpit`** | 入口路由 · 在任何带 `docs-cockpit.yaml` 的项目里随会话启动自动注入 · 负责分发下面两位 |
| **`docs-cockpit-build`** | 「把项目做成看板」「关联模块和文档」「规划整个项目的 spec/plan」—— 0→1 / 全项目级关联构建,每条决定都在对话里和你一起做 |
| **`docs-cockpit-rebuild`** | 「anchor 失效了」「重构后关联乱了重新梳理」「哪些卡了」—— 诊断 + 刷新既有关联,或只读状态 |

### 其他 AI 编程助手

Codex 已通过上面的 Codex marketplace 安装方式支持。Cursor · Gemini CLI · OpenCode · GitHub Copilot CLI —— 打包仍在 roadmap 上(Cursor 已有 hook 适配 `hooks/hooks-cursor.json`)。看板 / 校验器 / 规范本身是 agent-agnostic 的 —— 就是 markdown skill + Python CLI;只是 skill 在不同 harness 上的分发机制不同。

如果你想给某个 harness 打包,欢迎开 issue 或 PR。

## 基本工作流

1. **让 agent 搭 cockpit** —— "给这个项目装 docs-cockpit"。build skill 的 Phase 0 扫一下仓库的文档布局、写好配置、跑第一次 render。老项目里 `docs/plans/` `docs/adrs/` `docs/RFC/` 已经写一堆的情况下,走 migrate 流程 —— 默认 dry-run 把"打算把谁移到哪"先讲清,你确认后才 `git mv` + 注入 frontmatter 脚手架。

2. **在对话里建关联** —— "关联模块和文档"、"规划整个项目的 spec"。build skill 发现全部文档,*带着证据*提出模块 ↔ 子任务 ↔ 文档段落的关联建议,写入前对每个 anchor 做 dry-run 验证,拿不准就问你而不是猜。缺失的 plan / spec 文档按 `references/schema.md` 起草 —— frontmatter 一次写对、放到正确路径(`docs/plans/YYYY-MM-DD-<id>-plan.md`)、`docs:` 链接回填到源模块。

3. **渲染看板** —— "重新生成 dashboard" 或 `docs-cockpit render`。浏览器开 `docs/index.html`,模块 Kanban 渲染,点任意卡片 → 抽屉显示 desc / status 选择器 / progress 滑块 / 子任务清单 / 关联文档,关联文档支持**抽屉内联 MD 预览**(marked.js 在抽屉里直接渲染 —— 不再跳出看 file:// 原文)。

4. **跟踪状态靠问** —— "哪些卡了"、"M1.2 sprint 进度"。rebuild skill 的 Phase 1 读 `state.json`,出表格 / 列表 / 可直接粘贴的 Markdown。纯状态查询到此为止 —— 不动任何文件。

5. **重构后刷新** —— "anchor 失效了"、"spec 改了同步关联"。rebuild skill 诊断漂移(lint + 对每个 anchor 做 dry-run 验证),只重新推理坏掉的链接,仍然准确的一概不动。

6. **Commit 前 lint** —— "校验 frontmatter"。每条 issue 都可操作:

   ```
   ❌ M07.md · id: missing required field — module won't appear in dashboard
      💡 fix: add `id: M07` to frontmatter
      📚 references/schema.md · frontmatter schema (required fields)
   ```

   三档 severity:`error`(根本不会渲染)· `warn`(渲染但状态错)· `hint`(锦上添花 · 影响 copy-prompt 上下文质量)。

7. **升级** —— "升级 docs-cockpit"。一条命令检测安装后端、对比 CLI + plugin 两层版本、拉 CHANGELOG diff、让你确认,如果 skill 层变了就原子清 cache + 提示重启。

## 安装后你得到了什么

### 看板功能

- **模块 Kanban + KPI strip** —— 5 列状态 · 点卡片 → split-view 抽屉显示 desc / status 选择器 / progress 滑块 / 子任务清单(每条 subtask 带 anchor 按钮 + Copy prompt)/ 关联文档 · localStorage 持久化 + build-time-aware 自动失效
- **Sprint Timeline** —— 模块按 sprint 分组 + 平均进度
- **Backlog 视图** —— `#/backlog` hash route · 跨模块扁平 subtask 清单 · 4 维筛选(时间 / 版本 / 状态 / 搜索)· URL state codec · 可分享链接
- **多选 bundle** —— 每 subtask 一个 checkbox · shift-click 范围选 · "全选当前" · 按状态快速加 · 底部 floating bar → Copy bundle prompt(覆盖所有已选 subtask 的可直接粘贴提示词)
- **Concept Grid** + **System Docs 抽屉** —— 精挑的系统级文档(CLAUDE.md / PRD / DESIGN / RFC / memory / roadmap)一键直达
- **Body 自动抽取** —— `## 待办` / `## TODO` → subtasks · `## 关联` / `## Related` → `docs:` · checklist 行可带 `@code:` / `@docs:` anchor
- **抽屉内联 MD 预览** —— 点关联文档 / code anchor / doc anchor · marked.js + highlight.js 在右栏渲染 · slice 信息徽章显「📍 Showing lines X-Y of <file>」
- **空 docs · 复制提示词 CTA** —— `Plan` / `RFC` / `Spec` 三个 tab · 提示词原文展示 · 单 Copy 按钮 · 粘贴到你的 AI 助手
- **needs-docs kanban chip** —— active 状态但无 docs 的模块在卡片上挂提示 chip
- **Frontmatter 校验器** —— 结构化 `error` / `warn` / `hint` · 含修法建议 · 每条都指向 `references/schema.md` 的具体段落
- **双语 UI** —— 顶栏 `[EN] [中]` 切换 · localStorage 持久化
- **树形浏览器**(`browse`)—— 侧边栏镜像目录结构 · 搜索 + 折叠 + 上次查看记忆 · marked.js + highlight.js 渲染

### Skill 层

Plugin 一共发布三个 skill,外加一个它们按需阅读的知识层:

- `skills/use-docs-cockpit/` —— 入口路由,由 SessionStart hook 随会话启动注入(条件注入:只在带 `docs-cockpit.yaml` 的项目里)
- `skills/docs-cockpit-build/` —— 7-phase 关联构建工作流(cockpit 搭建 + build 排障也归它,在 Phase 0)
- `skills/docs-cockpit-rebuild/` —— 5-phase 漂移诊断 + 刷新工作流(状态问答也归它,在 Phase 1)
- `references/schema.md` —— frontmatter + anchor 字段规范(每条校验 issue 引用的 SSOT)
- `references/association-method.md` —— 4 个原子关联方法(发现 / 推理 / dry-run 验证 / 高亮)
- `references/operations.md` —— bootstrap / 配置 / 升级 / 排障 runbook

没有 MCP server:自 v1.0 起 agent 接口**就是** skill 本身 —— agent 阅读 markdown 工作流,跑和你一样的 CLI。(v0.12 引入的 MCP server 已在 1.0 移除。)

### 机器可读 sidecar:`state.json`

每次 render 在 HTML 旁写一份 `docs/state.json`。和看板同一份 payload + 校验器的结构化 `issues[]`。rebuild skill 的 Phase 1 读它出状态叙事;CI 读它做不变式检查(`--strict`);任何外部工具都能消费。Schema 自 0.2.0 起只增不删(加字段 · 不删字段)。

## 哲学

- **认知在 skill,Python 只渲染** —— 关联工作是判断(搜索 · 阅读 · 决策);skill 在对话里和你一起做,CLI 保持确定性。Agent 是接口,CLI 是 runtime。
- **错误的 anchor 比缺失的 anchor 更糟** —— 缺失是诚实的缺口;错误的 anchor 把你带向无关内容,摧毁的是整张看板的可信度。skill 写入前先 dry-run 验证,拿不准就问而不是猜。
- **单文件交付** —— `docs/index.html` 完全自包含 · 无 localhost · 无 build pipeline · 无 JS 框架 · 运行时零网络。可以丢进 Slack DM 也可以 commit 进仓库。
- **Frontmatter 即 schema** —— 每个模块都是人类可读、同时 frontmatter 机器可解析的 markdown 文件。没有私有数据库。
- **一套规范统一一切**(`references/schema.md`)—— schema 写在一份 reference 文档里,AI 和人共读。校验器逐字段引用它。不再每次写文档都问 AI "frontmatter 该填啥"。
- **校验可选但要可操作** —— 每条 `❌` 与 `⚠️` 都带 `💡 fix` 和 `📚 see`。输出可 grep · IDE 能消费 · CI 能用。
- **`file://` 优先** —— 不依赖 webserver。浏览器的 file:// 安全模型就是发布目标。
- **原子升级** —— "清 plugin cache" 和 "提示重启" 压在一步里。Ghost state(CLI 升级后 plugin 仍跑老 SKILL.md)就是这条命令在防的。

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

Body 里的 checklist 可以给每条子任务钉上证据 —— `- [ ] 任务文本 @code:src/worker/fsm.py:42-89 @docs:docs/RFC/004.md#§2.1` —— build / rebuild skill 写入前会对每个 anchor 做 dry-run 验证。

完整规范见 [`references/schema.md`](references/schema.md)。规范覆盖 "docs vs subtasks 决策"、anchor 语法、文件命名约定、status × progress 不变式、跨文档引用规则。

## 升级

让 agent 升级即可 —— "升级 docs-cockpit"。路由把升级类请求直接分发给 `docs-cockpit upgrade` CLI:检测后端 · 对比版本 · 显示 CHANGELOG diff · 让你确认 · 跑升级,如果 skill 层变了就原子清 cache + 提示重启。`/docs-cockpit:update` slash 命令是同一流程的显式入口。

## 贡献

这是一个开源项目 —— 任何大小的贡献都欢迎。开发环假定你在改 docs-cockpit 本身(不是单纯使用):

```bash
git clone https://github.com/Guohao1020/docs-cockpit
cd docs-cockpit
pip install -e .              # editable 安装(Python 3.10+)
python -m pytest tests/ -q    # 253 个测试(unit + integration)
docs-cockpit render -c docs_cockpit/examples/minimal.yaml --debug
```

**动手前先看 [CLAUDE.md](CLAUDE.md)** —— 涵盖架构、SemVer 约定、语言约定、本仓库容易踩的坑。

新增 skill 时,参考现有三个的写法(`skills/*/SKILL.md`)—— frontmatter 的 `description` 是"pushy"路由(宁可过度触发也别欠触发 · 并点名负例该交给哪个兄弟 skill)· body 解释 **why** 而不只列 **what** · 文件命名 + 段落结构对齐 canonical-skill 风格。

涉及实质性改动(新功能 / schema 变更 / breaking change)先开 issue。Bug fix 和文档改进可以直接 PR。

## License

MIT · 见 [LICENSE](LICENSE)。

## 社区

- **落地页:** <https://guohao1020.github.io/docs-cockpit/>
- **Issues:** <https://github.com/Guohao1020/docs-cockpit/issues>
- **Release notes:** [CHANGELOG.md](CHANGELOG.md)
- **贡献者架构文档:** [CLAUDE.md](CLAUDE.md)
- **Skill-first pivot 规格:** [`docs/plans/P-skill-first-pivot.md`](docs/plans/P-skill-first-pivot.md)
- **Sync workflow:** [`references/sync_status_workflow.md`](references/sync_status_workflow.md)
- **Frontmatter 规范 (SSOT):** [`references/schema.md`](references/schema.md)
