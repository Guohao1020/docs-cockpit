# `docs-cockpit.yaml` · 全配置参考

> 读这份文档的时机:你要写一个新的 cockpit 配置,或往现有配置里加一类不熟悉的 group / 调整 frontmatter 治理规则 / 改 design tokens。SKILL.md 里的 Quick reference 给最常用的字段,这里给**全部**字段 + 每个字段的语义、默认值、为什么这么设。

## 顶层结构

```yaml
project:        { name, subtitle, glyph, description, output }
paths:          { repo, ... 任意命名的额外变量 }
groups:         [ { name, icon, color, files / scan / glob } ... ]
frontmatter:    { enabled, status_progress_ranges, kanban: { ... } }
design:         { colors: { primary, primary_deep, ... } }
```

所有 block 都可省略 · 缺省值见下方各节。`groups` 是唯一**必填**字段(否则页面没内容)。

---

## `project` · 品牌与输出路径

```yaml
project:
  name: MyProject                   # 必填 · wordmark 主标题 + footer 版权 + tab title
  subtitle: 文档预览                # 默认 "Docs preview" · wordmark 副标题
  glyph: M                          # 默认 "P" · wordmark 方块里的单字符
  description: 项目文档预览站        # 默认 "Project documentation preview" · footer 第一列描述
  output: docs/index.html           # 默认 "docs/index.html" · 相对 paths.repo
```

**为什么 output 不能用 absolute?** 可以 — 写成绝对路径(`/var/docs/index.html` / `C:\out\index.html`)build 也会写到那里。相对路径会被 `{repo}` 解析,所以最常见的 `docs/index.html` 不需要管 CWD。

**glyph 建议:** 单个字母或数字 · 中文字符也行(`图` / `站`)· 太长会被 28×28 的方块裁掉。

---

## `paths` · 路径变量

```yaml
paths:
  repo: "."                          # 默认 "." · 即 docs-cockpit.yaml 所在目录
  # 还可以定义任意命名的额外变量,后续在 groups[*].* 里用 {var} 引用
  external_plans: "{home}/.claude/plans/my-project"
  internal_docs: "{repo}/docs"
```

### 内置变量(永远可用)

| 变量 | 含义 |
|------|------|
| `{repo}` | `paths.repo` 解析后的绝对路径。默认是配置文件所在目录。如果是相对路径,以配置文件目录为基准 |
| `{home}` | `$USERPROFILE`(Windows)或 `$HOME`(Linux/macOS) |
| `{main_repo}` | 如果 `{repo}` 是 git worktree(`.git` 是文件 + 父目录叫 `worktrees`),上溯到 main repo · 否则等于 `{repo}` |
| `{env:VAR}` | 环境变量 `VAR` · 找不到则空串 |

### 自定义变量

`paths.*` 下面的任意 key 都会被注册为变量。求值时支持引用其他变量:

```yaml
paths:
  repo: "."
  docs: "{repo}/docs"
  plans: "{home}/.claude/plans/myproject"
```

之后在 `groups` 里:

```yaml
groups:
  - name: Plans
    scan: { dir: "{plans}/roadmap", recursive: true }
```

变量未定义时**保留原文**(不报错),方便 `--debug` 时一眼看出哪个变量没解析。

### worktree 处理

典型用法:在 `.claude/worktrees/<wt-name>/` 装 worktree。在 worktree 内跑 build 时,`{main_repo}` 会自动指回 main(用于读 main 的 DESIGN.md 等)。其他项目不用 worktree 就忽略这个变量。

---

## `groups` · 文档分组

每个 group 是侧边栏的一节。Group 内的文件可以三种方式提供:

### 1. 显式列表 · `files`

```yaml
- name: Overview
  icon: O
  color: primary
  files:
    - { title: README, path: "{repo}/README.md" }
    - { title: CHANGELOG, path: "{repo}/CHANGELOG.md" }
    - { title: 项目说明, path: "{repo}/CLAUDE.md" }
```

适合:每一条都是手挑的,不会动态增长。"Overview" / "项目说明" / "Design System" 是典型场景。

### 2. 目录扫描 · `scan`

```yaml
- name: Spec · Modules
  icon: "6"
  color: primary
  scan:
    dir: "{repo}/docs/spec/module"     # 必填
    pattern: "*.md"                     # 默认 "*.md"
    recursive: false                    # 默认 false
    title_transform: prefix-dot-titlecase   # 见下方
    exclude_underscores: true           # 默认 true · 跳过 _xxx.md 与 README.md
```

适合:目录里会持续加新文件 · `spec/concept/` / `spec/module/` / `plan/` / `task/` / `RFC/` 都是典型场景。

#### `title_transform` 选项

把文件名翻译成展示标题。三个内置 transform:

| transform | 输入 → 输出 | 用途 |
|-----------|------------|------|
| `stem` | `C03-site-adapter.md` → `C03-site-adapter` | 默认值(非递归扫时)· 不动文件名 |
| `prefix-dot-titlecase` | `C03-site-adapter.md` → `C03 · Site Adapter` | spec/concept 这种 `<ID>-<name>.md` 命名最好用 |
| `path-slash` | `roadmap/00-master.md` → `roadmap / 00-master` | 递归扫时默认值 · 把子目录加进 title |

### 3. Glob 模式 · `glob`

```yaml
- name: External roadmap
  icon: R
  color: storm-deep
  glob:
    - "{home}/.claude/plans/my-project/**/*.md"
    - "{home}/Documents/notes/my-project-*.md"
```

适合:文件分散在多个不连续路径,或要跨工作目录引入文档。`**/*.md` 是递归(Python `glob.glob(recursive=True)` 语义)。

