[English](README.md) · **中文**

# docs-cockpit

> 单文件 HTML 看你项目的所有 markdown · YAML 配置 + frontmatter 驱动 · 浏览器 `file://` 直接打开。
>
> **Dashboard**(Kanban / Sprint Timeline / KPI)看模块进度 · **Browser**(树形侧边栏 + marked.js 渲染)读散落文档 · 两个产出都有 **EN / 中** 切换。

`docs-cockpit` 解决两个相关问题:

1. **你有 module spec 写 status/progress · 想要 dashboard** —— 但不想为此装 Jira / Notion / Linear。→ `docs-cockpit build` 产出 `docs/index.html` · 含 Module Kanban + Sprint Timeline + KPI bar + 模块 drawer(含 subtask checklist)。
2. **你有一堆 MD(ADR、plan、RFC)想在浏览器里读** —— 但不想为此装 Sphinx / Docusaurus。→ `docs-cockpit browse` 产出 `docs/browse.html` · 树形文件侧边栏 + marked.js 渲染。

## 亮点

- **模块 Kanban** · 5 列状态 · 点卡片弹 drawer 含 desc / status / progress 滑块 / **subtask checklist** · localStorage 持久化用户覆盖
- **Sprint Timeline** · 按 sprint 字段分组 · 平均 % · locale 排序
- **概念 Grid + 系统文档 Drawer** · 手挑入口(CLAUDE.md / PRD / DESIGN / RFC / memory / roadmap)一键打开
- **自动 body 提取**(0.4.0+) · MD body 的 `## 待办` / `## TODO` checklist **自动**变成 subtasks · 不用 frontmatter 重复维护
- **Subtask → 自动 progress** · `manualProgress: false` 时按 subtask 完成率算 progress
- **树形 Browser**(0.5.0+) · 侧边栏镜像项目目录结构 · 搜索 + 折叠 + localStorage 记上次看哪个
- **双语 UI**(0.6.0+) · 顶部右上 `[EN] [中]` toggle · 默认英文 · localStorage 持久化
- **`migrate` 命令**(0.3.0+) · 一键扫 legacy 项目散落 MD(`docs/plans/` / `docs/adrs/` 等)+ 自动注入 frontmatter + 物理迁到 canonical `docs/spec/module/` 布局
- **机器可读 `state.json`** sidecar · 给 status skill 用 · 答 "哪些 module 卡了 / 周报" 不用解析 HTML
- **跨平台** · 纯 Python 3.10+ + `pyyaml` · Windows / macOS / Linux 同一份 yaml
- **以 Claude Code plugin 形式发布** · 3 个自动触发 skill + 5 个 slash command

---

## Quickstart · Claude Code 用户(60 秒)

docs-cockpit 是**为 Claude Code 优先设计的 plugin**。装它两条命令 + 跟 Claude 说人话。

```bash
# 1. 在 Claude Code 里注册 plugin marketplace
/plugin marketplace add Guohao1020/docs-cockpit

# 2. 装 CLI(Claude 作为子进程调它)
pip install git+https://github.com/Guohao1020/docs-cockpit.git
# 或者 Python <3.10 / uv 用户:
# uv tool install --python 3.11 git+https://github.com/Guohao1020/docs-cockpit.git

# 3. 重启 Claude Code · 让 plugin 加载
```

然后在任何项目里 · 跟 Claude 说其中一句:

> "用 docs/spec/module/ 给我做个 dashboard" · 或 · "浏览这项目所有 markdown" · 或 · "把这个 legacy 项目迁到 docs-cockpit"

Claude 自动选对应 skill · 写 yaml · 跑 build。**就这样。**

