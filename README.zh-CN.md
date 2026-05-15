[English](README.md) · **中文**

# docs-cockpit

> 单文件项目**模块进度 dashboard** · 由 `docs/spec/module/M*.md` 的 YAML frontmatter 驱动 · 浏览器 `file://` 直接打开 · 改 md 重跑就同步。

> **⚠️ 0.2.0 产品转型**:docs-cockpit 从 "MD 文档预览" 转为 "项目模块 dashboard"。0.1.x → 0.2.0 配置迁移见 [CHANGELOG.md](CHANGELOG.md)。

`docs-cockpit` 解决一个具体问题:**项目有几十个模块 / 概念 spec 散落各处 · 你需要一个 dashboard 看哪些在做 / 哪些卡了 / 哪些做完了 · 但不想为此装 Jira / Notion / Linear**。它扫 `docs/spec/module/*.md` + `docs/spec/concept/*.md`,读 YAML frontmatter(id / status / sprint / progress / desc / subtasks),产出一个自包含的 `index.html` dashboard。

亮点:

- **模块 Kanban** · 5 列(not-started / planned / in-progress / blocked / done)· 点卡片弹 drawer 含 desc / status select / progress 滑块 / subtask checkbox · localStorage 持久化用户覆盖
- **Sprint Timeline** · 按 frontmatter `sprint` 字段分组 · 平均 % 显示 · locale 排序
- **概念 Grid** · 底部 grid · 5 字段简化卡片
- **System Docs Drawer** · 手挑常驻入口(CLAUDE.md / PRD / DESIGN.md / RFC / memory / roadmap)· topbar 按钮弹出
- **Subtask 自动 progress** · `manualProgress: false` 时按子任务完成率算 progress
- **机器可读的 `state.json`** · sidecar JSON 给 sibling status skill 回答 blocker / 周报问题用
- **跨平台** · 纯 Python 3.10+ + pyyaml · Windows / macOS / Linux 同一份 yaml 跑
- **以 Claude Code plugin 形式发布** · 三个 skill(`docs-cockpit` / `docs-cockpit-status` / `docs-cockpit-update`)+ 三个 slash command(`/docs-cockpit:build` / `:status` / `:update`)

---

## Quickstart · Claude Code 用户(60 秒)

docs-cockpit 是**为 Claude Code 优先设计的 plugin**。装它就两条命令 + 一句话让 Claude 做事。

```bash
# 1. 在 Claude Code 里注册 plugin marketplace
/plugin marketplace add Guohao1020/docs-cockpit

# 2. 装 CLI(Claude 作为子进程调它)
pip install git+https://github.com/Guohao1020/docs-cockpit.git

# 3. 重启 Claude Code · 让 plugin 加载
```

然后在任何项目里,跟 Claude 说:

> 把 `docs/spec/module/` 下的 md 做成 dashboard

Claude 自动触发 `docs-cockpit` skill,**帮你写 `docs-cockpit.yaml`,跑 `docs-cockpit build`**,产出 `docs/index.html` 可以直接打开。

**就这样。三条命令 · 配置和 build 都是 Claude 做。**

