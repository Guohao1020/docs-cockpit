[English](README.md) · **中文**

# docs-cockpit

> 把项目里散落的 Markdown 汇总成单文件 HTML 看板 · 浏览器 `file://` 直接打开 · 改 md 重跑就同步。

`docs-cockpit` 解决一个具体问题:**项目文档堆得到处都是,缺一个统一入口随时浏览**。它扫描你配置的目录(`docs/PRD/`、`docs/spec/`、`docs/plan/`、`docs/RFC/`、`docs/task/`、根 `README.md`、外部 `~/.claude/plans/...`、session memory…),把每篇 MD 序列化进**一个**自包含的 `index.html` —— 没有 web server,没有 build pipeline,直接拖进浏览器就能用。

亮点:

- **侧边栏导航 + 文档视图** · marked.js + highlight.js 客户端渲染 · 锚点跳转 · 搜索框 · 浏览状态走 localStorage 持久化
- **可选项目看板** · MD 文件加 YAML frontmatter(`status: in-progress` / `progress: 60` / `sprint: M1.2`)就自动出 KPI / 模块 Kanban / Sprint Timeline
- **机器可读的 `state.json`** · 每次 build 在 `index.html` 旁同步写一份 sidecar JSON · 让其他工具 / sibling status skill 不解析 HTML 就能回答"哪些卡 blocked / sprint 进度 / 周报"
- **跨平台** · 纯 Python 3.10+ + pyyaml · Windows / macOS / Linux 同一份 yaml 跑
- **以 Claude Code plugin 形式发布** · 三个 skill 自动触发(`docs-cockpit` / `docs-cockpit-status` / `docs-cockpit-update`)+ 三个 slash command 显式调用(`/docs-cockpit:build` / `:status` / `:update`)· 两套入口任你挑

---

## Quickstart · 60 秒上手

