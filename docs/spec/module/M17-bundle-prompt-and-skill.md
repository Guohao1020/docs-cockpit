---
id: M17
type: module
title: "Bundle prompt + recommendation skill · 后端 + LLM 指南"
status: done
sprint: "0.14"
progress: 100
desc: "（v1.0 已移除 · 历史模块）docs-cockpit prompt --bundle CLI + bundle.md.j2 模板 + author skill §14 bundle 启发式 + build-time cohesion scoring sidecar"
owner: harvey
prd_ref: "v0.14 plan §5.3"
docs:
  - { title: "v0.14 plan · §5.3",            path: "docs/plans/P-v0.14-batch-driver.md" }
  - { title: "关联方法论(原 author §11)",     path: "references/association-method.md" }
  - { title: "M16 multi-select UX",          path: "docs/spec/module/M16-multi-subtask-bundle-ux.md" }
  - { title: "M10 suggest module",           path: "docs/spec/module/M10-llm-doc-optimizer.md" }
depends_on: [M15, M16]
blocks: []
---

# M17 · Bundle prompt + recommendation skill

> **v1.0 已移除 · 历史模块** — bundle prompt CLI / 模板 / sidecar / 推荐 skill 章节均已在 v1.0 随认知 CLI 层删除（多选 UX 的 Copy 按钮改为前端拼自然语言 prompt · 见 M16）。本模块保留为 0.14 sprint 的历史记录（特性曾完整 ship · 故 `status: done` 不变）· 发布详情见 CHANGELOG 的 0.14.0 节。

## §1 · 范围

后端 + LLM 指南。3 件事一起做:

1. **Bundle prompt template** · `docs_cockpit/templates/prompts/bundle.md.j2` · 输入 N subtasks · 输出聚合 prompt(共享 module 上下文一次给 · subtask 清单分别列)
2. **Bundle CLI** · `docs-cockpit prompt --bundle <id1>,<id2>,...`(v1.0 已删)· 跟单 subtask `docs-cockpit prompt M07 M07-f75501` 同款 dispatcher 加 --bundle 路径
3. **Bundle build-time sidecar** · `docs/prompts-bundle.js` · 给 backlog UI 多选时直接读 · 含 cohesion scoring · key 是 sorted subtask-id list 的 hash
4. **Bundle recommendation skill** · author skill §14 加「Bundle heuristics」+ suggest template `bundle-recommendation.md.j2`(author skill 与 suggest 均 v1.0 已删)· LLM 检查 module 内 subtask 哪些适合 bundle

## §2 · 关键文件

| 文件 | 角色 |
|---|---|
| ~~`docs_cockpit/bundle.py`~~ | `render_bundle_prompt(subtasks, modules)` + `cohesion_score(a, b)` + `render_all_bundles(modules)`（v1.0 已删） |
| ~~`docs_cockpit/templates/prompts/bundle.md.j2`~~ | 聚合 prompt 模板 · 共享 context 去重（v1.0 已删） |
| ~~`docs_cockpit/templates/suggest/bundle-recommendation.md.j2`~~ | suggest template · LLM 检查 module bundle 候选（v1.0 已删） |
| `docs_cockpit/cli.py` · ~~`prompt` subcommand 加 `--bundle <ids>`~~ | CLI 入口（prompt 子命令 v1.0 已删） |
| `docs_cockpit/build.py::cmd_build` · ~~写 `docs/prompts-bundle.js` sidecar~~ | build-time precompute（sidecar v1.0 已删） |
| 原 author SKILL §14 「Bundle heuristics」(v1.0 已随 bundle 删除) | LLM 指南 |
| ~~`tests/unit/test_bundle.py`~~ | render_bundle_prompt + cohesion scoring 单测（v1.0 已删） |

## §3 · Bundle prompt 结构

