---
id: P-V1.0-STAGE-B
type: plan
title: "v1.0 Stage B · CLI 瘦身 + skill 归并（breaking）"
status: planned
sprint: "1.0"
desc: "skill-first pivot 第二刀：CLI build→render + 删认知子命令/MCP/portfolio + 删旧 4 skill + 触发路由唯一化"
owner: harvey
prd_ref: "docs/plans/P-skill-first-pivot.md"
docs:
  - { title: "Stage A plan(已完成)", path: "docs/plans/P-v1.0-stage-a-build-rebuild.md" }
---

# v1.0 Stage B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 CLI 从「双产物认知引擎」削成「纯机械渲染核」（`build`→`render` + 删 8 个认知子命令 + 删 MCP/portfolio ≈ -3.4k 行 python），删旧 4 skill（认知已全部迁入 Stage A 的 1 入口 + 2 流程 + 3 references），触发路由唯一化。

**Architecture:** 删除顺序「由外向内、引用先行」：先改名（后续一切引用新名）→ 翻转 Stage A 过渡注 → 删认知 CLI 层 → **repoint validator references**（在删 author 之前，避免悬空窗口）→ 逐个删 skill（portfolio→author→standup→主 skill）→ 路由唯一化收口 → 回归。**每个 task 的 commit 点上 pytest + lint 必须绿**（tree 时刻可回退）。本 Stage 不 bump 版本不发布——B+C 合并为一次 1.0.0 release（Stage C 做版本/CHANGELOG/README）。

**Tech Stack:** Python argparse 重构（cli.py/build.py/schema.py）· Markdown skill 手术 · pytest（真实存在 · `tests/unit` + `tests/integration`，CLAUDE.md 说没有是陈旧信息）· 烟测下游 `D:/harvey_work/Sourcery` + `D:/shulex_work/bastion`。

**已锁定的边界裁定**（执行者不要重新议）：
- `sync-status`（391 行）**保留**——确定性 JSON→MD 写回，删除会孤儿化 dashboard 模板里的 Export 按钮（动模板超 B 范围）；post-1.0 再议
- `apply-patch` / `apply-body-patch` **删除**——专为「浏览器 LLM 无 Edit 工具」模式 B 而生，用户已明确「无需支持不依赖 claude/codex 的场景」
- `migrate`（state.json 迁移）/ `init` / `browse` / `lint` / `upgrade` **保留**（机械/运维）
- 旧 4 skill 全删，`commands/*.md` 清理留给 Stage C（同一 release 内，无中间破窗）
- **执行期偏离（T3 spec review 裁定 · 终审确认）**：`prompt.py`（裁剪为 206 行）+ `templates/prompts/*.j2`（4 件）+ pyproject 的 jinja2 依赖与 prompts package-data **存活**——File Structure 表与 Task 3 原文把它们列入删除，但 `docs/prompts.js` sidecar 是 dashboard「Copy prompt」CTA 的数据源（`build.py::cmd_build → render_all_subtask_prompts`），属渲染层数据而非认知 CLI。

---

## File Structure（Stage B 触碰面）

| 动作 | 文件 | Task |
|---|---|---|
| 改 | `docs_cockpit/cli.py`（402 行 · render 改名 + 删 8 组 wiring） | 1, 3 |
| 改 | `docs_cockpit/build.py`（删 `cmd_prompt`/`cmd_migrate_subtasks` 等内嵌认知实现 + bundle 耦合处理） | 3 |
| 改 | `docs_cockpit/schema.py` + `docs_cockpit/build.py`（Issue.reference 全部 repoint） | 4 |
| 删 | `docs_cockpit/{mcp_server,prompt,bundle,suggest,verify,sprint,apply_patch,body_patch}.py`（~3.2k 行） | 3 |
| 删 | `docs_cockpit/portfolio.py`（310 行） | 5 |
| 删 | `docs_cockpit/templates/{prompts/,suggest/,sprint-plan.md.j2}` | 3 |
| 删 | `tests/integration/test_mcp_server.py` + `tests/unit/{test_bundle,test_suggest,test_apply_patch}.py` + `test_cli_v011.py` 认知段 | 3 |
| 改 | `pyproject.toml`（删 mcp extra + prompts package-data ± jinja2） | 3 |
| 改 | `.claude-plugin/plugin.json`（删 mcpServers · description 重写） | 3, 9 |
| 删 | `skills/{docs-cockpit-portfolio,docs-cockpit-author,docs-cockpit-standup,docs-cockpit}/` | 5-8 |
| 改 | `skills/docs-cockpit-build/SKILL.md`（过渡注翻转 + 吸收 setup 触发） | 2, 9 |
| 改 | `skills/docs-cockpit-rebuild/SKILL.md`（过渡注翻转 + 删 standup 临时态声明） | 2, 7 |
| 改 | `skills/use-docs-cockpit/SKILL.md`（CLI 行翻转 + upgrade 路由行） | 2, 9 |
| 改 | `references/schema.md`（死链清理 D7）+ `references/operations.md`（吸收 troubleshooting） | 6, 8 |
| 增 | `hooks/hooks-cursor.json`（D9 · 照搬 superpowers） | 10 |

