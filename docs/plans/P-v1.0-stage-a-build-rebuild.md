---
id: P-V1.0-STAGE-A
type: plan
title: "v1.0 Stage A · 新建 use-docs-cockpit + build + rebuild skill + references + hooks"
status: done
sprint: "1.0"
desc: "skill-first pivot 第一刀：零破坏新建 1 入口+2 流程 skill、3 个 references、SessionStart 条件注入 hooks"
owner: harvey
prd_ref: "docs/plans/P-skill-first-pivot.md"
---

# v1.0 Stage A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 零破坏地新建 `use-docs-cockpit`（入口）+ `docs-cockpit-build` + `docs-cockpit-rebuild` 三个 skill、`references/` 三份共享规范、`hooks/` SessionStart 条件注入；旧 4 skill 原样保留，新旧并存可立即 dogfood。

**Architecture:** 认知方法论沉到 skill（markdown），python 不动（渲染核保留）。skill 引用 `references/`（schema 规范 + 4 原子方法 + 运维）。`hooks/` 在有 `docs-cockpit.yaml` 的项目把 `use-docs-cockpit` 引导注入 SessionStart。本 Stage **不删任何旧文件、不改 build.py、不改 plugin.json**。

**Tech Stack:** Markdown（SKILL.md / references）· JSON（hooks.json）· bash + cmd polyglot（hook 脚本）· `docs-cockpit lint` / sys.path-injection smoke test（验证）。

**验证哲学（本项目无 pytest）：** 每个产物的"测试"= 三件事之一或全部 ——(a) `docs-cockpit lint` 仍 0-error（证明没破坏现有 build）；(b) 文件 section 完整性人工 review（对照本 plan 的 section 清单）；(c) dogfood（在本仓库或 Sourcery 跑一遍真实流程）。脚本类产物（hooks）有可执行 smoke。

---

## File Structure（本 Stage 新建/触碰的文件）

| 文件 | 责任 | 本 plan 任务 |
|---|---|---|
| `references/schema.md` | frontmatter / anchor / 命名 字段规范（从 author §1–§4 提取，**复制非移动**，author 暂留） | Task 1 |
| `references/association-method.md` | 检索 / 推理 / 预演 / 高亮 4 原子方法（net-new 创作） | Task 2 |
| `references/operations.md` | bootstrap / config / upgrade 运维（从 `docs-cockpit` 主 skill 提取） | Task 3 |
| `skills/docs-cockpit-build/SKILL.md` | 构建关联体系 7-phase 流程 | Task 4 |
| `skills/docs-cockpit-rebuild/SKILL.md` | 刷新重建 5-phase 流程 | Task 5 |
| `skills/use-docs-cockpit/SKILL.md` | 入口元 skill · 薄路由表 | Task 6 |
| `hooks/hooks.json` | SessionStart hook 注册 | Task 7 |
| `hooks/run-hook.cmd` | 跨平台 polyglot wrapper | Task 7 |
| `hooks/session-start` | 条件注入脚本（检测 `docs-cockpit.yaml`） | Task 7 |

**依赖顺序：** references（Task 1-3）→ skill（Task 4-6，引用 references）→ hooks（Task 7，注入 use-docs-cockpit）→ dogfood（Task 8）。

---

## Task 1: `references/schema.md` — 字段规范（从 author 提取）

**Files:**
- Create: `references/schema.md`
- Source（只读参考，不改）: `skills/docs-cockpit-author/SKILL.md` §1–§4、§2.x、§3.1.x

- [ ] **Step 1: 创建 `references/schema.md`，含以下 section（内容从 author 对应节提取，保持字段定义逐字一致）**

