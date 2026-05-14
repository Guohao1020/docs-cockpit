# CHANGELOG

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) · 版本号采用 [SemVer](https://semver.org/lang/zh-CN/)。

## [Unreleased]

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

[Unreleased]: https://github.com/Guohao1020/docs-cockpit/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/Guohao1020/docs-cockpit/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/Guohao1020/docs-cockpit/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Guohao1020/docs-cockpit/releases/tag/v0.1.0
