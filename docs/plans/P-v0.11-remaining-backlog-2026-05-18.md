---
id: DOCS-COCKPIT-V0.11-BACKLOG-2026-05-18
type: plan
title: "v0.11 未完成需求 backlog · alpha.5 之后"
status: planned
sprint: "0.11"
owner: harvey
desc: "v0.11 alpha.1-5 之后剩余的所有未完成需求 · 按优先级排序 · 含 UI split-view(用户最早提但一直没做)+ M03/M04 剩余 + Step 5 收口 + v0.12 候选"
created: 2026-05-18
depends_on: [DOCS-COCKPIT-V0.11-PLAN-2026-05-18]
docs:
  - { title: "v0.11 driver-seat plan · 主 design doc", path: "docs/plans/P-v0.11-driver-seat.md" }
  - { title: "v0.11 test plan", path: "docs/plans/P-v0.11-test-plan.md" }
---

# v0.11 未完成需求 backlog · alpha.5 之后

## §0 · 当前进度快照

```
M01 Build Engine        · done  · 100% · 10/10  ✅ alpha.3
M02 CLI                 · done  · 100% · 9/9    ✅ alpha.3
M03 Plugin              · in-progress · 57% · 4/7
M04 Author Skill        · in-progress · 44% · 4/9
M05 Portfolio           · done  · 100% · 4/4
M06 Browse Reader       · done  · 100% · 4/4

Overall: 94.2%
Step 1 ✅  Step 2 ❌(0%)  Step 3 ✅  Step 4 ✅  Step 5 ❌(0%)
```

**alpha session 实际推进路线 vs plan §11 原顺序**:

| Plan §11 顺序 | 实际推进 | 备注 |
|---|---|---|
| Step 0 prerequisite | ✅ 0.10.1 / 0.10.2 ship | dogfood + bug fix |
| Step 1 测试基础 + refactor | ✅ 5 个 commit · 0.11.0-alpha.1 | 用户视觉无感知 |
| **Step 2 UI split-view** | ❌ **整个跳过** | **user 最早实测提的需求(图一/图二反馈)· 优先级被 M01/M02 完成压过去了** |
| Step 3 W1 数据层 | ✅ 0.11.0-alpha.2 | subtask 一等公民 |
| Step 4 W3 prompt scaffolding | ✅ 0.11.0-alpha.3 | M01 + M02 全 done |
| Step 5 收口 + 公告 | ❌ 没做 | 0.11.0 正式 release 没出 |

**两个 alpha 期间发现的 bug fix**:
- alpha.4 · validator status × subtasks cross-field 校验
- alpha.5 · frontend localStorage key 改用 stable subtask.id

## §1 · 未完成 backlog 总览(按优先级)

```
┌──────────────────────────────────────────────────────┬──────────┬───────┐
│ Item                                                  │ Priority │ Step  │
├──────────────────────────────────────────────────────┼──────────┼───────┤
│ A · UI split-view 二级页面 + systemDocs inline preview │ P0       │ 2     │
│ B · M03 / M04 剩余 5 subtask(全是文档 + bump 工作)      │ P0       │ 5     │
│ C · 0.11.0 正式 release 收口(version / README / 公告) │ P1       │ 5     │
│ D · alpha 期间发现的 follow-up issue(localStorage 漂移) │ P1       │ N/A   │
│ E · v0.12 候选(W2 LLM 优化器 / MCP / apply-patch 等) │ P2       │ v0.12 │
└──────────────────────────────────────────────────────┴──────────┴───────┘
```

P0 = 阻塞 v0.11 正式 release · P1 = 应做 · P2 = 下个版本

## §2 · P0 · A · UI split-view 二级页面 + systemDocs inline preview

**为什么是 P0**:这是 user 最早实测反馈的需求(2026-05-18 dogfood 当天)· plan-eng-review round-3 已 fold 进 §6.6 + §6.7 + §11 Step 2 · 但 alpha session 推进时选了「M01 / M02 完成优先」路线 · 整个 Step 2 跳过了。**不做 = v0.11 'driver-seat' 叙事不闭环**。

### A.1 · UI split-view 二级页面(plan §6.6)

用户原话:「点 in-progress 任务 · 就跳转到二级页面 · 然后左侧显示现在的抽屉 · 右侧自动预览每个任务的 md 计划和关联文档」。