必含 section（缺一不可，对照打勾）：
- `## 五种 doc kind` — module/concept/plan/rfc/spec 表（author §1）
- `## frontmatter schema` — 完整字段表 + 必填 `id`、`status` enum、`status × progress` 不变式（author §2.1–§2.3）
- `## cross-doc 字段` — `docs:` / `depends_on` / `blocks` / `prd_ref`（author §2.6）
- `## subtasks vs docs 决策` — 两概念区分表（author §3）
- `## subtask 格式` — Form A/B/C + heading 接受形式表 + id 算法（author §3.1, §3.1.1）
- `## code anchor 格式` — 4 种 shape + 三步路径回退 + 解析后字段表（author §3.1.2）
- `## doc anchor 格式` — 4 种 shape（path / :lines / #heading）+ 解析后字段表（author §3.1.3）
- `## 文件命名约定` — 各 kind 的 path 模式表（author §4）
- `## subtask title 4 法则` — 单句/单语言/无 anchor/讲需求（author §16.2）

文件顶部加一行溯源注释：`<!-- 规范 SSOT · 原 docs-cockpit-author §1-§4/§16.2 · Stage B 后 author 删除，本文成唯一来源 -->`

- [ ] **Step 2: 验证字段一致性（机械层未变，规范必须与 validator 对齐）**

Run（确认 build 校验规则与本文档不矛盾）:
```
py -3.13 -c "import sys; sys.path.insert(0, r'D:\harvey_work\docs-cockpit'); from docs_cockpit.build import main; main(['lint'])"
```
Expected: 退出码 0，无新增 error（本 Task 只新建 references，不应影响 lint）。

- [ ] **Step 3: 人工 review section 完整性**

对照 Step 1 的 9 个 section 清单逐项打勾；确认 `status` enum、`progress` band、anchor 4-shape 表与 author 原文逐字一致（grep `skills/docs-cockpit-author/SKILL.md` 对照）。

- [ ] **Step 4: Commit**

```bash
git add references/schema.md
git commit -m "feat(v1.0-A): add references/schema.md extracted from author spec"
```

---

## Task 2: `references/association-method.md` — 4 原子方法（net-new）

**Files:**
- Create: `references/association-method.md`
- Source（思路参考）: author §11（authoring flow）、§16.6（verify 4 档 verdict）、§12（一致性）

- [ ] **Step 1: 创建文件，4 个方法各成一节，每节固定三块「何时用 / 怎么做 / 反模式」**

`## 方法 1 · 检索 discovery`
- 何时用：面对一个 module/subtask，不知道该关联哪个文档时
- 怎么做：(1) `Glob docs/spec/module/*.md docs/spec/concept/*.md docs/plans/**/*.md docs/RFC/*.md docs/spec/*-spec.md` 建全景；(2) 从 module 的 `title`/`desc`/`sprint`/`prd_ref` 抽关键词，`Grep` 反查候选文档；(3) 标记孤儿文档（没被任何 module `docs:` 引用）和无支撑 subtask（0 anchor）
- 反模式：只 grep 一个关键词就下结论；把整个 plan 当 anchor（不收窄到 section）

`## 方法 2 · 推理 reasoning`
- 何时用：有候选文档后，判断哪一段真正相关
- 怎么做：建「证据链」——subtask 讲 X → Read 候选 plan，定位也讲 X 的 §N → 该 §N 即 anchor。**actually Read，不靠关键词碰运气**。用 plan 的术语对齐 subtask title（author §11.1 step 2）
- 反模式：语义不匹配硬凑；一个 subtask 关联整篇文档

`## 方法 3 · 预演 dry-run`
- 何时用：落地 anchor 前，验证它真指对
- 怎么做：Read 候选 anchor 的精确行/章节，对照 subtask title 给 4 档 verdict（accurate / partial / wrong / missing，author §16.6 表）。错 anchor 比缺 anchor 伤害大——找不到对应 section 必须给 ❌ + `# TODO`，**不准瞎猜行号**
- 反模式：写 `:42-89` 却没 Read 过那 42-89 行；verify 不过仍落地

`## 方法 4 · 高亮 highlight（skill-only）`
- 何时用：把关联呈现给用户 / 写进 anchor 时
- 怎么做：用文字标出「片段第 X–Y 行 / 这句话」为什么支撑这条 subtask——即给 anchor 配精确行范围 + 一句关联理由。**不是改 template 渲染高亮**，是推理层证据呈现
- 反模式：只给文件路径不给行范围；不解释为什么相关

