<!-- 运维参考 · build Phase 0 + 渲染期排障（build Phase 7 / rebuild Phase 5）引用 · 原 docs-cockpit 主 skill 提取 -->

# docs-cockpit · 运维参考（bootstrap / config / upgrade / troubleshooting）

docs-cockpit 运维知识 SSOT：CLI 首次安装、config 结构概览、自身升级（以上为 build skill Phase 0 引用），外加渲染期故障排查（build Phase 7 / rebuild Phase 5 遇到异常时查阅）。不包含 frontmatter 字段（→ `references/schema.md`）和关联方法（→ `references/association-method.md`）。

---

## bootstrap

**触发时机** — 首次在新环境运行 `docs-cockpit <subcommand>` 前，先探测 CLI 是否存在：

```bash
docs-cockpit --version 2>/dev/null || echo "MISSING"
```
```powershell
# Windows PowerShell
try { docs-cockpit --version } catch { "MISSING" }
```

输出含 `MISSING` 则需要安装。下面四条按优先级排列——逐条尝试，第一条成功即停，不是顺序全跑（agent 自行判断短路，勿整块复制执行）：

```bash
# 1. uv（最优）
command -v uv >/dev/null && uv tool install --python 3.11 git+https://github.com/Guohao1020/docs-cockpit.git
# 2. pipx（次优）
command -v pipx >/dev/null && pipx install git+https://github.com/Guohao1020/docs-cockpit.git
# 3. pip --user（回退）
python3 -m pip install --user git+https://github.com/Guohao1020/docs-cockpit.git
# 4. pip（最后手段 · 系统 Python 可能需要 sudo）
pip install git+https://github.com/Guohao1020/docs-cockpit.git
```

安装过程**必须告知用户**，不能静默进行。说明范例：「Installing the docs-cockpit Python toolkit via uv (one-time setup)…」安装后执行 `docs-cockpit --version` 确认成功再继续。

若 bootstrap 失败（无 Python、网络封锁、写保护 /usr），**原样暴露错误信息**并询问用户如何处理，不要掩盖——后续所有操作都依赖 CLI。

**设计说明** — Claude Code plugin 系统目前无 post-install hook 可执行 pip install，所以安装逻辑放在 skill 里；首次构建时运行一次，后续 CLI 已在 PATH 则跳过。

---

## config

`docs-cockpit.yaml` 是驱动整个 build 的唯一配置文件。以下是关键结构概览；**完整字段定义见 `references/config_reference.md`，本节不重复它的内容**。

### modules / concepts 的三种扫描方式

```yaml
modules:
  scan:                                    # 方式 A · 整目录
    dir: "{repo}/docs/spec/module"
    title_transform: prefix-dot-titlecase
  glob:                                    # 方式 B · 通配符（必须是 list）
    - "{repo}/docs/spec/module/M*.md"
  files:                                   # 方式 C · 手动列举
    - "{repo}/docs/spec/module/M01-core.md"
    - "{repo}/docs/spec/module/M02-api.md"
```

`concepts:` 用相同的 `scan` / `glob` / `files` 结构。同一个 `modules:` 块可以混用三种方式——build 会合并（注意：同一文件若被 `files` 和 `scan` 同时命中，会生成两张卡）。

路径变量（`{repo}` / `{home}` / `{env:X}` / `{main_repo}`）的定义与解析规则见 `references/config_reference.md` 的「内置变量」表。

### 最小可用 config 骨架

```yaml
project:
  name: MyProject
  mark: M
  tagline: "项目进度概览"
  output: docs/index.html
paths:
  repo: "."
system_docs:
  - id: claude-md
    title: CLAUDE.md
    path: "{repo}/CLAUDE.md"
    desc: 项目根级 AI 协作约定
    icon: memory
modules:
  scan:
    dir: "{repo}/docs/spec/module"
    title_transform: prefix-dot-titlecase
```

完整字段（`frontmatter.status_progress_ranges`、`system_docs icon 枚举`、`project.eyebrow` 等）→ `references/config_reference.md`。

---

## Codex plugin marketplace

Codex-native installation uses the repo-scoped marketplace at `.agents/plugins/marketplace.json` plus the manifest at `.codex-plugin/plugin.json`:

