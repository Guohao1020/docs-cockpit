# `docs-cockpit.yaml` · 全配置参考(0.2.0)

> 读这份的时机:你要写一个新的 cockpit 配置 · 或扩展现有配置。SKILL.md 里的 Quick reference 给最常用字段 · 这里给**全部**字段 + 语义 + 默认值 + 为什么这么设。

## 0.2.0 schema(dashboard 形态)

```yaml
project:            { name, mark, tagline, eyebrow, output }
paths:              { repo, ... 任意命名的额外变量 }
system_docs:        [ { id, title, path, desc, icon } ... ]   # 手挑常驻入口
modules:            { files / scan / glob }                    # frontmatter 驱动
concepts:           { files / scan / glob }                    # 简化卡片
frontmatter:        { enabled, status_progress_ranges }
```

所有 block 都可省略。**至少给一个 `modules` 或 `concepts` 或 `system_docs`** 才有内容可看。

---

## `project` · 品牌与输出路径

```yaml
project:
  name: MyProject                  # 必填 · wordmark 主标题 + tab title
  mark: M                          # 默认 "·" · wordmark 方块里的单字符(替代 0.1.x 的 glyph)
  tagline: "项目模块进度概览"        # 可选 · hero 区下方一句话
  eyebrow: "DASHBOARD"             # 可选 · hero 顶部小标签
  output: docs/index.html          # 默认 "docs/index.html" · 相对 paths.repo
```

**为什么 output 不能用 absolute?** 可以 — 写成 `/var/docs/index.html` 或 `C:\out\index.html` 都行。

**mark 建议:** 单字母 / 数字 / 中文一字 · 太长会被 28×28 方块裁掉。

---

## `paths` · 路径变量

```yaml
paths:
  repo: "."                        # 默认 · 即配置文件所在目录
  # 任意自定义变量 · 后续在 system_docs / modules / concepts 用 {name}
  memory_dir: "{home}/.claude/projects/my-project/memory"
  external_plans: "{home}/.claude/plans/my-project"
```

### 内置变量

| 变量 | 含义 |
|---|---|
| `{repo}` | `paths.repo` 解析后的绝对路径 |
| `{home}` | `$USERPROFILE`(Windows) / `$HOME`(Linux/macOS) |
| `{main_repo}` | 如果 `{repo}` 是 git worktree · 自动上溯到 main · 否则等于 `{repo}` |
| `{env:VAR}` | 环境变量 `VAR` · 找不到则空串 |

未定义变量**保留原文** · 不报错 · 便于 `--debug` 排错。

### worktree 处理

典型用法:`.claude/worktrees/<wt-name>/` 装 worktree。在 worktree 内跑 build · `{main_repo}` 自动指回 main(用于读 main 的 DESIGN.md 等)。

---

## `system_docs` · 手挑常驻入口

```yaml
system_docs:
  - id: claude-md
    title: CLAUDE.md
    path: "{repo}/CLAUDE.md"
    desc: 项目根级 AI 协作约定
    icon: memory                   # memory / design / plan / doc
  - id: design
    title: DESIGN.md
    path: "{main_repo}/DESIGN.md"
    desc: 设计系统 tokens、视觉规范
    icon: design
```

每条字段:

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | 可省 · 缺则从 title slugify | 唯一标识(给 localStorage 用) |
| `title` | ✅ | drawer 里显示的标题 |
| `path` | ✅ | 可以是文件 / 目录 / 任意 URL · `{var}` 会展开 |
| `desc` | 可省 | drawer 里 title 下方的描述 |
| `icon` | 默认 `doc` | `memory` / `design` / `plan` / `doc` 之一 · 决定列表前的图标 |

**system_docs 是手挑的** — 不像 modules / concepts 是扫目录。这里放 CLAUDE.md / DESIGN.md / PRD.md / memory/ / roadmap 这种**全局常驻**的入口。每条点击在新 tab 打开 `path`。

---

## `modules` · 主 dashboard 数据源

```yaml
modules:
  scan:
    dir: "{repo}/docs/spec/module"
    title_transform: prefix-dot-titlecase
    # 同时支持 files / glob · 见下方
```

Modules 块支持三种来源 · 同 0.1.x:

### 1. 显式列表 · `files`

```yaml
modules:
  files:
    - { title: M01 Web Console, path: "{repo}/docs/spec/module/M01-web-console.md" }
    - { title: M07 Job FSM, path: "{repo}/docs/spec/module/M07-job-fsm.md" }
```

### 2. 目录扫描 · `scan`

```yaml
modules:
  scan:
    dir: "{repo}/docs/spec/module"          # 必填
    pattern: "*.md"                          # 默认 "*.md"
    recursive: false                         # 默认 false
    title_transform: prefix-dot-titlecase    # 见下方
    exclude_underscores: true                # 默认 true
```

#### `title_transform` 选项

