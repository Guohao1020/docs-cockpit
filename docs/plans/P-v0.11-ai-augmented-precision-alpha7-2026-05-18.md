---
id: DOCS-COCKPIT-V0.11-AI-PRECISION-2026-05-18
type: plan
title: "v0.11 AI-augmented precision · alpha.7 sub-plan"
status: planned
sprint: "0.11"
owner: harvey
desc: "把语义精度从 python regex 让出去给 LLM · 两条线:模式 3 教 AI 写 MD 时精确 + 模式 2 'Ask AI to refine' 让 AI 修现有 MD"
created: 2026-05-18
depends_on:
  - DOCS-COCKPIT-V0.11-PLAN-2026-05-18
  - DOCS-COCKPIT-V0.11-UI-SPLITVIEW-2026-05-18
docs:
  - { title: "主 driver-seat plan · §0 角色重新框架", path: "docs/plans/P-v0.11-driver-seat.md" }
  - { title: "alpha.6 UI split-view spec", path: "docs/plans/P-v0.11-ui-split-view-alpha6-2026-05-18.md" }
---

# v0.11 AI-augmented precision · alpha.7

## §1 · 设计原则

主 plan §0 lock:**driver-seat 是 AI 副驾不是精度引擎**。语义精度走 LLM · python 只做解析层。

实现两条线 · 并行无依赖:

| 线 | 时机 | 谁干活 | docs-cockpit 角色 |
|---|---|---|---|
| 模式 3 | write-time(用户写 MD 时) | Claude / Codex | SKILL.md 给 AI 喂规则 |
| 模式 2 | on-demand(用户在驾驶舱点按钮时) | Claude / Codex | 拼 prompt + 接 patch |

模式 1(build-time API)留 v0.12 + MCP 直连。

## §2 · 模式 3 · Write-time · 教 AI 写 MD 就精确

### §2.1 · `docs-cockpit-author/SKILL.md` 升级

skill 当前 8 节(§1-§8 frontmatter schema)+ alpha.6 计划加 §10 prompt template。alpha.7 加两节:

**§11 · 写 module MD 时的 AI 工作流**

教 Claude 收到「帮我写 M07 module」请求时的标准流程:

1. **先读相关 plan / RFC body**(用户引用的 sprint plan / driver-seat plan / module-related RFC)
   - 不是 grep · 是真读 · 看每个 section 在讲什么
2. **跨参考拆 subtask**:
   - 每个 subtask 应该对应 plan 的某个具体 section / RFC 的某个决策
   - subtask.title 用 plan 里的术语 · 保语义一致
3. **填精准 `code:` anchor**:
   - 阅读 repo · 找 subtask 实际要改的文件 + 函数 + 行号
   - 输出 `code: docs_cockpit/build.py:42-89` 这种精确格式 · 不是 `docs_cockpit/`
4. **填精准 `docs:` anchor**:
   - 用 `docs/plans/x.md#§6.1` 或 `:120-180` 锚到 plan 具体 section / 行号
   - 不要只写 `docs/plans/x.md`(整个 doc · 用户看不到重点)
5. **跨 subtask 一致性 self-check**:
   - 同 module 内 subtask 之间是否有依赖 · 在 title 里 hint(「Lane A 完成后做 Lane B」)
   - 同一 plan section 被多 subtask 引用 · 是否过度细分(merge 一下)

**§12 · 跨 module / doc 一致性 self-check**

教 Claude 在产出 module 后做一次 cross-check:

1. **doc backref**:同一 plan / RFC 被多 module 引用 · 检查 anchor 是否互不重复(M01 §6.1 / M02 §6.2 互斥而不是都指 §6.1)
2. **module 依赖闭环**:M01.blocks=[M02] + M02.depends_on=[M01] · 双向一致
3. **subtask status × module status 一致**:alpha.4 加的 cross-field · skill 提醒 AI 写 frontmatter 时主动 align

### §2.2 · `skills/docs-cockpit/SKILL.md` 主 skill 触发条件

主 skill 加触发规则:

- 用户说「帮我写 M07 module」 / 「补 M01 subtasks」 / 「这个 module spec 怎么写」 → 走 `docs-cockpit-author` skill
- 用户说「检查 M01 跟 plan 是否对齐」 / 「refine M01 docs anchor」 → 触发模式 2(下面 §3)

### §2.3 · 工程量 · ~30 分钟 SKILL.md edit

- `docs-cockpit-author/SKILL.md` 加 §11 + §12 = ~80 行 markdown
- `docs-cockpit/SKILL.md` 加触发条件 = ~20 行
- 不动 python · 不动 template · 不动 state.json schema

### §2.4 · 验收

- [ ] 用户在 Claude Code 里说「帮我写 M07 build worker module · plan 在 driver-seat plan §6 · 代码在 sourcery/worker/」
- [ ] Claude 产出的 MD `subtasks` 字段每条都有 `code:` 和 `docs:` 锚到具体行号 / 章节
- [ ] dogfood docs-cockpit 自身:用 Claude 重写 M03 / M04 剩余 subtasks · 看 anchor 精度

## §3 · 模式 2 · On-demand · split-view「Ask AI to refine」按钮

### §3.1 · UX flow