顶部声明：`<!-- build / rebuild 共享 · 4 原子方法 -->`，并写明「build 的 Phase 1-4、rebuild 的 Phase 2-3 都引用本文」。

- [ ] **Step 2: 自检——每个方法是否可被 agent 直接执行**

人工 review：每个「怎么做」是否给到具体工具调用（Glob/Grep/Read）和判据，而非抽象建议。把 4 个方法各想象成一条指令跑一遍。

- [ ] **Step 3: Commit**

```bash
git add references/association-method.md
git commit -m "feat(v1.0-A): add references/association-method.md (4 atomic methods)"
```

---

## Task 3: `references/operations.md` — 运维（从主 skill 提取）

**Files:**
- Create: `references/operations.md`
- Source: `skills/docs-cockpit/SKILL.md` 的 bootstrap / config / upgrade 段

- [ ] **Step 1: 创建文件，含 3 section**

- `## bootstrap` — 首次无 CLI 时的 `uv tool install` / `pipx install` / `pip install --user` 优先级链（主 skill 现有内容）
- `## config` — `docs-cockpit.yaml` 关键字段（modules/concepts scan 配置）+ 指向 `references/config_reference.md`
- `## upgrade` — `docs-cockpit upgrade` 一条命令（plugin cache + 原子重启），强调别让用户只「重启 Claude Code」

顶部声明：`<!-- 运维参考 · build 的 Phase 0 引用 · 原 docs-cockpit 主 skill 提取 -->`

- [ ] **Step 2: 人工 review** — 3 section 齐全，命令可复制。

- [ ] **Step 3: Commit**

```bash
git add references/operations.md
git commit -m "feat(v1.0-A): add references/operations.md (bootstrap/config/upgrade)"
```

---

## Task 4: `skills/docs-cockpit-build/SKILL.md` — 7-phase 构建流程

**Files:**
- Create: `skills/docs-cockpit-build/SKILL.md`
- Reference: `references/{schema,association-method,operations}.md`（Task 1-3 产物）

- [ ] **Step 1: 写 frontmatter（这是机器路由关键 · 逐字采用，pushy + 反向 discriminator）**

```yaml
---
name: docs-cockpit-build
description: |
  Build a docs-cockpit project's documentation-association system from scratch or fill its gaps — scan ALL project docs, infer which module/subtask should link to which spec/plan/rfc section, dry-run-verify the anchors, then write them. Defaults to planning the WHOLE project (every module's spec/plan), deciding each linkage WITH the user in dialogue. Produces module↔subtask↔doc anchors + drafts missing spec/plan docs, then renders the dashboard.

  TRIGGER when the user wants to: 「把项目文档体系建起来」「关联模块和任务/文档」「规划整个项目的 spec/plan」「给所有 module 补 anchor」「这些 subtask 该关联哪个文档」 / "build the doc association", "wire modules to specs", "plan the whole project's docs", "add anchors to every module".

  Do NOT trigger for: an EXISTING association that drifted / needs refresh after refactor (→ docs-cockpit-rebuild); just re-rendering the HTML with no association work (→ CLI `docs-cockpit render`); reading status narratives (→ docs-cockpit-rebuild Phase 1). Discriminator: this skill is 0→1 / whole-project association BUILDING; rebuild is refreshing an existing one.
---
```

- [ ] **Step 2: 写 body —— 7 phase，每 phase 固定「目标 / 动作 / 引用的原子方法 / 产出」**