**当前 v0.10 行为**:点 module card → 弹 modal drawer(单列 · max-width 960px) · 关联文档列表里点[预览]切换 drawer 内容。信息密度低 · subtask + code anchor + Copy prompt 一行密集元素挤不下。

**要做的事**:
- [ ] `templates/index.html.tmpl` 加 hash router · 支持 `#/module/<id>` / `#/sysdoc/<id>` / `#/concept/<id>` URL
- [ ] 加 split layout CSS · `display: grid; grid-template-columns: minmax(360px, 38%) 1fr`
- [ ] 左 navigator:复用现 `.drawer-body` 内容(desc / status / progress / subtask checklist / linked docs list)· 自适应宽度不再限 960px
- [ ] 右 preview:复用现 `.doc-preview-body` 渲染样式 · marked.js 加载关联文档 content
- [ ] 默认右栏渲染第一条关联文档 · 点 list 其他 row 切换 active state
- [ ] module card / system docs row click handler 改 `location.hash = '#/module/<id>'`(原来弹 modal)
- [ ] topbar 加「← 返回 dashboard」按钮 + Esc 键 hotkey 退出
- [ ] 响应式 < 1024px viewport 退化为 stacked 单列(左在上 / 右在下)
- [ ] `?ui=modal` URL query 保留原 modal 行为(向后兼容 · 重度用户 muscle memory 不破)
- [ ] W1 subtask 的 code anchor(0.11.0-alpha.2 已加 `code_anchors[]` payload)在右栏渲染 code preview snippet + `vscode://file/...` 深链按钮
- [ ] W3 「Copy prompt」按钮(0.11.0-alpha.3 已加 prompts.js sidecar)放在左 navigator 每条 subtask 末尾 · 右栏可选自动 preview rendered prompt

工程量估算:**1-1.5 周 human · CC+gstack 6-8 小时**(template HTML ~2900 行 · 改 400-500 行 + 新增 200-300 行 hash router / split CSS / responsive)

风险:HTML 体积大 · 改动跨多 section · 容易破现有 drawer / modal 行为。要 alpha.6 单独 ship · 不跟其他 feature 混。

### A.2 · systemDocs inline preview(plan §6.7)

**当前 v0.10 行为**:点系统文档抽屉里的某条(CLAUDE.md / README / Config Reference 等)· 浏览器新窗口打开 `file:///path.md` · 只 dump raw markdown(不渲染)。

**要做的事**:
- [ ] `build.py::build_payload` 给 systemDocs 跑同款 `_resolve_and_embed_docs` 逻辑(0.7.1 module docs 已有 · systemDocs 没接)· 输出 `systemDocs[].content` + `systemDocs[].mtime` + `systemDocs[].exists`
- [ ] 单 doc content hard cap 50KB(防 memory dir 撑爆 payload)
- [ ] template `renderSystemDocs()` (line 2755) 改 click handler · 不开新窗口 · 改 `location.hash = '#/sysdoc/<id>'` 进 §A.1 的 split-view
- [ ] 右栏 marked.js 渲染 system_doc content · 跟 module 关联文档同款体验

工程量:**2-3 天 human · CC+gstack 2-3 小时**(payload 改少 · 主要 §A.1 完成后顺手接)

### A.3 · 测试 + alpha.6 release

- [ ] `tests/e2e/test_split_view.py` · Playwright · navigate 触发 hash route · assert 右栏 marked.js 渲染 · click 切换 · Esc 返回
- [ ] systemDocs embed unit test(检 payload 含 content)
- [ ] 0.11.0-alpha.6 bump(4 文件 + CHANGELOG)
- [ ] dogfood docs-cockpit 自身 · screenshot 对比 alpha.5 vs alpha.6

**A 总工程量**:**~2 周 human · CC+gstack 1-2 工作日**。是 v0.11 剩余工作里最大块。

---

## §3 · P0 · B · M03 / M04 剩余 subtask(5 个 · 全是文档 + version bump 工作)

### B.1 · M03 Claude Code Plugin · 3 个未做

- [ ] **v0.11 skill section** · prompt scaffolding 触发条件 + CLI 用法
  - 改 `skills/docs-cockpit/SKILL.md` 加一节「使用 prompt scaffolding」· 介绍 `docs-cockpit prompt` / `--list` / `--copy` 用法
  - 触发条件:用户问「给我个提示词去做 subtask X」 / 「render prompt for M03-X1」等