---

## Task 1: CLI `build`→`render` + deprecated alias

**Files:**
- Modify: `docs_cockpit/cli.py:38-47`（build parser 段）
- Test: 手跑双命令 + `py -3.13 -m pytest tests/ -x -q`

- [ ] **Step 1: 重构 cli.py 的 build parser 为 render 主 + build 别名**

把现有 `build_p = sub.add_parser("build", ...)` 段重构为（选项集中到 helper 避免双份漂移）：

```python
def _add_render_options(p: argparse.ArgumentParser) -> None:
    """render/build 共用选项 · 单一定义防 alias 漂移"""
    # （把原 build_p 上的全部 add_argument 调用原样搬进来——执行时 Read cli.py:38-47 照抄）

render_p = sub.add_parser("render", help="按 config 渲染 HTML 看板（原 build 命令 · 1.0 改名）")
_add_render_options(render_p)
render_p.set_defaults(func=cmd_build)

# deprecated alias · 保留一个 minor 周期（1.0.x）· 1.1 移除
build_p = sub.add_parser("build", help="[deprecated] 用 render 替代 · 行为相同")
_add_render_options(build_p)
def _cmd_build_deprecated(args):
    print("[docs-cockpit] warning: `build` is deprecated, use `render` (same behavior). "
          "The alias will be removed in 1.1.", file=sys.stderr)
    return cmd_build(args)
build_p.set_defaults(func=_cmd_build_deprecated)
```

注意：`cmd_build` 本体（build.py 内）**不改名**——内部函数名不是用户面；只动 CLI 注册层。

- [ ] **Step 2: 验证双命令 + deprecation warning**

```bash
py -3.13 -c "import sys; sys.path.insert(0, r'D:\harvey_work\docs-cockpit'); from docs_cockpit.cli import main; main(['render', '--config', 'docs-cockpit.yaml'])"
# Expected: 正常构建 · 无 warning
py -3.13 -c "... main(['build', '--config', 'docs-cockpit.yaml'])"
# Expected: stderr 出 deprecation warning · 构建结果与 render 相同
```

- [ ] **Step 3: pytest 全绿**

```bash
py -3.13 -m pytest tests/ -x -q
```
Expected: 全过（若有 test 断言 `build` 子命令 help 文本，更新断言）。

- [ ] **Step 4: Commit**

```bash
git add docs_cockpit/cli.py tests/
git commit -m "feat(v1.0-B): rename CLI build to render with deprecated alias"
```

---

## Task 2: 翻转 Stage A 过渡注（D1）+ AGENTS.md 锚块自愈（D10）

**Files:**
- Modify: `skills/docs-cockpit-build/SKILL.md`（Phase 7 + Phase 0 AGENTS.md 模板）
- Modify: `skills/docs-cockpit-rebuild/SKILL.md`（Phase 5）
- Modify: `skills/use-docs-cockpit/SKILL.md`（路由表 CLI 行）

- [ ] **Step 1: 四处命令注翻转**（render 已存在 → 主句用 render，alias 作注）