phase 清单（对照 spec §4）：
- `## Phase 0 · 确保 cockpit 存在` — 检查 `docs-cockpit.yaml`，无则 init + bootstrap（引用 `references/operations.md`）。**Codex 适配**：本 phase 幂等往项目根 `AGENTS.md` 写引导锚点（已存在则跳过），内容指向 `use-docs-cockpit`（spec §5.5.2 决策 5）
- `## Phase 1 · 检索` — 引用 `association-method.md` 方法 1，建文档全景图 + 候选池 + 孤儿/缺口清单
- `## Phase 2 · 推理` — 方法 2，对每个 module/subtask 推断应关联的 doc section；列缺口（无 spec 的 module / 无 plan 的 sprint / 0-anchor subtask）
- `## Phase 3 · 预演` — 方法 3，落地前 Read 每个候选 anchor，给 4 档 verdict
- `## Phase 4 · 高亮` — 方法 4，对每条关联标出相关行 + 理由
- `## Phase 5 · 对话决策` — 逐个或批量提议，用户 accept/调整/skip（强调：error 级关联改动必须先问，参考 author §5 的"never silently fix"）
- `## Phase 6 · 落地 + 补文档` — 写 anchor 到 MD（格式见 `references/schema.md`）；为缺口起草新 spec/plan（frontmatter 见 schema.md）
- `## Phase 7 · 渲染` — 调 `docs-cockpit render`（注：Stage A 时 CLI 仍叫 `build`，本 skill 先写 `render` 并备注「Stage B 改名前用 `docs-cockpit build`」）；验证 0 warning

body 顶部加一段「why this skill exists」（north-star：认知交 skill / python 只渲染 / anchor 精度优先），仿 author 风格。

- [ ] **Step 3: lint 不破坏现有 build**

Run:
```
py -3.13 -c "import sys; sys.path.insert(0, r'D:\harvey_work\docs-cockpit'); from docs_cockpit.build import main; main(['lint'])"
```
Expected: 退出码 0（新建 skill 不影响 lint）。

- [ ] **Step 4: 触发路由自检** — 把 description 的正向触发短语和「Do NOT」短语各念一遍，确认与 `docs-cockpit-rebuild`（Task 5）边界不重叠。

- [ ] **Step 5: Commit**

```bash
git add skills/docs-cockpit-build/SKILL.md
git commit -m "feat(v1.0-A): add docs-cockpit-build skill (7-phase association build)"
```

---

## Task 5: `skills/docs-cockpit-rebuild/SKILL.md` — 5-phase 刷新流程

**Files:**
- Create: `skills/docs-cockpit-rebuild/SKILL.md`
- Reference: `references/association-method.md`、`docs/state.json`

- [ ] **Step 1: 写 frontmatter（含吸收 standup 的状态查询触发）**

```yaml
---
name: docs-cockpit-rebuild
description: |
  Refresh / repair an EXISTING docs-cockpit association system that has drifted — anchors gone stale after a refactor, specs evolved, links outdated, or status questions about current state. Reads state.json + MD, diagnoses drift (lint + dry-run-verify every anchor's 4-tier verdict), re-infers correct anchors, and refreshes ONLY the broken ones (keeping valid links intact). Also answers narrative status questions (what's blocked / sprint progress / which modules stalled) as its Phase 1 read-current-state.

  TRIGGER when the user says: 「关联乱了重新梳理」「重构后 anchor 失效了」「spec 改了同步关联」「这个 module 关联还准不准」「项目进度怎么样」「哪些卡了」「sprint 进度」 / "anchors are stale", "re-sync after refactor", "is this module's linkage still right", "what's blocked", "sprint progress", "weekly status".

  Do NOT trigger for: building association from scratch / whole-project planning (→ docs-cockpit-build); pure HTML re-render (→ CLI `docs-cockpit render`). Discriminator: rebuild = an association ALREADY EXISTS and we diagnose+refresh it (or just read its state); build = create it 0→1.
---
```

- [ ] **Step 2: 写 body —— 5 phase（对照 spec §5）**

- `## Phase 1 · 读现状` — 读 `state.json` + MD，叙述当前关联体系状态（吸收 standup：modules[] / issues[] / 进度 / blocker 叙事，无文件改动时此 phase 即终点）
- `## Phase 2 · 诊断漂移` — 跑 `lint`（死规则）+ 用 `association-method.md` 方法 3 重验所有 anchor，输出每条 4 档 verdict
- `## Phase 3 · 重新推理` — 对 partial/wrong/missing 的，用方法 1+2 重找正确 anchor
- `## Phase 4 · 刷新落地` — 改漂移 anchor，**保留 accurate 的不动**（最小 diff），格式见 `references/schema.md`
- `## Phase 5 · 渲染验证` — `docs-cockpit render`（同 Task 4 备注）+ 复查