> 不用 Claude Code(Codex / Cursor / Gemini / 单纯 Python CLI)?跳到 [Install · 按工具选](#install--按工具选)。

### Dashboard 长啥样

Claude 装完跑完后,打开 `docs/index.html`:

- **Topbar**:项目品牌 + 最后 build 时间 + "系统文档" drawer 按钮
- **Hero gauge**:总体 % 进度
- **KPI strip**:总数 / done / in-progress / blocked
- **模块 Kanban**:5 列状态分布 · 点卡片弹 drawer 含 subtask 勾选 + progress 滑块
- **Sprint Timeline**:模块按 sprint 分组 + 平均 %
- **概念 Grid**:底部简化卡片

模块要进 Kanban · MD 顶部需 YAML frontmatter:

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

重启 Claude Code → plugin 自动从 GitHub fetch → 3 个 skill(`docs-cockpit` / `docs-cockpit-status` / `docs-cockpit-update`)+ 3 个 slash command(`/docs-cockpit:build` / `:status` / `:update`)生效。

**自动升级**:在 `~/.claude/settings.json` 的 marketplace 条目加 `"autoUpdate": true`(或者直接说 *"升级 docs-cockpit"* · Claude 一气呵成)。Plugin 层重启时自动 re-fetch · CLI 层偶尔需要 `pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git`。

**`/plugin` 不可用**(老版本 Claude Code · PR review 等受限 surface)→ 手工 merge `~/.claude/settings.json`:

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

#### Claude 听啥触发(skill auto-trigger)

| 你说 | Claude 触发 |
|---|---|
| "把 docs 做成 dashboard" / "bundle docs into a dashboard" | `docs-cockpit`(写 yaml + 跑 build) |
| "这周 sprint M1.2 进度" / "哪些 module 卡了" / "weekly status" | `docs-cockpit-status`(读 state.json · 输出叙述) |
| "升级 docs-cockpit" / "update docs-cockpit" | `docs-cockpit-update`(pip + plugin re-fetch + autoUpdate 翻 flag) |

或者直接 slash command:`/docs-cockpit:build`、`/docs-cockpit:status weekly`、`/docs-cockpit:update`。

### B. 其他 vibe coding 工具 · 手动复制 skill

**Codex / Cursor / Gemini / OpenCode** 等工具(有 `~/.claude/skills/`-类似的 skill loading 机制)· 手动复制 SKILL.md:

```bash
# 仓 clone 到本地
git clone https://github.com/Guohao1020/docs-cockpit.git ~/.tools/docs-cockpit

# 复制 skill 到你工具的 skill 目录
# (把 <skills-dir> 替换成你工具的路径 · 比如 ~/.codex/skills/ / ~/.cursor/skills/)
cp -r ~/.tools/docs-cockpit/skills/docs-cockpit         <skills-dir>/
cp -r ~/.tools/docs-cockpit/skills/docs-cockpit-status  <skills-dir>/
cp -r ~/.tools/docs-cockpit/skills/docs-cockpit-update  <skills-dir>/

# 还要装 CLI · skill 才能调
pip install git+https://github.com/Guohao1020/docs-cockpit.git
```

重启你的工具。skill 会按同样的自然语言短语触发(SKILL.md 里的 Claude-specific 路径语法可能需要微调)。

### C. 单纯 Python CLI(不用 AI 工具)

只想用命令行 · 自己写 `docs-cockpit.yaml`:

```bash
pip install git+https://github.com/Guohao1020/docs-cockpit.git
docs-cockpit init                          # 生成起步 yaml
# 编辑 docs-cockpit.yaml
docs-cockpit build                         # 默认读 ./docs-cockpit.yaml
```

开发 / fork 用 editable 模式:

```bash
git clone https://github.com/Guohao1020/docs-cockpit.git
cd docs-cockpit
pip install -e .
```

**需要 Python ≥ 3.10**。系统默认 Python 是 3.9 或更老 · 用 [`uv`](https://docs.astral.sh/uv/):

```bash
uv tool install --python 3.11 git+https://github.com/Guohao1020/docs-cockpit.git
```

---

## 配置

0.2.0 schema 有 4 个顶层 block:

```yaml
project:        { name, mark, tagline, eyebrow, output }
paths:          { repo, ... 任意自定义变量 }
system_docs:    [ { id, title, path, desc, icon } ... ]   # 手挑常驻入口
modules:        { files / scan / glob }                    # frontmatter 驱动 dashboard 卡片
concepts:       { files / scan / glob }                    # 简化 grid 卡片
frontmatter:    { enabled, status_progress_ranges }
```

完整参考配置 · 见 [`examples/full.yaml`](examples/full.yaml)(6 个 system_docs + 模块扫描 + 概念扫描 + frontmatter 治理)。每个字段语义和默认值 · 见 [`references/config_reference.md`](references/config_reference.md)。模块 / 概念的 frontmatter 字段约定(status × progress 校验 / subtask 自动 progress 推导等)· 见 [`references/frontmatter_conventions.md`](references/frontmatter_conventions.md)。

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