| 位置 | 改前 | 改后 |
|---|---|---|
| build P7 | `` run `docs-cockpit build` `` + `*(renamed to render in Stage B)*` | `` run `docs-cockpit render` `` + `` *(`docs-cockpit build` still works as a deprecated alias until 1.1)* `` |
| rebuild P5 | 同上结构 | 同上改法 |
| use-docs-cockpit 路由表 | `` CLI `docs-cockpit build` (will be renamed `docs-cockpit render`) `` | `` CLI `docs-cockpit render` `` |
| build P0 AGENTS.md 模板 | `` `docs-cockpit build` (will be renamed `docs-cockpit render`) `` | `` `docs-cockpit render` `` |

- [ ] **Step 2: AGENTS.md 锚块自愈（D10）**——build P0 幂等逻辑从「found → skip」升级为「found → 比对块内容，不一致则整块替换（marker 间内容以当前模板为准），一致才 skip」。在 P0 Actions 里把 skip 句改写为这个三态逻辑（found+same→skip · found+diff→replace block · not found→append/create）。

- [ ] **Step 3: 验证**——grep 三个 skill 全文：`will be renamed` 0 命中；`renamed to .* render` 仅允许出现在 deprecated-alias 注里；frontmatter 的 `docs-cockpit render` 字样现在全部为真。

- [ ] **Step 4: Commit**

```bash
git add skills/
git commit -m "feat(v1.0-B): flip Stage A transitional CLI notes + self-healing AGENTS.md block"
```

---

## Task 3: 删认知 CLI 层（命令 + 模块 + 模板 + 测试 + 打包面）

**Files:**
- Modify: `docs_cockpit/cli.py`（删 8 组 wiring：migrate-subtasks L84-94 · prompt L97-137 · apply-patch L184-201 · apply-body-patch L204-223 · suggest L226-259 · mcp-serve L291-303 · sprint L306-350 · verify L353-376）
- Modify: `docs_cockpit/build.py`（删 `cmd_prompt` / `cmd_migrate_subtasks` 及其私有 helper）
- Delete: `docs_cockpit/{mcp_server,prompt,bundle,suggest,verify,sprint,apply_patch,body_patch}.py`
- Delete: `docs_cockpit/templates/prompts/` · `templates/suggest/` · `templates/sprint-plan.md.j2`
- Delete: `tests/integration/test_mcp_server.py` · `tests/unit/{test_bundle,test_suggest,test_apply_patch}.py`
- Modify: `tests/integration/test_cli_v011.py`（删 prompt/migrate-subtasks 相关 case · 保留 build/render/lint case）
- Modify: `pyproject.toml` + `.claude-plugin/plugin.json`

- [ ] **Step 1: 前置耦合检查（删前必查 · 结果决定 Step 2 细节）**

```bash
# (a) bundle 是否被 build 时调用（bundle-meta.js 预计算）？
grep -n "bundle" docs_cockpit/build.py
# (b) sprint.py 里除 CLI 外有没有 build 时用的扫描 helper？
grep -n "from .sprint import\|sprint\." docs_cockpit/build.py
# (c) sync_status 是否依赖将删模块？
grep -n "import" docs_cockpit/sync_status.py | grep -E "prompt|bundle|suggest|verify|sprint|apply_patch|body_patch|mcp"
```

处理规则：(a) 若 `cmd_build` 调 bundle 生成 `docs/bundle-meta.js` → 把该调用和产物一并删（bundle 推荐是认知特性）· 模板里引用 `bundle-meta.js` 的 `<script>` 行同步删；(b) 若 build 引用 sprint.py 的扫描 helper（sprint-plan 文档进 payload 是**渲染**行为，保留）→ 把该 helper 函数搬进 `schema.py` 再删 sprint.py；(c) 若 sync_status 依赖将删模块 → 把依赖的纯函数搬进 schema.py。

- [ ] **Step 2: 按检查结果执行删除**（cli.py wiring → build.py 内嵌实现 → 模块文件 → 模板 → 测试）。`lint_sprint_readiness`（schema.py:592）**保留不动**——spec 决策「DoR/DoD 死规则并入 lint」。

- [ ] **Step 3: 打包面收口**

