[English](README.md) · **中文**

# docs-cockpit

把一个文件夹的项目 markdown 变成单文件 HTML 的 **Kanban 看板** + **树形侧边栏阅读器**，浏览器 `file://` 直接打开。Frontmatter 驱动 · 自带 schema 校验 · 与 AI 编辑器协同。同时以**独立 Python CLI** 与 **Claude Code 插件**两种形态发布(3 个自动触发的 skill + 6 个 slash 命令)。

> 一条命令为任何项目搭一个 docs cockpit。模块自动汇成 Kanban + Sprint Timeline + KPI 条 + 模块抽屉(状态 / 进度 / 子任务 / 关联文档)。Frontmatter 校验器会精确告诉你缺什么、怎么改。当某模块还没写关联文档时,抽屉里的 CTA 会即时生成一段可直接粘贴给 AI 编辑器(Claude Code / Cursor / Codex / Continue / Aider …)的提示词,让它替你写 plan / RFC / spec。

## Quickstart

### 作为 Claude Code 插件(推荐 · 60 秒)

```bash
# 在 Claude Code 里
/plugin marketplace add Guohao1020/docs-cockpit
/plugin install docs-cockpit@docs-cockpit
```

3 个 skill 会按自然语言意图自动触发,6 个 slash 命令提供显式入口:

```
/docs-cockpit:build     # 生成 docs/index.html
/docs-cockpit:browse    # 生成 docs/browse.html(树形侧边栏 MD 阅读器)
/docs-cockpit:migrate   # 一键迁移老布局
/docs-cockpit:status    # 从 state.json 出叙事性 standup 报告
/docs-cockpit:lint      # 按 author 规范校验 frontmatter
/docs-cockpit:update    # 转交给 `docs-cockpit upgrade` CLI
```

### 作为独立 CLI(不用 Claude Code)

挑你已经在用的安装方式(需 Python 3.10+):

```bash
# uv(推荐 · 自动隔离 Python 版本)
uv tool install --python 3.11 git+https://github.com/Guohao1020/docs-cockpit.git

# pip
pip install git+https://github.com/Guohao1020/docs-cockpit.git

# pipx
pipx install git+https://github.com/Guohao1020/docs-cockpit.git
```

然后:

```bash
cd your-project
docs-cockpit init          # 写一份最小 docs-cockpit.yaml
docs-cockpit build         # 生成 docs/index.html + docs/state.json
open docs/index.html       # Windows 用 start · Linux 用 xdg-open
```

## 它怎么工作

把 `docs-cockpit` 指向项目里的 YAML 配置,它会遍历你列出的 `modules/` 和 `concepts/` 目录。每个 markdown 文件的 YAML frontmatter(`id` / `status` / `sprint` / `progress` / `desc` / `subtasks` / `docs:` ……)被读出来,渲染成一张卡。Build 把这些数据序列化为 JSON · 嵌入 HTML 模板 · 写出一个独立单文件,浏览器 `file://` 直接打开 —— 不需要 localhost · 不需要静态站点生成器 · 不需要 JS 框架 · 运行时零网络请求。

`docs-cockpit build` 同时产出两个文件:`docs/index.html` 给人看 · `docs/state.json` 给工具用(skill 用它出叙事状态 · CI 用它做不变式检查)。`state.json` 里还有 **frontmatter 校验器**输出的结构化 `issues[]` —— 每条 issue 精确指向字段名 · 给出修法建议 · 引用统一规范 **docs-cockpit-author** 里的具体段落。

当一个模块还没填 `docs:` 时,抽屉会出一个**复制提示词的 CTA**:在 `Plan` / `RFC` / `Spec` 三个 tab 间切换 · 看清楚替换好 id / title / status / sprint / desc / body 摘要的整段提示词 · 然后一键复制粘贴到你常用的 AI 编辑器。提示词本身引用 docs-cockpit-author 规范,所以 AI 写出来的 frontmatter 下次 build 就会被看板接住。

## 基本工作流

1. **Bootstrap** —— `docs-cockpit init`,或对老项目(`docs/plans/` `docs/adrs/` `docs/RFC/` 已经写了一堆)用 `docs-cockpit migrate`。migrate 默认 dry-run · 把"打算把谁移到哪"先打印出来 · 加 `--apply` 才真 `git mv` + 注入 frontmatter 脚手架。

2. **写文档**遵循 **docs-cockpit-author** skill(规范源头):必填字段 · status enum · status × progress 不变式 · 文件命名 · "docs 与 subtasks 怎么区分" · 跨文档引用规则 —— 都在一处。让 Claude 写 plan / RFC / spec / 模块 MD 时,这个 skill 自动接管。