```
用户打开 split-view #/module/M01
左 navigator 顶部加按钮:
  [🤖 Ask AI to refine this module]
       ↓ click
  生成 refine prompt(类似 alpha.3 的 prompt 但范围是「全 module」不是「single subtask」)
       prompt 内容:
       - module M01 当前完整 frontmatter
       - 所有 subtasks(含已有的 code / docs anchor)
       - 所有 linked docs full body(走 0.7.1 _resolve_and_embed_docs)
       - 指令:「分析这个 module · 检查每个 subtask 是否准确关联到正确的 plan
         section / code 行号 · 输出 YAML patch:
           subtasks:
             - id: M01-f0bd29
               docs: ['docs/plans/x.md#§6.1']  # 添加更精确 anchor
               code: 'docs_cockpit/build.py:200-280'  # 修正 code 范围
         不要改 status / progress / title · 只优化 code/docs anchor 精度」
       ↓ 复制到剪贴板 + toast「Prompt copied · paste to Claude」
       ↓
用户粘到 Claude/Codex · AI 输出 YAML patch
       ↓
用户选项 A · 手动复制 patch 回 module MD
用户选项 B · driver-seat 提供 `docs-cockpit apply-patch <module-id>` CLI 接受 patch(v0.12 候选)
```

### §3.2 · 实施

**Backend** · `docs_cockpit/prompt.py` 加 `render_refine_prompt(module, linked_docs)`:
- 类比 `render_prompt(subtask)` 但范围是「全 module」
- 新模板 `docs_cockpit/templates/prompts/refine.md.j2`
- 输出长 prompt(可能 10-30KB · 因为含多个 linked doc 全文)
- 单 doc 摘要 cap 提到 5000 char(refine prompt 比 single subtask prompt 需要更多 context)

**Frontend** · split-view 左 navigator 顶部按钮:
- `[🤖 Refine with AI]` 按钮
- click → fetch `prompts-refine.js` 拿对应 prompt → 走 alpha.3 同款 clipboard fallback
- toast 显示「Refine prompt copied · paste to Claude / Codex」

**Build-time sidecar** · `docs/prompts-refine.js`:
- 类比 `prompts.js`(alpha.3)· 给每个 module 输出 refine prompt
- `window.__REFINE_PROMPTS__ = {"M01": "...", ...}`

**CLI** · `docs-cockpit refine <module-id>` 直接输出 refine prompt 到 stdout / clipboard

### §3.3 · `docs-cockpit apply-patch <module-id>` CLI(可选 · 简单版)

接 YAML patch:

```bash
docs-cockpit apply-patch M01 < patch.yaml          # 从 stdin
docs-cockpit apply-patch M01 --from-clipboard      # 走 pyperclip
```

- 解析 patch yaml
- 对 module MD frontmatter 做 deep merge(patch 的 `subtasks[].id` 匹配现有 id · 更新该 entry 的 code / docs / status / etc)
- 写回 MD · 生成 `.bak` 备份
- dry-run 默认 · `--apply` 实写

工程量 · ~半天

### §3.4 · 工程量 · ~半天

- prompt.py 加 render_refine_prompt + refine.md.j2 template · ~1 小时
- build.py 输出 prompts-refine.js sidecar · ~30 分钟
- frontend 按钮 + clipboard 走 alpha.3 流程 · ~2 小时
- (可选)apply-patch CLI · ~半天单独

### §3.5 · 验收

- [ ] 打开 M01 split-view · 点「Refine with AI」· 看到「Prompt copied」toast
- [ ] 粘到 Claude · Claude 输出可解析的 YAML patch
- [ ] 复制 patch 到 module MD · build 后 anchor 精度提升(肉眼对比)
- [ ] dogfood:让 Claude 检查 docs-cockpit 自身 M03 / M04 · 看输出 patch 合理度

## §4 · 实施分块 · 2 个 commit

### §4.a · 模式 3 · SKILL.md 升级(纯文档)

工程量:**~30 分钟**
- `skills/docs-cockpit-author/SKILL.md` 加 §11 + §12
- `skills/docs-cockpit/SKILL.md` 加触发条件
- CHANGELOG note
- bump 0.11.0-alpha.6 → 0.11.0-alpha.7

风险:低 · 只动 skill markdown

### §4.b · 模式 2 · Refine 按钮 + sidecar

工程量:**~半天**
- prompt.py + refine.md.j2 template
- build.py 输出 prompts-refine.js
- template index.html.tmpl 加按钮(split-view 左 navigator 内)
- integration test
- bump 0.11.0-alpha.7

风险:中 · 改 template + 新 sidecar 文件

### §4.c · 可选 · apply-patch CLI(留 v0.12 决定)

工程量:**~半天**
- 实现 yaml merge 逻辑
- CLI 子命令 + dry-run / --apply
- integration test

风险:中 · 涉及写回用户 MD · 备份必须严

## §5 · 跟 alpha.6 split-view 的协作

alpha.6 是容器(split-view UI)· alpha.7 是内容(AI 加持的精度)。

```
alpha.6 ship 后 ──→  user 看到 split-view · 但 anchor 精度靠 user 手填
                       (可用 · 但完整体验差)
                              ↓
alpha.7 模式 3 ship ──→  user 用 Claude 写新 module · anchor 自动精确
alpha.7 模式 2 ship ──→  user 点按钮让 AI 检查老 module · 一键复制 patch
                       (完整 driver-seat 叙事闭环)
```

## §6 · 不动的东西

- HTML 仍单文件 · 不引 SPA
- subtask schema(alpha.2)/ prompt scaffolding(alpha.3)/ split-view(alpha.6)所有数据结构不变
- python `_resolve_doc_anchor` / `_resolve_code_anchor` 只做解析层 · 不试图语义判断
- prompts.js sidecar 格式不变(只新增 prompts-refine.js sibling)
- 用户老 MD 不要求 migrate

## §7 · v0.12 候选(本 plan 不做)

- 模式 1 · `docs-cockpit build --ai-augment` · Claude API build-time 自动 augment
- MCP server 直连 · 用户在 Claude Code 里直接「refine M01」· Claude 自动读 cockpit + 写 patch · 不需要 copy-paste
- 跨多 module refine session · AI 一次性优化整 sprint

---

**Status:** planned · alpha.7 follow alpha.6 ship 之后启动