- `pyproject.toml`：删 `[project.optional-dependencies].mcp`；删 package-data `"templates/prompts/*.j2"`；然后 `grep -rln "jinja2" docs_cockpit/*.py`——若仅剩已删模块残留 import 则清掉；若 build.py 仍有存活的 jinja2 用途（如 sprint-plan 渲染 helper）则 jinja2 依赖保留，否则从 `dependencies` 删除
- `.claude-plugin/plugin.json`：删 `mcpServers` 块和 `"//mcpServers"` 注释行；keywords 删 `"mcp-server"`

- [ ] **Step 4: 回归**

```bash
py -3.13 -m pytest tests/ -q                  # Expected: 全绿（删掉的 test 不再跑）
py -3.13 -c "... main(['render'])"            # Expected: 构建成功
py -3.13 -c "... main(['lint'])"              # Expected: exit 0 · sprint-readiness 类目仍工作
py -3.13 -c "... main(['suggest'])" 2>&1 | head -2   # Expected: argparse 报 invalid choice
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(v1.0-B): remove cognitive CLI layer (8 subcommands, MCP server, ~3.2k lines)"
```

---

## Task 4: Repoint validator Issue.reference（删 author 前必做）

**Files:**
- Modify: `docs_cockpit/schema.py` + `docs_cockpit/build.py`（全部 `reference="docs-cockpit-author · §N"` 字符串）

- [ ] **Step 1: 清点 + 建映射**

```bash
grep -rn 'docs-cockpit-author' docs_cockpit/*.py
```

对每条建「author §N → schema.md 对应 section」映射（schema.md 的 9 个 H2 见其 TOC）。例：`docs-cockpit-author · §2.1 required frontmatter` → `references/schema.md · frontmatter schema`；`§17 sprint-readiness` → schema.md 没有 sprint 节（§17 本来就不在提取范围）→ 这类指到 spec 文档 `docs/plans/P-skill-first-pivot.md` 不合适，**就地写短语**：`reference="sprint-plan DoR rules (docs-cockpit lint --include sprint-readiness)"`。原则：reference 必须指向**删除后仍存在**的锚。

- [ ] **Step 2: 全量替换 + 验证 0 残留**

```bash
grep -rn 'docs-cockpit-author' docs_cockpit/ tests/   # Expected: 0 命中
py -3.13 -m pytest tests/ -q                          # 若 test 断言 reference 文本 · 同步更新
py -3.13 -c "... main(['lint'])"                      # Expected: exit 0 · 输出里 📚 see: 行指向新锚
```

- [ ] **Step 3: Commit**

```bash
git add docs_cockpit/ tests/
git commit -m "refactor(v1.0-B): repoint validator references from author skill to references/schema.md"
```

---

## Task 5: 删 portfolio（CLI 模块 + skill）

**Files:**
- Modify: `docs_cockpit/cli.py:180-181`（portfolio wiring）
- Delete: `docs_cockpit/portfolio.py` · `skills/docs-cockpit-portfolio/`

- [ ] **Step 1: 删 wiring + 模块 + skill 目录**。检查 `grep -rn "portfolio" docs_cockpit/*.py tests/` 处理残留 import / test。
- [ ] **Step 2: pytest + lint 绿；`main(['portfolio','list'])` 报 invalid choice。**
- [ ] **Step 3: Commit** — `feat(v1.0-B): remove portfolio (CLI module + skill)`

---

## Task 6: 删 author skill + schema.md 死链清理（D7）

**Files:**
- Delete: `skills/docs-cockpit-author/`（1226 行 · 字段规范已在 schema.md · §11/§16.6 方法论已在 association-method.md/build/rebuild）
- Modify: `references/schema.md`