> 不用 Claude Code?跳到 [Install · 按工具选](#install--按工具选) 看 Codex / Cursor / Gemini / OpenCode 的手动 skill 复制。

### 三种产出

```
docs-cockpit build     →  docs/index.html   (模块 Kanban + Sprint + KPI dashboard)
                          docs/state.json   (sidecar JSON · 给 status skill 读)

docs-cockpit browse    →  docs/browse.html  (树形 markdown 浏览器)

docs-cockpit migrate   →  把 legacy 散落 MD 迁到 docs/spec/module/M{NN}-*.md
                          + 写 tailored docs-cockpit.yaml
```

所有 HTML 顶部右上都有 `[EN] [中]` toggle · 默认英文 · 点一下切中文(localStorage 记)。

### 模块 frontmatter(让卡片进 Kanban)

模块要进卡板 · MD 顶部需 YAML frontmatter:

```markdown
---
id: M07
title: Job FSM
status: in-progress
sprint: M1.2
progress: 45
desc: "12 类 FSM 状态机"
subtasks:
  - { title: "核心实体定义", done: true }
  - { title: "字段校验", done: false }
---
```

或者 —— **直接在 body 写 `## TODO` / `## 待办`** checklist · docs-cockpit 自动提取为 subtasks(0.4.0+):

```markdown
---
id: M07
title: Job FSM
status: in-progress
---

# M07 · Job FSM

## 待办
- [ ] 核心实体定义
- [x] 字段校验
- [ ] 跨模型引用约束
```

完整 frontmatter 约定:[references/frontmatter_conventions.md](references/frontmatter_conventions.md)。

---

## Install · 按工具选

### A. Claude Code(推荐 · 主路径)

**一行 plugin install + 一行 CLI install + 重启。**

```bash
# 在 Claude Code 里:
/plugin marketplace add Guohao1020/docs-cockpit

# 在你的 shell 里:
pip install git+https://github.com/Guohao1020/docs-cockpit.git
```

重启 Claude Code → plugin 自动从 GitHub fetch → 3 个 skill + 5 个 slash command 生效。

**自动升级**:在 `~/.claude/settings.json` 的 `extraKnownMarketplaces.docs-cockpit` 加 `"autoUpdate": true`。或者跟 Claude 说 *"升级 docs-cockpit"* · update skill 走完整流程(pip 升级 + plugin cache 强清 + 提示重启)。**Cache 强清这步很重要** · 当前 Claude Code 的 `autoUpdate: true` 不可靠 · 0.3.1+ 的 update flow 自动替你处理。

**`/plugin` 不可用**(老版本 / PR review 等受限 surface) → 手工 merge `~/.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "docs-cockpit": {
      "source": { "source": "github", "repo": "Guohao1020/docs-cockpit" },
      "autoUpdate": true
    }
  },
  "enabledPlugins": {
    "docs-cockpit@docs-cockpit": true
  }
}
```

#### 说人话自动触发(skill auto-trigger)

| 你说 | Claude 触发 |
|---|---|
| "把 docs 做成 dashboard" / "Make a project Kanban" | `docs-cockpit` → 写 yaml + 跑 `build` |
| "浏览项目所有 md" / "读所有 ADR" | `docs-cockpit` → 跑 `browse` |
| "迁移这个 legacy 项目" / "我项目用 docs/plans/, 帮我迁" | `docs-cockpit` → 跑 `migrate`(先 dry-run · 用户确认后 `--apply`) |
| "哪些 module 卡了" / "sprint M1.2 进度" / "weekly standup" | `docs-cockpit-status` → 读 `state.json` · 叙述输出 |
| "升级 docs-cockpit" / "update docs-cockpit" | `docs-cockpit-update` → pip 升级 + plugin cache 强清 + 重启提示 |

#### 显式 slash command

- `/docs-cockpit:build` · Dashboard build → `docs/index.html` + `docs/state.json`
- `/docs-cockpit:browse [--dir <path>]` · MD 浏览器 → `docs/browse.html`
- `/docs-cockpit:migrate [--apply]` · Legacy 布局迁移(默认 dry-run · `--apply` 真执行)
- `/docs-cockpit:status [问题]` · 读 state.json 答状态查询
- `/docs-cockpit:update` · 两层升级 workflow

### B. 其他 vibe coding 工具 · 手动复制 skill

**Codex / Cursor / Gemini / OpenCode** 等(有 `~/.claude/skills/` 类似 skill loading 机制):

```bash
# 仓 clone 到本地
git clone https://github.com/Guohao1020/docs-cockpit.git ~/.tools/docs-cockpit

# 复制 skill 到你工具的 skill 目录
# (把 <skills-dir> 换成你工具路径 · 比如 ~/.codex/skills/、~/.cursor/skills/)
cp -r ~/.tools/docs-cockpit/skills/docs-cockpit         <skills-dir>/
cp -r ~/.tools/docs-cockpit/skills/docs-cockpit-status  <skills-dir>/
cp -r ~/.tools/docs-cockpit/skills/docs-cockpit-update  <skills-dir>/

# 还要装 CLI · skill 才能调
pip install git+https://github.com/Guohao1020/docs-cockpit.git
```

重启你的工具。skill 按同样的自然语言短语触发(SKILL.md 里的 Claude-specific 路径语法可能要微调)。

> **需要 Python ≥ 3.10**。系统默认 Python 更老 · 用 [`uv`](https://docs.astral.sh/uv/):`uv tool install --python 3.11 git+https://github.com/Guohao1020/docs-cockpit.git`。

---

## 配置(给 `docs-cockpit build` 用)

Dashboard 的 `docs-cockpit.yaml` 有 4 个顶层数据 block:

```yaml
project:        { name, mark, tagline, eyebrow, output }
paths:          { repo, ... 任意自定义变量 }
system_docs:    [ { id, title, path, desc, icon } ... ]   # 手挑常驻入口
modules:        { files / scan / glob }                    # frontmatter 驱动 dashboard 卡片
concepts:       { files / scan / glob }                    # 简化 grid 卡片
frontmatter:    { enabled, status_progress_ranges }
```

`docs-cockpit browse` **不需要任何 yaml** · 默认扫项目 + `~/.claude/{plans,projects}/<project>/`。用 `--dir` 覆盖。

参考:
- [`docs_cockpit/examples/full.yaml`](docs_cockpit/examples/full.yaml) · 完整参考配置(6 system_docs + 模块扫描 + 概念扫描 + frontmatter 治理)
- [`docs_cockpit/examples/minimal.yaml`](docs_cockpit/examples/minimal.yaml) · 最小可用配置
- [`references/config_reference.md`](references/config_reference.md) · 每个字段的语义和默认值
- [`references/frontmatter_conventions.md`](references/frontmatter_conventions.md) · 模块 / 概念的 frontmatter 字段 + body 兜底提取规则(`## TODO` → subtasks 等)

---

## 日常工作流

### Dashboard build

```bash
docs-cockpit build                          # 默认读 ./docs-cockpit.yaml
docs-cockpit build -c configs/preview.yaml  # 指定配置
docs-cockpit build --debug                  # 打印解析后路径变量(排错神器)
```

每次 build 覆写 `docs/index.html` + `docs/state.json`。浏览器 `Ctrl+R` 看新内容。

### Markdown browser

```bash
docs-cockpit browse                              # 默认:扫项目 + ~/.claude
docs-cockpit browse --dir docs/adrs              # 限定某子目录
docs-cockpit browse --output docs/adrs.html      # 自定义输出
docs-cockpit browse --no-claude                  # 跳过 ~/.claude 扫描
```

每次跑重新生成 HTML · 没有 live watch。编辑 MD 后重跑 + `Ctrl+R`。

### Legacy 项目迁移

```bash
docs-cockpit migrate                # dry-run · 只 print 计划 · 不动文件
docs-cockpit migrate --apply        # 真执行 · git mv 文件 + 注入 frontmatter + 写 yaml
docs-cockpit migrate --apply --keep-originals   # 复制不移动
```

Migrate 自动分类 legacy 布局(`docs/plans/` / `docs/adrs/` / `docs/superpowers/plans/` → modules; `docs/PRD/` / `docs/RFC/` / `docs/architecture/` → system_docs)· 生成 ID 前缀的 frontmatter(`M01-*.md`、`M02-*.md`...)。

### 嵌进 git workflow(可选 · 强烈推荐)

cockpit 持续更新才有用。三种 pattern:

**Pre-commit hook**(零负担):

```bash
# .git/hooks/pre-commit
#!/bin/bash
if git diff --cached --name-only | grep -E '\.md$|\.yaml$' > /dev/null; then
  docs-cockpit build
  git add docs/index.html docs/state.json
fi
```

**CI 检查**(严格):

```yaml
# .github/workflows/docs.yml
- run: pip install git+https://github.com/Guohao1020/docs-cockpit.git
- run: docs-cockpit build
- run: git diff --exit-code docs/index.html docs/state.json
```

**CONTRIBUTING 约定**(最轻):

> 任何 PR 涉及 `*.md` 必须重跑 `docs-cockpit build` 并 commit 重新生成的产物。

### `docs/index.html` 入库还是 gitignore?

**入库** · clone 后 `start docs/index.html` 立即能用 · 适合内部工具 / 团队预览。GitHub 上 `docs/` 视图更好。

**ignore** · 仓库轻量 · 每次本地 build · 适合公开项目 / 不爱 binary diff 的 maintainer。

---

## 升级

`docs-cockpit-update` skill 走完整流程 · 跟 Claude 说 *"升级 docs-cockpit"* 即可。手动步骤:

```bash
# 1. CLI 升
pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git
# 或: uv tool upgrade docs-cockpit

# 2. 强清 plugin 缓存(autoUpdate 不可靠 · 0.3.1 教训)
rm -rf ~/.claude/plugins/cache/*docs-cockpit*                                # POSIX
# Windows: Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\plugins\cache\*docs-cockpit*"

# 3. 重启 Claude Code · 让它重新 fetch marketplace
```

**验证升级到位**(重启后):

- `/plugin` UI 看 `docs-cockpit` 版本号是新的
- Skills 列表显示 5 个 slash command(`/build`、`/browse`、`/migrate`、`/status`、`/update`)
- `docs-cockpit build` 不再打印 `[!] X.Y.Z available` banner

**如果版本还是老的** · 跑兜底:

```
/plugin marketplace remove docs-cockpit
/plugin marketplace add Guohao1020/docs-cockpit
/plugin install docs-cockpit@docs-cockpit
```

升级会破坏配置吗?
- `0.x.y` patch / minor 版本:向后兼容(除非 CHANGELOG 标了 breaking)
- `0.x → 1.0`:CHANGELOG 列迁移路径
- 未知字段静默忽略 · 加新字段不破坏老版本

完整版本历史见 [CHANGELOG.md](CHANGELOG.md)。

---

## 故障排查 · 高频问题

| 现象 | 大概率原因 | 修法 |
|---|---|---|
| `[WARN] 0 items` 跑 build | `paths.repo` 错 / modules/concepts 路径没扫到 MD | `docs-cockpit build --debug` 看 vars dict |
| 模块没进 Kanban 卡板 | MD 缺 `id:` frontmatter · 或 id 是模板占位(`MXX`)| 加 `id: M07` 等 · 见 `references/frontmatter_conventions.md` |
| Drawer 子任务空 · 但 MD body 有 `## TODO` | section header 不匹配 · 必须是 `## 待办` / `## TODO` / `## Subtasks` / `## Tasks`(可带数字前缀)| 见 `references/frontmatter_conventions.md` body 提取规则 |
| 浏览器顶部红 banner | CDN 拉不到 marked.js / highlight.js | 内网用户:vendor JS 到本地 · 暂未支持 · 开 issue |
| YAML 报 unknown-key | typo · schema 严格 | 在 `references/config_reference.md` 查拼写 |
| Plugin 重启后版本没变 | Plugin 缓存陈旧 · `autoUpdate` 不可靠 | 强清 cache · 见上方 升级 段第 2 步 |
| `pip install` 报 "requires-python: >=3.10" | 系统 Python 太老 | 切 `uv tool install --python 3.11 git+...` |

深度排错见 `skills/docs-cockpit/SKILL.md` 末尾的 "Common failure modes" 节。

---

## 文档索引

### Skills(Claude 自动触发)
- [`skills/docs-cockpit/SKILL.md`](skills/docs-cockpit/SKILL.md) · 操作型 skill(setup / build / browse / migrate workflow)
- [`skills/docs-cockpit-status/SKILL.md`](skills/docs-cockpit-status/SKILL.md) · 读状态 skill(解读 `state.json` 给周报)
- [`skills/docs-cockpit-update/SKILL.md`](skills/docs-cockpit-update/SKILL.md) · 自动升级 skill(CLI + plugin 双层)

### Slash commands
- [`commands/build.md`](commands/build.md) · `/docs-cockpit:build`
- [`commands/browse.md`](commands/browse.md) · `/docs-cockpit:browse`
- [`commands/migrate.md`](commands/migrate.md) · `/docs-cockpit:migrate`
- [`commands/status.md`](commands/status.md) · `/docs-cockpit:status`
- [`commands/update.md`](commands/update.md) · `/docs-cockpit:update`

### Reference 文档
- [`references/config_reference.md`](references/config_reference.md) · `docs-cockpit.yaml` 全字段 schema
- [`references/frontmatter_conventions.md`](references/frontmatter_conventions.md) · frontmatter 字段约定 + body 提取规则
- [`references/design_tokens.md`](references/design_tokens.md) · CSS token / 品牌色 / 字体 / 暗色模式

### 示例(pip wheel 内置)
- [`docs_cockpit/examples/minimal.yaml`](docs_cockpit/examples/minimal.yaml) · 最小可用配置
- [`docs_cockpit/examples/full.yaml`](docs_cockpit/examples/full.yaml) · 完整参考配置

### 代码
- `docs_cockpit/build.py` · dashboard build + state.json + body 提取
- `docs_cockpit/browse.py` · markdown 浏览器
- `docs_cockpit/migrate.py` · legacy 布局迁移
- `docs_cockpit/templates/index.html.tmpl` · dashboard 模板(含 i18n)
- `docs_cockpit/templates/browse.html.tmpl` · browser 模板(含 i18n)

### Meta
- [`CHANGELOG.md`](CHANGELOG.md) · 每版本的发布记录 + 迁移说明
- [`README.md`](README.md) · English README

> 注:SKILL.md 和 `references/*.md` 仍是中文优先。README 和 HTML 产出有完整 EN/ZH 双语支持(顶部 toggle)。

---

## License

MIT