body 顶部 why-section + 「rebuild vs build 差别」一段（共享 4 方法；rebuild 增量诊断、只动漂移、保留有效）。

- [ ] **Step 3: lint 不破坏**（同 Task 4 Step 3 命令）Expected: 退出码 0。

- [ ] **Step 4: 触发路由自检** — 与 build（Task 4）+ 旧 standup 的边界检查（standup 仍存在，rebuild 的状态查询触发会与之重叠——这是预期的「新旧并存」，Stage B 删 standup 后唯一化；在 body 注明此临时重叠）。

- [ ] **Step 5: Commit**

```bash
git add skills/docs-cockpit-rebuild/SKILL.md
git commit -m "feat(v1.0-A): add docs-cockpit-rebuild skill (5-phase refresh + state read)"
```

---

## Task 6: `skills/use-docs-cockpit/SKILL.md` — 入口元 skill（薄）

**Files:**
- Create: `skills/use-docs-cockpit/SKILL.md`

- [ ] **Step 1: 写 frontmatter**

```yaml
---
name: use-docs-cockpit
description: |
  Entry/router for the docs-cockpit skill ecosystem. Loaded by default in any project that has a docs-cockpit.yaml. Tells the agent: this project uses docs-cockpit; cognition lives in skills, python only renders; route to docs-cockpit-build (create/extend association), docs-cockpit-rebuild (refresh/diagnose/read-status), or CLI docs-cockpit render (just regenerate HTML).
---
```

- [ ] **Step 2: 写 body（薄 · 只路由 · 对照 spec §5.5.1）**

- 一句话 north-star：认知交 skill、python 只做渲染、anchor 精度优先（错 anchor 比缺 anchor 伤害大）
- `## 路由表`（spec §5.5.1 的 4 行表逐字采用）：建/补关联→build；漂移/失效/spec改→rebuild；只刷新 HTML→CLI `render`；查状态进度→rebuild Phase 1
- `## 何时不用` — 不是 docs-cockpit 项目（无 `docs-cockpit.yaml`）时本入口不应触发

**保持 < 60 行**（每 session 注入吃 token，必须薄）。

- [ ] **Step 3: 字数检查**

Run:
```
py -3.13 -c "print(sum(1 for _ in open(r'D:\harvey_work\docs-cockpit\skills\use-docs-cockpit\SKILL.md', encoding='utf-8')))"
```
Expected: 行数 < 60。超了就砍内容（路由表 + north-star 即可，细节交给被路由的 skill）。

- [ ] **Step 4: Commit**

```bash
git add skills/use-docs-cockpit/SKILL.md
git commit -m "feat(v1.0-A): add use-docs-cockpit entry/router skill"
```

---

## Task 7: `hooks/` — SessionStart 条件注入

**Files:**
- Create: `hooks/hooks.json`
- Create: `hooks/run-hook.cmd`
- Create: `hooks/session-start`
- Reference（照搬模式）: `C:\Users\86157\.claude\plugins\cache\superpowers-marketplace\superpowers\5.1.0\hooks\`

- [ ] **Step 1: 创建 `hooks/hooks.json`**

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" session-start",
            "async": false
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: 创建 `hooks/run-hook.cmd`（照搬 superpowers polyglot wrapper）**

完整内容复制 superpowers 的 `run-hook.cmd`（已读过：cmd 块找 Git-bash 跑、无 bash 静默 `exit /b 0`；Unix 段 `exec bash "${SCRIPT_DIR}/${SCRIPT_NAME}"`）。逐字照搬，仅注释里的 "superpowers" 改 "docs-cockpit"。

- [ ] **Step 3: 创建 `hooks/session-start`（条件注入 · 与 superpowers 的关键差异）**

输出协议必须是结构化 JSON（Claude Code 读 `hookSpecificOutput.additionalContext`），照搬 superpowers 的三路平台检测 + bash 参数替换 JSON 转义；裸文本 + XML 标签包裹是错误协议。

```bash
#!/usr/bin/env bash
# SessionStart hook · 仅在 docs-cockpit 项目注入 use-docs-cockpit 路由引导
#
# 与 superpowers 的 session-start 的关键差异：docs-cockpit 是「条件注入」——
# 向上 6 层探测 docs-cockpit.yaml，不是 docs-cockpit 项目则静默 exit 0。
# 输出协议与 JSON 转义机制照搬 superpowers（生产验证）的三路平台检测：
#   Cursor       → {"additional_context": "..."}                     （snake_case）
#   Claude Code  → {"hookSpecificOutput": {"hookEventName":
#                    "SessionStart", "additionalContext": "..."}}     （嵌套）
#   Copilot/其它 → {"additionalContext": "..."}                       （SDK 标准顶层）
set -euo pipefail