- [ ] **Step 1: 删前差异审计（防丢内容）**——对照 author §1-§17 与已迁移产物清单：§1-§4/§16.2→schema.md ✓ · §11/§12/§16.6→association-method.md+build/rebuild ✓ · §5(validation flow)→build P5 的对话决策已覆盖其精神 · §6/§10/§13/§14/§15(copy-prompt CTA/prompt 模板/suggest/bundle/超技能编排)→随认知 CLI 死，**不迁** · §16.3(per-subtask plan MD)/§17(sprint schema)→**仍是活规范但无归宿** → 把这两节压缩提取进 `references/schema.md` 新增 section（`## per-subtask plan MD` ~30 行 · `## sprint-plan schema` ~40 行，含 §17.2 字段表 + §17.3 DoR 表，删 CLI workflow 段）。完成后 author 才可删。
- [ ] **Step 2: schema.md 死链清理**——L198 `docs-cockpit migrate-subtasks` 引用改为「v0.10 string 形式是 legacy · agent 用 Edit 直接重写为 object 形式」；L287 删 `prompts/*.md.j2` 模板举例句（模板已删）。grep schema.md：`migrate-subtasks|md.j2` 0 命中。
- [ ] **Step 3: 删 `skills/docs-cockpit-author/`**。全仓 grep `docs-cockpit-author`——除 CHANGELOG（历史记录 · 不动）和 commands/（Stage C）外 0 命中。
- [ ] **Step 4: pytest + lint 绿（lint 输出的 📚 行已在 Task 4 repoint，复确认）。Commit** — `feat(v1.0-B): remove author skill, absorb live spec sections into references/schema.md`

---

## Task 7: 删 standup skill + rebuild 过渡声明

**Files:**
- Delete: `skills/docs-cockpit-standup/`
- Modify: `skills/docs-cockpit-rebuild/SKILL.md`（L28 附近的 by-design 过渡段）

- [ ] **Step 1: 删 skill 目录；rebuild 的「standup 重叠是过渡态」整段删除**（含「don't fix the overlap」句——重叠不复存在）。
- [ ] **Step 2: grep `docs-cockpit-standup` 全仓**——除 CHANGELOG/commands(C 处理) 外 0 命中。pytest + lint 绿。
- [ ] **Step 3: Commit** — `feat(v1.0-B): remove standup skill (absorbed by rebuild Phase 1)`

---

## Task 8: 主 skill 内容分诊 + 删除

**Files:**
- Modify: `references/operations.md`（吸收 troubleshooting）
- Delete: `skills/docs-cockpit/`

- [ ] **Step 1: 分诊**——Read 主 skill 全文，按归宿清单处理：bootstrap/config/upgrade→operations.md 已有 ✓ · 路由/scope 段→use-docs-cockpit 已有 ✓ · **debug build issues 知识（0 modules / wrong status / yaml schema err误）→ 提取为 operations.md 新 `## troubleshooting` section（~20 行 · 症状→原因→修法表）** · v0.11 subtask-schema 升级段→随 migrate-subtasks 死，不迁 · 其余 workflow 叙述→不迁（build/rebuild phase 已覆盖）。
- [ ] **Step 2: 删 `skills/docs-cockpit/`。pytest + lint 绿。**
- [ ] **Step 3: Commit** — `feat(v1.0-B): remove main skill (ops absorbed into operations.md troubleshooting)`

---

## Task 9: 触发路由唯一化（D8）+ plugin.json description

**Files:**
- Modify: `skills/docs-cockpit-build/SKILL.md`（frontmatter description——Stage A 锁字解除，这是计划内修订）
- Modify: `skills/use-docs-cockpit/SKILL.md`（+1 路由行）
- Modify: `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json`（description 重写）

- [ ] **Step 1: build description 吸收原主 skill 触发**——TRIGGER 段追加：`「把项目做成 dashboard / 项目看板」 "set up a docs-cockpit", "extend the config to scan new dirs", "debug build issues (0 modules / yaml errors)"`（原主 skill (a)(b)(e) 类）；Do-NOT 段删除已不存在的指向（确认无指向旧 skill 的句子）。
- [ ] **Step 2: use-docs-cockpit 路由表 +1 行**——`升级 docs-cockpit 本体 → CLI \`docs-cockpit upgrade\`（见 references/operations.md · upgrade）`，触发例「升级 docs-cockpit」"update docs-cockpit"。全文仍 <60 行。
- [ ] **Step 3: plugin.json / marketplace.json description 重写**——现 description 列举 4 旧 skill + portfolio + MCP，全部失实。改为：skill-first 一句话定位 + 「1 entry router + 2 flow skills (build/rebuild) + mechanical render CLI」+ 保留 dashboard 特性描述。keywords 增 `"skill-first"`。版本号**不动**（Stage C bump）。
- [ ] **Step 4: 六类查询路由自检**（建关联/漂移刷新/纯渲染/查状态/搭建 cockpit/升级本体）逐一走 use-docs-cockpit 表 + 两 skill frontmatter——每类有且仅有一个归宿。
- [ ] **Step 5: Commit** — `feat(v1.0-B): unify trigger routing, absorb setup triggers into build, rewrite plugin description`

