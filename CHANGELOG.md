# CHANGELOG

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) · 版本号采用 [SemVer](https://semver.org/lang/zh-CN/)。

## [Unreleased] · v0.13 sprint kickoff

v0.13 主题:**DX polish · schema 一致性 · 边界场景**。不引大功能 · 清光 v0.11/v0.12 dogfood 累积的 4 类 maintenance debt。Plan: `docs/plans/P-v0.13-polish-and-edges.md`。

### Sprint backlog seeded(模块 stub · 待实施)

- **M11** · Schema consistency cleanup · 加 `code_anchors[].path_only` + `doc_anchors[].raw_with_anchor` alias · 修 0.11.2 `:lines:lines` 双拼 bug 根 schema 不一致
- **M12** · Parser robustness · `_SUBTASK_SECTION_RE` / `_DOCS_SECTION_RE` 放宽 · 接受 `## §4 · 待办` / `### 待办` / tab 空格
- **M13** · `sync-status --from-browser` · 兑现 M09-1be62a stub · Chrome LevelDB + Firefox SQLite 直读 profile localStorage
- **M14** · CSS time-bomb audit + UX polish · `[hidden]` specificity safety net · subtask doc preview 加 `path:lines` 标识 · 扫光 alpha 占位文案

Distribution plan:alpha.1 (M11) → alpha.2 (M12) → alpha.3 (M13) → alpha.4 (M14) → 0.13.0 finalize。

## [0.12.1] · 2026-05-19

修一个 dogfood 立刻暴露的 v0.12.0 dashboard 显空区域 bug · template/CSS-only patch。

### Why · 用户截图反馈「下面这块区域应该没啥用了删除了吧」

dashboard root(无 hash 路由)滚到底看到一对空白卡片 · 左空 / 右显「Select a doc to preview · §4.d will fill this with marked.js」alpha.6 开发占位文案。这块是 split-view 容器(`#split-page`)· 设计上应该 `hidden` 直到用户进 `#/module/X` 路由。

根因:`.split-page { display: grid }` (specificity 0,0,1,0)跟 UA 的 `[hidden] { display: none }` (specificity 0,0,1,0)同级 · author CSS 后置 winning · 所以 `hidden` HTML 属性失效 · split-page 在 dashboard root 仍然渲染。

### Changed · 1 行 CSS override

`docs_cockpit/templates/index.html.tmpl` 加显式 `.split-page[hidden] { display: none; }` · 让 `hidden` 属性真生效。本来就有的 `body.split-mode .split-page[hidden] { display: grid !important; }` 继续 work · 进 split-view 时正常显。

### Changed · placeholder 文案

把 alpha.6 开发期遗留的「Select a doc to preview · §4.d will fill this with marked.js」改成用户友好版「Select a linked doc, code anchor, or doc anchor from the left to preview here.」(EN + 中)· 走 i18n key `split.placeholder`。

### Not changed

- 不动 schema · 不动 build pipeline · 不动 CLI · 不动 SKILL.md → 走 patch 不走 minor
- 老用户 docs-cockpit upgrade 拿 0.12.1 不强制重启

## [0.12.0] · 2026-05-19

v0.11 driver-seat 的「展示 → 驱动」叙事彻底闭环。v0.11 让用户在 dashboard 看到 + 复制 prompt;v0.12 让 AI 直接消费 prompt / 反向同步状态 / 软优化 MD 质量 · **不再需要人工搬运**。整体跨 4 个 module(M07-M10)· 4 个新 CLI 子命令 · 1 个 MCP server · 6 个新 prompt template · 105 新测试。

### Why · plan §11 v0.12 候选 list 全部 ship

v0.11.0 release 时 plan §11 留了 4 条 v0.12 候选 · 标「本 plan 不做 · 留窗口」。0.12 把这 4 条全部落地:

1. **MCP server**(M07)· 让 Claude / Cursor / Codex 直连消费 cockpit prompt · 替代 v0.11 copy-paste(driver-seat 模式 1)
2. **`docs-cockpit apply-patch`**(M08)· 把 LLM 输出 YAML patch 自动落回 MD · 收口模式 B 的最后一公里
3. **`docs-cockpit sync-status`**(M09)· localStorage 用户勾选反向写回 MD · 闭环 plan §1 缺口 3
4. **`docs-cockpit suggest`**(M10)· LLM 软优化文档质量 · plan §5 Approach W2

Sprint state:`10 modules · 10 done · overall 100% · 0 issues`。dogfood 自身验证全程跑过。

### Added · M07 · MCP Server(driver-seat 模式 1)

`docs_cockpit/mcp_server.py` · Anthropic 官方 `mcp` SDK · stdio transport · 暴露 3 endpoint:

| Endpoint | Type | Backend |
|---|---|---|
| `cockpit_prompt(module_id, subtask_id?, template?)` | tool | `prompt.py::render_prompt` |
| `cockpit_apply_patch(yaml_patch, module_id, apply?)` | tool | `apply_patch.py` (M08) |
| `cockpit://state` | resource | `docs/state.json` |

CLI:`docs-cockpit mcp-serve [-c docs-cockpit.yaml]`。
Plugin 自动注入:`.claude-plugin/plugin.json::mcpServers` · `/plugin install docs-cockpit@docs-cockpit` 后 Claude Code 重启即开箱可用。
Cursor / Codex / Continue 接线步骤:`references/mcp_clients.md`。

Optional dep · `pip install 'docs-cockpit[mcp]'` · 核心 CLI 不强依 · v0.10/v0.11 老用户 footprint 不变。

13 integration tests · all pass。

### Added · M08 · Apply Patch CLI

`docs_cockpit/apply_patch.py` · 收口 refine 流程模式 B:

```bash
docs-cockpit apply-patch path/to/M07.md < patch.yaml             # dry-run
docs-cockpit apply-patch path/to/M07.md --apply < patch.yaml     # 写回 + .bak
```

支持 2 种 MD subtask 表达(跟 author skill §3.1 对齐):
- **Path 1 · frontmatter Form A** · merge by subtask id · YAML 序列化写回
- **Path 2 · body checklist Form C** · 反查 id · 改 `[x]` · 追 inline `@code:` / `@docs:` annotation · 去重不复加

白名单字段 · `status / code / docs / desc`(LLM 想改 title / id / sprint 一律 silently drop · 防越权)。冲突检测 · stale subtask ref / patch parse error 全部 graceful。

被 M07 `cockpit_apply_patch` tool 复用 · 模式 1 (MCP) 走同一 backend。

24 unit tests · all pass。

### Added · M09 · Sync Status CLI

`docs_cockpit/sync_status.py` · 闭环 plan §1 缺口 3「任务清单状态控制不闭环」· dashboard ticks → MD frontmatter 反向同步。

Dashboard 顶栏加 **Export** 按钮 · 下载 localStorage JSON。CLI 路径:

```bash
docs-cockpit sync-status --import overrides.json              # dry-run
docs-cockpit sync-status --import overrides.json --apply      # 写回 + .bak per MD
docs-cockpit sync-status --from-browser chrome                # v0.13 候选 · MVP stub
```

优先级规则 promotion-only · `localStorage=true / MD=false` → MD 接管为 true。`localStorage=false / MD=true` → 信 MD(避免反向同步过激)。

跨机器 workflow doc:`references/sync_status_workflow.md`。

17 unit tests · all pass。

### Added · M10 · LLM Doc Optimizer (`docs-cockpit suggest`)

`docs_cockpit/suggest.py` · plan §5 Approach W2 · 跟 `lint` 互补:
- `lint` 死规则报错 · `suggest` LLM 软建议

4 内置 template(`docs_cockpit/templates/suggest/`):
- `desc-rewrite` · desc 短 / 空 / 过泛 → 改写 prompt
- `subtask-recompose` · >15 或 <3 subtask → merge / split 建议
- `anchor-completeness` · 缺 `@code:` / `@docs:` → 补完 prompt
- `cross-doc-consistency` · 走 author skill §12 self-check 4 个 check

CLI:`docs-cockpit suggest [module] [--all] [--template T] [--strict] [--copy]`。
`--strict` 任意 trigger 退 1 · CI 用。

Author skill §13 「How to consume suggest output」· 5 步流程跟 §11 对齐。

24 unit tests · all pass。

### Changed · `docs_cockpit/cli.py` · 4 新子命令注册

dispatcher 加 `apply-patch` / `mcp-serve` / `sync-status` / `suggest`。pyproject `[project.scripts]` entry point 不动 · `docs-cockpit <subcommand>` 自动 dispatch。

### Schema · state.json 不变 · 向后兼容

state.json shape 完全不动 · v0.11 的 standup / portfolio skill 老逻辑全 work。新 module 字段(`apply_patch` / `sync_status` / `suggest` / `mcp_server`)纯加 module-level · 不动 schema 边界。

### Migration

无需手工迁移:
- `docs-cockpit upgrade` 拿 0.12.0 + 自动 plugin cache 失效 + 重启提示
- MCP server 需要 optional `[mcp]` extra · `pip install 'docs-cockpit[mcp]'` 或 `uv tool install --with mcp docs-cockpit`
- 老 `docs-cockpit.yaml` / 老 MD 一字不动 · 继续 work
- 4 个新 CLI 子命令是纯加 · 不破坏现有 build / lint / migrate / portfolio / browse / upgrade

### Acknowledgements

dogfood 自身仍然是核心 forcing function。M07-M10 全程在本 repo 上跑通 · 198 tests cover 关键路径。`docs-cockpit upgrade` 路径回归 · 下游 Sourcery + bastion 可一键拉 0.12.0。

## [0.11.3] · 2026-05-19

修 plan §1 缺口 3「状态控制不闭环」的最严重副作用 · subtask localStorage override 永远赢 · 反向覆盖 source MD 真值。这是 v0.11 dogfood 反复抱怨的「修改了驾驶舱没啥变化」根因 · M07-9db754 commit `[x]` 之后 dashboard 仍显 0/8 也是同一个 bug 的表现。Template/JS-only patch · 0 schema 改动。

### Why · 用户原话「还是没同步」

build 跑过 + state.json 写了 `M07-9db754.done = true` + body MD 有 `[x]` · 但浏览器仍显 `[ ]` · 0/8 完成。控制台扒 localStorage 看到老的 `M07__st__M07-9db754: false` override · merge 逻辑 `(k in overrides) ? !!overrides[k] : st.done` 让 override 永久赢。

这是 plan §1 缺口 3 的真实表现:**localStorage 跟 source MD 漂移** · v0.10 起就埋下 · alpha.5 修 index→id 时没动 merge 语义 · 0.11.0 ship 没人 notice · dogfood 才暴露。

### Changed · `loadOverrides` build-time-aware 失效

`docs_cockpit/templates/index.html.tmpl` 1830 行附近的 `loadOverrides` 加新逻辑:

```js
const last_built = stored._built_at || '';
if (BUILD_TIME && last_built && last_built !== BUILD_TIME) {
  // build 刷过了 · subtask 级 override 全部失效 · source MD 真值接管
  const fresh = { _built_at: BUILD_TIME };
  for (const k of Object.keys(stored)) {
    if (k === '_built_at') continue;
    if (k.indexOf('__st__') !== -1) continue;  // subtask · 失效
    fresh[k] = stored[k];                       // module 级 · 保留
  }
  ...
}
```

行为变化:
- **同一 build 内** · subtask toggle 仍持久(用户勾 checkbox · 刷页面还在)
- **build 刷过** · subtask override 全部 invalidate · source MD 接管(用户编辑 MD + build · dashboard 立刻同步)
- **module 级 override**(status select / progress slider)保留 · 这种是用户长期意图 · 不该被 build 弹回

`saveOverrides` 同步加 `_built_at: BUILD_TIME`。

### Added · 「同步 source」按钮(显式 escape hatch)

split-mode module-drawer head 加 secondary outline 按钮:
- Refine 按钮(filled HP 蓝)旁 · 风格次级(outline + tint hover)
- click 清当前 module 的 subtask + module 级 override · reload
- i18n:`'reset.btn_label': '同步 source' / 'Reset to source'` + tooltip + done toast

用户在等下次 build 之前 · 主动同步。

### 用户立刻 fix 老 dashboard 的 one-liner

老 0.11.2 build 出来的 HTML 没有这个修复 · 用户在 dashboard 控制台跑:

```javascript
localStorage.removeItem('project-kanban-state-v1'); location.reload();
```

升到 0.11.3 build 之后 · 这一切都自动处理。

### Not changed

- Override storage shape 不变(`{[key]: bool, [moduleId]: {...}, _built_at: string}`)· 加 `_built_at` 字段是向后兼容(老 dashboard 看到陌生 key 忽略)
- 不动 SKILL.md / 不动 schema / 不动 build pipeline · 走 patch 不走 minor
- `docs-cockpit upgrade` 拿 0.11.3 不强制重启

### Verified

- 118 unit + 10 integration tests pass · 0 回归
- `docs-cockpit build` 干净 · 10 modules / 6 done / 4 not-started / 60%
- 新 `loadOverrides` 跨 BUILD_TIME 比较走通 · 模拟 stale localStorage + 新 build 验 wipe
- 「同步 source」按钮渲染 + click 清 override + reload 流程跑通

## [0.11.2] · 2026-05-19

vibe-agent 范式重写 4 个 subtask prompt template · 砍内联文本 · 改成路径+行号引用 · 信任 AI 自己 Read。Template-only patch · 不动 SKILL.md / 不动 schema / context vars 不变。

### Why

用户 dogfood 反馈:「prompt 都有一个共性问题就是太啰嗦和限制太多 · 如果有文档引用应该改为文件路径和行数参考标记即可 · 而不是直接复制到提示词中 · 按照 vibe agent 开发范式 · 结合 superpower spec/plan 的规范要求它按照这种方式实现即可」。

老 prompt 的问题:
1. **2000 字 linked_docs summary 内联** · 把 plan / RFC body 摘要直接塞进 prompt · 复制成本高 · 大部分 subtask 用不上 · 浪费 token
2. **code_anchor preview block 内联** · Python 源代码直接贴进 prompt · 现代 AI 工具(Claude Code / Cursor)有 Read 工具 · 给路径让它自己拉更合理
3. **6 步 caller-aware sync 流程** · 啰嗦 · 用户原话「限制太多」 · vibe-agent 范式应该信任模型 · 不写流程图
4. **重复定义 spec/plan 范式** · 跟 `docs-cockpit-author` §11 内容重复 · stale 风险

结果:M07-f75501 prompt 3845 chars · 大部分是 driver-seat plan §6.2 全文 + alpha.7 sub-plan 全文 + author skill §10 节录 · 全是给浏览器 LLM 准备的 fallback context。

### Changed · 4 主 template 重写为 vibe-agent 范式

`generic.md.j2` / `feature.md.j2` / `fix.md.j2` / `refactor.md.j2`:

**砍掉**:
- linked_docs 的 `{{ doc.summary }}` 内联(留路径 list)
- code_anchor 的 `ca.preview` 内联(留 `path[:lines]`)
- 6 步 sync flow(留 2 行 partial)
- 重复定义 spec/plan 规范(改成引用 `docs-cockpit-author` §11)

**保留**:
- subtask.id / title / desc(基本信息)
- code_anchors / doc_anchors / linked_docs 的路径列表(让 AI 自己 Read · 不预灌)
- feature / fix / refactor 各自的范式差异(单测 + diff / root cause + regression / behavior preserving + Beck)· 一句话
- caller-aware 模式 A vs B(简化到 3 句话)

Template 体积:
- generic: 3845 → 918 chars(4.2x 压缩)
- feature: 3762 → 1006 chars(3.7x)
- fix: 3769 → 1041 chars(3.6x)
- refactor: 3902 → 1077 chars(3.6x)

### Changed · `_caller_aware_sync.md.j2` partial 简化

从 25 行流程图 → 6 行:
- 1 句话讲范式:按 `docs-cockpit-author` §11 实施
- 2 步动作:改 body checklist + `docs-cockpit build`
- 1 句 fallback:没 fs 工具就输出 YAML patch

### Not changed · 兼容性

- Context vars 一字不动(plan-eng-review 2A stability contract):`module` / `subtask` / `linked_docs` / `repo_root` / `current_branch` 全保留 · `doc.summary` / `ca.preview` 字段也保留(只是 built-in template 不再渲染)· 用户自定义 template 引用这些字段不破
- `refine.md.j2` (module-level Refine with AI prompt) 不动 · 那是另一个使用场景 · 浏览器 LLM 用户分析全 module 需要深度 doc 内联
- 不动 SKILL.md / 不动 schema.py / 不动 build pipeline · 走 patch
- 老用户 `docs-cockpit upgrade` 拿 0.11.2 不强制重启

### Verified

- 4 template 全部 render 含 caller-aware sync section · subtask.id 替换准确
- M07-f75501 prompts.js sidecar 重生成 · 1134 chars(原 ~5000)
- 路径+行号 anchor 渲染干净 · 无 `:lines:lines` 重复 bug(发现 `ca.path` 本来就含 raw `:lines` · 修了模板里多余的拼接)
- 118 unit + 10 integration tests pass · 0 回归
- `docs-cockpit prompt --list` 仅显 `feature / fix / generic / refactor / refine` · 不出 partial

## [0.11.1] · 2026-05-19

修一个 dogfood 暴露的 prompt friction · Copy prompt 跑完之后驾驶舱不自动同步 · 用户必须自己回去手动勾 checkbox + 重 build · 跟 v0.11 alpha.7 修过的 Refine prompt 是同一个 caller-aware mode 缺口。Template-only patch · 不动 SKILL.md / 不动 schema / 不动 build pipeline · 老用户 footprint 0 变。

### Why

用户截图 dogfood 反馈:「完成后没有实时同步过来 · 让他实时更新吧」。M07-9db754 在 Claude Code 里跑完 Copy prompt 之后 · scaffold 写好了但驾驶舱仍显示 `0/8 完成` · M07-9db754 那条 checkbox 仍然空。

根因跟 alpha.7 修过的 Refine prompt 完全一样:`generic.md.j2` / `feature.md.j2` / `fix.md.j2` / `refactor.md.j2` 收尾全部是「**完成后输出 frontmatter patch 让我复制回 MD**」· 这套文字默认假设 caller 是浏览器 LLM。Claude Code 当 caller 时本该直接动手 · 但 prompt 没告诉 AI 这件事 · AI 默认照 prompt 字面行事 · 输出 patch 就停。

副驾价值核心是「让 AI 直接闭环 · 不让人工搬运」· 不告诉 AI 这件事就实现不了。

### Added · `_caller_aware_sync.md.j2` partial(共享 snippet)

新建 `docs_cockpit/templates/prompts/_caller_aware_sync.md.j2` · 4 个主 template 通过 `{% include "_caller_aware_sync.md.j2" %}` 复用。下划线开头 = Jinja 约定的 partial · `list_builtin_templates()` 加过滤跳过 `_*.md.j2` · 不污染 `--list` 输出 · 不能被 `--template _caller_aware_sync` 误选。

内容覆盖:

- **模式 A · 有文件编辑工具(Claude Code / Cursor / Codex CLI)**:6 步 sync flow
  1. 编辑 module MD body checklist · 把本 subtask 的 `[ ]` 改 `[x]`
  2. 写/改了代码 → 行尾追加 `@code:path[:start-end]` annotation(parser 支持多次堆叠 · 空格分隔)
  3. 引用了新文档 → 追加 `@docs:path[#§N.M | :start-end]`
  4. 跑 `docs-cockpit build -c docs-cockpit.yaml` · 验证 state.json 里本 subtask done=true + anchor 落到 code_anchors[] / doc_anchors[]
  5. 简短报告:做了什么 + 改了哪些文件 + build 是否干净。用户 Ctrl+Shift+R 看驾驶舱 0/N → 1/N
  6. (可选)module 最后一个 subtask → 帮翻 module frontmatter status/progress

- **模式 B · 浏览器 LLM 无 fs**:输出 YAML patch · 用户自己复制回 MD + 跑 build

- 判断标准:能调 `Edit`/`Write`/`MultiEdit` = A · 只能 chat 输出文本 = B · **默认走 A**

### Changed · 4 主 template 收尾

`generic.md.j2` / `feature.md.j2` / `fix.md.j2` / `refactor.md.j2` 末尾的「输出 patch」+ 内嵌 yaml block 都换成 `{% include "_caller_aware_sync.md.j2" %}` · 渲染后行为统一。

具体哪个 template 保留各自前置 wording 不变(feature 强调 diff / fix 强调 root cause + regression / refactor 强调 behavior preserving + Beck)· 只统一了收尾这一段。

### Changed · `list_builtin_templates()` 过滤 partial

`docs_cockpit/prompt.py::list_builtin_templates` 加 `if not p.name.startswith("_")` 过滤 · 0.11.1 引入的 `_caller_aware_sync.md.j2` 不出现在 `docs-cockpit prompt --list` · `--template _caller_aware_sync` 也命中不了(因为 BUILTIN_TEMPLATES enum 没加它)。

### Verified

- 4 template 全部 render 含「完成后 · 必须把驾驶舱同步好(`<subtask.id>`)」sentinel · subtask.id 替换准确
- 118 unit + 10 integration tests pass · 0 回归
- `docs-cockpit build` 干净 · prompts.js sidecar 重建带新 sync section · 10 modules / 6 done / 4 not-started / 60%
- `docs-cockpit prompt --list` 仅显 `feature / fix / generic / refactor / refine` · 不出 partial
- 老用户 footprint:核心 deps 不变 · 不动 SKILL.md(走 patch 不走 minor)· `docs-cockpit upgrade` 拿 0.11.1 时 plugin cache 不强制重启

### Known limitation

- 用户的 module MD body 不一定都用 `## 待办` / `## 3 · 待办` 风格的 section heading · 如果用 `## §4 · 待办` 这种带 § 的 · parser 不匹配 · AI 改 checkbox 时跳过(M08/M09/M10 上次 refine 时遇到的 parser bug)。建议保持 `## N · 待办` 形式 · v0.13 候选放宽 regex 接受 § 前缀。

## [0.11.0] · 2026-05-19

driver-seat · v0.10 的「项目状态展示器」升级到 v0.11 的「AI 协作驾驶舱」。docs-cockpit 自 0.7.0 以来最大的一次升级 · 跨 8 个 alpha 迭代 · 4 个核心叙事。下方按主题聚合 · alpha.1-8 各自的 section 在下面作为 audit trail 保留。

### Why · plan §0 driver-seat 角色重新框架

主 plan §0 lock 的方向:**docs-cockpit 不是精度引擎 · 是 AI 副驾**。
- 旧:cockpit 用 python regex / 反向 index 算 subtask 跟 doc 哪段相关 · 一直做不准
- 新:cockpit 做上下文供给(context)+ UI 展示 + 工作流编排 · 语义精度由 Claude Code / Codex / Cursor 通过 prompt 完成

driver-seat 体验闭环:
1. 用户打开 dashboard · 点 in-progress module · split-view 左栏看 subtask checklist · 右栏看 code/doc anchor 切片预览
2. 点「Copy prompt」拼好的 prompt 进剪贴板 · 包含 module/subtask/linked docs/code anchor 全部上下文
3. 粘到 Claude 跑 · Claude 知道要做什么 / 在哪改 / 验收标准
4. 跑完输出 frontmatter patch · 用户审阅后落回 MD · 状态闭环
5. 或者点「Refine with AI」让 AI 检查/精化现有 module(模式 2)

### Added · W1 数据层 · subtask 一等公民

- `docs_cockpit/schema.py` · `normalize_subtasks(raw, module_id)` · `list[str]` 自动 normalize 到 `list[dict]` · 4 种 status enum
- `docs_cockpit/schema.py` · `_subtask_id_for(module_id, title)` · `<module-id>-<sha1(title)[:6]>` 跨 build 稳定
- `docs_cockpit/schema.py` · `extract_subtasks_from_body()` · 支持 body checklist + 内联 `@code:path:lines` / `@docs:ref` annotation(多次堆叠)
- `docs_cockpit/schema.py` · `validate_subtask_schema()` · id / status / status × subtasks 一致性 · 输出 Issue
- `docs_cockpit/paths.py` · `_resolve_code_anchor()` · `path:start-end` → 绝对路径 + line range + preview + vscode:// 深链 · defensive IO + lru_cache
- `docs_cockpit/paths.py` · `_resolve_subtask_doc_anchor()` (alpha.8) · `path[:lines][#heading]` → 切片 markdown content
- `docs-cockpit migrate-subtasks <file> [--apply]` · 一键 v0.10 → v0.11 升级 · dry-run-first + .bak 备份

### Added · Split-view UI(plan §6.6 + §6.7)

- `templates/index.html.tmpl` · hash router · `#/module/<id>` / `#/sysdoc/<id>` 触发二级页面 · Esc / 点 brand 回 dashboard · `?ui=modal` URL query 走 v0.10 兼容
- Split layout · grid `minmax(360px, 38%) 1fr` · 左 navigator 复用 drawer 内容 · 右 preview marked.js inline 渲染 + 切换 active 高亮
- subtask 多 anchor 按钮(alpha.8) · `code_anchors[]` forEach 多 chevron · `doc_anchors[]` forEach 多 doc 图标 · 2+ 时右上角小数字标 · click 切右栏聚焦渲染那一条
- subtask doc anchor 右栏 marked 切片预览(alpha.8) · backend 已切好 `path:lines` / `path#§heading` / 整 file 三种 spec · 100KB 截断护栏
- systemDocs payload 嵌内容(50KB cap)· split-view 沿用相同渲染逻辑
- HP 蓝 design.md token 统一 sweep · 干掉散落的 `#4f46e5` 靛蓝 / `#f5f7ff` 雾蓝 / 紫渐变

### Added · W3 prompt scaffolding(plan §6.2)

- `docs_cockpit/prompt.py` · `render_prompt(module, subtask, repo_root)` · Jinja2 `SandboxedEnvironment` + `ChoiceLoader` 白名单(repo `docs/prompts/` + 内置 `templates/prompts/`)
- 4 内置 template · `generic` / `feature` / `fix` / `refactor`
- 5 context vars stability contract · `module` / `subtask` / `linked_docs` / `repo_root` / `current_branch` · backward-compat 规则(no-remove / no-rename / new-vars-guarded · 见 `docs-cockpit-author` §10.2)
- `docs-cockpit prompt [module] [subtask] [--copy] [--list] [-t <template>]` CLI
- build 输出 `prompts.js` sidecar(`window.__PROMPTS__`)· dashboard subtask 行加「Copy prompt」按钮 · navigator.clipboard + execCommand fallback(file:// 兼容)

### Added · AI-augmented precision(模式 2 + 模式 3)

**模式 3 · write-time** · `skills/docs-cockpit-author/SKILL.md` 加四章:
- §3.1 重写(alpha.8) · cover v0.11 subtask object schema + id 算法 + title-is-identity tradeoff + 3 种 form
- §10 / §10.1 / §10.2 · prompt template + ChoiceLoader 寻找顺序 + context vars stability contract
- §11 · Writing module MD with AI assistance · 5 步标准流程(读 plan body · 拆 subtask · 填精准 code/docs anchor · self-check)
- §12 · Cross-module / cross-doc consistency self-check

**模式 2 · on-demand** · split-view 顶部「Refine with AI」按钮:
- `docs_cockpit/templates/prompts/refine.md.j2` · module 完整 frontmatter + ALL subtasks + ALL linked docs(summary cap 5000 chars · 比 single subtask 2000 更宽)+ 检查 anchor 精度指令
- **caller-aware execution mode** · refine prompt 顶部「执行模式 · 二选一」· A=Claude Code 直接 Edit · B=浏览器 LLM 输出 YAML patch · 副驾不让用户复制粘贴
- 走 `prompts-refine.js` sidecar · click 复制 module 级 refine prompt

### Added · 测试基础 + CI matrix(plan-eng-review 4A)

- `pyproject.toml` 加 `[project.optional-dependencies] dev = ["pytest>=7", "pytest-cov>=4"]`
- `tests/unit/test_schema.py` + `tests/unit/test_paths.py` + `tests/unit/test_prompt.py` + `tests/integration/test_cli_v011.py` · 118 unit + 10 integration tests
- `.github/workflows/test.yml` · 3 Python (3.10/3.11/3.12) × 3 OS (Ubuntu/macOS/Windows) = 9 cells · 测 Windows backslash + macOS fs case sensitivity + Linux utf-8

### Changed · 模块化 refactor(plan-eng-review 1A · Step 1)

- `docs_cockpit/build.py` 从 1201 行 → 575 行(-52%)· 拆 `schema.py` / `paths.py` / `cli.py` 三个模块
- `build.py` 仍 re-export 全部老 API · 外部 `from docs_cockpit.build import validate_meta` 这类老 import 全部 work · `pyproject.toml entry-point` 不动

### Schema · state.json 新字段(向后兼容)

- `modules[].subtasks[].id` · sha1 衍生稳定 id
- `modules[].subtasks[].status` · not-started / in-progress / done / blocked
- `modules[].subtasks[].code_anchors[]` · 完整 anchor entry(path / lines / resolved / preview / vscode_url / warning)
- `modules[].subtasks[].doc_anchors[]` (alpha.8) · `{raw, path, lines, heading, title, resolved, content, mtime, warning}`
- `modules[].systemDocs[*]` · content / mtime / exists 字段(alpha.6 split-view 用)

老 state.json 没新字段不影响读 · downstream `docs-cockpit-standup` / `docs-cockpit-portfolio` 老逻辑全部 work。

### Migration

无需手工迁移:
- `docs-cockpit upgrade` 拿 0.11.0 + 自动 plugin cache 失效 + 重启提示
- 老 `docs-cockpit.yaml` / `subtasks: list[str]` 全部继续 work
- 一键升级 subtasks schema:`docs-cockpit migrate-subtasks <file> --apply`
- localStorage 旧 subtask key(`M02__st0` 等 index-based · alpha.5 自动迁移)

### Known limitations / v0.12 候选

- **W2 LLM 文档优化器**(`docs-cockpit suggest`) · 自动改写用户 MD 的 prompt 生成 · 延后
- **MCP server**(模式 1) · 让 Claude 直接消费 cockpit prompt(替代 copy-paste) · 延后
- **`docs-cockpit apply-patch`** · 把 Claude 输出的 frontmatter patch 自动落回 MD · 延后
- **`docs-cockpit sync-status`** · localStorage state.json 合并回 MD · 延后
- subtask docs anchor 行号高亮(`path:88-100` 切 13 行 · 没有「整 doc 渲染 + 高亮 88-100」模式 · 因为 line→DOM 映射 unreliable) · 不计划做

### Acknowledgements

dogfood 验证全程跑在 docs-cockpit 自己 repo 上:6 module 自身切分 + 8 个 alpha 每个 build 验证(M01 build engine / M02 CLI / M03 plugin / M04 author skill / M05 portfolio / M06 browse reader)。alpha.5 的 frontend stable-id 修复完全是用户截图「没变化啊」启发 · alpha.7 的 caller-aware refine 模板源于用户「为什么修改了驾驶舱没啥变化」 · alpha.8 的 subtask doc_anchors UI 同样源于「数据全在 UI 不渲染」。dogfood 是 driver-seat 的核心 forcing function。

## [0.11.0-alpha.8] · 2026-05-19

补 v0.11 driver-seat 的最后一个 UI 缺口 · subtask 级 `code:` / `docs:` anchor 终于在 dashboard 里能看见、能点、能跳。alpha.6 split-view 接通了数据 · alpha.7 接通了 AI · 但 anchor 字段一直只 surface 第一条 code · subtask 级 docs 完全 invisible · 导致用户 refine 完看不到反馈。

### Why

dogfood 暴露的真实 friction:用户跑 Refine prompt 把每个 subtask 的 code 拆成 4 个具体 file path、docs 拆成多个 anchor 之后 · 打开 dashboard 看到的还是「📄 一个图标」 · 跟之前 directory anchor 长得一模一样 · 「为什么修改了驾驶舱没啥变化」。根因不在 build · 在 UI 没接住:模板里 `st.code_anchors[0]` 写死单条 · `st.docs` 模板里零命中。这是 plan §6.6 split-view 设计阶段的 known gap · 补上。

### Added · subtask doc_anchors 后端切片(paths.py)

`docs_cockpit/paths.py`:
- `_parse_subtask_doc_ref(raw)` · 解析 `path[:lines][#heading]` 三态 ref
- `_slice_by_lines(text, "88-100")` · 1-indexed 行切片(start-end / single 两种 spec)
- `_slice_by_heading(text, "§6.2")` · 找标题包含 slug 的 heading · 切到下一同/更高级 heading
- `_resolve_subtask_doc_anchor(raw, module_path, repo_root, vars_)` · 主入口 · 输出 `{raw, path, lines, heading, title, resolved, exists, content, mtime, warning}` · 100KB 截断护栏跟 module 级 docs 一致

`docs_cockpit/build.py::_build_card`:
- code_anchor 循环之后追加 doc_anchor 循环 · subtask `docs:` 不管 str 还是 list 都 normalize 到 list[dict] · 落到 `subtask.doc_anchors[]`

### Added · subtask 多 anchor UI(index.html.tmpl)

`docs_cockpit/templates/index.html.tmpl`:
- subtask 行渲染 · `st.code_anchors` 和 `st.doc_anchors` 都改 forEach · 每条 anchor 画一颗按钮 · 多 anchor 时右上角小数字标 `.badge-idx` · CSS `.st-doc-btn` 复用 `.st-code-btn` 样式(HP 蓝 hover + active state)
- click handler 用 `data-st-idx` 定位具体 anchor · 不再写死 `[0]`
- `renderSplitPreviewCode(subtask, focusIdx, sourceBtn)` · 加 focusIdx 参数 · 单条聚焦时右栏只渲染那一条 + 标题加 "anchor N/M"
- `renderSplitPreviewSubtaskDoc(da, subtask, sourceBtn)` · 新函数 · backend 已切好片直接走 `_markdownToHtml(da.content)` · 找不到 anchor 显 missing 状态 + warning · 头部带 vscode:// 深链按钮跳源文件

### Schema · state.json 新增 `modules[].subtasks[].doc_anchors[]`

形状:
```json
{ "raw": "CLAUDE.md:88-100", "path": "CLAUDE.md", "lines": "88-100",
  "heading": null, "title": "", "resolved": "<abs>", "exists": true,
  "content": "<sliced markdown>", "mtime": "2026-05-19 10:24", "warning": "" }
```
向后兼容:老 state.json 没有 `doc_anchors` 字段不影响读 · standup / portfolio skill 暂未消费 · 后续可加。

### Verified

- 6 module dogfood build 干净 · M03 7 subtask 全部有 `doc_anchors` · 16 个 anchor 全部带 sliced content(2-2589 chars)
- M03-e6adea 3 个 anchor 验证三种 spec 形式都正常:`#§6.2` heading(2589 chars · 完整 §6.2 段)/ `:566-577` 行范围(789 chars · 12 行)/ `:367` 单行(69 chars · 1 行)
- 模板 JS 结构 sanity check:`renderSplitPreviewSubtaskDoc` 已定义 · `.st-doc-btn` handler 已绑 · CSS class 全部 emit

### Out of scope · 留 follow-up

- 行号高亮:用户写 `path:88-100` UI 只显示 88-100 那 13 行 · 没有「整篇渲染并高亮 88-100」模式(MVP 选 slice · 因为整篇 marked.parse 后 line→DOM 映射 unreliable)。如果有需求再加。
- standup / portfolio skill 消费 `doc_anchors` · 暂未做 · 现在两个 skill 还是读 raw `docs` 字段。

## [0.11.0-alpha.7] · 2026-05-18

AI-augmented precision · 把语义精度让给 LLM · driver-seat 完成「AI 副驾」转型。两条线并行落地:模式 3(write-time · 教 AI 写 MD 时精确)+ 模式 2(on-demand · split-view 「Refine with AI」按钮)。

### Why

主 plan §0(driver-seat 角色重新框架)lock 的方向:**docs-cockpit 不是精度引擎 · 是 AI 副驾**。语义精度从 python regex 让给 LLM · python 只做解析层。alpha.6 split-view 把容器和数据接通 · alpha.7 把 AI 接进来给精度。

### Added · 模式 3 · 教 AI 写 MD(facb07c)

`skills/docs-cockpit-author/SKILL.md` 加三节:
- §10 · Prompt template chapter(规范化 alpha.3 的 W3 工作)· 4 内置 templates 寻找顺序 + 选择 precedence
- §10.2 · Context vars stability contract · v0.11 5 个 vars + backward-compat 规则
- §11 · Writing module MD with AI assistance · 5 步标准流程(读 plan body · 跨参考拆 subtask · 填精准 code/docs anchor · self-check)· good vs bad 对比 · "when in doubt" 兜底
- §12 · Cross-module / cross-doc consistency · doc backref / dependency 闭环 / status × subtasks / sprint alignment

`skills/docs-cockpit/SKILL.md` 主 skill 加触发条件 · 何时 hand off 给 author skill。

### Added · 模式 2 · split-view 「Refine with AI」按钮

**`docs_cockpit/templates/prompts/refine.md.j2`** · 新模板:
- 输入:module 完整 frontmatter + ALL subtasks + ALL linked docs(摘要 cap 提到 5000 chars · 比单 subtask 2000 更宽)
- 指令:检查 anchor 精度 · 不要改 status/title · 输出 YAML patch
- 找不到 plan section 输出 `# TODO:` 注释 · 不瞎猜

**`docs_cockpit/prompt.py`**:
- `render_refine_prompt(module, repo_root, linked_docs)` · 渲染单 module refine prompt
- `render_all_refine_prompts(modules, repo_root)` · 给 build sidecar 用
- `_REFINE_LINKED_DOC_SUMMARY_MAX = 5000` · 摘要 cap

**`docs_cockpit/build.py`**:
- `cmd_build` 额外输出 `docs/prompts-refine.js` sidecar
- 跟 alpha.3 prompts.js 同款格式 · `window.__REFINE_PROMPTS__[module-id] = "..."`

**`templates/index.html.tmpl`**:
- `<script src="prompts-refine.js" defer>` 加载 sidecar
- `_injectRefineButton(moduleId)` · split-mode 进 module 时在 drawer-head 插「🤖 Refine with AI」按钮
- `copyModuleRefinePrompt(moduleId)` · 走 `window.__REFINE_PROMPTS__` + clipboard fallback(0.10.1 同款)
- CSS · purple gradient 按钮 · drawer-head 改 flex layout · split-mode only
- i18n · `refine.btn_label` / `refine.btn_tooltip` / `toast.refine_copied` / `toast.refine_missing`(EN + 中)

### User flow

```
1. 打开 dashboard · 点 M03 module card
   → URL #/module/M03 · split-view · 左 navigator 顶部出现 🤖 Refine with AI 按钮
2. 点按钮
   → 取 window.__REFINE_PROMPTS__[M03](~15-25KB · 含 module + subtasks + linked docs 摘要 + 指令)
   → navigator.clipboard.writeText · file:// fallback execCommand
   → toast 「Refine prompt copied · paste to Claude / Codex」
3. 粘到 Claude 跑
   → Claude 读 prompt · 分析 anchor 精度 · 输出 YAML patch
4. 复制 patch 回 module MD frontmatter
   → 跑 docs-cockpit build · dashboard 反映新 anchor
```

### Not changed

- 主 plan §0 仍是「driver-seat 是 AI 副驾」· python 不做语义精度
- alpha.6 split-view 容器不变 · 只新增 Refine 按钮 + 新 sidecar
- subtask schema(alpha.2)/ prompts.js(alpha.3)格式不变
- `?ui=modal` URL query 切回老 modal · 老用户不破

### What's next

- **0.11.0 正式** · 收口 + push + 公告(Step 5)
- **v0.12** · 模式 1 · Claude API build-time augment + MCP server 直连 · 去掉 copy-paste

## [0.11.0-alpha.6] · 2026-05-18

driver-seat split-view 真上线。点 module / sysdoc → URL 切 hash → 左右双栏:左 navigator 完整 module 内容(subtasks 行带 code anchor 图标 + Copy prompt 按钮)· 右 preview 自动 marked.js 渲染关联文档 + 切换跟随 + code anchor click 渲染 code snippet。

### Why

alpha.1-5 把 W1 schema + W3 prompt 后端做完 · 但 frontend 还在用老 modal drawer · alpha.2/3 加的 `subtask.code_anchors[]` + `prompts.js` sidecar **都没在 dashboard 上接通**。alpha.6 把 split-view UI 上线 · 用上所有 alpha.x backend 数据 · 让 driver-seat 叙事第一次闭环可见。

同时主 plan §0 加入 **driver-seat 角色重新框架**:driver-seat 是 AI 副驾不是精度引擎 · 语义精度走 alpha.7 AI-augmented(模式 2 + 模式 3)· python 只做解析层。

### Added · 5 块 commit chain(已分块 ship)

| commit | 内容 |
|---|---|
| `d66fbe0` §4.a | Backend systemDocs content embed(50KB cap)+ 主 plan §0 重新框架 + alpha.7 spec |
| `58867e5` §4.b | Hash router(`#/module/<id>` / `#/sysdoc/<id>`)+ topbar Back 按钮 + Esc + `?ui=modal` 兼容 |
| `19c3bc0` §4.c | Split layout CSS · grid `minmax(360px, 38%) 1fr` + JS 移 module-drawer DOM 进 split-nav-slot · 全部复用现有 render |
| `940a832` §4.d MVP | 右 preview marked.js 渲染 · 默认显示第一条 linked doc · 点切换 + active 高亮 · sysdoc 二级页面接通 |
| 本 commit §4.e | subtask code anchor 图标 + Copy prompt 按钮 · 接 alpha.2 `code_anchors[]` + alpha.3 prompts.js sidecar |

### §4.e 完整内容(本 commit)

- subtask 行右侧加 `<span class="st-extras">` · 内含两个按钮:
  - `.st-code-btn` · 显图标 · click 渲染右栏 code preview(snippet + vscode 深链)
  - `.st-prompt-btn` · 总是显 · click 取 `window.__PROMPTS__[stKey]` 复制(0.10.1 同款 clipboard fallback)
- `renderSplitPreviewCode(subtask)` · 右栏渲染所有 code_anchors:path / lines / preview / vscode_url + warning(alpha.2 defensive IO)
- `copySubtaskPrompt(stKey)` · 走 navigator.clipboard → execCommand fallback · file:// 兼容
- HTML 加 `<script src="prompts.js" defer>` 加载 sidecar · `window.__PROMPTS__` 全局
- subtask click toggle 加 guard:点 extras 区不切 done 状态
- CSS `.st-code-btn / .st-prompt-btn / .code-anchor-block` 全套样式
- i18n:`toast.prompt_copied` / `toast.prompt_missing`(EN + 中)

### 体积

主 HTML 411KB(alpha.5)→ 567KB(alpha.6 · +38% · 超 plan §8 +20% budget)。主要膨胀来自 systemDocs 95KB content embed(§4.a)+ 350 行新 JS / CSS。alpha.7 / 0.11.0 决定是否 sidecar 化 sysdoc content。

### Not changed

- `?ui=modal` URL query 切回老 modal drawer · 老用户书签 / muscle memory 不破
- state.json schema 仅 systemDocs 加 content/mtime/exists 字段
- subtask schema / code_anchor 数据(alpha.2)/ prompts.js 格式(alpha.3)全部沿用
- 老 frontend 模块 drawer 代码保留 · split-mode CSS override · 双模式并存

### What's next

- **alpha.7** · AI-augmented precision(模式 2 「Ask AI to refine」按钮 + 模式 3 SKILL.md 教 AI 写 MD 时直接产出精准 anchor)· 详见 `docs/plans/P-v0.11-ai-augmented-precision-alpha7-2026-05-18.md`
- **0.11.0** · 收口 + 公告 + push

## [0.11.0-alpha.5] · 2026-05-18

修一个被 alpha.4 漏掉的 frontend 真 bug:**dashboard 用 subtask index 算 localStorage key · 改 subtask 顺序或 id 算法后状态错位 · 用户看到 M02 显示 status=done 但子任务 3/9**。

### Why

用户实测反馈截图:M02 抽屉显示 status=`已完成` + 进度 33% + 子任务 3/9 完成。alpha.4 我修了 validator cross-field 但 user 说「没变化啊」。深挖发现真 bug 在 frontend:

`templates/index.html.tmpl` 三处用 **index 算 localStorage key**:
- line 1516 `getModule()` · `const k = id + '__st' + i;`
- line 2380 render · `data-i="' + i + '"`
- line 2511 toggle · `const k = id + '__st' + i;`

v0.11.0-alpha.2 我把 subtask id 算法从「body 顺序索引」改成「sha1(title)[:6]」(plan §6.1 + plan-eng-review issue #3) · **schema/paths/build.py 全做对了 · payload 里每条 subtask 都带 stable id** · 但 frontend JS **从来没用这个 id** · 一直拿 index 算 localStorage key。

后果:用户 v0.10 时代手工勾过的 subtask · localStorage 存的是 `M02__st0` / `M02__st3` 等 index-based key。alpha.2 之后 subtasks 顺序 / 数量改了 · 老 override 错位 · M02 9 个 subtask 里只有 3 个 index 对得上(被 override 成 done)· 其他 6 个走 `base.done`(state.json 是 true 但前端 merge 逻辑 `(k in overrides) ? overrides[k] : st.done` 在 overrides 有 false 老值时就显 false)。

### Fixed · 3 处 frontend 都改用 stable subtask.id

```js
// 0.11.0-alpha.5
const stKey = st.id || ('idx-' + i);   // v0.10 fallback
const k = id + '__st__' + stKey;        // 双下划线区分老格式
```

- render `data-st-key="<sha1-id>"`
- toggle 读 `stEl.dataset.stKey`
- getModule merge 同样 key

新 key 跟老 key namespace 隔开(`__st__` vs `__st`)· 不冲突。

### Added · one-time localStorage migration

页面 init 时扫 localStorage · 删所有匹配 `^[^_]+__stN$` 老格式 key:

```js
(function migrateOldSubtaskKeys() {
  let dirty = false;
  for (const k of Object.keys(overrides)) {
    if (/^[^_]+__st\d+$/.test(k)) {
      delete overrides[k];
      dirty = true;
    }
  }
  if (dirty) saveOverrides(overrides);
})();
```

用户打开 alpha.5 dashboard 一次自动清完 · 之后老 key 不存在。

### 用户怎么 verify

打开 docs/index.html · 硬刷新(Ctrl+Shift+R)· M02 子任务应该看到 **9 / 9 完成** · 进度 **100%** · 跟 status=done 一致。

### Not changed

- payload 数据格式不变 · state.json 不变
- subtask.id 算法不变(仍 sha1(title)[:6])
- 老用户 docs/spec/module/ 不动

## [0.11.0-alpha.4] · 2026-05-18

修一个用户实测发现的数据完整性 bug:`status: done` 但 subtasks 没全做完 · validator 之前不报警。

### Why

用户在 dashboard 上看到 M02 module 抽屉显示「**已完成**」status + 「**33%** 进度」+「**3 / 9** 完成」· 三个数字互相矛盾(33% 是 localStorage 老 cache 的残影 · 真 state.json 是 9/9 done · 但暴露的本质 bug 是 **validator 不校验 status × subtasks 是否一致** · 任何用户都能写 `status: done` + 几个 [ ] 未做的 subtask 不被发现)。

### Fixed · `validate_meta` 加 status × subtasks cross-field 校验

之前 validator 只校:
- status × progress 区间(`done` 必须 progress=100)
- subtask 内部(id 唯一 / status 枚举 / title 存在)

**没**校 module status × subtasks done 比例。0.11.0-alpha.4 加:

- `status=done` 但 subtask `sub_done < sub_total` → **warn** + suggestion(勾完剩余 · 或把 status 调回 in-progress)
- `status=not-started` 但 `sub_done > 0` → **warn** + suggestion(bump 到 in-progress)
- `in-progress` / `planned` / `blocked` 不 cross-check(它们 by definition 部分完成是合理状态)

所有 cross-check 是 **warn 而不是 error** · 不阻塞 build · 但 lint 会出来 + drawer 后续可以加 ⚠ 角标。

### Added · 6 个 unit tests · 覆盖 5 个 case

- `done` + subtasks 没全完 → warn
- `done` + 全完 → no warn
- `not-started` + 有人 done → warn
- `in-progress` + 部分 done → no warn(合理状态)
- v0.11 dict-form subtasks(`{status: done/...}`)同样 work
- 空 subtasks → 不 trigger

总 pytest:**109 passed in 6.45s**(103 + 6 new)

### Why 截图显示 33% 而 state.json 是 9/9

用户截图里看到 33% 而不是 100%· 因为 v0.11.0-alpha.2 把 subtask id 从「index-based」改成「sha1(title)[:6]」· 浏览器 localStorage 还存着 v0.10 时代用户手工勾的老 id · 跟新 id 对不上 · dashboard 拿不到 override · 直接显示 frontmatter 的 status(done)+ 算 subtasks done 比例(localStorage 没匹配项就全按未勾)。

**用户怎么修**:Ctrl+Shift+R 硬刷新 · 或 F12 → Application → Local Storage → 清掉 docs-cockpit.

### Not changed

- validator API 不变 · 老调用方不破
- HTML template / state.json schema 不动 · 不需 docs-cockpit upgrade

### Migrate

无需迁移 · 老用户 `docs-cockpit upgrade` 或 `pip install --upgrade` 即可。如果 `lint` 出新 warn · 按 suggestion 改就行。

## [0.11.0-alpha.3] · 2026-05-18

v0.11 W3 prompt scaffolding 完成 · **M01 + M02 两个 module 全部 done(100%)**。这两个 module 是用户在 dashboard 上明确指要完成的(用户实测反馈)。Step 2 UI split-view 仍待后续 alpha.4。

### Added · `docs_cockpit/prompt.py` · W3 核心

- `render_prompt(module, subtask, repo_root, *, template_name, linked_docs)`
- 用 Jinja2 `SandboxedEnvironment` + `ChoiceLoader` (plan §6.2 + plan-eng-review issue 6)
  - 优先 user override `<repo>/docs/prompts/<name>.md.j2`
  - 回退内置 `docs_cockpit/templates/prompts/<name>.md.j2`
- Context vars stability contract(plan-eng-review 2A):
  - v0.11 提供 5 个:module / subtask / linked_docs / repo_root / current_branch
  - `current_branch` lazy + try/except · CI / shallow / 非 git 场景 None · template 用 `{% if current_branch %}` 守护
- linked_docs 单 doc 摘要 hard cap 2000 char(plan §6.2)
- `render_all_subtask_prompts(modules, repo_root)` · 给 build sidecar 用

### Added · 4 个内置 prompt templates(`docs_cockpit/templates/prompts/`)

- `generic.md.j2` · 通用 · plan §6.2 标准模板
- `feature.md.j2` · 实现新 feature
- `fix.md.j2` · bug fix · 强调 root cause + regression test
- `refactor.md.j2` · behavior preserving · Beck make-the-change-easy 原则

### Added · `docs-cockpit prompt` CLI(M02 subtask 4/5/6)

```bash
docs-cockpit prompt --list                          # 列内置 4 个 template
docs-cockpit prompt                                  # 列所有 module
docs-cockpit prompt M01                              # 列 M01 所有 subtask
docs-cockpit prompt M01 M01-S1                       # 渲染 subtask prompt 到 stdout
docs-cockpit prompt M01 M01-S1 --copy                # 复制到剪贴板(pyperclip)
docs-cockpit prompt M01 M01-S1 -t feature            # 显式指定 template
```

- `--copy` 时 pyperclip 未装 → stderr 提示 + stdout 输出 prompt(不 raise)
- 用 sys.stdout.write(不走 _safe_print)· 让 `| pbcopy` / `| clip` 管道工作

### Added · sidecar `docs/prompts.js`(M01 subtask 8 · plan §6.3)

build 时把每个 subtask 渲染好的 prompt 写到 `docs/prompts.js`:

```js
window.__PROMPTS__ = {
  "M01-f0bd29": "你正在 docs-cockpit ...",
  ...
};
```

主 HTML 通过 `<script src="prompts.js" defer>` 引入 · drawer 「Copy prompt」按钮直接读 `window.__PROMPTS__[subtask.id]` · 不走 fetch 避免 file:// 限制。

实测 docs-cockpit 自身 dogfood:`prompts.js` 344KB · 43 个 subtask × 平均 ~8KB prompt。

### Added · `docs-cockpit lint --prompts`(M02 subtask 8)

跑完 frontmatter lint 后 · 额外校验 prompt template syntax:
- 扫 `docs_cockpit/templates/prompts/*.md.j2` 内置
- 扫 `<repo>/docs/prompts/*.md.j2` user override
- Jinja2 `TemplateSyntaxError` → 加 Issue · 报 lineno + message
- 单测 + integration 覆盖

### Added · `tests/integration/test_cli_v011.py`(M02 subtask 9)

10 个 integration 测 · 跑真 subprocess:
- `prompt --list` / `prompt` / `prompt M01` / `prompt M01 M01-S1` / 错 module / 错 subtask = 6 测
- `migrate-subtasks` dry-run / `--apply` + backup / 已 v0.11 不动 = 3 测
- `lint --prompts` 通过 = 1 测

总 pytest 计:**103 passed in 6.43s**(93 unit + 10 integration)

### Changed · `pyproject.toml`

- 加 runtime dep `jinja2>=3.1`(W3 必需)
- `[tool.setuptools.package-data]` 包含 `templates/prompts/*.j2`(让 pip install 把 4 个内置 template 装到 site-packages)

### Changed · M01 + M02 全部 done

- M01:9/10 → 10/10 (90% → 100%) · status: in-progress → **done**
- M02:4/9 → 9/9 (44% → 100%) · status: in-progress → **done**
- overall progress 83.2% → ~88%

### What's next

剩 Step 2 UI split-view 二级页面 + Step 5 收口 + 0.11.0 正式 release。这俩跟 M01 / M02 的 subtask 无关 · 单独 alpha.4 / 0.11.0。

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