在**你的项目根**(假设 `D:\projects\myapp\`):

```bash
# 1. 装 docs-cockpit(任选一种,见下方 Install 节)
pip install git+https://github.com/Guohao1020/docs-cockpit.git

# 2. 生成最小配置模板
docs-cockpit init

# 3. 编辑生成的 docs-cockpit.yaml · 改两三行就够了

# 4. Build
docs-cockpit build

# 5. 打开
start docs/index.html      # Windows
open  docs/index.html      # macOS
xdg-open docs/index.html   # Linux
```

最小配置模板大概长这样(`docs-cockpit init` 已经写好):

```yaml
project:
  name: MyProject
  glyph: M

groups:
  - name: Overview
    icon: O
    color: primary
    files:
      - { title: README, path: "{repo}/README.md" }

  - name: Docs
    icon: D
    color: graphite
    scan:
      dir: "{repo}/docs"
      recursive: true
```

跑完打开 `docs/index.html` · 应该看到侧边栏列出 `docs/` 下所有 md。

---

## Install · 三种装法 · 按场景选

### A. 直接 pip install · 推荐给"日常用工具"场景

```bash
pip install git+https://github.com/Guohao1020/docs-cockpit.git
```

装完后:
- 命令 `docs-cockpit` 出现在 PATH 里 · 可直接 `docs-cockpit build`
- 也可以 `python -m docs_cockpit build` · 两种等价

**升级**:`pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git`

### B. Clone + 开发模式 · 推荐给"想 fork 改逻辑"场景

```bash
git clone https://github.com/Guohao1020/docs-cockpit.git
cd docs-cockpit
pip install -e .
```

`pip install -e .` 让你改源码立即生效 · 不用每次 reinstall。

### C. 不装 · 临时用 PYTHONPATH

```bash
git clone https://github.com/Guohao1020/docs-cockpit.git /some/where
# 在你自己项目根:
PYTHONPATH=/some/where python -m docs_cockpit build
```

适合只想试一次 · 或不想动 site-packages 的洁癖场景。

### D. 装为 Claude Code plugin · 让 Claude 主动用

Claude Code 用户推荐这条路。Plugin 同时给两种调用入口 · **skill 自然语言自动触发** + **slash command 显式调用**:

**Skill · 说人话自动触发**:

- **`docs-cockpit`**(操作型)· 触发于 "把 docs 做成 dashboard"、"给我 cockpit 加一个 group"、"写个 pre-commit 让 HTML 不腐烂"、"改下 cockpit 的配色"、"build 跑不起来"
- **`docs-cockpit-status`**(只读状态)· 触发于 "哪些 module 卡了"、"sprint M1.3 进度多少"、"给我生成一份周报"、"哪些 doc 太久没改"、"这周 cockpit 状态有啥变化"
- **`docs-cockpit-update`**(自动升级)· 触发于 "升级 docs-cockpit"、"update docs-cockpit",或者一次 build 跑出 `[!] docs-cockpit X.Y.Z available (current: ...)` 这条 banner 时自动接手

**Slash command · tab 补全 / 快速触发**:

- **`/docs-cockpit:build`** · 立刻跑一次 build(可选参数:配置路径)
- **`/docs-cockpit:status [问题]`** · 快速查询(如 `/docs-cockpit:status weekly` / `:status sprint M1.2` / `:status blockers`)
- **`/docs-cockpit:update`** · 显式触发升级

两套入口任选 · slash command 适合记住名字的 power user · skill 适合说人话的所有人。

按你 Claude Code 版本走两条路:

**D-1 · 用 slash command(较新版本 · 大约 v2.1+)**:

```
/plugin marketplace add Guohao1020/docs-cockpit
/plugin install docs-cockpit@docs-cockpit
```

如果提示 `/plugin isn't available in this environment`,说明版本太老,走下面 D-2 兜底(或者跑 `claude --version` 看版本号,旧的用 `npm install -g @anthropic-ai/claude-code@latest` 升级)。

**D-2 · 改 settings.json(永远能用 · 也是老版本回退路径)**:

编辑 `~/.claude/settings.json`(Linux/macOS)或 `%USERPROFILE%\.claude\settings.json`(Windows),**合并**进这两个 block(不要把其他已有 key 删掉):

```json
{
  "extraKnownMarketplaces": {
    "docs-cockpit": {
      "source": { "source": "github", "repo": "Guohao1020/docs-cockpit" }
    }
  },
  "enabledPlugins": {
    "docs-cockpit@docs-cockpit": true
  }
}
```

如果 `extraKnownMarketplaces` 或 `enabledPlugins` 这两个 key 已经存在,把新条目**追加进去** · 不要整段替换。

**任选一条路改完后,重启 Claude Code。** 重启时它会从 GitHub fetch `Guohao1020/docs-cockpit`,解析 `.claude-plugin/marketplace.json` + `plugin.json`,skill 就上线了。

**验证**:让 Claude 跑一句 *"把 docs/ 下面所有 md 做成 dashboard"* — 应该自动调起 docs-cockpit 开始工作流。

> ⚠️ **仍然需要 `pip install`**(上面选项 A)让 `docs-cockpit` CLI 进 PATH · Claude 是当子进程调用的。Plugin 安装 + pip 安装是组合不是互斥。

---

## 配置 · 三种典型项目结构

### 配方 1 · 简单项目 · 一个 docs/ 目录

```yaml
project: { name: MyLib, glyph: L }

groups:
  - name: Overview
    icon: O
    color: primary
    files:
      - { title: README, path: "{repo}/README.md" }
      - { title: CHANGELOG, path: "{repo}/CHANGELOG.md" }
  - name: Docs
    icon: D
    color: graphite
    scan:
      dir: "{repo}/docs"
      recursive: true
```

适合:开源库 · 内部小工具 · 文档不多。看板不启用 · 只有侧边栏 + 文档视图。

### 配方 2 · 多 sub-spec · 含项目看板

```yaml
project: { name: MyProduct, glyph: P, subtitle: 内部文档 }

groups:
  - name: Overview
    icon: O
    color: primary
    files:
      - { title: README, path: "{repo}/README.md" }
      - { title: CHANGELOG, path: "{repo}/CHANGELOG.md" }

  - name: Spec · Concepts
    icon: C
    color: primary-deep
    scan:
      dir: "{repo}/docs/spec/concept"
      title_transform: prefix-dot-titlecase    # C03-foo-bar.md → C03 · Foo Bar

  - name: Spec · Modules
    icon: M
    color: primary
    scan:
      dir: "{repo}/docs/spec/module"
      title_transform: prefix-dot-titlecase

  - name: Plans
    icon: P
    color: graphite
    scan:
      dir: "{repo}/docs/plan"
      recursive: true
      title_transform: path-slash              # roadmap/00-master.md → "roadmap / 00-master"

  - name: Tasks
    icon: T
    color: bloom-coral
    scan:
      dir: "{repo}/docs/task"

  - name: RFCs
    icon: F
    color: storm-deep
    scan:
      dir: "{repo}/docs/RFC"

frontmatter:
  enabled: true
  kanban:
    enabled: true
    kpi_type: module                            # KPI bar 只算 module 类卡
    sprint_order: [M0, M1, M2, M3, GA]
```

适合:中大型项目 · 需要按 spec / plan / RFC / task 分类。看板要求 md 文件加 YAML frontmatter:

```markdown
---
id: M07
type: module
title: Job FSM
status: in-progress
progress: 45
sprint: M1.2
---

# M07 · Job FSM ...
```

详细 frontmatter 字段见 `references/frontmatter_conventions.md`。

### 配方 3 · 跨外部路径 · plans 在 home 目录

```yaml
project: { name: MyProject, glyph: M }

paths:
  repo: "."
  plans: "{home}/.claude/plans/myproject"      # 外部路径变量

groups:
  - name: Internal docs
    icon: I
    color: primary
    scan:
      dir: "{repo}/docs"
      recursive: true

  - name: External plans
    icon: E
    color: storm-deep
    glob:
      - "{plans}/**/*.md"
```

适合:有些 plan/notes 不想 commit 进项目仓库 · 但希望在 cockpit 里能集中浏览。`{home}` 是内置变量(`$HOME` / `$USERPROFILE`)· 自定义变量在 `paths:` 下任意 key 即可。

完整配置 schema 见 `references/config_reference.md`。

---

## 日常工作流

### 1. 跑 build

```bash
docs-cockpit build                          # 默认读 ./docs-cockpit.yaml
docs-cockpit build -c configs/preview.yaml  # 指定配置
docs-cockpit build --debug                  # 打印解析后的路径变量(排错神器)
```

### 2. 浏览

每次 build 都覆写 `docs/index.html`(或你 `project.output` 指的路径)。浏览器里 `Ctrl+R` 即可看到新内容。

### 3. 嵌进 git workflow(可选但强烈推荐)

cockpit 只有持续更新才有用。建议在 PR 流程里强制重跑:

**方法 a · pre-commit hook**(零负担):

```bash
# .git/hooks/pre-commit
#!/bin/bash
if git diff --cached --name-only | grep -E '\.md$|\.yaml$' > /dev/null; then
  docs-cockpit build
  git add docs/index.html
fi
```

**方法 b · CI 检查**(严格):

```yaml
# .github/workflows/docs.yml
- run: pip install git+https://github.com/Guohao1020/docs-cockpit.git
- run: docs-cockpit build
- run: git diff --exit-code docs/index.html
  # 如果 docs/index.html 没同步更新 → CI fail · PR 改完才能 merge
```

**方法 c · CONTRIBUTING 文档约定**(最轻):

> 任何 PR 涉及 `*.md` 必须重跑 `docs-cockpit build` 并 commit 生成的 `docs/index.html`。

### 4. `docs/index.html` commit 还是 ignore?

**Commit 进仓库**:任何人 clone 后 `start docs/index.html` 立即能用 · 适合内部工具 / 团队预览。
**加 .gitignore**:仓库轻量 · 但每次都得本地 build · 适合公开项目。

推荐 commit 进去 · 让 GitHub 的 docs/ 目录浏览体验也更好。

---

## 升级

```bash
# 从 GitHub 升
pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git

# Clone 模式(开发模式)
cd docs-cockpit && git pull
```

升级是否破坏配置:
- `0.1.x` 内升级 · 配置 100% 向后兼容
- `0.x → 1.0` 可能 break · 届时 CHANGELOG 会列迁移路径
- 配置文件加新字段不会让旧版本崩 · 加未知字段也只是被忽略

---

## 故障排查 · 高频问题

| 现象 | 大概率原因 | 修法 |
|---|---|---|
| `[WARN] 0 docs exist` | `paths.repo` 写错 | 删 `paths` 整段 · 用默认(配置文件所在目录) |
| 侧边栏全是 `missing` chip | 路径变量没解析 | `docs-cockpit build --debug` 看 vars 字典 |
| 浏览器顶部红 banner | CDN 拉不到 marked.js | 内网用户:见 `references/design_tokens.md` "Offline mode" |
| 看板空了 / 卡没出现 | frontmatter `id` 缺失 / `kanban.enabled: false` | 见 `references/frontmatter_conventions.md` |
| YAML 报 unknown key | typo · 配置 schema 严格 | 查 `references/config_reference.md` 拼写 |

深度排错见 `SKILL.md` 末尾的 "Common failure modes" 节。

---

## 文档索引

- **`skills/docs-cockpit/SKILL.md`** — 操作型 skill · 含 setup + 维护 workflow + 每步该读哪个 reference
- **`skills/docs-cockpit-status/SKILL.md`** — 读状态 skill · 怎么解读 `docs/state.json` 回答 blockers / sprint 进度 / 周报
- **`skills/docs-cockpit-update/SKILL.md`** — 自动升级 skill · CLI + plugin 两层升级流程
- **`commands/build.md` / `status.md` / `update.md`** — slash command 定义 · 对应 `/docs-cockpit:build|status|update`
- **`references/config_reference.md`** — `docs-cockpit.yaml` 全字段 schema · 必备
- **`references/frontmatter_conventions.md`** — YAML frontmatter 字段约定 + status × progress 校验
- **`references/design_tokens.md`** — CSS token / 品牌色 / 字体 / 暗色模式 / 离线 vendor
- **`examples/minimal.yaml`** — 最小可用配置
- **`examples/full.yaml`** — 完整配置参考 · 10 groups + 看板

---

## License

MIT
