"""docs-cockpit MCP Server · driver-seat mode 1 scaffold.

把 cockpit prompt / state.json / apply-patch 通过 MCP 协议直接暴露给 Claude /
Cursor / Codex / Continue 等 MCP-aware 客户端 · 替代 v0.11 的 copy-paste 工作流。

driver-seat 角色:
    用户在 split-view 点 Copy prompt  →  剪贴板  →  切到 Claude  →  粘贴
                            ↓ 这条人工搬运在 v0.12 被以下 MCP endpoint 取代 ↓
    Claude / Codex 通过 MCP 直接调 cockpit_prompt(M07, M07-9db754) · 拿到 prompt
    Claude 跑完输出 patch · 通过 cockpit_apply_patch(yaml) 自动落回 MD
    任何时候 Claude 想查项目状态 · 读 cockpit://state resource

Endpoints (scaffold · 只声明 schema · 实施分给后续 subtask):
    tool      cockpit_prompt(module_id, subtask_id?, template?)  → M07-f75501
    tool      cockpit_apply_patch(yaml_patch)                    → M07-fbe944
    resource  cockpit://state · application/json                 → M07-53a63a

本文件 scope · 完成 M07-9db754:
    - Server() 实例 + 命名 + capability registration
    - stdio transport entrypoint
    - 三个 endpoint 的 schema 声明 + stub handler(返回「待实施」+ 指向具体
      subtask · 不 crash · client 看得见 graceful degradation)
    - 公开 run_stdio() · 给 cli.py::cmd_mcp_serve (M07-35e45a) 导入用
    - 可直接 `python -m docs_cockpit.mcp_server` 起 stdio server 自检

不在本 scope:
    - 三个 endpoint 的真实 handler 逻辑(留给 M07-f75501 / M07-53a63a / M07-fbe944)
    - `docs-cockpit mcp-serve` CLI 子命令(留给 M07-35e45a)
    - Claude Code mcp_servers.json 自动注入(留给 M07-fdf16c)
    - Cursor / Codex 接线 doc(留给 M07-976fe0)
    - round-trip 集成测试(留给 M07-bd8bd2)

SDK 选型:Anthropic 官方 `mcp` Python SDK(`pip install mcp`)· 走 optional
dep `[mcp]` extra · 核心 CLI 不强依 · 老用户 `pip install docs-cockpit` footprint 不变。
"""

from __future__ import annotations

import asyncio
import logging

# mcp SDK 是 optional dep · 缺包时 import 直接抛清晰错误 · 别让 docs-cockpit
# 其它子命令受牵连(cli.py 只在 cmd_mcp_serve 内 lazy import 本模块)
try:
    import mcp.types as types
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
except ImportError as e:  # pragma: no cover · 测试环境装了 mcp 才走真路径
    raise ImportError(
        "docs-cockpit mcp-serve requires the optional `mcp` SDK. "
        "Install with: pip install 'docs-cockpit[mcp]'  "
        "(or: uv tool install --with mcp docs-cockpit)"
    ) from e


# Server name 暴露给 MCP client · 列在 Claude Code / Cursor 的 MCP server 列表
# 时显示这个串。保持跟 CLI / plugin 名字一致 · 用户认得出。
SERVER_NAME = "docs-cockpit"

# 三个 endpoint 的 id · 全 server 共享常量 · 给 stub handler 跟实施 subtask 互引
TOOL_COCKPIT_PROMPT = "cockpit_prompt"
TOOL_COCKPIT_APPLY_PATCH = "cockpit_apply_patch"
RESOURCE_COCKPIT_STATE = "cockpit://state"

# 实施 subtask 反向指针 · stub 报错时告诉 client / debug 人员该看哪个 subtask
_IMPL_TODO = {
    TOOL_COCKPIT_PROMPT: "M07-f75501",
    TOOL_COCKPIT_APPLY_PATCH: "M07-fbe944",
    RESOURCE_COCKPIT_STATE: "M07-53a63a",
}

_log = logging.getLogger(__name__)


# ─── Server 实例 + capability registration ─────────────────────────────────
# 单例 · 模块级 · MCP SDK 的 Server 跟 capability registration 是 decorator-based ·
# 进程内只起一份 stdio server · 没有多实例需求。

server: Server = Server(SERVER_NAME)


