# docs-cockpit

> Turn a folder of Markdown into a single-file project cockpit you can open with `file://`.

`docs-cockpit` 是一个 Claude skill + 独立 CLI 工具,把项目里散落的 MD 文档(PRD、spec、plan、RFC、task、design system、todos、session memory…)汇总成**一个自包含的 HTML 文件**,内置:

- **侧边栏导航** · 按你定义的 group 分组
- **文档视图** · 浏览器端 marked.js 渲染 + highlight.js 高亮 + 锚点跳转
- **可选项目看板** · KPI / 模块 Kanban / Sprint Timeline · 从 YAML frontmatter 自动算
- **localStorage 持久化** · 上次看到哪、看了什么视图,刷新后回来还在
- **CDN 兜底 banner** · 离线时显眼提示

是一个 file:// 单文件 · 不要 web server · 不要 build pipeline 之外的依赖。

## 安装

```bash
# 把仓库 clone 到本地
git clone <repo> docs-cockpit
cd docs-cockpit

# 装依赖(就一个 pyyaml)
pip install pyyaml
```

或装成 pip 包:

```bash
pip install -e <path-to-docs-cockpit>
```

## 用法

### 1. 给项目写配置

在项目根创建 `docs-cockpit.yaml`:

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

或拷一份模板:

```bash
python -m docs_cockpit init
# 写出 ./docs-cockpit.yaml,基于 examples/minimal.yaml
```

### 2. Build

```bash
python -m docs_cockpit build
# 默认读 ./docs-cockpit.yaml,输出到 ./docs/index.html
```

或指定路径:

```bash
python -m docs_cockpit build --config path/to/config.yaml --debug
```

### 3. 打开

```bash
# Windows
start docs/index.html

# macOS
open docs/index.html

# Linux
xdg-open docs/index.html
```

或直接拖进浏览器 · file:// 协议跑就行。

## 用作 Claude skill

把整个目录拷进 `~/.claude/skills/docs-cockpit/`(或对应 skills 安装路径)。然后跟 Claude 说:

- "帮我把 docs/ 下的 MD 做成 dashboard"
- "把这个项目的 PRD / spec / plan 汇总成一个 HTML 看板"
- "我要一个实时同步的 docs 预览站"

Claude 会读 `SKILL.md` 自动走对应 workflow。

## 文档

- **`SKILL.md`** — Claude 用的主指令,含工作流与故障排查
- **`references/config_reference.md`** — `docs-cockpit.yaml` 全部字段
- **`references/frontmatter_conventions.md`** — 给 MD 加 YAML 头进看板
- **`references/design_tokens.md`** — 改品牌色 / 离线 vendor
- **`examples/minimal.yaml`** — 最小可行配置
- **`examples/sourcery.yaml`** — Sourcery 完整复刻(10 groups + 看板)

## 起源

抽自 [Sourcery](https://github.com/harvey/sourcery) 项目的 `scripts/build_docs_html.py`(~1800 行 inline · 含 HTML 模板)。

抽象做了:

1. `DOC_GROUPS` 硬编码 → YAML 配置
2. Sourcery-specific 路径 → `{repo}` / `{home}` / `{main_repo}` / `{env:X}` 变量
3. HTML 模板从 Python 字符串里抽出来,独立 `index.html.tmpl` 文件
4. 品牌 / 看板 sprint 顺序 / status 区间全部参数化

Sourcery 的原配置完整保留在 `examples/sourcery.yaml`,可作 "看板模式" 的参考。

## 许可

MIT
