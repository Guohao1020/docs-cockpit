# CHANGELOG

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) · 版本号采用 [SemVer](https://semver.org/lang/zh-CN/)。

## [Unreleased]

## [0.11.0-alpha.2] · 2026-05-18

v0.11 W1 数据层完成 · subtask 升级为一等公民。M01 从 70% → 90% · M02 从 33% → 44%。仍按 plan §11 走 Step 3 → Step 4(W3 prompt scaffolding)。

### Why

0.10 subtask 是字符串数组 · 没 id / 没 code anchor / 没 docs 引用。dashboard 上能勾 checkbox 但状态在跨 build / 改 title 时丢失 · localStorage 用 index 为 key · 加新 subtask 全错位。v0.11 W1 把 subtask 升为对象 · 接代码 anchor + linked docs · 驱动 drawer 里「点 subtask 看代码 + spec」体验。

### Added · schema.py W1

- `normalize_subtasks(raw, module_id)` · 把 list[str] / list[dict] / 混合统一为对象数组 · 自动补 id(sha1-of-title)+ 默认 status
- `validate_subtask_schema(subs, module_id, path)` · id 唯一性 · status 枚举 · title 必填 · 3 档 Issue
- `VALID_SUBTASK_STATUSES = {not-started, in-progress, done, blocked}` · plan §6.1 lock
- `_subtask_id_for(module_id, title)` · `<module-id>-<sha1(title)[:6]>` 稳定 id 算法

### Added · paths.py W1

- `_resolve_code_anchor(raw, module_path, repo_root, vars_)` · 解析 `path:start-end` / `path:single` / `path` 三种格式 · 走三步 fallback 拿绝对路径
- `_parse_code_ref` helper · 切 path + line range
- `_read_code_lines` · 带 `@functools.lru_cache(maxsize=256)` · 多 subtask 引用同 path 不重复读 fs(plan-eng-review 4A · 1.5-3x 加速)
- Defensive IO 全套(plan-eng-review 3A · plan §6.1):
  - `OSError` / `PermissionError` · warn + None preview
  - `UnicodeDecodeError` · warn + None preview
  - binary 检测(前 1KB null byte)· skip
  - 文件 > 5MB · skip
  - 行号越界 · skip
- 输出含 `vscode://file/...` 深链 · ±5 行 context · 800 char hard cap

### Added · body parser 内联 `@code` / `@docs` 语法 (plan §6.1)

```markdown
- [x] Lane A · BrowserVendor abstraction @code:sourcery/x.py:42-89 @docs:M09-spec
```

切出:
- title = "Lane A · BrowserVendor abstraction"
- code = "sourcery/x.py:42-89"(单个)或 `["a.py", "b.py"]`(多个)
- docs = "M09-spec"(单个)或 list(多个)

写在 `extract_subtasks_from_body()` 里 · build 时自动透传到 normalize_subtasks。

### Added · build.py wire-up

`_build_card` 用 `normalize_subtasks` 把所有 subtask 统一对象 schema · 然后对每条 subtask 的 `code` 字段(string / list)调 `_resolve_code_anchor` · 输出 `subtasks[].code_anchors[]` 含 resolved path + preview + vscode_url · drawer 后续直接渲染。

### Added · `docs-cockpit migrate-subtasks <file>` CLI

把 v0.10 字符串 subtasks 升级到 v0.11 对象 schema · 默认 dry-run 输出 diff · `--apply` 写回 + 生成 `.bak` 备份。M02 subtask 7 完成。

### Added · 单元测试

- schema W1:11 个 `normalize_subtasks` 测 + 7 个 `validate_subtask_schema` 测 + 4 个 `extract_subtasks_from_body` 内联语法测 = 22 新测
- paths W1:6 个 `_parse_code_ref` 测 + 6 个 `_resolve_code_anchor` 测(含 binary / OOR / empty / truncated)= 12 新测
- 总 pytest:**93 passed in 0.17s**(0.11.0-alpha.1 是 52 · 本 alpha.2 多 41 测)

### Changed · M01 / M02 subtask 状态

- M01:7/10 → 9/10(70% → 90%)· 还差 1 个 sidecar prompts.js(Step 4)
- M02:3/9 → 4/9(33% → 44%)· 还差 5 个 W3(Step 4)
- 这些 subtask checkbox 在 MD 里勾上 · build 自动算 progress 反映

### Not changed

- HTML template / state.json 主结构 / drawer 渲染 · 这些是 Step 2 UI 范围
- 用户已有的 subtask:list[str] / list[dict{title,done}] 全部兼容 · normalize 自动 upgrade · `subtasks[].code_anchors[]` 是新增字段 · 前端 0.10 不消费也不破

### What's next · Step 4 W3 prompt scaffolding

- `docs_cockpit/prompt.py` + Jinja2 SandboxedEnvironment + 4 内置 template
- `docs-cockpit prompt <module-id> [<subtask-id>]` CLI(M02 subtask 4/5/6)
- `docs-cockpit lint --prompts`(M02 subtask 8)
- `docs/prompts.js` sidecar 输出(M01 subtask 8)
- `tests/integration/test_cli_v011.py`(M02 subtask 9)

## [0.11.0-alpha.1] · 2026-05-18

v0.11 driver-seat plan §11 Step 1 完成 · 给 W1 / W3 / UI split-view 立个测试 + 模块化基础。alpha.1 用户视觉**无感知** · 全是内部 refactor。

### Why

v0.11 W1(subtask 一等公民)+ W3(prompt scaffolding)+ Step 2 UI split-view 这三件事要在 `build.py` 同一个 1200 行文件里加 5-7 个新函数 + 改 HTML template 大半 + 引入 Jinja2 prompt 渲染。在动这些之前 · Beck 「make the change easy, then make the easy change」· 先把 build.py 切薄 + 立 pytest 基础 · 之后每一个 W 改起来都简单 · 也有测试 cover。

### Changed · `docs_cockpit/build.py` 拆 3 个新模块

build.py 从 1201 行 → 575 行(-52%)· 跨 4 个独立 commit · 每个能独立验证:

| commit | 新文件 | 内容 |
|---|---|---|
| `71dfa82` | `docs_cockpit/schema.py` | `Issue` 类 / `validate_meta` / `extract_subtasks_from_body` / `extract_docs_from_body` / `split_frontmatter` / `slugify` / 5 个 body section regex / 3 个 status/type enum |
| `639bc3a` | `docs_cockpit/paths.py` | `_build_vars` / `_expand` / 3 个 title transforms / `_resolve_group_files` / `read_md` / `_resolve_doc_path` / `_resolve_and_embed_docs` |
| `d543aca` | `docs_cockpit/cli.py` | `main()` argparse dispatcher |
| `c195d06` | `tests/` | pytest 基础 + 52 unit tests(schema.py 32 测 · paths.py 20 测) |

`build.py` 通过 `from .schema import ...` / `from .paths import ...` / `from .cli import main` re-export 所有公开 API · 外部 `from docs_cockpit.build import validate_meta` 这类老 import 全部 work · 老 `pyproject.toml entry-point docs_cockpit.build:main` 也不动。

### Added · pytest 测试基础 (plan-eng-review 4A)

- `pyproject.toml` 加 `[project.optional-dependencies] dev = ["pytest>=7", "pytest-cov>=4"]`
- `pyproject.toml` 加 `[tool.pytest.ini_options]` · testpaths / markers / addopts 齐
- `tests/__init__.py` + `tests/unit/__init__.py` + `tests/conftest.py`(sys.path 插入)
- `tests/unit/test_schema.py` · 32 个测 · 覆盖 schema.py 所有公开 API
- `tests/unit/test_paths.py` · 20 个测 · 覆盖 paths.py 所有公开 API
- 装法:`pip install -e .[dev]` · 跑:`pytest tests/ -v`
- 实测:52 passed in 0.12s

### Added · `.github/workflows/test.yml` CI matrix

3 Python (3.10 / 3.11 / 3.12) × 3 OS (Ubuntu / macOS / Windows) = 9 个 cells。覆盖:
- Windows backslash 路径处理(测 `_expand` + `_resolve_doc_path` 在 Windows 下行为)
- macOS fs case-sensitivity(`docs/Spec/Module/X.md` vs `docs/spec/module/x.md`)
- Linux 默认 utf-8 encoding(测中文 frontmatter)

每个 push / PR 都跑 · `fail-fast: false` 让所有 cell 都跑完 · 不在第一个失败就停。

### Not changed · 用户视觉

- HTML template 一行没动 · dashboard 看起来跟 0.10.2 完全一样
- state.json schema / payload 结构不变
- 所有 7 个 CLI 子命令(build / lint / init / migrate / browse / portfolio / upgrade)接口和输出格式不变(stdout 仍是 0.10.2 的 fenced bash blocks 格式)
- 用户 docs-cockpit.yaml / module MD / subtask 写法不变

### Migrate

无需迁移 · 用户:
- 跑 `docs-cockpit upgrade` 拿 0.11.0-alpha.1 · 或者 `pip install --upgrade docs-cockpit`
- 现有 docs-cockpit.yaml + MD 文件不动
- build 结果完全一样(366,628 bytes HTML · 6 modules · 43 subtasks · 21 done · 0 issues 在 docs-cockpit 自身 dogfood 上)

### What's next (alpha.2 / alpha.3 / alpha.4 → 0.11.0)

- **alpha.2** · UI split-view 二级页面(Step 2 · §6.6)· 用户**真正能看到**的第一个 v0.11 改进
- **alpha.3** · W1 subtask schema 一等公民(Step 3 · §6.1)
- **alpha.4** · W3 prompt scaffolding(Step 4 · §6.2)
- **0.11.0** · 收口 + 公告(Step 5)

## [0.10.2] · 2026-05-18

让 Claude Code 用户在每次 build / browse 后能一键打开 dashboard,而不是手动复制路径。

### Why

跑完 `docs-cockpit build` 后,CLI 输出三行带缩进的提示(`  start D:\...`、`  open D:\...`、`  xdg-open D:\...`)。这种格式 Claude Code 不会渲染成可点击的运行按钮 · 用户得手动选中、复制、粘到终端。0.10.1 之前我们没注意这个 UX 缝。

### Changed · build.py + browse.py stdout 格式

跑完后输出改成三个独立的 markdown fenced bash block(每个 OS 一个),Claude Code 看到自动给每个块加 run 按钮,用户点对应系统那一个就行。终端用户看到的就是 fence 包着的命令 · 也不影响 copy-paste。

旧格式(0.10.1 及之前):

```
Open in browser:
  start D:\...    # Windows
  open  D:\...    # macOS
  xdg-open D:\... # Linux
```

新格式(0.10.2):

````
Open in browser (Claude Code: 点击对应系统的代码块右上角 run 一键执行):

```bash
start D:\...
```

```bash
open D:\...
```

```bash
xdg-open D:\...
```
````

### Changed · skills/docs-cockpit/SKILL.md 加 Post-build reporting 节

写一条规则给 Claude:跑完 `docs-cockpit build` / `docs-cockpit browse` 后,在 chat reply 里必须把开启命令以独立 fenced bash block 列出 · 不能合并成一个多行块。CLI 的 stdout 已经是这格式 · 直接 echo 就行 · 但 Claude 总结回复时不能漏。

### Not changed

- 不动 build engine / state.json schema / frontmatter spec / config schema
- 不动 4 个 skill 的触发条件 / scope · 仅 docs-cockpit skill 加一段 output 规则
- 严格按 CLAUDE.md SemVer 约定 · SKILL.md 改 = 至少 minor · 但本次 SKILL.md 改的是「输出格式 follow-up 规则」· 不是 trigger / scope / schema · 不会触发 ghost-state 风险 · patch 表达准确

### Migrate

无需迁移 · 升级 CLI 即可,旧用户的 docs-cockpit.yaml / MD / build artifact 全部兼容。

## [0.10.1] · 2026-05-18

Dogfood docs-cockpit 自己 · 验证 v0.10 schema 能否承载 docs-cockpit 项目本体 · 同时为 v0.11 driver-seat plan(`docs/plans/P-v0.11-driver-seat.md`)的 Step 0 prerequisite。本 patch 不动 build engine / schema · 只引入项目自身的 `docs-cockpit.yaml` + 6 个 module MD + 关联文档 · 让 docs-cockpit 自己变成 docs-cockpit 看板。

### Why

v0.11 driver-seat plan 通过两轮 review (office-hours + plan-eng-review)· 落地前需要先把 docs-cockpit 自己接到 docs-cockpit 上,否则两份关键设计文档(driver-seat plan + test plan)在 repo 里是孤立 markdown · 形不成可视化驾驶舱。这次 patch 是 v0.11 W1 设计输入的来源:dogfood 暴露的 schema 缺口直接喂 v0.11 W1。

### Added · `docs-cockpit.yaml`(repo 根)

- `project.name: docs-cockpit` · `mark: D` · tagline 描述双形态(CLI + plugin)
- `system_docs` 7 项:CLAUDE.md / README EN / README 中文 / CHANGELOG / 3 个 references
- `modules.scan: docs/spec/module` · v0.10 默认机制
- 暂不开 concepts(等 v0.11 W1 落地后再补)

### Added · `docs/spec/module/` 6 个 module MD

- M01 build-engine(in-progress · 85% · v0.11 W1 即将动它)
- M02 cli(in-progress · 80% · v0.11 W3 加 prompt 子命令)
- M03 plugin(in-progress · 85%)
- M04 author-skill(in-progress · 80% · §2.4 + §10 待补)
- M05 portfolio(done · 100%)
- M06 browse-reader(done · 100%)

总 43 个 subtasks(21 done / 43)· overall progress 88.3% · build 时 0 issues。

### Added · `docs/plans/`

- `P-v0.11-driver-seat.md`(approved · /office-hours 2 轮 + /plan-eng-review 4 sections review)
- `P-v0.11-test-plan.md`(配套测试计划 · pytest + CI matrix + manual QA)

### Dogfood 暴露的 v0.10 schema 缺口(v0.11 W1 input)

- `_SUBTASK_SECTION_RE` 不识别带 `§` 字符的 section 标题(`## §3 · 待办` 不命中 · 必须用 `## 3 · 待办`)· 本 patch 暂时按 v0.10 规范 ship · v0.11 W1 增强 regex 支持 `§N` / `Section N` 等可选前缀
- subtask 仍是字符串数组 · 无 id / status / code / docs ref · 是 v0.11 W1 的核心改造点

### Fixed · `build.py::render_html` · `</script>` 字面串导致 dashboard 白屏

Dogfood docs-cockpit 自己时 · `P-v0.11-driver-seat.md` body 含字面 `</script>`(讨论 v0.11 W1 的 sidecar 策略时引用 `<script type="application/json">...</script>` 示例 token)· build 把 plan 全文嵌入 `state.json::modules[].docs[].content` 后 · 用 `template.replace("__DOCS_JSON__", docs_json)` 单点替换写到 HTML · 浏览器在解析 `<script>` tag 时遇到 payload 内字面 `</script>` 提前关闭 script tag · 剩余 JSON 溢出为 HTML body 文本 · `JSON.parse` 拿不到完整数据 · 整个 dashboard 渲染 0 modules / 0 concepts。

修法(2 行):

```python
docs_json = docs_json.replace("</script>", "<\\/script>")    # JSON spec 允许 forward-slash escape
return template.replace("__DOCS_JSON__", docs_json, 1)        # count=1 防 paranoia
```

这是任何用户 spec / plan / RFC 引用 script 示例代码都会触发的 bug · 不限于 dogfood 场景 · 因此走 patch fix 而不是 v0.11 minor。v0.11 W1 改 sidecar(`prompts.js` / `code_previews.js`)+ `<script type="application/json">` 包裹后 · 本 fix 仍是 defense-in-depth。

修复后 dogfood verify:`docs/index.html` 314546 字节 · 11 个 `</script>` 是 template 自带 script tag · 23 个 payload `</script>` 已转义为 `<\/script>` · dashboard 正常渲染 6 modules / 43 subtasks / 0 issues。

### Not changed

- 不动 `docs_cockpit/build.py` 的核心 schema / pipeline · 仅 2 行 bug fix
- 不动 `docs_cockpit/*.py` 其他模块 · `docs_cockpit/templates/*` · 这些是 v0.11 minor 范围
- 不动 4 个 skill SKILL.md 主体 · 同上

### Migrate

无需迁移 · 老用户项目不受影响 · 仅 docs-cockpit repo 自身增加 docs/ 内容。

## [0.10.0] · 2026-05-15

跨项目周报。引入"用户级 portfolio 注册表"概念 · 新 skill +
CLI 子命令组 + 周快照机制 · 解决"同时跑多个 docs-cockpit 项目时,
怎么出一份统一周报"这个问题。

### Why

用户实测场景:同时维护 Sourcery + Bastion 两个 docs-cockpit 项目,
每周想要一份覆盖两个的周报。0.9.x 的 `docs-cockpit-standup` 是
单项目设计 —— 读一个 `state.json` 出叙事。要跨项目得手工跑两遍
+ 自己拼接 · 周差异(本周新 done / 新 blocker)也算不出来 ·
因为没有快照机制。

### Added · `docs-cockpit portfolio` CLI 子命令组

`docs_cockpit/portfolio.py` ~280 行 · 含:

```bash
docs-cockpit portfolio add [path]    # 把当前目录或指定路径加进注册表
docs-cockpit portfolio list          # 表格展示 · 含 state.json mtime · stale 警告
docs-cockpit portfolio remove <name> # 移除(snapshot 保留)
docs-cockpit portfolio tag <name> +work -archived  # 加/减标签
docs-cockpit portfolio snapshot      # 给每个项目的 state.json 存今日快照
```

注册表路径: `~/.docs-cockpit/projects.yaml`(跟 Claude Code 路径解耦
· standalone CLI 也能用)。快照路径: `~/.docs-cockpit/snapshots/
<project>/<YYYY-MM-DD>.json`。

注册表 schema:

```yaml
projects:
  - name: Sourcery
    state: D:/harvey_work/Sourcery/docs/state.json
    repo:  D:/harvey_work/Sourcery
    tags:  [active, work]
    added: 2026-05-15
```

`add` 命令自动从 CWD 推断 `state.json` 位置(优先读 `docs-cockpit.yaml`
里的 `project.output` · 退回 `docs/state.json` · 再退回 `state.json`)。
重复 add 同名项目走更新路径 · 不报错 · 方便 CI / script。

### Added · `docs-cockpit-portfolio` skill

`skills/docs-cockpit-portfolio/SKILL.md` ~250 行 · 按 skill-creator 写法:

- **Trigger 设计 pushy**:任何"周报 / weekly report / 多项目状态"
  意图 · 即使用户没显式说"portfolio" · 即使用户在 CWD 没 docs-cockpit.yaml
  下问状态(说明他不在某个具体项目里)
- **跟 standup 的边界**:standup 是单项目 · portfolio 是多项目 ·
  description 里写清 discriminator
- **Workflow**:`docs-cockpit portfolio list` → 编号清单挑选 →
  各项目 load state.json + 找最近的 5-14 天前快照 → 跨快照算 diff
  → 拼装多项目 Markdown 周报
- **报告模板固化**: `🚀 Wins this week` / `🔥 Blockers` / `📋 In flight`
  / `📈 Progress this week` / `🆕 Added this week` / `🥶 Stale` /
  `⚠️ Frontmatter issues` 七节 · 加 cross-project highlights
- **diff 计算规则**(skill body §4):newly-done / newly-blocked /
  newly-added / progress jumps(≥15 点 · 过滤噪音)/ sprint move /
  subtask shifts

### Added · `/docs-cockpit:weekly` slash command

`commands/weekly.md` · 显式入口 · 支持参数: `/docs-cockpit:weekly`
(交互式)· `/docs-cockpit:weekly all` · `/docs-cockpit:weekly active`
· `/docs-cockpit:weekly Sourcery,Bastion`。

### Changed · `docs-cockpit-standup` description 加 discriminator

明示"如果用户问周报不限定项目 → 给 portfolio · 这个 skill 只管单项目"。
避免两个 skill 抢同一类问题。

### Changed · 主 skill `docs-cockpit/SKILL.md` 注册表 sibling

Scope 段从"3 skills"改成"4 skills"(0.10.0 后 portfolio 加入兄弟链):
- `docs-cockpit` (写 cockpit-level)
- `docs-cockpit-standup` (读单项目)
- `docs-cockpit-portfolio` (读多项目 · 新)
- `docs-cockpit-author` (写单个 doc)

### Notes

- portfolio 注册表是**用户级**(`~/.docs-cockpit/`)· 不进任何项目仓库 ·
  这样一个用户多套 docs-cockpit 项目共享一份 portfolio
- snapshot 没有自动 prune · 一项目一年 52 张快照 ≈ 几 MB · 用户级
  目录扛得住 · 日后可加 `--prune --keep N`
- 第一次跑没有 5-14 天前 snapshot → 退化成"只看现状"模式 +
  提醒用户每周跑 `docs-cockpit portfolio snapshot`
- 跨项目 diff 只算 `modules[].id` 主键 · `concepts[]` 暂不参与
  diff(变化频率低 · 噪音大)
- 想让 snapshot 自动化:cron / Task Scheduler / pre-commit hook 跑
  `docs-cockpit portfolio snapshot` 即可(等价 idempotent · 一天多次
  跑同样结果)

## [0.9.0] · 2026-05-15

把"怎么写出能被看板接住的文档"从口耳相传/反复试错变成**一套被代码强制的统
一规范**。同时按用户反馈打理了 UX 与 skill/command 命名冲突。

### Why · 用户实测的三个症结

> 1. "提示词需要让人看到再复制" — 0.8.0 是 3 个直接 copy 按钮 · 用户不知道
>    复制了啥
> 2. "你就默认把侧边栏拉宽" — 540px 太窄 · 表格 / prompt / 长文都不够看
> 3. "现在的子任务关联逻辑和文档关联逻辑,太差了,人都很难梳理 · 必须做
>    出一个统一的规范 · 如果检测到用户不符合标准要二次确认"
> 4. "skill 名称和 command 名称尽量别重复 · 不然两个一样的命令"

### Added · `docs-cockpit-author` skill(统一规范源头)

按 skill-creator 写法原则起草:**这是 docs-cockpit 项目里"如何写文档"的
canonical spec**。写在一处 · 改在一处。覆盖:

- **§1 · The five doc kinds** — module / concept / plan / RFC / spec 各自
  的"什么时候用"判别式
- **§2 · Frontmatter schema** — required vs recommended 字段 · status enum ·
  status × progress 区间 · type enum · 跨文档引用字段(docs / depends_on /
  blocks / prd_ref)
- **§3 · "docs vs subtasks" 决策** — 把用户痛点直接拆掉:
  - subtasks · 该 doc 自己的工作项 → 子任务清单
  - docs · 链接到其他详述文档 → 关联文档
  - 各自两种 form(frontmatter list / body section)+ frontmatter 优先规则
- **§4 · File naming** — 路径模板 + slug 规则
- **§5 · Validation flow** — `❌`/`⚠️`/`💡` 三档分别怎么处理 · 修前必须
  跟用户确认(error 一律确认 · hint 可批量 · warn 看情况)
- **§6 · Copy-prompt CTA 协议** — 用户从看板复制提示词到 AI 编辑器后,
  对应 AI 应按 §2-§4 写文档 · 写完后回去更新源 module 的 docs:
- **§7 · 与 superpowers / gstack 等工具的 interop**
- **§8 · 反模式清单** — 不要把 checkbox 塞进 docs: 等

Trigger 设计采用 skill-creator 推荐的 pushy 描述:不只是"用户说 author 才
触发",而是"凡是要写 plan / RFC / spec / module-MD,凡是 build 报 ❌/⚠️/💡,
凡是用户问 frontmatter 怎么填 → 都触发"。

### Added · `docs-cockpit lint` CLI + `build --strict`

`docs-cockpit/build.py` 把 validator 从干瘪 warning 升级成结构化 Issue:

- 每条 issue 含 `severity / path / field / message / suggestion / reference`
- severity 三档:
  - `error` · 看板根本接不住(no id / unknown status / progress 非数值)
  - `warn` · 看板能接住但 UX 烂(no status / progress 出范围)
  - `hint` · 锦上添花(no desc / active 模块 no docs)
- 终端输出三段式:`❌ M07 · id: missing required ... · 💡 fix: add id: ... ·
  📚 see: docs-cockpit-author §2.1`
- state.json 多一个 `issues[]` 字段(structured · 给 IDE / CI 消费),
  老的 `warnings[]` 保留兼容(只有 message)

新 CLI 子命令:

```bash
docs-cockpit lint               # 校验全部 module/concept · 不 build · 退出 1 if any error
docs-cockpit lint --json        # 给 CI / IDE 消费
docs-cockpit lint --strict-warn # warn 也升 error
docs-cockpit build --strict     # build 仍写 HTML · 但 error 时退出 3(CI 用)
```

新 slash command:`/docs-cockpit:lint`。

### Changed · drawer 默认宽度 540 → 720

预览模式仍 960。0.7.2 是"默认窄 · 预览才宽",0.9.0 改成"默认就够看 · 预
览再宽一档",照顾"模块 desc + status + progress + subtask 一屏看全"。

### Changed · empty-docs CTA 重做(0.8.0 痛点)

0.8.0 的 3 个直接 copy 按钮 → 0.9.0 的"tab 切换 + 提示词原文展示 + 单 Copy":

- Tab 条:`Plan` / `RFC` / `Spec` · 各自带一行解释"什么时候选这个"
- 提示词全文展示在等宽 `<pre>` 里 · 用户先看清(长度 / 替换变量 / 是否要
  手工微调)再决定是否复制
- 单个 Copy 按钮 · 复制后变成 `✓ 已复制` 反馈
- 字符数 meta:"X 字 · 粘贴到 AI 编辑器对话框即可"
- `copyDocPrompt()` 拆成 `buildDocPrompt()`(返回文本,不复制)+ 复制路径,
  让 tab 切换能 preview 不污染剪贴板

### Changed · skill 重命名(消除 skill/command 命名冲突)

| 0.8.0                    | 0.9.0                       | 原因                    |
|--------------------------|-----------------------------|------------------------|
| `docs-cockpit-status`    | `docs-cockpit-standup`      | 跟 `/status` 命令名重复 |
| `docs-cockpit-update`    | (删除 · 合并入 `docs-cockpit`) | 跟 `/update` 命令名重复 + CLI `docs-cockpit upgrade` 已接管 |
| `docs-cockpit`           | `docs-cockpit`              | 不变                    |
| —                        | `docs-cockpit-author` (新)   | 新增统一规范 skill       |

最终 3 skills:`docs-cockpit` (写 cockpit) · `docs-cockpit-standup` (读 +
narrative) · `docs-cockpit-author` (写单个项目 doc)。

`docs-cockpit/SKILL.md` 把原 `docs-cockpit-update` 的升级触发逻辑(用户说
"update docs-cockpit" / 看到 banner 时)折进来,trigger 部分相应扩展。

### Migration

- 用户卸载 plugin 后重装(`docs-cockpit upgrade` 帮你做),0.8.x 的 trigger
  短语("升级 docs-cockpit" / "what's blocked")仍然命中,但内部路由到了
  新名字的 skill。
- state.json 仍兼容老 status skill — `warnings[]` 字段没去。
- 用户已有的 `docs/spec/module/*.md` 不动 — 规范是 RECAP,不强制改写存量。
  但下次 build 会用新 validator 报 hint(no desc / no docs),按需修。

## [0.8.0] · 2026-05-15

把"build 后无 docs:"从一个静默缺失变成可操作 UX:active 模块在 kanban
上挂醒目 chip · drawer 内一键复制提示词丢给 AI 编辑器自动生成 plan /
RFC / spec · 中英文双语提示词。

### Why

用户在 Sourcery 项目实测 0.7.x:24 个 module · 19 个 frontmatter 没写
`docs:` 字段 · build 完 dashboard 全是"无关联文档"占位符 · 没有任何提
示让用户知道这是需要修复的状态。原话:

> "项目build后未关联docs,这是很严重的问题,有任务无 task 需要标记并且
> 支持在页面一键复制编写建议,如果用户安装了 superpower 或者 gstack,
> 利用这个 skill 编写 spec 或者 plan,需要加一个复制提示词的功能,
> 复制给对应的 vibe coding 编辑器,生成对应的文档,提示词也注意要多语言"

### Added · kanban "needs-docs" chip

`docs_cockpit/templates/index.html.tmpl` 的 kanban 卡片渲染:

- 当 `status ∈ {in-progress, planned, blocked}` 且 `docs.length === 0`
  时,卡片右上角显示黄色 `⚠ docs?` chip(中文环境:"待补")
- `done` / `not-started` / `deferred` 不显示(已完成或还没启动 · 不催)
- chip 的 tooltip 解释"该 module 已 active 但未关联文档 · 点开抽屉一键
  生成提示词"
- 视觉上比"docs 数量 chip"用更暖的 amber 色调 · 一眼看出"这条要补"

### Added · drawer empty-docs CTA panel

之前 drawer 的 "Linked Docs" 段只在 `docs.length === 0` 时显示一行虚
线灰字"No linked docs"。0.8.0 改成 amber 渐变背景的 CTA 面板:

- 标题:`No docs linked yet` / `尚未关联任何文档`(配警告图标)
- 提示:用 `<code>` 高亮的 `docs:` / `## 关联` 两种缺失情况说明
- **3 个 copy-prompt 按钮**(并排):Plan / RFC / Spec
- 底部工具兼容说明行:"Works with Claude Code (superpowers / gstack),
  Cursor, Codex, Continue, Aider"

### Added · `copyDocPrompt(moduleId, kind)` + clipboard fallback

新增 JS 主流程:点击按钮 → 把 module 上下文(id / title / status /
sprint / progress / path / desc / bodyExcerpt + project name + 今天
日期 + idLower)填进对应 kind 的提示词模板 → 复制到剪贴板 → 弹 toast。

剪贴板用 `navigator.clipboard.writeText()` 优先 · 失败 fallback 到
`document.execCommand('copy')`(file:// 上下文 + Firefox 严格策略下
需要 fallback)。两层都失败时 toast "Copy failed"。

### Added · 3 套 prompt 模板 × 2 语言

每条提示词约 50 行 · 内含:

- 项目 + module 全量上下文(LLM 不用问就知道这是什么模块)
- 输出文件路径建议:`docs/plans/{date}-{idLower}-plan.md` /
  `docs/RFC/<NNN>-<slug>.md` / `docs/spec/{idLower}-spec.md`
- **docs-cockpit 兼容的 frontmatter 模板**(id / type / title / status /
  sprint / owner / depends_on / blocks 等都按 sourcery 看板的约定写)
- 正文段落清单(plan 5 段 / RFC 6 段 / spec 6 段),其中 plan 显式
  要求 `## 待办` / `## TODO` 子段,触发 0.4.0 引入的 body fallback
- **"After writing"** 段:提醒 AI 写完后回去更新 module frontmatter
  的 `docs:` 字段把刚写的文件挂上(避免下次 build 又是空)
- **"Tooling hints"**:superpowers `/plan` `/spec` `/rfc` · gstack 生
  成器 · Cursor / Codex / Continue / Aider 直接粘贴 chat

中英文模板独立维护(不是机翻)· 中文版用 zh-CN 标点(`·` `:`)· 字段名
保持英文(machine-facing token 遵守 global CLAUDE.md 约定)。

### Added · `bodyExcerpt` field on module cards

`docs_cockpit/build.py · _build_card()` 给每张 module card 加
`bodyExcerpt` 字段:剥掉 frontmatter 后的 body 前 1500 字(超长加 `…`)。

当 module 没填 `desc:` 时,这段摘要兜底进 prompt 模板的 `{descOrExcerpt}`
占位符,保证 LLM 收到 prompt 时有足够上下文知道这个 module 在做什么 ·
不至于盲目编 spec/plan。

### Notes

- 提示词中 `<NNN>` `<slug>` 是给 LLM 看的占位符 · 不是模板变量 · 不会
  被前端替换,LLM 自己根据上下文填(扫已有 RFC 编号 + 标题派 slug)
- HTML 体积:Sourcery 24 个 module · 加 bodyExcerpt 后 state.json
  增长 ~25-40KB · 可接受
- 单文件分发不变 · 提示词全在 HTML 里 · 无网络依赖
- 兼容旧 payload:`bodyExcerpt` 缺省视为空,prompt 模板会用 `desc` 兜底,
  都没有则给"请手工补上下文"占位符

## [0.7.2] · 2026-05-15

0.7.1 实测反馈两个小问题的 follow-up:

### Fixed · drawer 宽度

预览长 MD(尤其带宽表格)时,540px drawer 把表格右侧截断。新增
`.drawer.wide { width: min(960px, 96vw); }` 类 · `showDocPreview()` 调用
时 JS 添加 · `openModuleDrawer()` 回模块视图时移除 · `closeDrawer()` 关
时也清。drawer width 进 transition · 加宽是平滑过渡而非闪一下。

### Fixed · embed 前剥 YAML frontmatter

0.7.1 把整个 MD 文件原样塞给 marked.parse,YAML frontmatter 被当成段落
渲染成一坨 `id: foo type: bar status: done ...` 文本压在标题上方,观感
极差。`_resolve_and_embed_docs()` 现在先调 `split_frontmatter()` 切掉
frontmatter,只 embed body。frontmatter 本身保留在 `entry.meta` 字段
里(留给后续可能加的"显示元数据摘要"功能用 · 当前前端未消费)。

截断阈值也改成基于 body 字节数而非原文件大小,文件大但 frontmatter 占
大头的情况下不再误触发截断。

## [0.7.1] · 2026-05-15

Dashboard 内 docs 路径修复 + 内联 MD 预览 · 点击 `docs:` 链接不再跳出浏览器
（即文档放在哪个目录都能正确解析,并在抽屉内直接 marked 渲染）。

### Why

用户实测两个直接相关的痛点:

1. **Path doubling**:frontmatter 写 `docs: [{path: docs/plans/foo.md}]`
   （repo-relative · 自然写法），看板渲染在 `<repo>/docs/index.html`,浏览器
   把 `href` 当成"相对于 HTML 自己"解析,实际请求成了
   `<repo>/docs/docs/plans/foo.md` → `ERR_FILE_NOT_FOUND`。链接打不开。
2. **不再是"预览"**:点 docs 链接走 file:// 跳出抽屉、跳出看板、跳到浏览器
   raw view(原文 MD 或乱码),完全失去看板的连贯性。用户原话:
   *"我不是让你做实时预览吗,为什么还是浏览器预览"*

### Fixed · path resolution 三级回退

`docs_cockpit/build.py` 新增 `_resolve_doc_path(raw, module_path, repo_root, vars_)`,
按以下顺序解析:

1. `{repo}/{home}/{env:X}` 变量展开
2. 绝对路径 → 直接用
3. 相对路径 → 依次试 `[module_path.parent, repo_root]`

解析后的绝对路径写到 payload 的 `resolved` 字段(老 `path` 不动 · 兼容旧前端)。
配合 `exists: bool` 标记,缺失的 docs 在 UI 上显示 `404` chip + 斜纹背景。

### Added · drawer 内联 MD 预览(`showDocPreview`)

`docs_cockpit/build.py · _resolve_and_embed_docs()` 把每条 docs 的 MD 文本
读进 payload(`content` 字段 · 上限 100KB · 超过截断 + 提示)。
`docs_cockpit/templates/index.html.tmpl` 集成:

- `<head>` 加 highlight.js github.min.css 样式
- `</body>` 前加 marked@12.0.2 + highlight.js@11.9.0(python/javascript/typescript/bash/yaml/json/markdown 7 种语言)
- 新增 `.doc-preview-head` / `.doc-preview-body` / `.doc-preview-missing` 三套 CSS
- 新增 `showDocPreview(moduleId, docIndex)` JS:
  - 有 `content` → `marked.parse` 渲染 + `hljs.highlightElement` 高亮 · 替换 `#md-body`
  - 文件不存在(`exists: false`)→ 红底虚框面板提示"找不到文件"+ 已尝试的路径
  - 非 .md / 超大文件 → 用 `file:///` 在浏览器新标签打开(图片 / PDF 走这条)
- drawer-head 不动(还是模块上下文)· `← Back to module` 按钮一键回模块视图

### Changed · docs-row 视觉

- 从 `<a href>` 改成 `<button>`(配合 JS 路由,不再依赖浏览器 file:// 行为)
- 加 `Preview` / `Open` action chip · 一眼能看出会内联还是跳出
- 缺失文件:`404` chip + 斜纹背景 · 鼠标悬停 tooltip 显示用户原始写的 path

### Added · i18n 词条

新增 7 条 EN/ZH 键:`drawer.docs_preview` / `docs_open` / `docs_back` /
`docs_missing_title` / `docs_missing_hint` / `docs_missing_tooltip` /
`docs_open_external`。

### Notes

- 老 payload 兼容:`d.exists` 缺省视为存在 · `d.content` 缺省走 file:// 打开 ·
  老 build 的 HTML 直接换新 build 即可恢复完整体验,不需要前端单独升级。
- HTML 文件会因为内嵌 doc content 变大(Bastion 仓库 588KB · 之前约 400KB)·
  对单文件分发是可接受的折衷,换来零网络请求 + 抽屉内 instant 预览。
- 100KB embed 上限是经验值 · 超过的 MD 仍能浏览(截断 + 提示),只是看不全。
  下游想调可以改 `docs_cockpit/build.py · _MAX_EMBED_BYTES`。

## [0.7.0] · 2026-05-15

Gstack-inspired upgrade architecture · 新增 `docs-cockpit upgrade` CLI 子命令 ·
一条命令搞定 CLI + plugin 升级 · 智能判断要不要重启 · 消灭 ghost state。

### Why

用户实测三次升级体验问题:
- 0.2.x → 0.3.0:plugin autoUpdate 不可靠 · 重启了还是老版本 → 0.3.1 加 cache clear
- 0.5.x → 0.6.0:cache clear + restart 不重视顺序 · 用户在中间停顿 → 0.6.1 加 atomic 规则
- 0.6.x → 0.7.0:即使 atomic 规则 · 用户每次都得手工记 cache 路径 + 怎么清 + 立即重启

**根因**:之前的设计让 Claude / 用户去 "记仪式" · 没把仪式自动化进 CLI。
**gstack 的启发**:它把升级逻辑放进 CLI 自己 · 不依赖 plugin 仪式 · 因为它根本
不是 plugin。docs-cockpit 仍是 plugin · 但可以把 "判断要不要重启" 的智能挪进
CLI · 只在 SKILL.md 真改了的时候才动 plugin 层。

### Added · `docs-cockpit upgrade` CLI 子命令

```bash
docs-cockpit upgrade                # 默认 · 交互
docs-cockpit upgrade --dry-run      # 只看计划
docs-cockpit upgrade --yes          # 非交互
docs-cockpit upgrade --no-clear-cache  # 跳过自动 cache clear
docs-cockpit upgrade --skip-changelog
```

`docs_cockpit/upgrade.py` ~250 行 · 含:
- **`_detect_install_backend()`** · 启发式检测 install 来源(pip / uv / pipx /
  editable)· 看 `docs_cockpit.__file__` 路径里有没有 `uv/tools/` / `pipx/` 等
  标记
- **`_find_plugin_cache_paths()`** · 走 `~/.claude/plugins/cache/` 找含
  docs-cockpit 的目录 · 1-2 层都试
- **`_read_local_plugin_version()`** · 读 plugin cache 里的 plugin.json version
- **`_fetch_remote_version()`** · GitHub raw 拉最新 plugin.json
- **`_show_changelog_diff()`** · 拉 CHANGELOG · print 从用户版本到最新版本区段
- **`_run_cli_upgrade()`** · 根据 backend 跑对应升级命令(uv tool upgrade /
  pipx upgrade / pip install --upgrade / editable 走 git pull)
- **`_clear_plugin_cache()`** · 安全清缓存目录
- **`cmd_upgrade()`** · 八步走完整流程

### 智能决策树

```
比较 local CLI · local plugin · remote 三方版本:

CLI current AND plugin current:
  → ✓ "Already up to date" · 退出

CLI 落后:
  → Step 1/2 跑 CLI upgrade 命令(按 backend)

plugin 跟 CLI 同版本 (patch-only 改动):
  → ✓ "no restart needed" · 完事 · 新 CLI features 已生效

plugin 版本落后 (SKILL.md 真改了):
  → 自动清 cache(safe rmtree)
  → 打印 "ATOMIC NEXT STEP" 醒目分隔栏
  → 告诉用户 30 秒内退 Claude Code · 立即重启
  → 列 verification checklist
```

### 关键设计 · 原子性

之前 0.6.1 加了 atomic 规则但只是 SKILL.md 文字说明 · 还是要 Claude 给用户。
0.7.0 把它**编码进 CLI** · 用户跑命令 · 后台自动清 cache · **立刻**打印"现在
退 Claude Code"提示 · 中间没有可被截胡的窗口。

### Added · 版本约定

定下 semver 语义:
- **patch** (0.x.Y → 0.x.Y+1) · 只动 CLI 代码 · 不动 SKILL.md / commands · plugin
  不需要 restart
- **minor** (0.X → 0.X+1) · 动了 SKILL.md / commands / 新 skill · plugin 要 restart
- **major** (X → X+1) · 破坏 config schema · restart + 配置迁移

`docs-cockpit upgrade` 按这个约定比对 plugin.json 版本 · 决定要不要清 cache。

### Updated · SKILL + commands + README

- `skills/docs-cockpit-update/SKILL.md` 完全重写 · 主推 `docs-cockpit upgrade` ·
  老手动流程作 fallback(pre-0.7.0 用户)· 保留 ghost state recovery 整段
- `commands/update.md` 同步 · slash command 现在 delegate 给 `docs-cockpit upgrade`
- README.md + README.zh-CN.md 升级段全部重写 · 把 `docs-cockpit upgrade` 摆为
  主路径 · 手动作 fallback

### Migration · 0.6.x → 0.7.0

需要手工跑一次老 ritual 才能升上来(0.6.x 还没有 `docs-cockpit upgrade`):

```bash
# 老 ritual · 一次性
pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git
# 或: uv tool upgrade docs-cockpit

# 原子 · 清 cache + 立即重启 Claude Code
rm -rf ~/.claude/plugins/cache/*docs-cockpit*    # POSIX
# Windows: Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\plugins\cache\*docs-cockpit*"
# 立即退 Claude Code 完整重开
```

升上来 0.7.0 之后 · 以后所有升级都跑:

```bash
docs-cockpit upgrade
```

一条命令完事。

### 实测 · `docs-cockpit upgrade --dry-run` on docs-cockpit's own editable repo:

```
docs-cockpit upgrade

Current state:
  CLI version:    0.6.1
  Plugin layer:   not detected (editable install · no Claude Code plugin)
  Install backend: editable

  GitHub latest:  0.7.0

CHANGELOG diff (your 0.6.1 → latest 0.7.0):
  [...0.7.0 entry...]

Step 1/2 · Upgrading CLI (0.6.1 → 0.7.0) ...
  Editable install detected · running git pull from project root
  Would run: git -C /d/harvey_work/docs-cockpit pull  (dry-run)

Step 2/2 · Checking plugin layer ...
  Plugin layer not detected · skipping

✓ Done. CLI is up to date.
```

## [0.6.1] · 2026-05-15

修 update skill 的实战盲点 · "清缓存 + 重启" 之前是两个独立 Step · 用户实测
清完没立即重启 → 进入 ghost state(plugin Directory 显示已装 · 但 sidebar 消失 ·
reinstall 报"已安装")。

### Fixed

- **`docs-cockpit-update` SKILL.md + `commands/update.md` 加 atomic 规则**:
  - 原 Step 6(清缓存)和 Step 7(重启)合并为 **Step 6+7 · atomic**
  - 加 ⚠️ **HARD RULE** banner:cache clear 和 restart 必须连着做 · 中间不能停
  - 解释 ghost state 成因:Claude Code 的 plugin 状态有 in-memory sidebar 和
    settings.json registry 两个来源 · 清缓存 + 不重启 = 两边发散
  - "Right way to phrase to the user" 段:让 Claude 把两步打包成一句话给用户 ·
    避免用户在中间暂停

- **新增 "Ghost state recovery" 整段**:
  - 症状清单(Directory 有 / sidebar 没 / reinstall 报"已安装")
  - 3 步恢复路径(restart → uninstall + restart → 手工删 settings.json 条目)
  - 写明 "prevent" 节 · 告诉 Claude 怎么从源头避免

- **`Don't do these things`** 节加新条:
  > Don't separate cache clear from restart in time — Step 7+8 is ONE atomic
  > action. If user pauses between, they get ghost state.

### Why this matters

之前 SKILL.md 的 Step 6 / Step 7 是两段 · Claude 给用户时也是两条命令分发 ·
用户清完缓存忙别的去了 · 半小时后再重启 → ghost state。0.6.1 把它绑死成
**一个原子操作** · Claude 不能拆开告诉用户。

### Migration · 0.6.0 → 0.6.1

无 breaking · 现有产出 + 配置全不变。这版纯文档 / skill 加固。

```bash
# 升 CLI(可选 · 0.6.0 → 0.6.1 没代码差异 · 只是文档)
pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git

# 强清 plugin cache + 立即重启 Claude Code(0.6.1 的 atomic rule)
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\plugins\cache\*docs-cockpit*" -ErrorAction SilentlyContinue
# ⬆ 跑完立即退 Claude Code 重开 · 不要拖延
```

## [0.6.0] · 2026-05-15

加 i18n 多语言切换 · 默认英文 · 顶部 toggle 切中文。dashboard 和 browse
两个产出都支持。

### Added

- **顶部语言切换器** `[EN] [中]`:
  - 位置:dashboard topbar 右上 / browse topbar 右上 · 一致
  - 样式:深色方块 toggle · active 用 ink 底白字 · `font-family: var(--f-mono)`
  - 默认 lang: **EN**(0.5.x 默认是中文)
  - 切换记 localStorage(`<storage-key>::lang`)· 跨会话持久化
- **完整 i18n 字典**:
  - dashboard 60+ 个 key · en/zh 双语 · 覆盖 topbar / hero / KPI / Kanban /
    Sprint / Concept / Module Drawer / SystemDocs Drawer / Toast / Status labels
  - browse 6 个 key · 覆盖 topbar / search / empty state / CDN banner
- **新 i18n 基础设施**(两个 template 都加):
  - `I18N = { en: {...}, zh: {...} }` JS 字典
  - `t(key, vars)` 函数 · 支持 `{n}` 占位
  - `applyI18nStatic()` 扫所有 `data-i18n` / `data-i18n-placeholder` /
    `data-i18n-title` / `data-i18n-aria` 节点 · 注入对应文本
  - `STATUS_LABEL` 改成 Proxy · 老 `STATUS_LABEL[s]` bracket 访问无需改 · 自动
    走当前 LANG
  - 切换时同步 `<html lang>` 属性
- **dynamic JS render 全 i18n 化**:
  - renderKpi / renderKanban / renderSprints / renderConcepts / renderProject
    Meta / renderSystemDocs / openModuleDrawer 全部用 `t()`
  - toast 消息("Status updated" / "Progress set to 80%")用 `t()` + 变量插值

### Changed

- `<html lang="zh-CN">` → `<html lang="en">`(默认)· JS 切换时改为 `zh-CN`
- 静态 HTML fallback 文本全部翻成英文 · ZH 切换由 JS 注入

### 实测

dashboard build 验证 9/9 关键检查通过:
- I18N 字典 en/zh 各 60+ 条
- 24 个 `data-i18n` 静态 attr
- STATUS_LABEL Proxy 模式 · 老代码无需改
- 124 个 i18n 条目(en + zh 合计)
- 0 个 Chinese leak in JS render literals

### Migration · 0.5.0 → 0.6.0

无 breaking · 现有 build / browse / migrate / state.json 全不变。

```bash
pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git
rm -rf ~/.claude/plugins/cache/*docs-cockpit*    # POSIX 强清 cache
# Windows: Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\plugins\cache\*docs-cockpit*"
# 重启 Claude Code
```

升完跑一次 `docs-cockpit build` · 打开 HTML · 右上角看到 `[EN] [中]` toggle ·
点切换中英文。同样适用 `docs-cockpit browse` 的产出。

## [0.5.0] · 2026-05-15

加 `docs-cockpit browse` 命令 + `/docs-cockpit:browse` slash command · 单 HTML
markdown 浏览器 · 树形侧边栏 + marked.js 渲染。解决"项目 ADR/plan 散落 MD
不进 dashboard 但用户想读"的痛点。

### Added

- **`docs-cockpit browse` CLI**:
  ```
  docs-cockpit browse                    # 默认扫:项目 + ~/.claude/{plans,projects}
  docs-cockpit browse --dir docs/adrs    # 限定扫某子目录(可多次)
  docs-cockpit browse --no-claude        # 跳过 ~/.claude 扫描
  docs-cockpit browse -o docs/browse.html
  docs-cockpit browse --project Bastion  # 显示在 topbar
  ```
- **`/docs-cockpit:browse` slash command**:Claude 直接触发 · 适合"我想读这
  个项目所有文档"的需求。
- **新模板 `docs_cockpit/templates/browse.html.tmpl`**:
  - **树形侧边栏**:按目录嵌套展示 · 文件夹可折叠 · 折叠状态 localStorage
    持久化
  - **多 root 区分**:项目 root / project docs/ / ~/.claude/plans/ /
    ~/.claude/projects/memory/ 各自一个 section · 标签 + 路径 + 文件数
  - **主区渲染**:marked.js + highlight.js 9 种语言(py/js/ts/bash/yaml/
    json/markdown 等)+ GFM table + blockquote 样式
  - **搜索**:`/` 或 `k` 聚焦搜索框 · 实时过滤文件路径
  - **localStorage**:记上次看哪个文件 + 哪些文件夹展开
- **`docs_cockpit/browse.py`**:扫 + 启发式分组 + payload 序列化。

### 默认扫描覆盖

| Root | 路径 | 说明 |
|---|---|---|
| `project-root` | `<repo>/` 顶层 *.md | README, CLAUDE.md, CHANGELOG 等 |
| `project-docs` | `<repo>/docs/` 递归 | 项目所有文档 |
| `claude-plans` | `~/.claude/plans/<project-name>/` | Claude session plan 笔记 |
| `claude-memory` | `~/.claude/projects/<sanitized-cwd>/memory/` | Claude session memory 沉淀 |

`--no-claude` 跳过最后两条 · `--dir` 完全自定义。

### 实测 · Bastion docs/adrs/

```
docs-cockpit browse --repo D:/shulex_work/bastion --dir docs/adrs
→ 13 files · 1 root · HTML 113 KB
→ 浏览器开 docs/adrs.html · 左侧 13 个 ADR 整齐排列 · 点开右侧 marked.js
  渲染 · localStorage 记上次看哪个
```

### Why this matters

之前的产品只解决"frontmatter-driven 模块 dashboard"(0.2.0+)· 但用户实际
需求覆盖更广:

- ADR(架构决策记录)· 没 frontmatter · 大段长文本 · 需要读
- Plan / Roadmap · 没 frontmatter · 大段长文本 · 需要读
- ~/.claude/plans / memory · Claude 攒下的笔记 · 想集中读

这些都**不适合 dashboard** · 但需要**单 HTML 浏览器**。0.5.0 补齐这块。

### Migration · 0.4.x → 0.5.0

无 breaking · 现有 dashboard 输出 + 配置不变。

```bash
# 升 CLI
pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git
# 或 uv tool upgrade docs-cockpit

# 强清 plugin 缓存(沿用 0.3.1 的标准流程)
rm -rf ~/.claude/plugins/cache/*docs-cockpit*    # POSIX
# Windows: Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\plugins\cache\*docs-cockpit*"
# 重启 Claude Code

# 试新命令
docs-cockpit browse                              # 当前项目
```

### Package update

- `pyproject.toml package-data` 加 `templates/*.html`(以前只有 `*.tmpl`)·
  确保 wheel 装出来也带 browse 模板。

## [0.4.0] · 2026-05-15

加 MD body 自动 fallback 提取 · 解决"老项目用 body 写 `## 待办` checklist
但 frontmatter 没 subtasks 字段 · dashboard drawer 显示空"的痛点。

### Added

- **`extract_subtasks_from_body(body)`**:扫 H2 section 标题匹配 `(待办|TODO|
  To-do|Subtasks|Tasks|任务)` · 在该 section 下提取 `- [x]` / `- [ ]`
  checklist 项作 subtasks(完成标 done: true)。section 在下一 H1-H6 /
  `---` 分隔线终止。
- **`extract_docs_from_body(body)`**:扫 H2 section 标题匹配 `(关联(文档)?|
  Related(docs)?|Docs?|See also|参考|链接|Links?)` · 提取该 section 下的
  MD link `[title](path)` 作 docs。锚点链接 `#xxx` 跳过。
- **`_build_card` body 兜底**(0.4.0):当 frontmatter 缺 subtasks/docs 时 ·
  自动从 body 提取填充。frontmatter > body 优先级。`desc` 字段不参与 body
  提取(body 首段往往是引用 / metadata · 不可靠)。
- **`docs-cockpit migrate _inject_frontmatter` body 提取**:迁移时同样跑 body
  提取 · 把 subtasks / docs **写进** frontmatter · 让迁移后 frontmatter
  成为 source of truth。

### Why this matters

之前的 dashboard drawer 严格依赖 frontmatter 字段 · 实战中:

- Sourcery / Bastion 这种老项目 · MD body 已经用 `## 待办` 写好 checklist
- 让用户**再复制一份**到 frontmatter 是重复维护 · 不合理
- 而且用户经常忘改 · 或两份不同步

0.4.0 让 docs-cockpit "更智能":frontmatter 没写就**自动读 body** · 用户什么
都不用做 dashboard drawer 就能显示 checklist 和关联文档。想精控就显式写
frontmatter 接管。

### 实测 · Sourcery

- 24 个 module MD · 之前 dashboard drawer 全部"无子任务"
- 0.4.0 build · **24/24** 自动捞到 3 个 subtask(各自的 `## 3 · 待办` 段)
- `docs: 0`(Sourcery MDs 没 `## 关联` section · 符合预期 · 不强造)

### Bug fix

- 移除 `_build_card` 老的"frontmatter only" 行为不变 · 但去除了不必要的
  manualProgress check 边界 case。

### Migration · 0.3.x → 0.4.0

无 breaking change · 现有 frontmatter / state.json / template 全不动。

升级即得益:
```bash
pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git
# 或 uv tool upgrade docs-cockpit

# Plugin 层强清缓存 + 重启
rm -rf ~/.claude/plugins/cache/*docs-cockpit*    # POSIX
# Windows: Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\plugins\cache\*docs-cockpit*"
# 然后退出 Claude Code 重开
```

升完跑一次 `docs-cockpit build` · 模块卡的 drawer 应该开始显示 subtasks。

## [0.3.1] · 2026-05-15

修升级 skill 的实战盲点 · 用户实测 0.2.0 → 0.3.0 时,CLI 升上去了但 plugin 层
没跟上(autoUpdate: true + 重启 Claude Code 不够 · plugin 缓存依然显示 0.2.0)。

### Fixed

- **`docs-cockpit-update` SKILL.md + `commands/update.md` 加 cache 强清 + 多
  backend 检测**:
  - **新 Step 4(CLI 升级)** · 自动检测 install backend(pip / uv tool / pipx)·
    Python < 3.10 自动切 `uv tool install --python 3.11 --force git+...`
    回退路径,不再盲目假设 pip 能跑。
  - **新 Step 6(强清 plugin 缓存)** · 重启前主动跑
    `rm -rf ~/.claude/plugins/cache/*docs-cockpit*` · 不再相信 autoUpdate ·
    cache 没了 · 重启时被迫从 GitHub 重新 fetch。
  - **新 Step 8(用户侧验证)** · 明确告诉用户 restart 后检查:`/plugin`
    UI 的 version 字段 + Skills 列表里 `/docs-cockpit:migrate` 是否出现(0.3.0+
    的标志性 slash command)· 若还是老版本 → 跑兜底 `/plugin marketplace
    remove docs-cockpit && /plugin marketplace add Guohao1020/docs-cockpit`
    强制 remove+re-add。

### Why this matters

0.2.x 升级到 0.3.0 的"plugin 升级失败"是真实 reproducible 的:
- autoUpdate: true 已开 · 重启完 plugin 依然 0.2.0
- 用户必须手动 remove + re-add marketplace 才能拿到 0.3.0

0.3.1 的 update skill 现在**默认就替你做这事** · 不用等用户发现升级没成功
来回排查。

### Migration · 0.3.0 → 0.3.1

无 breaking · 配置 / state.json / template 全不变。直接升:

```bash
# 任一 backend 都能升
pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git
# 或
uv tool upgrade docs-cockpit
```

升完后**强清 plugin 缓存**(0.3.1 新流程):

```bash
# POSIX
rm -rf ~/.claude/plugins/cache/*docs-cockpit*

# Windows PowerShell
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\plugins\cache\*docs-cockpit*"
```

重启 Claude Code · 验证 plugin 升到 0.3.1(`/plugin` UI 看 version)。

## [0.3.0] · 2026-05-15

新增 `docs-cockpit migrate` 命令 · 解决"非 canonical 布局的现有项目怎么 bootstrap"
的痛点。无 breaking change · 老用户照常用。

### Added

- **`docs-cockpit migrate` CLI**:扫现有项目的散落 MD(`docs/plans/` /
  `docs/adrs/` / `docs/superpowers/plans/` / `docs/PRD/` 等)· 启发式分类
  + 生成 frontmatter + `git mv` 到 `docs/spec/module/M{NN}-{slug}.md`
  canonical 布局 + 写出 tailored `docs-cockpit.yaml`。dry-run by default ·
  `--apply` 才真改。`--keep-originals` 复制不动。
- **`/docs-cockpit:migrate` slash command**:显式触发上面那个 workflow ·
  Claude 强制先 dry-run → 给用户看 plan → 等确认 → 才 --apply。
- **`docs_cockpit/migrate.py`**:实现文件 · ~330 行 · 含分类启发式表 +
  H1 title 提取 + slug 生成 + frontmatter merge(已有字段优先 · 默认填
  status=not-started / sprint=M0 / progress=0)+ git mv with rename fallback。
- **operational SKILL.md 拆 Bootstrap workflow 为 A.1 / A.2**:
  - A.1:project 已是 canonical → 手写 yaml + 加 frontmatter
  - A.2:project 不是 canonical(legacy 散落布局)→ 用 `docs-cockpit migrate`

### Classification heuristics (migrate)

  modules:    docs/spec/module/, docs/plans/, docs/tasks/, docs/adrs/,
              docs/superpowers/plans/, docs/superpowers/specs/
  concepts:   docs/spec/concept/, docs/concepts/
  system_docs (root files): README.md, CLAUDE.md, AGENTS.md, GEMINI.md,
              PROGRESS.md, CHANGELOG.md, PRE-LAUNCH-CHECKLIST.md,
              dogfood-onboarding.md, DESIGN.md
  system_docs (dirs): docs/PRD/, docs/RFC/, docs/architecture/,
                      docs/DESIGN/, docs/audits/, docs/review/
  icon mapping:  memory(claude/agents/gemini) · design(design/architecture)
                 · plan(plan/roadmap/checklist/rfc/adr) · doc(其他)

### 实测

- Sourcery(已 canonical · 24 modules + 11 concepts + 6 system_docs):
  dry-run 正确识别 + 标 ✓(已有 frontmatter)+ 标 source=target(idempotent)·
  --apply 时 dst.exists() 会全 SKIP · 安全。
- Bastion(legacy · docs/plans/ + docs/adrs/ + docs/superpowers/plans/):
  现在能一键迁 · 之前要手动写 16+ 个 frontmatter。

### Migration · 0.2.x → 0.3.0

无 breaking change。配置 schema / state.json shape / template 都不变。直接升:

```bash
pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git
```

Claude Code plugin 用户重启 Claude Code · 自动重 fetch · 新 `/docs-cockpit:migrate`
slash command 即上线。

## [0.2.1] · 2026-05-15

打包修复 + metadata 同步 · 让 `pip install`(以及 `uv tool install`)装出来的
docs-cockpit 真正能用 `docs-cockpit init` 起 yaml(0.2.0 之前漏 bundle examples)。

### Fixed

- **`examples/` 现在打包进 wheel**:`docs_cockpit/` 目录新增 `examples/` 子目录
  装着 `minimal.yaml` + `full.yaml` · `pyproject.toml` 的 `package-data` 把
  `examples/*.yaml` 显式包含。0.2.0 之前 `docs-cockpit init` 在 pip 装好的
  纯 wheel 环境里(没有 repo 源码)会报 `[ERR] template missing`,现修复。
- **`cmd_init` 路径修正**:从 `<package>/../examples/` 改成 `<package>/examples/`
  (package-relative · pip 装环境也能读到)。

### Changed

- **pyproject.toml 完整重写**:
  - `version` 改成 dynamic · 从 `docs_cockpit.__version__` 读 · 以后只改 `__init__.py` 一处
  - `description` 同步 0.2.0 dashboard 定位(去掉旧 "sidebar + kanban" 措辞)
  - `keywords` 加 `claude-code` / `claude-code-plugin` / `claude-skill` /
    `kanban` / `sprint-tracking` 等高信号 tag · 移除老 `static-site`
  - `authors` / `urls` 用 `Guohao1020` 实际账号(原 `harvey` 占位)
  - `classifiers` Development Status 从 Alpha 升 Beta · Python 加 3.13
  - 加 `Issues` / `Changelog` 两个 project.urls
- **README 文档索引 + skill SKILL.md**:所有指 `examples/*.yaml` 的链接
  改成 `docs_cockpit/examples/*.yaml`(因为 examples 移到了 package 内)。

### Migration · 0.2.0 → 0.2.1

无 breaking change。配置 schema / frontmatter 字段 / state.json 结构都不变。
单纯升级即可:

```bash
pip install --upgrade git+https://github.com/Guohao1020/docs-cockpit.git
```

Claude Code plugin 用户重启 Claude Code · 自动重 fetch · 即生效。

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

[Unreleased]: https://github.com/Guohao1020/docs-cockpit/compare/v0.7.0...HEAD
[0.7.0]: https://github.com/Guohao1020/docs-cockpit/compare/v0.6.1...v0.7.0
[0.6.1]: https://github.com/Guohao1020/docs-cockpit/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/Guohao1020/docs-cockpit/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/Guohao1020/docs-cockpit/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/Guohao1020/docs-cockpit/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/Guohao1020/docs-cockpit/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/Guohao1020/docs-cockpit/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/Guohao1020/docs-cockpit/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/Guohao1020/docs-cockpit/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/Guohao1020/docs-cockpit/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/Guohao1020/docs-cockpit/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/Guohao1020/docs-cockpit/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Guohao1020/docs-cockpit/releases/tag/v0.1.0