- [ ] **v0.11 4 文件 version bump** · plugin.json / marketplace.json / __init__.py / CHANGELOG → 0.11.0 正式(去 alpha 后缀)
- [ ] **v0.12 候选 · MCP server**(留 v0.12 不做 · 这条 subtask 应该改为 [deferred to v0.12])

### B.2 · M04 Author Skill · 5 个未做

- [ ] **§2.4 · subtask 对象 schema** 完整定义(`id / title / status / code / docs`)· 引用 alpha.2 实施
- [ ] **§2.4 · id 算法说明** · `<module-id>-<sha1(title)[:6]>` + title 改 = id 重算的 trade-off
- [ ] **§10 · prompt template 新节** · 4 内置 template(generic / feature / fix / refactor)介绍 + ChoiceLoader 寻找顺序(user override → builtin)
- [ ] **§10.2 · context vars stability contract** · 列 v0.11 5 个 vars(module / subtask / linked_docs / repo_root / current_branch)+ since-version + 升级守则(plan-eng-review 2A)
- [ ] **`## 3 · 待办` body 内联语法 `@code @docs`** · 文档化(alpha.2 实施时已 work · 但 author skill 没写规范)

工程量:**1 天 human · CC+gstack 2-3 小时**(纯文档 · 跟 v0.11 alpha.1-5 实施对齐 · 不动代码)

### B.3 · 同步 references/ 文档

- [ ] `references/frontmatter_conventions.md` 加 subtask schema 速查
- [ ] `references/prompt_templates.md` · 新文件 · 列内置 templates + 写自定义 template 指南

工程量:**0.5 天 · CC+gstack 1 小时**

**B 总工程量**:**~1.5 天 human · CC+gstack 半个工作日**

---

## §4 · P1 · C · 0.11.0 正式 release 收口(plan §11 Step 5)

- [ ] `CHANGELOG.md` 加 0.11.0 final section(汇总 alpha.1-6 全部内容 + Why 段落)
- [ ] `README.md` / `README.zh-CN.md` 加 v0.11 banner + 截图(必有 split-view 截图 + Copy prompt 录屏)
- [ ] 4 文件 version 同步 bump 到 `0.11.0`(去 alpha 后缀)
- [ ] `docs-cockpit upgrade` 路径回归(0.10 → 0.11 upgrade flow 跑通)
- [ ] 给下游 Sourcery + bastion 用户单点通知 + migrate 指南
- [ ] (可选)1 篇 blog 或 long-form CHANGELOG · 解释「为什么 W2 不在 v0.11」(trust 边界产品 essay)
- [ ] git push + tag `v0.11.0`(+ alpha.1-6 历史 tag 如果要保留)

工程量:**0.5-1 天 · CC+gstack 2-3 小时**

---

## §5 · P1 · D · alpha session 期间发现的 follow-up

### D.1 · localStorage 状态写回 MD(plan §7 #1)

alpha.5 我已经修了 localStorage key stable · 但更深的问题:**用户在 dashboard 上勾的 subtask 状态只存 localStorage · 不写回 MD frontmatter**。结果跨机器 / 跨 git pull 状态丢失。