```bash
codex plugin marketplace add Guohao1020/docs-cockpit
```

After adding the marketplace, install `docs-cockpit` from the Codex plugin directory. This does not replace the existing `.claude-plugin/` entry; both plugin surfaces point at the same `skills/`, `commands/`, and `hooks/` content and must share the same release version.

---

## upgrade

当用户说「升级 docs-cockpit」/「update docs-cockpit」/「看到 new version available banner」，执行 `docs-cockpit upgrade`。0.7.0+ 一条命令完成全流程：检测后端 → 对比版本 → 展示 CHANGELOG diff → 确认 → 升级 → 若 SKILL.md hash 有变更则原子清 cache + 提示重启。**常用 flag**：`--dry-run` · `--yes` · `--no-clear-cache`（仅当升级不含 SKILL.md 变更——即 patch 级 CLI-only 更新——才可用 `--no-clear-cache`；含 skill 变更时必须走完整原子清 cache） · `--skip-changelog`

### ghost state 警告

> **绝对不能**只让用户「重启 Claude Code」了事。

不清 plugin cache 直接重启会造成 ghost state（旧 SKILL.md + 新 CLI 不一致 → 路由错误）。正确流程是 `docs-cockpit upgrade`（cache 清除 + 重启提示为原子操作）。

### pre-0.7.0 手动回退

若 CLI 低于 0.7.0（报 `unknown subcommand: upgrade`），先升级 CLI：

```bash
pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git  # 或
uv tool upgrade docs-cockpit  # 或  pipx upgrade docs-cockpit
```

然后**手动清除 plugin cache** 并重启（先清后启，原子操作）：

```powershell
# Windows PowerShell
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\plugins\cache\*docs-cockpit*"
```
```bash
# POSIX / macOS / Linux
rm -rf ~/.claude/plugins/cache/*docs-cockpit*
```

---

## troubleshooting

渲染期常见故障（症状 → 原因 → 修法）。仅收录对照当前代码仍成立的条目：

| 症状 | 原因 | 修法 |
|---|---|---|
| render 后 `[WARN] 0 items`，看板空 | 所有路径解析到不存在的文件——几乎总是 `paths.repo` 配错或 scan 目录 typo | `docs-cockpit render --debug` 打印解析后的路径变量与每条 entry 的绝对路径，逐条核对 |
| 个别 module 不出现在 Kanban | frontmatter 缺 `id:`，或 id 是 `MXX` 这类模板占位符（设计上跳过，lint 会报 "looks like a template placeholder"） | 给 MD 补真实 id（格式见 `references/schema.md`） |
| `progress=N out of range [lo, hi] for status=...` | status 与 progress 不匹配 | 改 MD 的 status / progress 之一，或放宽 config 的 `frontmatter.status_progress_ranges` |
| render / lint 报其它 frontmatter issue | 字段不符规范 | 每条 issue 自带 suggestion + reference，按引指向的 `references/schema.md` 小节修 |
| dashboard 勾过的 subtask 状态「丢了」 | 勾选状态存浏览器 localStorage，按 `file://` URL 区分——换路径打开不带旧覆盖 | 用同一 `file://` 路径重新打开；要持久化回 MD 用 `docs-cockpit sync-status` |
| Copy prompt 按钮灰 / 点击 toast 报错 | `prompts.js` 不在 `index.html` 旁。最常见：提交了 `index.html` 但 `.gitignore` 排除了 `docs/*.js` | 重跑 `docs-cockpit render` 重新生成；若提交构建产物，`index.html` + `state.json` + `prompts.js` 三件一起提交 |
| drawer「消失」/ URL 停在 `#/module/...` 回不去 | hash 路由按设计工作（split-view 深链，方便把某 module 视图链接发给他人） | 点 topbar 项目 brand 或按 Esc 返回 dashboard |
| 断网打开 dashboard 字体 / MD 预览异常 | Google Fonts 与 marked.js 走 CDN | 预期降级：看板本体可用，内联 MD 预览自动回退 `<pre>`，字体回退系统字体——无需修复 |
| 升级后 skill 行为没更新（ghost state） | plugin cache 未清 | 见上文 `## upgrade`——走 `docs-cockpit upgrade` 原子清 cache，不能只重启 |