```markdown
你在 docs-cockpit sprint **0.14** 串行执行 **N 个 subtask**(bundle)。

## Bundle 概览
- M07-f75501 · cockpit_prompt tool · M07
- M07-53a63a · cockpit_state resource · M07
- M11-9adb12 · code_anchors path_only · M11

推荐执行顺序(沿 depends_on chain + 同 file cohesion):
1. M07-f75501 → 2. M07-53a63a → 3. M11-9adb12

## 共享 module 上下文
### M07 · MCP Server (3 subtask in this bundle)
{desc + status + key links}

### M11 · Schema consistency (1 subtask in this bundle)
{desc + status + key links}

## 共享参考(去重 · 用 Read 工具按需拉)
- `docs_cockpit/mcp_server.py:120-220` (M07-f75501 + M07-53a63a 共用)
- `docs_cockpit/paths.py:300-450` (M11-9adb12)
- `docs/plans/P-v0.13-polish-and-edges.md#§5.1` (M11)

## 子任务详情
### 1. M07-f75501 · cockpit_prompt tool
{title · code anchor · doc anchor}

### 2. M07-53a63a · cockpit_state resource
{...}

### 3. M11-9adb12 · code_anchors path_only
{...}

## 完成 + 同步驾驶舱(N 个 subtask 都要勾完才报告)
- 按推荐顺序串行实施
- 每个 subtask done 改对应 body checklist `[ ]` → `[x]`
- 全部完成跑 docs-cockpit build · 简短报告 N 个 subtask 都做了什么
- (没 fs 工具就输出 N 行 YAML patch 让用户复制)
```

## §4 · Cohesion scoring(轻量启发式 · 不调 LLM)

每对 subtask 算 cohesion(int):
- 同 module · +3
- 同 code 文件路径(`ca.path_only` 相等) · +2
- 同 doc anchor path · +1
- depends_on chain(A in B.depends_on) · +2

每对 subtask 算 conflict(int):
- 同 file · lines 区间重叠 · +5(red flag · UI 上 red badge)
- 跨 sprint · +1(只警告)

最终 bundle scoring = avg pairwise cohesion - max conflict。

## §5 · Bundle skill · author skill §14

§14 加 4 维 cohesion + 4 维 conflict 文档:
- §14.1 · cohesion 4 维(module / file / doc / depends_on)
- §14.2 · conflict 4 维(file overlap / sprint mismatch / owner / blocking reverse)
- §14.3 · 推荐顺序规则(depends_on chain → file cohesion → 自由)
- §14.4 · `docs-cockpit suggest --bundle-candidates [M07]` LLM 检查命令用法(suggest CLI v1.0 已删)

## 3 · 待办

- [x] 起 bundle 引擎核心 · 渲染聚合 prompt + 算 cohesion / conflict + 推荐执行顺序 @docs:CHANGELOG.md#0.14.0
- [x] 聚合 prompt 模板 · 共享 module 上下文去重 · 列推荐顺序 · 提示串行汇报 @docs:CHANGELOG.md#0.14.0
- [x] suggest 视角的 bundle 候选模板 · 让 LLM 自动挑哪些 subtask 适合一起打包 @docs:CHANGELOG.md#0.14.0
- [x] CLI 加批量 prompt 入口 · 用户传一串 subtask id 就拿到聚合 prompt @docs:CHANGELOG.md#0.14.0
- [x] build 阶段把 pairwise cohesion / conflict 预算成 sidecar · 给驾驶舱多选 UI 即时 verdict @docs:CHANGELOG.md#0.14.0
- [x] author skill 加 bundle 启发式章节 · 讲清 4 维 cohesion + 4 维 conflict + 推荐顺序 + 反例(该章节随 v1.0 bundle 删除) @docs:docs/plans/P-v0.14-batch-driver.md
- [x] 单元测试覆盖 bundle 引擎全部能力 · cohesion / conflict / 顺序 / 渲染 / sidecar @docs:CHANGELOG.md#0.14.0