### Group 公共字段

```yaml
- name: <str>           # 必填 · 侧边栏组标题
  icon: <single char>   # 默认 "·" · group-label 左边的小方块
  color: <token>        # 默认 "primary" · 见下方 token 列表
  files / scan / glob:  # 至少给一种;同时给两种也行,会合并
```

#### `color` 可用 token

`primary` · `primary-bright` · `primary-deep` · `graphite` · `storm-deep` · `ink` · `bloom-deep` · `bloom-coral`

如果传了 token 名以外的值,前端会回退到默认蓝。要加新颜色?在 `design.colors` 里加 + 在 template 的 `.sidebar .group-label .group-icon.color-<name>` 加 CSS rule。

### 同一 group 内三种来源混用

允许。例如 "RFCs" group 用 `files` 显式列出 4 条 RFC + DATA_SCHEMA 就是典型做法。如果想加一个"我手挑两篇 + 再扫一个目录"的 group,直接两个 block 都给:

```yaml
- name: Mixed
  icon: M
  color: graphite
  files:
    - { title: 主索引, path: "{repo}/INDEX.md" }
  scan:
    dir: "{repo}/docs/notes"
    recursive: true
```

---

## `frontmatter` · YAML 头治理 + 看板

```yaml
frontmatter:
  enabled: true                       # 默认 true · 关掉就完全不解析 frontmatter
  status_progress_ranges:             # status × progress 一致性检查的区间
    not-started: [0, 0]
    planned: [0, 15]
    in-progress: [5, 95]
    blocked: [0, 100]
    done: [100, 100]
    deferred: [0, 100]
  kanban:
    enabled: false                    # 默认 false · 不开就只有文档视图
    card_types: [module, concept]     # 默认空(所有 type 都进卡)
    kpi_type: module                  # 默认 "module" · KPI 与 Kanban 主聚合
    sprint_order: [M0, M1, M2, M3]    # 默认空 · timeline 排序的优先顺序
```

### `status_progress_ranges`

每行是 `<status>: [min_progress, max_progress]`(闭区间)。校验时:

- `status` 不在表里 → warning `"unknown status 'xxx'"`
- `progress` 在表里但越界 → warning `"progress=N out of range [a, b] for status=S"`

警告只是 stderr 打印 + build 终端 `[!] N frontmatter warning(s)`,不会 fail build。

如果你的项目用不同的 status 词汇(`todo` / `wip` / `shipped`),把整张表替换:

```yaml
status_progress_ranges:
  todo: [0, 0]
  wip: [1, 99]
  shipped: [100, 100]
```

但要注意:前端 Kanban 的 5 列(`STATUS_ORDER`)硬编码了默认这套词(`planned` / `in-progress` / `blocked` / `done` / `deferred`)。换词汇就要同步改 `templates/index.html.tmpl` 里的 `STATUS_ORDER` / `STATUS_LABEL` / `STATUS_COLOR`。

### `kanban.card_types`

只有这些 `type:` 值的文档才作为卡片进入 dashboard。例:

```yaml
kanban:
  card_types: [module, concept, task]
```

→ 一个 frontmatter `type: rfc` 的文档不会出现在 dashboard,但侧边栏照常列出。

留空 / 不设就是**全部 type 都进卡**(只要文档有 `id`)。

### `kanban.kpi_type`

KPI bar + Module Kanban + Sprint Timeline 三个区块,都只统计 `type` 等于 `kpi_type` 的卡片。其他 type(比如 `concept`)会出现在底部的 Concept Grid。

### `kanban.sprint_order`

Sprint Timeline 排序时,这个列表里的 sprint 名优先(按列表顺序)· 不在列表里的 sprint 排到末尾,字母序。

```yaml
sprint_order: [M0, M1.1, M1.2, M2, M3, GA]
```

完整示例见 `examples/full.yaml`。

---

## `design` · 颜色 token override

```yaml
design:
  colors:
    primary: "#3b82f6"
    primary_deep: "#1d4ed8"
    primary_bright: "#60a5fa"
    primary_soft: "#dbeafe"
    # 任何 --colors-<name> token 都可覆盖
```

实现机制:把 `colors.<name>: <value>` 写进 `:root { --colors-<name>: <value>; }` 末尾。CSS 后定义的同名变量会覆盖前面,所以无侵入。

完整 token 列表见 `references/design_tokens.md`。

---

## 路径解析的优先级与排错

build 流程:

1. 加载配置 → 计算 `vars_` 字典(`repo` / `home` / `main_repo` + 自定义)
2. 对每个 group,先处理 `files` → 再 `scan` → 再 `glob`
3. 每条 entry 的 `path` 经过 `{var}` 替换 → 转 `pathlib.Path`
4. `Path.exists()` 判断 → 不存在则 `exists: false` 进 payload(不丢)

排错:`python -m docs_cockpit build --debug` 会打印解析后的 `vars_` 字典与 output 路径。最常见的问题是 `paths.repo` 写错(配置文件在 `<x>/docs-cockpit.yaml` · 但 repo 写了 `./..` 之类的相对路径)。绝大多数情况下,**把 `paths.repo` 干脆删掉**就行 — 默认就是配置文件所在目录。

---

## 最小可行配置(粘贴可跑)

```yaml
project:
  name: MyProject

groups:
  - name: Docs
    icon: D
    color: primary
    scan:
      dir: docs
      recursive: true
```

3 行真功夫。把所有 MD 都堆进一组,默认 `path-slash` transform 把子目录加进 title。看板未启用 · UI 自动隐藏 toggle,只显示文档视图。