# ── 1 · 条件注入：向上找 docs-cockpit.yaml（含 cwd 最多 6 层）──
dir="$(pwd)"
found=""
for _ in 1 2 3 4 5 6; do
  if [ -f "$dir/docs-cockpit.yaml" ]; then found="$dir"; break; fi
  parent="$(dirname "$dir")"
  [ "$parent" = "$dir" ] && break
  dir="$parent"
done

# 不是 docs-cockpit 项目 → 静默退出，绝不污染无关项目
[ -z "$found" ] && exit 0

# ── 2 · 定位 plugin root（set -u 安全展开；env 缺失回退脚本位置推导）──
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-${CURSOR_PLUGIN_ROOT:-}}"
if [ -z "$PLUGIN_ROOT" ]; then
  PLUGIN_ROOT="$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)" || PLUGIN_ROOT=""
fi
[ -z "$PLUGIN_ROOT" ] && exit 0

SKILL="${PLUGIN_ROOT}/skills/use-docs-cockpit/SKILL.md"
[ -f "$SKILL" ] || exit 0

# ── 3 · 注入内容：剥掉 YAML frontmatter，只取 SKILL.md body ──
skill_body="$(awk 'BEGIN{f=0} /^---$/{f++; next} f>=2{print}' "$SKILL" 2>/dev/null || true)"
[ -z "$skill_body" ] && exit 0

# JSON 字符串转义（superpowers 同款：bash 参数替换，每个 ${s//old/new}
# 是一次 C 级整串替换，远快于逐字符循环）
escape_for_json() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/\\r}"
    s="${s//$'\t'/\\t}"
    printf '%s' "$s"
}

skill_body_escaped=$(escape_for_json "$skill_body")
# 注意：下面字符串里的 \n 是字面量反斜杠+n——内容已 JSON 转义，
# 这里继续拼 JSON 转义序列，最终由 printf '%s' 原样嵌入 JSON。
session_context="# docs-cockpit router (auto-injected)\n\n${skill_body_escaped}"

# ── 4 · 三路平台检测输出（照搬 superpowers · printf 规避 bash 5.3+ heredoc 挂起）──
# Claude Code 会同时读 additional_context 和 hookSpecificOutput 且不去重，
# 所以每个平台只输出它自己消费的那一个字段。
if [ -n "${CURSOR_PLUGIN_ROOT:-}" ]; then
  # Cursor 设 CURSOR_PLUGIN_ROOT（可能同时设 CLAUDE_PLUGIN_ROOT）
  printf '{\n  "additional_context": "%s"\n}\n' "$session_context"
elif [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -z "${COPILOT_CLI:-}" ]; then
  # Claude Code 设 CLAUDE_PLUGIN_ROOT 且无 COPILOT_CLI
  printf '{\n  "hookSpecificOutput": {\n    "hookEventName": "SessionStart",\n    "additionalContext": "%s"\n  }\n}\n' "$session_context"
else
  # Copilot CLI（COPILOT_CLI=1）或未知平台 → SDK 标准顶层字段
  printf '{\n  "additionalContext": "%s"\n}\n' "$session_context"
fi