| transform | 输入 → 输出 | 用途 |
|---|---|---|
| `stem` | `M07-job-fsm.md` → `M07-job-fsm` | 不动文件名 |
| `prefix-dot-titlecase` | `M07-job-fsm.md` → `M07 · Job Fsm` | 最常用 |
| `path-slash` | `roadmap/00-master.md` → `roadmap / 00-master` | 递归扫时默认 |

### 3. Glob 模式 · `glob`

```yaml
modules:
  glob:
    - "{repo}/docs/spec/module/M*.md"
    - "{home}/.claude/plans/my-project/modules/*.md"
```

### 同时混用

允许 `files` + `scan` + `glob` 共存 · 结果合并。

### Module → Dashboard 卡片

扫出的每个 MD 经过 frontmatter 解析 · 生成一张卡:

```python
{
    "id":       meta["id"],            # 必有 · 不然跳过
    "title":    meta["title"] or filename,
    "status":   meta["status"] or "not-started",
    "sprint":   meta["sprint"] or "",
    "progress": meta["progress"] or 0,
    "desc":     meta["desc"] or "",
    "docs":     meta["docs"] or [],
    "subtasks": meta["subtasks"] or [],
    "manualProgress": meta.get("manualProgress", False),
    # + 治理字段:owner / prd_ref / depends_on / blocks / updated_at
}
```

frontmatter 各字段语义见 `references/frontmatter_conventions.md`。

---

## `concepts` · 底部 Concept Grid

```yaml
concepts:
  scan:
    dir: "{repo}/docs/spec/concept"
    title_transform: prefix-dot-titlecase
```

结构跟 `modules` 一样(`files` / `scan` / `glob` 三选 / 混用)。**区别**:concepts 卡片**只用** 5 字段(id / title / status / sprint / progress)· 即使 MD 写了 desc / docs / subtasks 也会被忽略。

---

## `frontmatter` · YAML 头治理

```yaml
frontmatter:
  enabled: true                       # 默认 true · 关掉就完全不解析 frontmatter
  status_progress_ranges:             # status × progress 一致性区间
    not-started: [0, 0]
    planned: [0, 15]
    in-progress: [5, 95]
    blocked: [0, 100]
    done: [100, 100]
    deferred: [0, 100]
```

详细治理规则、自定义 status 词汇、subtasks 自动 progress 计算见 `references/frontmatter_conventions.md`。

**0.2.0 移除了** `frontmatter.kanban.*` 配置块。`card_types` / `kpi_type` / `sprint_order` 都不再需要 —— 因为现在 modules / concepts 是顶层独立 block,kpi 就是 modules · 不存在歧义。

---

## 0.1.x → 0.2.0 迁移

| 0.1.x | 0.2.0 |
|---|---|
| `project.glyph` | `project.mark` |
| `project.subtitle` | `project.tagline` |
| `project.description` | 删掉 · 不再使用 |
| `groups[]` 含 `type: module` 的 group | `modules:` 顶层 block |
| `groups[]` 含 `type: concept` 的 group | `concepts:` 顶层 block |
| `groups[]` 普通文档 group | `system_docs:` 顶层 block(改 schema:逐条 `{id, title, path, desc, icon}`) |
| `frontmatter.kanban.card_types: [module, concept]` | 删掉 · modules/concepts 已分开 |
| `frontmatter.kanban.kpi_type: module` | 删掉 · kpi 始终统计 modules |
| `frontmatter.kanban.sprint_order: [...]` | 删掉 · JS 自动按 locale 排序 |
| `frontmatter.kanban.enabled: true/false` | 删掉 · 0.2.0 永远是 dashboard 形态 |
| `design.colors.*` | 暂未支持 · 0.2.x 待加回 |

完整迁移示例对照见 [CHANGELOG.md](../CHANGELOG.md) 0.2.0 入口。

---

## 路径解析的优先级与排错

build 流程:

1. 加载配置 → 计算 `vars_` 字典(`repo` / `home` / `main_repo` + 自定义)
2. 各 block(`system_docs` / `modules` / `concepts`)分别处理
3. 每条 entry 的 `path` 经过 `{var}` 替换 → `pathlib.Path`
4. `Path.exists()` 判断 → 不存在则跳过(modules / concepts)或保留(system_docs)

排错:`docs-cockpit build --debug` 打印解析后 `vars_` 字典 + output 路径。最常见的坑是 `paths.repo` 写错 —— 大多数情况下**把 `paths.repo` 干脆删掉**即可。

---

## 最小可行配置(粘贴可跑)

```yaml
project:
  name: MyProject

modules:
  scan:
    dir: docs/spec/module
    title_transform: prefix-dot-titlecase
```

只要 `docs/spec/module/M*.md` 里有 frontmatter 带 `id` · 跑 `docs-cockpit build` 就出 dashboard。