- [ ] 新增 `docs-cockpit sync-status` CLI(plan §7 #1 已规划 · 标为 v0.11.1 patch)
- [ ] 读 localStorage export JSON · 跟 MD frontmatter merge · 输出 diff · 用户 review 后 apply
- [ ] **决策**:作为 v0.11.x patch 做 · 还是延到 v0.12

### D.2 · subtask.id 算法跟 body fallback 一致性

alpha.2 schema.py normalize_subtasks 用 sha1(title)[:6] · `## 3 · 待办` body parser 也调用 normalize · 所以 id 算法已经统一。但 plan-eng-review round-2 issue #3 提的「混源 module(部分 subtask 在 frontmatter 部分在 body)id 冲突」没专门测。

- [ ] 加 1 个 unit test 覆盖混源 module 的 id 一致性

工程量:**0.5 小时**

### D.3 · pyperclip 实测覆盖

alpha.3 `docs-cockpit prompt --copy` 用 pyperclip · 装了走剪贴板没装走 stdout。CI matrix 上没装 pyperclip · 实际行为没测。

- [ ] integration test 加一个 `--copy` 不装 pyperclip 的 case(用 `pip uninstall pyperclip -y` 然后跑 · 或者用 `monkeypatch.setattr` 模拟 ImportError)

工程量:**0.5 小时**

### D.4 · build.py SyntaxWarning(已修)

alpha.1 时 `render_html` docstring 里 `<\/script>` 触发 Python 3.12+ SyntaxWarning。alpha.1 我加 `r"""` raw string 已修。✅ 无 follow-up。

### D.5 · status 跟 progress 字段在 module level 跟 frontend 算的也可能不一致

- v0.10 frontend `getModule()` (line 1530) 有自动:
  - `m.progress === 100 && status !== 'done'` → 自动设 status=done
  - `m.progress > 0 && < 100 && status === 'not-started'` → 自动设 in-progress
- 这是 frontend 单方面 override · 没写回 state.json · 跟 alpha.4 backend validator 可能再次产生不一致风险
- [ ] 评估这条 frontend override 要不要移除 · 改由 backend `_build_card` 做(数据一致性 single source)

工程量:**0.5-1 小时 分析 + 决策**

---

## §6 · P2 · E · v0.12 候选(本 plan 不做)

跟 plan §11 末尾「v0.12 候选」一致 · 这里整合 alpha.1-5 实施后 confirm 还有:

- [ ] **W2 LLM 文档优化器** · `docs-cockpit suggest <file>` · plan §6.4 trust premise 限制必须走「生成 prompt 让用户跑 Claude」路径
- [ ] **MCP server** · Claude 直接消费 cockpit prompt(替代 copy-paste · M03 subtask 7 提到了)
- [ ] **`docs-cockpit apply-patch` CLI** · 解析 Claude 输出的 frontmatter patch yaml · 自动落回 MD(plan §7 #2)
- [ ] **`docs-cockpit sync-status` CLI**(如果 §5 D.1 没在 v0.11.x patch 做就推迟)
- [ ] **per-module prompts shard** · `prompts/<module-id>.json` · 大 cockpit (>50 mods) prompts.js 体积超 1.2MB 时拆(plan §7 #4)
- [ ] **`editor:` config 字段** · `docs-cockpit.yaml` 加 `editor: vscode | cursor | jetbrains` · 让 code anchor 深链按用户编辑器切换 schema(plan §7 #3)

---

## §7 · 推荐顺序

按 dependency + 用户优先级排:

```
1. §2 A · UI split-view + systemDocs inline preview  → alpha.6
   (用户最早提的 · 价值最高 · 工程量最大 · ~2 周)
   ↓
2. §3 B · M03 / M04 剩余 subtask(全文档)              → alpha.7 或 0.11.0
   (~1.5 天 · 边推 UI 边写)
   ↓
3. §5 D · alpha session follow-up                      → 顺手做 · 0.11.0 前
   (~2-3 小时)
   ↓
4. §4 C · 0.11.0 正式 release 收口                     → 0.11.0
   (~0.5-1 天 · CHANGELOG / README / version bump / push)
   ↓
5. §6 E · v0.12 候选                                   → 下个 release cycle
```

**v0.11 完整 ship 还差**:~3 周 human · 或 CC+gstack 8-10 工作日。

---

## §8 · 决策点 · 需要用户确认

- [ ] **D1**:UI split-view(§2 A)是 v0.11 必做还是可以推 v0.12?(我建议必做 · 不然「driver-seat」叙事不闭环 · 但 user 决策)
- [ ] **D2**:M03 subtask 7「MCP server」标 `deferred-to-v0.12` 还是删掉?(我建议改 deferred · 不让 M03 永远不 done)
- [ ] **D3**:§5 D.1 localStorage 写回 MD 是 v0.11.1 patch 还是 v0.12?(plan §7 #1 写的是 v0.11.1 · 但 alpha.5 fix 后用户痛感降低 · 可以延)
- [ ] **D4**:`?ui=modal` 向后兼容要不要做 · 还是直接 break-change(plan §6.6 写要做 · 但可能没人用)

---

**Status:** planned · backlog 整理完毕 · 等用户决定 §8 决策点 + 启动 §2 A(UI split-view)
