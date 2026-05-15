# CHANGELOG

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) · 版本号采用 [SemVer](https://semver.org/lang/zh-CN/)。

## [Unreleased]

## [0.6.1] · 2026-05-15

修 update skill 的实战盲点 · "清缓存 + 重启" 之前是两个独立 Step · 用户实测
清完没立即重启 → 进入 ghost state(plugin Directory 显示已装 · 但 sidebar 消失 ·
reinstall 报"已安装")。

### Fixed

- **`docs-cockpit-update` SKILL.md + `commands/update.md` 加 atomic 规则**:
  - 原 Step 6(清缓存)和 Step 7(重启)合并为 **Step 6+7 · atomic**
  - 加 ⚠️ **HARD RULE** banner:cache clear 和 restart 必须连着做 · 中间不能停
  - 解释 ghost state 成因:Claude Code 的 plugin 状态有 in-memory sidebar 和
    settings.json registry 两个来源 · 清缓存 + 不重启 = 两边发散
  - "Right way to phrase to the user" 段:让 Claude 把两步打包成一句话给用户 ·
    避免用户在中间暂停

- **新增 "Ghost state recovery" 整段**:
  - 症状清单(Directory 有 / sidebar 没 / reinstall 报"已安装")
  - 3 步恢复路径(restart → uninstall + restart → 手工删 settings.json 条目)
  - 写明 "prevent" 节 · 告诉 Claude 怎么从源头避免

- **`Don't do these things`** 节加新条:
  > Don't separate cache clear from restart in time — Step 7+8 is ONE atomic
  > action. If user pauses between, they get ghost state.

### Why this matters

之前 SKILL.md 的 Step 6 / Step 7 是两段 · Claude 给用户时也是两条命令分发 ·
用户清完缓存忙别的去了 · 半小时后再重启 → ghost state。0.6.1 把它绑死成
**一个原子操作** · Claude 不能拆开告诉用户。

### Migration · 0.6.0 → 0.6.1

无 breaking · 现有产出 + 配置全不变。这版纯文档 / skill 加固。

```bash
# 升 CLI(可选 · 0.6.0 → 0.6.1 没代码差异 · 只是文档)
pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git

# 强清 plugin cache + 立即重启 Claude Code(0.6.1 的 atomic rule)
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\plugins\cache\*docs-cockpit*" -ErrorAction SilentlyContinue
# ⬆ 跑完立即退 Claude Code 重开 · 不要拖延
```

## [0.6.0] · 2026-05-15

加 i18n 多语言切换 · 默认英文 · 顶部 toggle 切中文。dashboard 和 browse
两个产出都支持。

### Added

- **顶部语言切换器** `[EN] [中]`:
  - 位置:dashboard topbar 右上 / browse topbar 右上 · 一致
  - 样式:深色方块 toggle · active 用 ink 底白字 · `font-family: var(--f-mono)`
  - 默认 lang: **EN**(0.5.x 默认是中文)
  - 切换记 localStorage(`<storage-key>::lang`)· 跨会话持久化
- **完整 i18n 字典**:
  - dashboard 60+ 个 key · en/zh 双语 · 覆盖 topbar / hero / KPI / Kanban /
    Sprint / Concept / Module Drawer / SystemDocs Drawer / Toast / Status labels
  - browse 6 个 key · 覆盖 topbar / search / empty state / CDN banner
- **新 i18n 基础设施**(两个 template 都加):
  - `I18N = { en: {...}, zh: {...} }` JS 字典
  - `t(key, vars)` 函数 · 支持 `{n}` 占位
  - `applyI18nStatic()` 扫所有 `data-i18n` / `data-i18n-placeholder` /
    `data-i18n-title` / `data-i18n-aria` 节点 · 注入对应文本
  - `STATUS_LABEL` 改成 Proxy · 老 `STATUS_LABEL[s]` bracket 访问无需改 · 自动
    走当前 LANG
  - 切换时同步 `<html lang>` 属性
- **dynamic JS render 全 i18n 化**:
  - renderKpi / renderKanban / renderSprints / renderConcepts / renderProject
    Meta / renderSystemDocs / openModuleDrawer 全部用 `t()`
  - toast 消息("Status updated" / "Progress set to 80%")用 `t()` + 变量插值

### Changed

- `<html lang="zh-CN">` → `<html lang="en">`(默认)· JS 切换时改为 `zh-CN`
- 静态 HTML fallback 文本全部翻成英文 · ZH 切换由 JS 注入

### 实测

dashboard build 验证 9/9 关键检查通过:
- I18N 字典 en/zh 各 60+ 条
- 24 个 `data-i18n` 静态 attr
- STATUS_LABEL Proxy 模式 · 老代码无需改
- 124 个 i18n 条目(en + zh 合计)
- 0 个 Chinese leak in JS render literals

### Migration · 0.5.0 → 0.6.0

无 breaking · 现有 build / browse / migrate / state.json 全不变。

```bash
pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git
rm -rf ~/.claude/plugins/cache/*docs-cockpit*    # POSIX 强清 cache
# Windows: Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\plugins\cache\*docs-cockpit*"
# 重启 Claude Code
```

升完跑一次 `docs-cockpit build` · 打开 HTML · 右上角看到 `[EN] [中]` toggle ·
点切换中英文。同样适用 `docs-cockpit browse` 的产出。

## [0.5.0] · 2026-05-15

加 `docs-cockpit browse` 命令 + `/docs-cockpit:browse` slash command · 单 HTML
markdown 浏览器 · 树形侧边栏 + marked.js 渲染。解决"项目 ADR/plan 散落 MD
不进 dashboard 但用户想读"的痛点。

### Added

- **`docs-cockpit browse` CLI**:
  ```
  docs-cockpit browse                    # 默认扫:项目 + ~/.claude/{plans,projects}
  docs-cockpit browse --dir docs/adrs    # 限定扫某子目录(可多次)
  docs-cockpit browse --no-claude        # 跳过 ~/.claude 扫描
  docs-cockpit browse -o docs/browse.html
  docs-cockpit browse --project Bastion  # 显示在 topbar
  ```
- **`/docs-cockpit:browse` slash command**:Claude 直接触发 · 适合"我想读这
  个项目所有文档"的需求。
- **新模板 `docs_cockpit/templates/browse.html.tmpl`**:
  - **树形侧边栏**:按目录嵌套展示 · 文件夹可折叠 · 折叠状态 localStorage
    持久化
  - **多 root 区分**:项目 root / project docs/ / ~/.claude/plans/ /
    ~/.claude/projects/memory/ 各自一个 section · 标签 + 路径 + 文件数
  - **主区渲染**:marked.js + highlight.js 9 种语言(py/js/ts/bash/yaml/
    json/markdown 等)+ GFM table + blockquote 样式
  - **搜索**:`/` 或 `k` 聚焦搜索框 · 实时过滤文件路径
  - **localStorage**:记上次看哪个文件 + 哪些文件夹展开
- **`docs_cockpit/browse.py`**:扫 + 启发式分组 + payload 序列化。

### 默认扫描覆盖

| Root | 路径 | 说明 |
|---|---|---|
| `project-root` | `<repo>/` 顶层 *.md | README, CLAUDE.md, CHANGELOG 等 |
| `project-docs` | `<repo>/docs/` 递归 | 项目所有文档 |
| `claude-plans` | `~/.claude/plans/<project-name>/` | Claude session plan 笔记 |
| `claude-memory` | `~/.claude/projects/<sanitized-cwd>/memory/` | Claude session memory 沉淀 |

`--no-claude` 跳过最后两条 · `--dir` 完全自定义。

### 实测 · Bastion docs/adrs/

```
docs-cockpit browse --repo D:/shulex_work/bastion --dir docs/adrs
→ 13 files · 1 root · HTML 113 KB
→ 浏览器开 docs/adrs.html · 左侧 13 个 ADR 整齐排列 · 点开右侧 marked.js
  渲染 · localStorage 记上次看哪个
```

### Why this matters

之前的产品只解决"frontmatter-driven 模块 dashboard"(0.2.0+)· 但用户实际
需求覆盖更广:

- ADR(架构决策记录)· 没 frontmatter · 大段长文本 · 需要读
- Plan / Roadmap · 没 frontmatter · 大段长文本 · 需要读
- ~/.claude/plans / memory · Claude 攒下的笔记 · 想集中读

这些都**不适合 dashboard** · 但需要**单 HTML 浏览器**。0.5.0 补齐这块。

### Migration · 0.4.x → 0.5.0

无 breaking · 现有 dashboard 输出 + 配置不变。

```bash
# 升 CLI
pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git
# 或 uv tool upgrade docs-cockpit

# 强清 plugin 缓存(沿用 0.3.1 的标准流程)
rm -rf ~/.claude/plugins/cache/*docs-cockpit*    # POSIX
# Windows: Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\plugins\cache\*docs-cockpit*"
# 重启 Claude Code

# 试新命令
docs-cockpit browse                              # 当前项目
```

### Package update

- `pyproject.toml package-data` 加 `templates/*.html`(以前只有 `*.tmpl`)·
  确保 wheel 装出来也带 browse 模板。

## [0.4.0] · 2026-05-15

加 MD body 自动 fallback 提取 · 解决"老项目用 body 写 `## 待办` checklist
但 frontmatter 没 subtasks 字段 · dashboard drawer 显示空"的痛点。

### Added

- **`extract_subtasks_from_body(body)`**:扫 H2 section 标题匹配 `(待办|TODO|
  To-do|Subtasks|Tasks|任务)` · 在该 section 下提取 `- [x]` / `- [ ]`
  checklist 项作 subtasks(完成标 done: true)。section 在下一 H1-H6 /
  `---` 分隔线终止。
- **`extract_docs_from_body(body)`**:扫 H2 section 标题匹配 `(关联(文档)?|
  Related(docs)?|Docs?|See also|参考|链接|Links?)` · 提取该 section 下的
  MD link `[title](path)` 作 docs。锚点链接 `#xxx` 跳过。
- **`_build_card` body 兜底**(0.4.0):当 frontmatter 缺 subtasks/docs 时 ·
  自动从 body 提取填充。frontmatter > body 优先级。`desc` 字段不参与 body
  提取(body 首段往往是引用 / metadata · 不可靠)。
- **`docs-cockpit migrate _inject_frontmatter` body 提取**:迁移时同样跑 body
  提取 · 把 subtasks / docs **写进** frontmatter · 让迁移后 frontmatter
  成为 source of truth。

### Why this matters

之前的 dashboard drawer 严格依赖 frontmatter 字段 · 实战中:

- Sourcery / Bastion 这种老项目 · MD body 已经用 `## 待办` 写好 checklist
- 让用户**再复制一份**到 frontmatter 是重复维护 · 不合理
- 而且用户经常忘改 · 或两份不同步

0.4.0 让 docs-cockpit "更智能":frontmatter 没写就**自动读 body** · 用户什么
都不用做 dashboard drawer 就能显示 checklist 和关联文档。想精控就显式写
frontmatter 接管。

### 实测 · Sourcery

- 24 个 module MD · 之前 dashboard drawer 全部"无子任务"
- 0.4.0 build · **24/24** 自动捞到 3 个 subtask(各自的 `## 3 · 待办` 段)
- `docs: 0`(Sourcery MDs 没 `## 关联` section · 符合预期 · 不强造)

### Bug fix

- 移除 `_build_card` 老的"frontmatter only" 行为不变 · 但去除了不必要的
  manualProgress check 边界 case。

### Migration · 0.3.x → 0.4.0

无 breaking change · 现有 frontmatter / state.json / template 全不动。

升级即得益:
```bash
pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git
# 或 uv tool upgrade docs-cockpit

# Plugin 层强清缓存 + 重启
rm -rf ~/.claude/plugins/cache/*docs-cockpit*    # POSIX
# Windows: Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\plugins\cache\*docs-cockpit*"
# 然后退出 Claude Code 重开
```

升完跑一次 `docs-cockpit build` · 模块卡的 drawer 应该开始显示 subtasks。

## [0.3.1] · 2026-05-15

修升级 skill 的实战盲点 · 用户实测 0.2.0 → 0.3.0 时,CLI 升上去了但 plugin 层
没跟上(autoUpdate: true + 重启 Claude Code 不够 · plugin 缓存依然显示 0.2.0)。

### Fixed

- **`docs-cockpit-update` SKILL.md + `commands/update.md` 加 cache 强清 + 多
  backend 检测**:
  - **新 Step 4(CLI 升级)** · 自动检测 install backend(pip / uv tool / pipx)·
    Python < 3.10 自动切 `uv tool install --python 3.11 --force git+...`
    回退路径,不再盲目假设 pip 能跑。
  - **新 Step 6(强清 plugin 缓存)** · 重启前主动跑
    `rm -rf ~/.claude/plugins/cache/*docs-cockpit*` · 不再相信 autoUpdate ·
    cache 没了 · 重启时被迫从 GitHub 重新 fetch。
  - **新 Step 8(用户侧验证)** · 明确告诉用户 restart 后检查:`/plugin`
    UI 的 version 字段 + Skills 列表里 `/docs-cockpit:migrate` 是否出现(0.3.0+
    的标志性 slash command)· 若还是老版本 → 跑兜底 `/plugin marketplace
    remove docs-cockpit && /plugin marketplace add Guohao1020/docs-cockpit`
    强制 remove+re-add。

### Why this matters

0.2.x 升级到 0.3.0 的"plugin 升级失败"是真实 reproducible 的:
- autoUpdate: true 已开 · 重启完 plugin 依然 0.2.0
- 用户必须手动 remove + re-add marketplace 才能拿到 0.3.0

0.3.1 的 update skill 现在**默认就替你做这事** · 不用等用户发现升级没成功
来回排查。

### Migration · 0.3.0 → 0.3.1

无 breaking · 配置 / state.json / template 全不变。直接升:

```bash
# 任一 backend 都能升
pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git
# 或
uv tool upgrade docs-cockpit
```

升完后**强清 plugin 缓存**(0.3.1 新流程):

```bash
# POSIX
rm -rf ~/.claude/plugins/cache/*docs-cockpit*

# Windows PowerShell
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\plugins\cache\*docs-cockpit*"
```

重启 Claude Code · 验证 plugin 升到 0.3.1(`/plugin` UI 看 version)。

## [0.3.0] · 2026-05-15

新增 `docs-cockpit migrate` 命令 · 解决"非 canonical 布局的现有项目怎么 bootstrap"
的痛点。无 breaking change · 老用户照常用。

### Added

- **`docs-cockpit migrate` CLI**:扫现有项目的散落 MD(`docs/plans/` /
  `docs/adrs/` / `docs/superpowers/plans/` / `docs/PRD/` 等)· 启发式分类
  + 生成 frontmatter + `git mv` 到 `docs/spec/module/M{NN}-{slug}.md`
  canonical 布局 + 写出 tailored `docs-cockpit.yaml`。dry-run by default ·
  `--apply` 才真改。`--keep-originals` 复制不动。
- **`/docs-cockpit:migrate` slash command**:显式触发上面那个 workflow ·
  Claude 强制先 dry-run → 给用户看 plan → 等确认 → 才 --apply。
- **`docs_cockpit/migrate.py`**:实现文件 · ~330 行 · 含分类启发式表 +
  H1 title 提取 + slug 生成 + frontmatter merge(已有字段优先 · 默认填
  status=not-started / sprint=M0 / progress=0)+ git mv with rename fallback。
- **operational SKILL.md 拆 Bootstrap workflow 为 A.1 / A.2**:
  - A.1:project 已是 canonical → 手写 yaml + 加 frontmatter
  - A.2:project 不是 canonical(legacy 散落布局)→ 用 `docs-cockpit migrate`

### Classification heuristics (migrate)

  modules:    docs/spec/module/, docs/plans/, docs/tasks/, docs/adrs/,
              docs/superpowers/plans/, docs/superpowers/specs/
  concepts:   docs/spec/concept/, docs/concepts/
  system_docs (root files): README.md, CLAUDE.md, AGENTS.md, GEMINI.md,
              PROGRESS.md, CHANGELOG.md, PRE-LAUNCH-CHECKLIST.md,
              dogfood-onboarding.md, DESIGN.md
  system_docs (dirs): docs/PRD/, docs/RFC/, docs/architecture/,
                      docs/DESIGN/, docs/audits/, docs/review/
  icon mapping:  memory(claude/agents/gemini) · design(design/architecture)
                 · plan(plan/roadmap/checklist/rfc/adr) · doc(其他)

### 实测

- Sourcery(已 canonical · 24 modules + 11 concepts + 6 system_docs):
  dry-run 正确识别 + 标 ✓(已有 frontmatter)+ 标 source=target(idempotent)·
  --apply 时 dst.exists() 会全 SKIP · 安全。
- Bastion(legacy · docs/plans/ + docs/adrs/ + docs/superpowers/plans/):
  现在能一键迁 · 之前要手动写 16+ 个 frontmatter。

### Migration · 0.2.x → 0.3.0

无 breaking change。配置 schema / state.json shape / template 都不变。直接升:

```bash
pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git
```

Claude Code plugin 用户重启 Claude Code · 自动重 fetch · 新 `/docs-cockpit:migrate`
slash command 即上线。

## [0.2.1] · 2026-05-15

打包修复 + metadata 同步 · 让 `pip install`(以及 `uv tool install`)装出来的
docs-cockpit 真正能用 `docs-cockpit init` 起 yaml(0.2.0 之前漏 bundle examples)。

### Fixed

- **`examples/` 现在打包进 wheel**:`docs_cockpit/` 目录新增 `examples/` 子目录
  装着 `minimal.yaml` + `full.yaml` · `pyproject.toml` 的 `package-data` 把
  `examples/*.yaml` 显式包含。0.2.0 之前 `docs-cockpit init` 在 pip 装好的
  纯 wheel 环境里(没有 repo 源码)会报 `[ERR] template missing`,现修复。
- **`cmd_init` 路径修正**:从 `<package>/../examples/` 改成 `<package>/examples/`
  (package-relative · pip 装环境也能读到)。

### Changed

- **pyproject.toml 完整重写**:
  - `version` 改成 dynamic · 从 `docs_cockpit.__version__` 读 · 以后只改 `__init__.py` 一处
  - `description` 同步 0.2.0 dashboard 定位(去掉旧 "sidebar + kanban" 措辞)
  - `keywords` 加 `claude-code` / `claude-code-plugin` / `claude-skill` /
    `kanban` / `sprint-tracking` 等高信号 tag · 移除老 `static-site`
  - `authors` / `urls` 用 `Guohao1020` 实际账号(原 `harvey` 占位)
  - `classifiers` Development Status 从 Alpha 升 Beta · Python 加 3.13
  - 加 `Issues` / `Changelog` 两个 project.urls
- **README 文档索引 + skill SKILL.md**:所有指 `examples/*.yaml` 的链接
  改成 `docs_cockpit/examples/*.yaml`(因为 examples 移到了 package 内)。

### Migration · 0.2.0 → 0.2.1

无 breaking change。配置 schema / frontmatter 字段 / state.json 结构都不变。
单纯升级即可:

```bash
pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git
```

Claude Code plugin 用户重启 Claude Code · 自动重 fetch · 即生效。

## [0.2.0] · 2026-05-15

**🚨 Breaking change · 产品转型版本**:从 "项目 MD 文档预览" 转型为 "项目模块进度 dashboard"。

### 转型本质

- **0.1.x**: 把 MD 文档汇总成单 HTML · 侧边栏 + 文档视图 · marked.js 客户端渲染
- **0.2.0**: 把 module / concept frontmatter 卷成单 HTML dashboard · topbar + Hero + KPI strip + Kanban + Sprint Timeline + Concept Grid + System Docs drawer · MD body **不再嵌入** · 只展示 frontmatter 结构化数据

### Added

- **新 UI 范式**:dashboard-first · 侧边栏视图删除 · MD body 不再客户端渲染
- **模块 drawer**:点击 Kanban 卡片弹出 · 含 desc / status select / progress 滑块 / subtask checklist · localStorage 持久化用户覆盖
- **System Docs drawer**:topbar "系统文档" 按钮 · 弹出 curated 入口列表(CLAUDE.md / PRD / DESIGN.md / memory / RFC / roadmap 等)· 每条 `{id, title, path, desc, icon}` 自配 icon
- **Subtasks 自动 progress**:`manualProgress: false` 时按子任务完成率算 · `manualProgress: true` 时用 frontmatter `progress` 字段
- **新 frontmatter 字段**(modules 卡用):`desc` / `docs[]` / `subtasks[]` / `manualProgress`
- **state.json 新 schema**:`{project, systemDocs, modules, concepts, warnings}` · 替代 0.1.x 的 `{groups, cards, kpi, ...}`

### Changed (breaking)

- **配置 schema 大改**:
  - `project.glyph` → `project.mark`
  - `project.subtitle` → `project.tagline`
  - `project.description` 删除
  - 顶层 `groups[]` 删除 · 拆成三个独立 block:
    - `system_docs:` — 手挑常驻入口
    - `modules:` — frontmatter 驱动主 dashboard
    - `concepts:` — 简化卡片(底部 grid)
  - `frontmatter.kanban.*` 全部删除(`card_types` / `kpi_type` / `sprint_order` / `enabled` 都不再需要)
- **build_payload() 重写**:返回 `(payload, warnings)` 二元组 · 不再返 4 元组
- **render_html() 简化**:模板只剩 `__DOCS_JSON__` 一个占位符 · 其他都由 JS 从 JSON 渲染
- **`design.colors.*` override 暂时移除**:CSS 变量改成 `--c-*` namespace · 0.2.x 后续会重新加回 design override

### Migration · 0.1.x → 0.2.0

完整对照见 `references/config_reference.md` 末尾。最小迁移示例:

```yaml
# 0.1.x
project: { name: MyProject, glyph: M, subtitle: Docs preview }
groups:
  - name: Overview
    files:
      - { title: README, path: "{repo}/README.md" }
  - name: Modules
    scan: { dir: "{repo}/docs/spec/module" }
frontmatter:
  kanban: { enabled: true, card_types: [module], kpi_type: module }

# 0.2.0
project: { name: MyProject, mark: M, tagline: "项目进度" }
system_docs:
  - { id: readme, title: README, path: "{repo}/README.md", desc: "项目总览", icon: doc }
modules:
  scan: { dir: "{repo}/docs/spec/module" }
frontmatter: { enabled: true }
```

模块 frontmatter 升级(可选 · 为 dashboard 展示完整):

```yaml
---
id: M07
title: Job-Task FSM
status: in-progress
sprint: M1.2
progress: 45
# ── 0.2.0 新加(可选)─────────
desc: 12 类 FSM 状态机
docs:
  - { title: "Schema 设计文档", path: "docs/design/schemas.md" }
subtasks:
  - { title: "核心实体定义", done: true }
  - { title: "字段校验", done: false }
manualProgress: false
---
```

老的字段(`owner` / `prd_ref` / `depends_on` / `blocks` / `updated_at`)继续支持 · 在 state.json 里仍然导出 · 给 docs-cockpit-status skill 答 blocker / 周报问题用。

## [0.1.3] · 2026-05-14

加 3 个 slash command 作为 skill 的显式调用入口 · 给 power user 一条快速通道。

### Added

- **`commands/build.md`** → 用户输入 `/docs-cockpit:build` 触发 · 显式跑一次 build · 支持 `/docs-cockpit:build configs/preview.yaml` 传配置路径 · 无 config 自动 hand off 给 docs-cockpit skill bootstrap workflow。
- **`commands/status.md`** → 用户输入 `/docs-cockpit:status [问题]` 触发 · 比如 `/docs-cockpit:status weekly` / `:status sprint M1.2` / `:status blockers` · 直接读 state.json 输出叙述。
- **`commands/update.md`** → 用户输入 `/docs-cockpit:update` 触发 · 走完 7 步两层升级。

### Changed

- `plugin.json` / `marketplace.json` 描述显式说明含 3 skill + 3 slash command 两套入口。
- 双入口设计:**skill** 处理自然语言("把 docs 做成 dashboard")· **slash command** 给 tab 补全 + 快速触发("/docs-cockpit:status weekly")。

### Notes

- Skill 和 slash command 共享底层 workflow · slash command 只是 "fast path entry" · skill 是 "natural language entry"。维护时改 SKILL.md 是真理之源 · command 文件只是路由层。
- 升级到本版本需要重启 Claude Code · plugin 才能 re-fetch 新的 `commands/` 目录。

## [0.1.2] · 2026-05-14

让 plugin 自己感知版本过期 + 提供升级路径。三 skill 结构。

### Added

- **CLI 版本检测**:`docs-cockpit build` 启动时 best-effort 拉 GitHub 上 `.claude-plugin/plugin.json` 的 version 字段对比 · 远端更新则打印 banner `[!] docs-cockpit X.Y.Z available (current: ...)` + 升级命令 + 提示让 Claude 调 `docs-cockpit-update` skill。结果缓存 24h · 网络失败静默 · 加 `--no-version-check` 跳过(也可设 `DOCS_COCKPIT_NO_VERSION_CHECK=1`)。
- **`docs-cockpit-update` skill**:走两层升级流程 · Python CLI (`pip install --upgrade`) + Claude Code plugin (`settings.json` 加 `autoUpdate:true` + 重启)。覆盖 4 个常见场景(全升 / 单层升 / 钉版本 / 离线兜底)+ 4 种失败模式诊断。
- **`docs_cockpit.__version__`**:包级单一版本号源 · 来自 `docs_cockpit/__init__.py`。

### Changed

- **`docs-cockpit` skill scope 段加 update sibling 路由说明**:看到 build banner 报新版本 → hand off。
- **`docs-cockpit-status` skill scope 段加 update sibling 路由说明**:`state.json` 缺失 / 格式老 → 优先推升级而不是叫用户跑 build。
- **`plugin.json` 描述**:显式说明 ships THREE skills · keywords 不变。

## [0.1.1] · 2026-05-14

按"读 / 写"职责拆 skill 的一次重构。引入 sidecar 状态数据,让 Claude 既能 build cockpit 也能解读 cockpit。

### Added

- **`state.json` sidecar 输出**:每次 `docs-cockpit build` 在 `docs/index.html` 旁同步写一份 `docs/state.json`(无 markdown 正文 · 仅 groups / cards / kpi / sprint_order / warnings)· 给 `docs-cockpit-status` skill 读。
- **`docs-cockpit-status` skill**:只读 `docs/state.json` · 回答 "哪些卡 blocked / sprint M1.X 进度多少 / 哪些 doc 太久没改 / 给我生成周报 / 这周 cockpit 状态有啥变化" 这类问题 · 不写任何文件。

### Changed

- **Skill 目录结构**:`SKILL.md` 从仓根搬到 `skills/docs-cockpit/SKILL.md` · 给 plugin 加多 skill 的能力(参考 superpowers 等多 skill plugin 的惯例)。
- **`docs-cockpit` skill 描述收窄**:只覆盖 "set up / 加 group / build / 调 design / debug" 等**写文件**的场景。状态/进度查询的 trigger 短语全部移走给 sibling skill。
- **`plugin.json` description / keywords 更新**:显式说明 plugin 含两个 skill;keywords 加 `status-tracking` / `standup-report`。

## [0.1.0] · 2026-05-14

首个公开版本。可用作 Python CLI、也可作为 Claude Code skill / plugin 装用。

### Added

- **核心 build pipeline**:`docs_cockpit.build` 扫描配置里的 groups,把每篇 MD 内联进单文件 `index.html` · 浏览器端用 marked.js + highlight.js 渲染。
- **CLI**:`docs-cockpit init` 起一份最小配置 · `docs-cockpit build` 跑构建 · `--debug` 打印路径变量。
- **三种 group 来源**:`files`(显式列表)/ `scan`(目录扫描 + title transform)/ `glob`(跨路径)。同一 group 内可混用。
- **路径变量系统**:`{repo}` / `{home}` / `{main_repo}` / `{env:VAR}` 四个内置 + `paths.*` 下任意自定义。`{main_repo}` 在 git worktree 内自动指回 main。
- **YAML frontmatter 驱动的看板**:`status` × `progress` 一致性校验 + KPI bar + 模块 Kanban(5 列)+ Sprint Timeline。`kpi_type` 控制主聚合 type · 其他 type 进底部 Concept Grid。
- **品牌 / 设计 token override**:`design.colors.*` 覆盖前端 CSS `:root` 变量 · HP-style 默认主题。
- **Claude Code plugin manifest**:`.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` · 支持 `/plugin marketplace add Guohao1020/docs-cockpit` 一键装用。
- **示例配置**:`examples/minimal.yaml`(最小可用)+ `examples/full.yaml`(10 groups + 看板的完整参考)。
- **参考文档**:`references/config_reference.md`(全字段 schema)/ `references/frontmatter_conventions.md`(ID 命名 + status × progress 校验)/ `references/design_tokens.md`(CSS token + 离线 vendor 指引)。

### Notes

- Python 依赖只有 `pyyaml`,装 plugin 后仍需 `pip install git+https://github.com/Guohao1020/docs-cockpit.git` 让 `docs-cockpit` CLI 进 PATH。
- 离线 mode(CDN 拉不到 marked.js)目前需手工 vendor `_assets/` · 见 `references/design_tokens.md` "Offline mode" 节。

[Unreleased]: https://github.com/Guohao1020/docs-cockpit/compare/v0.6.1...HEAD
[0.6.1]: https://github.com/Guohao1020/docs-cockpit/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/Guohao1020/docs-cockpit/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/Guohao1020/docs-cockpit/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/Guohao1020/docs-cockpit/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/Guohao1020/docs-cockpit/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/Guohao1020/docs-cockpit/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/Guohao1020/docs-cockpit/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/Guohao1020/docs-cockpit/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/Guohao1020/docs-cockpit/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/Guohao1020/docs-cockpit/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/Guohao1020/docs-cockpit/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Guohao1020/docs-cockpit/releases/tag/v0.1.0
