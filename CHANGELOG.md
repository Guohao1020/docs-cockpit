# CHANGELOG

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) · 版本号采用 [SemVer](https://semver.org/lang/zh-CN/)。

## [Unreleased]

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

[Unreleased]: https://github.com/Guohao1020/docs-cockpit/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Guohao1020/docs-cockpit/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/Guohao1020/docs-cockpit/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/Guohao1020/docs-cockpit/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/Guohao1020/docs-cockpit/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Guohao1020/docs-cockpit/releases/tag/v0.1.0