# ─── Tool list · 把 cockpit_prompt / cockpit_apply_patch 声明出来 ───────────
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """MCP client 启动时调一次 · 拿 server 暴露的 tool 清单 + input schema."""
    return [
        types.Tool(
            name=TOOL_COCKPIT_PROMPT,
            description=(
                "Render the executable prompt for a specific module subtask. "
                "Returns the same string that 'docs-cockpit prompt <module> <subtask>' "
                "CLI would output · ready to be consumed by an LLM."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "module_id": {
                        "type": "string",
                        "description": "Module id, e.g. 'M07'",
                    },
                    "subtask_id": {
                        "type": "string",
                        "description": (
                            "Optional subtask id, e.g. 'M07-9db754'. "
                            "If omitted, returns a module-level overview prompt."
                        ),
                    },
                    "template": {
                        "type": "string",
                        "enum": ["generic", "feature", "fix", "refactor"],
                        "description": (
                            "Optional template override. Defaults to "
                            "subtask.prompt → module.prompt_kind → 'generic'."
                        ),
                    },
                },
                "required": ["module_id"],
            },
        ),
        types.Tool(
            name=TOOL_COCKPIT_APPLY_PATCH,
            description=(
                "Apply a YAML frontmatter patch (as emitted by the Refine-with-AI "
                "workflow) back to the source module MD. Calls the M08 apply-patch "
                "backend · dry-run by default · returns a unified diff summary."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "yaml_patch": {
                        "type": "string",
                        "description": (
                            "The YAML patch text. Must follow the M08 patch format "
                            "(subtask id-based · frontmatter-only · no body edits)."
                        ),
                    },
                    "apply": {
                        "type": "boolean",
                        "default": False,
                        "description": (
                            "If true, writes back to MD with .bak backup. "
                            "If false (default), returns diff without modifying files."
                        ),
                    },
                },
                "required": ["yaml_patch"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    """Tool dispatcher · scaffold 阶段只画 stub · 真实逻辑分给后续 subtask."""
    arguments = arguments or {}
    if name == TOOL_COCKPIT_PROMPT:
        return _stub_response(name)
    if name == TOOL_COCKPIT_APPLY_PATCH:
        return _stub_response(name)
    # 未知 tool · MCP 协议要求返回错误而不是抛异常(client 才能拿到清晰错误)
    return [
        types.TextContent(
            type="text",
            text=f"Unknown tool: {name}. Available: {TOOL_COCKPIT_PROMPT}, {TOOL_COCKPIT_APPLY_PATCH}.",
        )
    ]


# ─── Resource list · 把 cockpit://state 声明出来 ──────────────────────────
@server.list_resources()
async def list_resources() -> list[types.Resource]:
    """MCP client 拉 resource 清单 · 用于 attach context 时挑选。"""
    return [
        types.Resource(
            uri=RESOURCE_COCKPIT_STATE,
            name="cockpit state",
            description=(
                "Full project state.json · modules / subtasks / concepts / "
                "systemDocs / issues. The same payload the dashboard reads."
            ),
            mimeType="application/json",
        ),
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Resource handler · scaffold 阶段返回 stub JSON 提示 · 真实读 state.json
    留给 M07-53a63a 实施。"""
    if uri == RESOURCE_COCKPIT_STATE:
        # 返回 stub JSON · client 拿到能解析 · 知道是 "not yet wired"
        return (
            '{"_stub": true, '
            '"_impl_subtask": "M07-53a63a", '
            '"_message": "cockpit_state resource scaffold · '
            'real implementation pending M07-53a63a · '
            'will return docs/state.json content"}'
        )
    return f'{{"error": "Unknown resource: {uri}"}}'


# ─── Stub response helper ──────────────────────────────────────────────────


def _stub_response(endpoint: str) -> list[types.TextContent]:
    """Tool 还没实施时返回的占位响应 · 不抛异常 · 让 client 看见 graceful stub."""
    impl_subtask = _IMPL_TODO.get(endpoint, "unknown")
    text = (
        f"[docs-cockpit MCP scaffold] Endpoint `{endpoint}` not yet implemented.\n"
        f"Tracked by subtask {impl_subtask} (sprint 0.12 · M07).\n"
        f"Until then this endpoint returns this stub message instead of failing.\n"
        f"See: docs/spec/module/M07-mcp-server.md"
    )
    return [types.TextContent(type="text", text=text)]


# ─── Entry points ──────────────────────────────────────────────────────────


async def run_stdio() -> None:
    """启动 stdio MCP server · 给 CLI 入口(M07-35e45a)和直接 python -m 调用复用."""
    _log.info("docs-cockpit MCP server starting on stdio · server name=%s", SERVER_NAME)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    """`python -m docs_cockpit.mcp_server` entrypoint · scaffold 自检用."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    asyncio.run(run_stdio())


if __name__ == "__main__":  # pragma: no cover
    main()
