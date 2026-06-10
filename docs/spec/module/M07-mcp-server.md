---
id: M07
type: module
title: "MCP Server · driver-seat mode 1"
status: done
sprint: "0.12"
progress: 100
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
| ~~`references/mcp_clients.md`~~ | 已在 v1.0 删除 |

## 3 · 待办

- [x] 起 MCP 服务端骨架 · 走 stdio 通道 · 选官方 SDK 做底层 @code:docs_cockpit/mcp_server.py:1-243 @code:pyproject.toml:60-66 @docs:docs/plans/P-v0.11-driver-seat.md:40 @docs:docs/plans/P-v0.11-driver-seat.md:81 @docs:docs/plans/P-v0.11-ai-augmented-precision-alpha7-2026-05-18.md:20-32
- [x] 给 MCP 客户端一个直接拉 subtask prompt 的 tool · 复用现有渲染器 @code:docs_cockpit/mcp_server.py:152-218 @code:docs_cockpit/prompt.py:130-191 @docs:docs/plans/P-v0.11-driver-seat.md#§6.2
- [x] 把整个项目状态作为 JSON 资源暴露给 MCP 客户端读 @code:docs_cockpit/mcp_server.py:289-309 @code:docs_cockpit/build.py:486-498 @docs:CLAUDE.md:146
- [x] 让 MCP 客户端能把 LLM 输出的 YAML patch 直接回写 MD · 返回 diff 概要 @code:docs_cockpit/mcp_server.py:222-286 @code:docs_cockpit/apply_patch.py:248-273 @docs:docs/spec/module/M08-apply-patch.md @docs:docs/plans/P-v0.11-ai-augmented-precision-alpha7-2026-05-18.md:133-148
- [x] 让用户从命令行一键启 MCP 服务 · 接通到主 CLI dispatcher @code:docs_cockpit/cli.py:200-215 @code:docs_cockpit/mcp_server.py:336-352 @docs:docs/spec/module/M07-mcp-server.md#§1
- [x] 插件安装时自动给 Claude Code 注册 MCP 服务 · 用户无需手配置 @code:.claude-plugin/plugin.json:26-33 <!-- anchor removed: mcp_clients deleted in v1.0 -->
- [x] 给 Cursor / Codex CLI / Continue 等客户端写接线步骤文档 @docs:CHANGELOG.md#0.12.0 <!-- 接线文档 mcp_clients 已随 v1.0 删除 · 历史锚指向 0.12.0 release 节 -->
- [x] 起本地集成测试 · 三个 endpoint 都走一遍验 round-trip @code:tests/integration/test_mcp_server.py <!-- anchor removed: mcp_clients deleted in v1.0 -->

