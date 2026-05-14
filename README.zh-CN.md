[English](README.md) · **中文**

# docs-cockpit

> 把项目里散落的 Markdown 汇总成单文件 HTML 看板 · 浏览器 `file://` 直接打开 · 改 md 重跑就同步。

`docs-cockpit` 解决一个具体问题:**项目文档堆得到处都是,缺一个统一入口随时浏览**。它扫描你配置的目录(`docs/PRD/`、`docs/spec/`、`docs/plan/`、`docs/RFC/`、`docs/task/`、根 `README.md`、外部 `~/.claude/plans/...`、session memory…),把每篇 MD 序列化进**一个**自包含的 `index.html` —— 没有 web server,没有 build pipeline,直接拖进浏览器就能用。

亮点:

- **侧边栏导航 + 文档视图** · marked.js + highlight.js 客户端渲染 · 锚点跳转 · 搜索框 · 浏览状态走 localStorage 持久化
- **可选项目看板** · MD 文件加 YAML frontmatter(`status: in-progress` / `progress: 60` / `sprint: M1.2`)就自动出 KPI / 模块 Kanban / Sprint Timeline
- **跨平台** · 纯 Python 3.10+ + pyyaml · Windows / macOS / Linux 同一份 yaml 跑
- **同时是 Claude skill** · 装到 `~/.claude/skills/` 后,Claude 看到 "把 docs 汇总成 dashboard" 类请求自动调用

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

### D. 装为 Claude skill · 让 Claude 主动用

```bash
# Linux/macOS
cp -r docs-cockpit ~/.claude/skills/docs-cockpit

# Windows PowerShell
Copy-Item -Recurse docs-cockpit "$env:USERPROFILE\.claude\skills\docs-cockpit"
```

装完后 Claude Code / Cowork 看到下面这类问题会自动调用 docs-cockpit skill:

- "把我项目的 md 文档做成 dashboard"
- "docs/ 下面 spec/plan/RFC 一堆 md · 想集中浏览"
- "build a docs preview that scans docs/spec/module/M*.md"

**注意**:作为 skill 用还是建议**同时** `pip install` 一下 · 否则 Claude 跑 `python -m docs_cockpit build` 时找不到包。两步是组合关系不是互斥。

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

- **`SKILL.md`** — Claude 用的主指令 · 含 4 workflow + 每步该读哪个 reference
- **`references/config_reference.md`** — `docs-cockpit.yaml` 全字段 schema · 必备
- **`references/frontmatter_conventions.md`** — YAML frontmatter 字段约定 + status × progress 校验
- **`references/design_tokens.md`** — CSS token / 品牌色 / 字体 / 暗色模式 / 离线 vendor
- **`examples/minimal.yaml`** — 最小可用配置
- **`examples/full.yaml`** — 完整配置参考 · 10 groups + 看板

---

## License

MIT
