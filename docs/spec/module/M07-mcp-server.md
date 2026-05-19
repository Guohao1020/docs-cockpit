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

- [ ] mcp_server.py scaffold · stdio transport · MCP Python SDK 选型(`mcp` 官方 SDK)
- [ ] `cockpit_prompt(module_id, subtask_id, template?)` tool · 复用 `prompt.py::render_prompt` · 返回 rendered text
- [ ] `cockpit_state()` resource · MIME type `application/json` · 返回 state.json 内容
- [ ] `cockpit_apply_patch(yaml_patch)` tool · 调用 M08 apply-patch · 返回 diff summary
- [ ] `docs-cockpit mcp-serve` CLI 子命令 · 加 cli.py main() dispatcher
- [ ] Claude Code mcp_servers.json 自动注入 · plugin install 即开箱可用
- [ ] `references/mcp_clients.md` · Cursor / Codex CLI / Continue 接线步骤
- [ ] 集成测试:本地起 server + mcp client 跑一遍三个 tool / resource · 验证 round-trip