---

## Task 10: `hooks/hooks-cursor.json`（D9）

**Files:**
- Create: `hooks/hooks-cursor.json`（照搬 `C:\Users\86157\.claude\plugins\cache\superpowers-marketplace\superpowers\5.1.0\hooks\hooks-cursor.json` 结构，command 指向同一 `run-hook.cmd session-start`）

- [ ] **Step 1: Read superpowers 版（137 字节）→ 适配创建。session-start 的三路 JSON 已支持 Cursor（Stage A 实现）——本文件只是注册层。**
- [ ] **Step 2: smoke——`CURSOR_PLUGIN_ROOT=... bash hooks/session-start` 应输出 `additional_context`（snake_case）JSON。**
- [ ] **Step 3: Commit** — `feat(v1.0-B): add hooks-cursor.json registration`

---

## Task 11: 全量回归 + Stage C 输入清单

- [ ] **Step 1: 全套绿灯**

```bash
py -3.13 -m pytest tests/ -q          # 全绿
py -3.13 -c "... main(['lint'])"      # exit 0
py -3.13 -c "... main(['render'])"    # 本仓库构建成功 · dashboard 打开正常
```

- [ ] **Step 2: 下游烟测（模拟 pre-commit 的旧命令路径）**

```bash
cd D:/harvey_work/Sourcery  && py -3.13 -c "import sys; sys.path.insert(0, r'D:\harvey_work\docs-cockpit'); from docs_cockpit.cli import main; main(['build'])"
cd D:/shulex_work/bastion   && 同上
# Expected: 两项目构建成功 + stderr deprecation warning（alias 兜底生效）
```

- [ ] **Step 3: 残留 grep 扫描 → 产出 Stage C 输入**

```bash
grep -rn "mcp-serve\|docs-cockpit prompt\|docs-cockpit suggest\|docs-cockpit verify\|docs-cockpit sprint\|migrate-subtasks\|portfolio\|standup\|docs-cockpit-author" --include="*.md" --include="*.json" --include="*.yml" . | grep -v CHANGELOG | grep -v "docs/plans/" | grep -v ".git/"
```

Expected 命中仅限 Stage C 范围：`commands/*.md`（status/weekly/build 等待清理）、`README*.md`、`CLAUDE.md`、`references/config_reference.md`（如有）、`.github/workflows/test.yml`（如断言已删模块）。把命中清单**原样记入本文件末尾新章节 `## Stage C 输入 · 残留清单`**，作为 Stage C plan 的素材。模板 `index.html.tmpl` 若 grep 出 copy-prompt CTA 文案引用已删 CLI——记入清单（Stage C 或 post-1.0 处理，模板手术不在 B 做）。

- [ ] **Step 4: 零意外改动确认**——`git diff main --stat` 复核改动面与本 plan File Structure 表一致。

- [ ] **Step 5: Commit（如 Step 3 产生清单写入）** — `docs(v1.0-B): record residual references as Stage C input`

---

## Stage B 完成定义（DoD）

- [ ] `skills/` 只剩 `use-docs-cockpit` + `docs-cockpit-build` + `docs-cockpit-rebuild`
- [ ] CLI 子命令只剩：`render`（+`build` alias）/ `init` / `lint` / `browse` / `migrate` / `sync-status` / `upgrade`
- [ ] `docs_cockpit/` 无 mcp_server/prompt/bundle/suggest/verify/sprint/apply_patch/body_patch/portfolio
- [ ] 全仓（除 CHANGELOG/docs/plans 历史）`docs-cockpit-author` 0 命中（validator reference 已 repoint）
- [ ] pytest 全绿 · lint exit 0 · 本仓库 + Sourcery + bastion render 烟测过
- [ ] 下游旧命令 `docs-cockpit build` 仍可用（deprecation warning）
- [ ] 版本号未动（1.0.0 bump 在 Stage C）

**Stage B 后接续：** Stage C plan（CLAUDE.md 重写 · README 双语 · commands/ 清理 · CHANGELOG · 1.0.0 bump · `docs-cockpit upgrade` 发布链路验证），输入 = Task 11 Step 3 的残留清单。