exit 0
```

- [ ] **Step 4: smoke test —— 无 docs-cockpit.yaml 的目录应静默**

Run:
```bash
cd /tmp && CLAUDE_PLUGIN_ROOT="D:/harvey_work/docs-cockpit" bash "D:/harvey_work/docs-cockpit/hooks/session-start"; echo "exit=$?"
```
Expected: 无输出，`exit=0`。

- [ ] **Step 5: smoke test —— docs-cockpit 项目应注入引导**

Run:
```bash
cd "D:/harvey_work/docs-cockpit" && CLAUDE_PLUGIN_ROOT="D:/harvey_work/docs-cockpit" bash hooks/session-start; echo "exit=$?"
```
Expected: 打印一段合法 JSON——含 `hookSpecificOutput.hookEventName = "SessionStart"` 与 `hookSpecificOutput.additionalContext`，后者以 `# docs-cockpit router (auto-injected)` 开头、包含 use-docs-cockpit 的 SKILL.md body（frontmatter 已剥除、内容经 JSON 转义），`exit=0`。可用 `... | py -3.13 -c "import json,sys; d=json.load(sys.stdin); print(d['hookSpecificOutput']['additionalContext'][:80])"` 验证 JSON 合法性。

- [ ] **Step 6: Commit**

```bash
git add hooks/hooks.json hooks/run-hook.cmd hooks/session-start
git commit -m "feat(v1.0-A): add SessionStart hook with docs-cockpit.yaml conditional injection"
```

---

## Task 8: Dogfood —— 在本仓库跑通新流程

**Files:** 无新建 · 端到端验证 Task 1-7 产物

- [ ] **Step 1: 路由验证 —— use-docs-cockpit 指对地方**

人工：读 `skills/use-docs-cockpit/SKILL.md` 路由表，对以下 4 句输入各确认路由正确：
- "把这个项目的 module 都关联上对应 plan" → docs-cockpit-build
- "重构后 M07 的 anchor 还准吗" → docs-cockpit-rebuild
- "重新生成 dashboard" → CLI render
- "现在哪些 module 卡了" → docs-cockpit-rebuild Phase 1

- [ ] **Step 2: build 流程 dry-run —— 对本仓库一个真实 module 走 Phase 1-4**

挑一个本仓库的 module（如 `docs/spec/module/` 下任一），实际执行 `association-method.md` 的方法 1-3：Glob 建全景 → 对其一个 subtask 推理候选 doc section → Read 验证 verdict。确认 4 原子方法可被照着执行、产出合理 anchor 建议。

- [ ] **Step 3: 全量 lint 仍绿**

Run:
```
py -3.13 -c "import sys; sys.path.insert(0, r'D:\harvey_work\docs-cockpit'); from docs_cockpit.build import main; main(['lint'])"
```
Expected: 退出码 0，issue 数不高于 Stage A 之前（新建文件未引入 schema 回归）。

- [ ] **Step 4: 确认零破坏 —— 旧 4 skill 原样存在**

Run:
```bash
ls skills/
```
Expected: 仍有 `docs-cockpit/ docs-cockpit-author/ docs-cockpit-standup/ docs-cockpit-portfolio/`（旧的全在）+ 新增 `docs-cockpit-build/ docs-cockpit-rebuild/ use-docs-cockpit/`。新旧并存。

- [ ] **Step 5: Commit（dogfood 记录，如有微调）**

```bash
git add -A
git commit -m "test(v1.0-A): dogfood new build/rebuild flow on this repo, lint green"
```

---

## Stage A 完成定义（DoD）

- [ ] `references/` 三份齐全，section 清单全打勾
- [ ] 三个新 skill frontmatter description 正反触发短语完整，互不重叠（standup 重叠是已知临时态）
- [ ] `hooks/session-start` 两个 smoke（有/无 yaml）都符合预期
- [ ] `docs-cockpit lint` 退出码 0
- [ ] 旧 4 skill + build.py + plugin.json **未被改动**（`git diff --stat` 确认只新增、无删改旧文件）
- [ ] 全程 commit 粒度为「一产物一 commit」

**Stage A 后接续：** dogfood 验证方法论有效 → 写 Stage B plan（CLI 瘦身 `build`→`render` + 删认知子命令/MCP/portfolio + author schema 降 reference + standup 并入 rebuild + 触发路由唯一化）。
