---
id: M07
type: module
title: "MCP Server · driver-seat mode 1"
status: not-started
sprint: "0.12"
progress: 0
desc: "MCP server · 让 Claude / Cursor / Codex 直连消费 cockpit prompt · 替代 copy-paste · driver-seat 模式 1"
owner: harvey
prd_ref: "v0.11 driver-seat plan §0 implications · v0.12 候选"
docs:
  - { title: "v0.11 driver-seat plan · v0.12 候选", path: "docs/plans/P-v0.11-driver-seat.md" }
  - { title: "AI-augmented precision sub-plan",   path: "docs/plans/P-v0.11-ai-augmented-precision-alpha7-2026-05-18.md" }
depends_on: [M03]
blocks: []
---

# M07 · MCP Server · driver-seat mode 1

## §1 · 范围

模式 1 是 driver-seat 收口动作:cockpit prompt 不再走「点 Copy 按钮 → 浏览器 → 切应用 → 粘贴」· 而是 Claude / Cursor / Codex 通过 MCP 协议直接拉。`docs-cockpit mcp-serve` 起一个 stdio MCP server · 暴露三件事:

1. `cockpit_prompt(module_id, subtask_id, template?)` · tool · 返回当前 module/subtask rendered prompt(沿用 `prompt.py::render_prompt`)
2. `cockpit_state()` · resource · 暴露 `docs/state.json`(所有 modules / subtasks / issues)· LLM 自己查
3. `cockpit_apply_patch(yaml_patch)` · tool · 把 LLM 输出的 frontmatter patch 落回 MD(走 M08 的 apply-patch 实现 · 不重复造轮子)

## §2 · 关键文件

| 文件 | 角色 |
|---|---|
| `docs_cockpit/mcp_server.py` | MCP server 入口 · stdio transport · 三个 tool / resource handler |
| `docs_cockpit/cli.py::cmd_mcp_serve` | `docs-cockpit mcp-serve` 子命令 · 起 server · 默认 stdio · 可加 `--port` 走 SSE |
| `.claude-plugin/mcp_servers.json` | Claude Code 自动注入 MCP server 配置 |
| `references/mcp_clients.md` | Cursor / Codex CLI / Continue 等 MCP-aware 客户端的接线说明 |

## 3 · 待办

- [x] mcp_server.py scaffold · stdio transport · MCP Python SDK 选型(`mcp` 官方 SDK) @code:docs_cockpit/mcp_server.py:1-243 @code:pyproject.toml:60-66 @docs:docs/plans/P-v0.11-driver-seat.md:40 @docs:docs/plans/P-v0.11-driver-seat.md:81 @docs:docs/plans/P-v0.11-ai-augmented-precision-alpha7-2026-05-18.md:20-32
- [ ] `cockpit_prompt(module_id, subtask_id, template?)` tool · 复用 `prompt.py::render_prompt` · 返回 rendered text @code:docs_cockpit/mcp_server.py @code:docs_cockpit/prompt.py:130-191 @docs:docs/plans/P-v0.11-driver-seat.md#§6.2 @docs:skills/docs-cockpit-author/SKILL.md:437-481
- [ ] `cockpit_state()` resource · MIME type `application/json` · 返回 state.json 内容 @code:docs_cockpit/mcp_server.py @code:docs_cockpit/build.py:486-498 @docs:CLAUDE.md:146
- [ ] `cockpit_apply_patch(yaml_patch)` tool · 调用 M08 apply-patch · 返回 diff summary @code:docs_cockpit/mcp_server.py @code:docs_cockpit/apply_patch.py @docs:docs/spec/module/M08-apply-patch.md @docs:docs/plans/P-v0.11-ai-augmented-precision-alpha7-2026-05-18.md:133-148
- [ ] `docs-cockpit mcp-serve` CLI 子命令 · 加 cli.py main() dispatcher @code:docs_cockpit/cli.py
  <!-- TODO docs anchor: 暂无专门 doc section 讲 mcp-serve CLI 子命令 · 实施时补 references/mcp_clients.md 或 docs-cockpit/SKILL.md 新章节后回填 -->
- [ ] Claude Code mcp_servers.json 自动注入 · plugin install 即开箱可用 @code:.claude-plugin/plugin.json @code:.claude-plugin/mcp_servers.json
  <!-- TODO docs anchor: plugin.json schema 没专门 doc · 实施时补到 docs-cockpit/SKILL.md 后回填 -->
- [ ] `references/mcp_clients.md` · Cursor / Codex CLI / Continue 接线步骤 @code:references/mcp_clients.md
  <!-- TODO docs anchor: 本 subtask 就是写 doc 自身 · 没上游 doc 可指 · 留空 -->
- [ ] 集成测试:本地起 server + mcp client 跑一遍三个 tool / resource · 验证 round-trip @code:tests/integration/test_mcp_server.py
  <!-- TODO docs anchor: alpha.7 sub-plan / 主 plan 都没专门讲集成测试设计 · 留空 -->