---

## Stage C 输入 · 残留清单

B-Task 11 全量回归后跑残留 grep（patterns：`mcp-serve / docs-cockpit prompt / docs-cockpit suggest / docs-cockpit verify / docs-cockpit sprint / migrate-subtasks / portfolio / standup / docs-cockpit-author / prompts-refine`，范围 `*.md / *.json / *.yml / *.tmpl`，另补查 `*.yaml / *.py / *.j2 / site/*.html`），排除 CHANGELOG 与 `docs/plans/`（历史叙事按约定保留）。命中按文件归组如下——这是 Stage C plan 的直接输入。

| 文件 | 残留内容类型 | Stage C 动作建议 |
|---|---|---|
| `commands/`（browse / build / lint / migrate / status / update / weekly · 共 7 个） | 旧 slash command 整目录：`lint.md` 全文引 `docs-cockpit-author` 并要求 hand off 给该 skill（已删）；`status.md` 调 `docs-cockpit-standup` skill（已删）；`weekly.md` 调 `docs-cockpit-portfolio` skill + `portfolio` CLI（均已删）；`build.md` 包装已废弃 alias | 整目录决策：删除（skill-first 后入口走 use-docs-cockpit）或重写指向 3-skill；`lint.md` 的 author 引用至少改指 `references/schema.md` |
| `README.md` | 四技能叙事（L39-43 · L102-103 · L119 · L131）；CLI cheat-sheet 列已删子命令 `prompt / prompt --bundle / suggest / mcp-serve / migrate-subtasks / portfolio`（L86-93）；MCP server 章节（L153-159）；portfolio 章节（L172-178 · L247 目录树）；state.json 消费者叙事提 standup/portfolio（L182 · L193） | 按 skill-first 全面重写：1 入口 + 2 流程 skill 叙事 · 删死命令与死章节 · state.json 消费者改写 |
| `README.zh-CN.md` | 同上的中文镜像（结构同步 · 行号一致：L39-47 · L76 · L86-93 · L102-103 · L119 · L131 · L153-159 · L172-178 · L182 · L193 · L247） | 与 EN 同步重写（双语结构保持一致） |
| `CLAUDE.md` | 架构段整体停留在 v0.x：L25 `portfolio list` 命令示例；L82-83 / L95-96 standup·portfolio 消费者表 + 四技能表；L86 dispatcher 子命令列表（含 build/portfolio）；L106 standup 命名史；L120 / L126 portfolio registry 章节；L161 where-to-look portfolio 行 | 架构段按 v1.0 重写（render + 3 skill + hooks）· 历史命名史可留但加「已删」注 |
| `site/index.html` | 营销页 4 处：L546/548 `docs-cockpit-author` skill 叙事；L633-634 「Subtask 一键复制 prompt」特性卡；L764 v0.14 引语含 portfolio；L852/857 hint 文案提 Copy prompt | 4 处文案更新为 skill-first 叙事 · prompt CTA 描述与现状对齐（prompts.js sidecar 仍在 · CLI prompt 已删） |
| `docs_cockpit/templates/index.html.tmpl` | L281-284 注释称「prompts-refine.js sidecar 保留 · MCP server 仍能消费」（build 已不产出 prompts-refine.js · MCP server 已删）；L2238 / L2547 `toast.refine_missing` 文案引 `docs-cockpit build` + prompts-refine.js；L4209 / L4248 Copy bundle prompt 仍向剪贴板写已删除的 `docs-cockpit prompt --bundle` CLI 命令 | 死注释删；死 toast 串删或改;bundle copy CTA 决策：直接输出 bundle prompt 文本（前端拼）或移除按钮 |
| `docs/spec/module/M02-cli.md` | L8 desc 提 `prompt / migrate-subtasks / lint --prompts`；L32 / L43 / L49 portfolio 子命令树·关键文件·subtask `@code:docs_cockpit/portfolio.py`（文件已删） | desc 更新至 v1.0 CLI 面（render/lint/init/migrate/browse/sync-status/upgrade）· 历史 subtask 改 CHANGELOG 历史锚（同 M07/M10 B-Task 11 做法） |
| `docs/spec/module/M03-plugin.md` | L32-33 skill 目录树含 standup / portfolio；L56 历史叙事注（已有锚 · 无 warn） | skill 树更新为 use-docs-cockpit + build + rebuild · 历史注保留 |
| `docs/spec/module/M05-portfolio.md` | 整个 module 即已删 portfolio 特性：L10 prd_ref · L12 docs 指已删 SKILL.md · L36-37 关键文件 · L42-45 subtasks `@code/@docs` 指已删文件 | 模块历史化：保 done（曾 ship）· 锚改 `@docs:CHANGELOG.md#0.10.0` 类历史锚 · docs: 链接换 CHANGELOG |
| `docs/spec/module/M07-mcp-server.md` | L22 / L33 `mcp-serve` CLI 叙事与关键文件表；L43 `@code:docs_cockpit/cli.py:200-215` 等行号锚指向已删代码 | 叙事补「已随 v1.0 删」注 · stale @code 锚改 CHANGELOG#0.12.0 历史锚（B-Task 11 已处理零锚 warn 的 1 条 · 余下 stale 行号锚 Stage C 收） |
| `docs/spec/module/M08-apply-patch.md` | L64 「与 migrate-subtasks 一致」措辞（该命令已删） | 措辞历史化（「与原 migrate-subtasks(已删)一致」） |
| `docs/spec/module/M10-llm-doc-optimizer.md` | title / desc / §1-§2 全文 `docs-cockpit suggest` CLI 叙事（命令已删 · 功能曾 ship） | 叙事历史化 · §1 用法代码块加已删说明或指 CHANGELOG#0.12.0 |
| `docs/spec/module/M16-multi-subtask-bundle-ux.md` | L57 Copy bundle prompt 走已删 `docs-cockpit prompt --bundle` CLI | 与 tmpl L4209 同一决策项 · 文案随之改 |
| `docs/spec/module/M17-bundle-prompt-and-skill.md` | L8 desc / L27 / L46 / L105：`prompt --bundle` CLI · author skill §14 · `suggest --bundle-candidates` | 模块历史化（同 M05 做法 · 锚指 CHANGELOG#0.14.0） |
| `references/sync_status_workflow.md` | L46 提 `migrate-subtasks`；且该文件不在 v1.0 六文件 references 清单（schema / association-method / operations / config_reference / design_tokens / frontmatter_conventions）内 | 措辞改 + 决策：并入 `references/operations.md` 或保留为 sync-status 专属文档 |
| `references/schema.md` | L1 头注「原 docs-cockpit-author 已删 · 活规范已并入」 | 有意历史说明 · 保留 · 无动作 |
| `docs_cockpit/build.py`（py 注释 · 扩展面） | L263 注释「standup / portfolio 可消费」· L652 注释「给 docs-cockpit-standup skill 读」（两 skill 已删） | 注释改为「给 rebuild skill / CI 读」类现状措辞（一行 polish） |
| `docs_cockpit/cli.py` L4 · `docs_cockpit/prompt.py` L7 · `docs_cockpit/schema.py` L1293 | 「已随认知层删除」类有意历史注 | 保留 · 无动作 |

| `docs_cockpit/templates/index.html.tmpl` L2234/L2543/L4519 | `toast.prompt_missing` 三处让用户跑 `docs-cockpit build`（deprecated 名） | Stage C 动作：措辞改 `render` |
| `tests/unit/test_aliases.py` L10 | docstring 引已删 standup/portfolio skill | 动作：一行 docstring 改写 |
| `tests/integration/test_dashboard_render.py` L8/L11 | 文件头 docstring 仍把 bundle-meta.js 写成正向覆盖项（实为反向断言） | 动作：一行校正 |

已确认干净（无残留命中）：`.claude-plugin/plugin.json` · `.claude-plugin/marketplace.json` · `docs-cockpit.yaml` · `skills/`（3 个 SKILL.md）· `hooks/` · `references/` 其余 5 文件。

**合并约束：Stage C 完成（版本 bump + commands/README 清理）前，本分支不得 merge 进 main、不得让 marketplace 指向本分支——否则用户拿到 0.19.0 版本号 + 1.0 内容的 ghost 状态。**