3. **Build 看板** —— `docs-cockpit build`。浏览器打开 `docs/index.html`。模块 Kanban 渲染出来 · 点任意卡片 → 抽屉显示 desc / status / progress 滑块 / 子任务清单 / 关联文档,关联文档支持**抽屉内联 MD 预览**(marked.js 在抽屉里直接渲染 · 不再跳出去看 file:// 原文)。

4. **跟踪状态** —— 直接问 Claude 自然语言("有什么 blocker" · "M1.2 进度怎么样" · "给我一份周报")。`docs-cockpit-standup` skill 读 `state.json` 出表格 / 列表 / 可直接粘贴的 Markdown 报告。**契约上只读** · 永远不改文件。

5. **Commit 前 lint** —— `docs-cockpit lint` 只校验不重 build。输出是结构化的:

   ```
   ❌ M07.md · id: missing required field — module won't appear in dashboard
      💡 fix: add `id: M07` to frontmatter
      📚 see: docs-cockpit-author · §2.1 required frontmatter
   ```

   三档 severity:`error`(根本不会渲染)· `warn`(渲染但状态错)· `hint`(锦上添花 · 影响 copy-prompt 上下文质量)。`--json` 给 IDE / CI · `--strict-warn` 把 warn 也升级成 error 退出。

6. **升级** —— `docs-cockpit upgrade`。一条命令检测后端(pip / uv / pipx / editable)· 对比 CLI + plugin 层版本 · 拉 CHANGELOG diff · 让你确认 · 跑对应升级命令 · 如果 plugin SKILL.md 变了 · 原子清缓存 + 提示重启。彻底消除"忘了重启 → ghost state"问题。

## 安装后你拿到了什么

### Skills(自动触发)

| Skill | 作用 | 读 vs 写 |
|---|---|---|
| **`docs-cockpit`** | 搭建 + 维护 cockpit · 跑 `build` / `migrate` / `browse` / `upgrade` | 写配置 + HTML + 跑 CLI |
| **`docs-cockpit-author`** (0.9.0 新增) | 写一份 module / concept / plan / RFC / spec 的规范源头 —— frontmatter schema · body 约定 · 文件命名 · 跨文档引用 | 写单个项目文档 |
| **`docs-cockpit-standup`** (0.9.0 从 `-status` 重命名) | 读 `state.json` 输出叙事状态报告 · sprint 进度 · blocker · 周报 | 只读 |

### Slash 命令

```
/docs-cockpit:build       从 YAML 配置 build 看板
/docs-cockpit:browse      生成树形侧边栏 MD 阅读器
/docs-cockpit:migrate     迁移老布局(docs/plans/ · docs/adrs/ …)到 canonical
/docs-cockpit:status      叙事状态 / standup 报告
/docs-cockpit:lint        只校验 frontmatter 不 build
/docs-cockpit:update      转交 `docs-cockpit upgrade` CLI
```

### CLI 子命令

```
docs-cockpit init         脚手架 docs-cockpit.yaml
docs-cockpit build        build 单文件看板 + state.json
docs-cockpit browse       生成树形侧边栏 MD 阅读器
docs-cockpit migrate      迁移老布局(默认 dry-run · --apply 才真改)
docs-cockpit lint         校验 frontmatter(--json · --strict-warn)
docs-cockpit upgrade      一条命令升级 CLI+plugin(--dry-run · --yes)
```

### 看板功能

- **模块 Kanban** —— 5 列状态 · 点卡片 → 抽屉显示 desc / status 选择器 / progress 滑块 / 子任务清单 / 关联文档 · localStorage 持久化覆盖
- **Sprint Timeline** —— 模块按 sprint 分组 + 平均进度
- **Concept Grid** + **System Docs 抽屉** —— 精挑的系统级文档(CLAUDE.md / PRD / DESIGN / RFC / memory / roadmap)一键直达
- **Body 自动抽取** —— `## 待办` / `## TODO` checklist 自动变 subtasks · `## 关联` / `## Related` 链接列表自动变 `docs:` · frontmatter 不用写重复
- **子任务 → 自动进度** —— `manualProgress: false` 时从子任务完成比例自动算
- **抽屉内联 MD 预览** (0.7.1+) —— 点关联文档 · marked.js + highlight.js 在抽屉里直接渲染 · "返回模块" 一键回卡片视图
- **空 docs · 复制提示词 CTA** (0.8.0+ · 0.9.0 重做) —— `Plan` / `RFC` / `Spec` 三个 tab · 提示词原文展示 · 单 Copy 按钮 · 粘贴到 Claude Code / Cursor / Codex / Continue / Aider
- **needs-docs kanban chip** —— active 状态但无 docs 的模块卡片右上挂 amber chip · 一眼看出谁要补
- **Frontmatter 校验器** (0.9.0+) —— 结构化 `error` / `warn` / `hint` · 含修法建议 + 规范引用 · 每条 issue 都指向 `docs-cockpit-author` 的具体段落
- **双语 UI** —— 顶栏 `[EN] [中]` 切换 · 默认 EN · localStorage 持久化
- **树形浏览器** (`docs-cockpit browse`) —— 侧边栏镜像目录结构 · 搜索 + 折叠 + 上次查看记忆 · marked.js + highlight.js 渲染

### 机器可读 sidecar:`state.json`

每次 build 在 HTML 旁写一份 `docs/state.json`。和看板同一份 payload + 校验器的 `issues[]`。`docs-cockpit-standup` skill 读它出叙事 · CI 读它做不变式检查。Schema 自 0.2.0 起稳定(只加字段 · 不删字段)。

## 哲学

- **单文件交付** —— `docs/index.html` 完全自包含 · 无 localhost · 无 build pipeline · 无 JS 框架 · 运行时零网络。可以丢进 Slack DM 也可以 commit 进仓库。
- **Frontmatter 即 schema** —— 每个模块都是人类可读、同时 frontmatter 机器可解析的 markdown 文件。没有私有数据库。
- **一套规范统一一切** (`docs-cockpit-author`) —— schema 写在一个 skill 里 · Claude 和人共享这份文档。校验器逐字段引用它。**不再每次写文档都问 Claude "frontmatter 该填啥"**。
- **校验可选但要可操作** —— 每条 `❌` 与 `⚠️` 都带 `💡 fix` 和 `📚 see`。输出可 grep · IDE 能消费 · CI 能用。
- **`file://` 优先** —— 不依赖 webserver。浏览器的 file:// 安全模型就是发布目标。
- **原子升级** —— `docs-cockpit upgrade` 把"清 plugin cache"和"提示重启"压在一步里。Ghost state(CLI 升级后 plugin 仍跑老 SKILL.md)就是这条命令在防的。
- **跨平台** —— 纯 Python 3.10+ + `pyyaml`。同一份 YAML 在 Windows / macOS / Linux 跑出同一份 HTML。

## 项目结构

```
your-project/
├── docs-cockpit.yaml              ← 配置(你写 · `init` 给脚手架)
├── docs/
│   ├── index.html                 ← BUILD 产物 · 看板(给人看)
│   ├── browse.html                ← BUILD 产物 · 树形侧边栏阅读器(可选)
│   ├── state.json                 ← BUILD 产物 · 机器可读 payload + issues[]
│   ├── spec/
│   │   ├── module/M01-*.md        ← 模块规范(frontmatter → Kanban 卡)
│   │   └── concept/C01-*.md       ← 概念规范(frontmatter → Concept Grid)
│   ├── plans/2026-MM-DD-<id>-plan.md   ← 执行计划(通过 `docs:` 关联回模块)
│   ├── RFC/<NNN>-*.md             ← 技术决策
│   └── PRD.md                     ← 作为 `system_docs` 条目展示
├── CLAUDE.md                       ← 作为 `system_docs` 条目展示
└── .git/
```

## 最小 `docs-cockpit.yaml`

```yaml
project:
  name: MyProject
  mark: M                          # 单字符 wordmark
  tagline: "模块进度 + sprint 追踪"
  output: docs/index.html

paths:
  repo: "."                        # 还可用 {home} / {env:VAR} / {main_repo}

system_docs:
  - { id: claude-md, title: CLAUDE.md, path: "{repo}/CLAUDE.md",  desc: "AI 协作约定", icon: memory }
  - { id: prd,       title: PRD.md,    path: "{repo}/docs/PRD.md", desc: "产品需求文档", icon: doc }

modules:
  scan:
    dir: "{repo}/docs/spec/module"
    title_transform: prefix-dot-titlecase

concepts:
  scan:
    dir: "{repo}/docs/spec/concept"
    title_transform: prefix-dot-titlecase
```

## Frontmatter(看板读的就是这块)

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

完整规范见 `docs-cockpit-author` skill —— 含 "docs vs subtasks 决策" · 文件命名约定 · status × progress 不变式 · 跨文档引用规则。

## 升级

```bash
docs-cockpit upgrade
```

整条流(0.7.0+)。后端检测 · 版本对比 · CHANGELOG diff · 让你确认 · 跑升级命令 · 如果 plugin SKILL.md 变了 · 原子清 cache + 提示重启。`--dry-run` 看计划 · `--yes` 非交互。

## 与 AI 编辑器协同

空 docs CTA 生成的提示词支持以下主流编辑器:

- **Claude Code** + **[superpowers](https://github.com/obra/superpowers)** —— 它的 `/plan` `/spec` `/rfc` skill 出脚手架 · 之后 docs-cockpit-author 对齐 frontmatter
- **Claude Code** + **gstack** —— 它的 plan / spec / rfc 生成器同样接得上
- **Cursor / Codex / Continue / Aider** —— 把复制好的提示词粘进 chat · 编辑器把文件写出来

不管走哪条 · AI 写完后,`docs-cockpit lint` 都是"这文件能不能正确渲染"的唯一真相。

## 贡献

欢迎 PR。开发环：

```bash
git clone https://github.com/Guohao1020/docs-cockpit
cd docs-cockpit
pip install -e .              # editable 安装
docs-cockpit build -c docs_cockpit/examples/minimal.yaml --debug
```

新增 skill 时,参考现有三个的写法(`skills/docs-cockpit*/SKILL.md`)—— frontmatter 的 `description` 要"pushy"(宁可过度触发也别欠触发)· body 解释 **why**,而不是只列 **what**。

## License

MIT · 见 [LICENSE](LICENSE)。

## 社区

- Issues: <https://github.com/Guohao1020/docs-cockpit/issues>
- Release notes: [CHANGELOG.md](CHANGELOG.md)
