"""docs-cockpit MCP Server · driver-seat mode 1.

把 cockpit prompt / state.json / apply-patch 通过 MCP 协议直接暴露给 Claude /
Cursor / Codex / Continue 等 MCP-aware 客户端 · 替代 v0.11 的 copy-paste 工作流。

driver-seat 角色:
    v0.11 模式 2:用户点 Copy prompt → 剪贴板 → 切到 Claude → 粘贴(人工搬运)
    v0.12 模式 1:Claude / Codex 通过 MCP 直接调 cockpit_prompt(M07, M07-9db754)
                  跑完输出 patch · 通过 cockpit_apply_patch(yaml) 自动落回 MD
                  任何时候查项目状态 · 读 cockpit://state resource

Endpoints (0.12 M07 ship · 全部 wired):

  tool      cockpit_prompt(module_id, subtask_id?, template?)
              → 调 docs_cockpit.prompt.render_prompt · 跟 `docs-cockpit prompt` CLI 等价 (M07-f75501)

  tool      cockpit_apply_patch(yaml_patch, apply?)
              → 调 docs_cockpit.apply_patch.apply_patch_to_file · 复用 M08 backend (M07-fbe944)

  resource  cockpit://state · application/json
              → 读 build 阶段写的 docs/state.json · LLM 自查项目状态 (M07-53a63a)

CLI:
    docs-cockpit mcp-serve [-c docs-cockpit.yaml]
              → 起 stdio MCP server · 进程跟着 Claude/Cursor 的 stdio child process 生命周期 (M07-35e45a)

SDK 选型:Anthropic 官方 `mcp` Python SDK(`pip install mcp`)· 走 optional dep
`[mcp]` extra · 核心 CLI 不强依 · 老用户 `pip install docs-cockpit` footprint 不变。
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import pathlib
from typing import Any

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


SERVER_NAME = "docs-cockpit"

TOOL_COCKPIT_PROMPT = "cockpit_prompt"
TOOL_COCKPIT_APPLY_PATCH = "cockpit_apply_patch"
TOOL_COCKPIT_APPLY_BODY_CHECKLIST_PATCH = "cockpit_apply_body_checklist_patch"  # 0.18.0 · gap #2
TOOL_COCKPIT_BUILD = "cockpit_build"  # 0.18.0 · gap #1 · MCP build trigger
RESOURCE_COCKPIT_STATE = "cockpit://state"

_log = logging.getLogger(__name__)

# 0.18.0 · build 是 IO-heavy(写 state.json / index.html / refine/*.md)·
# 副驾连续触发会 race condition · 用 asyncio.Lock 串行化 · 不丢任何调用 · 排队跑
_build_lock = asyncio.Lock()


# ─── Server context · 启动时由 cmd_mcp_serve 注入 ────────────────────────
#
# 模块级单例 · 给所有 handler 共享。stdio server 是单进程 · 不存在多 instance
# 冲突。包含 config_path / repo_root / state_path · 给每个 handler 拿。
class _ServerContext:
    def __init__(self, config_path: pathlib.Path):
        self.config_path = config_path.resolve()
        self.repo_root = self.config_path.parent
        # state.json 位置:跟 build 输出对齐 · 默认 docs/state.json
        # 真实使用时由 _load_config 计算 output_path 拿到准确位置
        self.state_path = self.repo_root / "docs" / "state.json"

    def reload(self) -> dict[str, Any]:
        """Lazy reload config + state.json · 每次调 tool 都重新读 · 不缓存.

        理由:用户可能在 docs-cockpit build 之后立刻在 Claude 里调 cockpit_prompt
        · 缓存反而 stale。stdio server 是 child process · 用户随时可以重启。
        """
        try:
            import yaml as _yaml

            cfg = _yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        except (OSError, Exception) as e:  # noqa: BLE001
            cfg = {"_load_error": str(e)}
        # 推 state.json 位置(走 project.output → 同 dir / state.json)
        proj = (cfg.get("project") or {}) if isinstance(cfg, dict) else {}
        out = proj.get("output") or "docs/index.html"
        self.state_path = (self.repo_root / out).parent / "state.json"
        return cfg


_ctx: _ServerContext | None = None


def _ensure_ctx() -> _ServerContext:
    """Handler 调用前的 guard · 测试 / 自检走 python -m 直接 import 时 ctx 为 None ·
    用 CWD 兜底初始化(对应 default `docs-cockpit.yaml` in CWD)。"""
    global _ctx
    if _ctx is None:
        cwd_yaml = pathlib.Path.cwd() / "docs-cockpit.yaml"
        _ctx = _ServerContext(cwd_yaml)
    return _ctx


# ─── Server 实例 ──────────────────────────────────────────────────────────


server: Server = Server(SERVER_NAME)


# ─── Tool list + dispatcher ────────────────────────────────────────────────


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """MCP client 启动时调一次 · 拿 server 暴露的 tool 清单 + input schema."""
    return [
        types.Tool(
            name=TOOL_COCKPIT_PROMPT,
            description=(
                "Render the executable prompt for a module subtask. "
                "Returns the same string that `docs-cockpit prompt <module> <subtask>` "
                "CLI would output. Ready to be consumed by an LLM."
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
                            "If omitted, returns the first not-done subtask's prompt."
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
                "Apply a YAML frontmatter patch (as emitted by the Refine workflow) "
                "back to the source module MD. Dry-run by default · returns unified "
                "diff. Pass apply=true to write back with .bak backup."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "yaml_patch": {
                        "type": "string",
                        "description": (
                            "YAML patch text. Must follow M08 format "
                            "(subtask id-based · frontmatter-only)."
                        ),
                    },
                    "module_id": {
                        "type": "string",
                        "description": (
                            "Module id to apply patch against, e.g. 'M07'. "
                            "Used to locate the source MD file."
                        ),
                    },
                    "apply": {
                        "type": "boolean",
                        "default": False,
                        "description": "If true, writes back to MD with .bak.",
                    },
                },
                "required": ["yaml_patch", "module_id"],
            },
        ),
        types.Tool(
            name=TOOL_COCKPIT_BUILD,
            description=(
                "Rebuild the cockpit dashboard from current module / concept MDs. "
                "Equivalent to `docs-cockpit build` CLI. Use this after editing MDs "
                "via cockpit_apply_patch / cockpit_apply_body_checklist_patch so "
                "subsequent cockpit_prompt / cockpit://state reads see fresh data. "
                "Returns { ok, modules, concepts, errors, warnings, hints, "
                "last_build, issues[] }."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "strict": {
                        "type": "boolean",
                        "default": False,
                        "description": (
                            "Equivalent to CLI --strict. If true, any error "
                            "issue makes ok=false (warnings still allowed)."
                        ),
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name=TOOL_COCKPIT_APPLY_BODY_CHECKLIST_PATCH,
            description=(
                "Apply a body checklist edit patch to a module MD. Operates on "
                "inline `@code:` / `@docs:` annotations on body `- [x] ...` lines "
                "(NOT frontmatter `subtasks:`). Three actions supported: "
                "add_annotation, replace_annotation, remove_annotation. "
                "Use this AFTER `cockpit_apply_patch` when you need fine-grained "
                "edit ops (e.g. verify CLI's ❌-verdict anchor removal + new add). "
                "Dry-run default · returns unified diff. apply=true writes with .bak."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "yaml_patch": {
                        "type": "string",
                        "description": (
                            "YAML body patch. Format:\n"
                            "  module: M07\n"
                            "  edits:\n"
                            "    - subtask: M07-f75501\n"
                            "      action: add_annotation         "
                            "# add_annotation | replace_annotation | remove_annotation\n"
                            "      annotation_type: code          "
                            "# code | docs\n"
                            "      value: 'path/file.py:42-89'\n"
                        ),
                    },
                    "apply": {
                        "type": "boolean",
                        "default": False,
                        "description": "If true, writes back to MD with .bak.",
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
    """Tool dispatcher · 真实 handler 调用入口."""
    arguments = arguments or {}
    if name == TOOL_COCKPIT_PROMPT:
        return await _handle_cockpit_prompt(arguments)
    if name == TOOL_COCKPIT_APPLY_PATCH:
        return await _handle_cockpit_apply_patch(arguments)
    if name == TOOL_COCKPIT_APPLY_BODY_CHECKLIST_PATCH:
        return await _handle_cockpit_apply_body_checklist_patch(arguments)
    if name == TOOL_COCKPIT_BUILD:
        return await _handle_cockpit_build(arguments)
    return [
        types.TextContent(
            type="text",
            text=(
                f"Unknown tool: {name}. "
                f"Available: {TOOL_COCKPIT_PROMPT}, {TOOL_COCKPIT_APPLY_PATCH}, "
                f"{TOOL_COCKPIT_APPLY_BODY_CHECKLIST_PATCH}, {TOOL_COCKPIT_BUILD}."
            ),
        )
    ]


# ─── Real tool handlers ───────────────────────────────────────────────────


async def _handle_cockpit_prompt(arguments: dict[str, Any]) -> list[types.TextContent]:
    """M07-f75501 · 复用 docs_cockpit.prompt.render_prompt · 跟 CLI 输出 byte-for-byte 等价."""
    ctx = _ensure_ctx()
    module_id = (arguments.get("module_id") or "").strip()
    subtask_id = (arguments.get("subtask_id") or "").strip() or None
    template = (arguments.get("template") or "").strip() or None

    if not module_id:
        return [types.TextContent(type="text", text="Error: module_id is required")]

    # 读 state.json(build 写的) · 拿 module + subtask payload
    try:
        state = json.loads(ctx.state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return [
            types.TextContent(
                type="text",
                text=(
                    f"Error: cannot read state.json at {ctx.state_path}: {e}\n"
                    f"Hint: run `docs-cockpit build` first to generate state.json."
                ),
            )
        ]

    module = next(
        (m for m in (state.get("modules") or []) if m.get("id") == module_id),
        None,
    )
    if module is None:
        return [
            types.TextContent(
                type="text",
                text=f"Error: module {module_id} not found in state.json",
            )
        ]

    subs = module.get("subtasks") or []
    if subtask_id:
        subtask = next((s for s in subs if s.get("id") == subtask_id), None)
        if subtask is None:
            return [
                types.TextContent(
                    type="text",
                    text=(
                        f"Error: subtask {subtask_id} not found in {module_id}. "
                        f"Available subtasks: {[s.get('id') for s in subs]}"
                    ),
                )
            ]
    else:
        # 拿第一个未完成的 subtask · 跟 driver-seat 「下一步要做什么」语义对齐
        subtask = next((s for s in subs if not s.get("done")), None)
        if subtask is None:
            return [
                types.TextContent(
                    type="text",
                    text=f"All subtasks in {module_id} are done · nothing to prompt for.",
                )
            ]

    from .prompt import render_prompt as _render

    linked_docs = []
    for d in module.get("docs") or []:
        linked_docs.append(
            {
                "title": d.get("title", ""),
                "path": d.get("path", ""),
                # content 可能很大 · MCP transport 也无所谓 · let render_prompt truncate
                "summary": d.get("content", ""),
            }
        )

    text = _render(
        module,
        subtask,
        ctx.repo_root,
        template_name=template,
        linked_docs=linked_docs,
    )
    return [types.TextContent(type="text", text=text)]


async def _handle_cockpit_apply_patch(
    arguments: dict[str, Any]
) -> list[types.TextContent]:
    """M07-fbe944 · 调 M08 apply_patch_to_file backend · 返回 diff + applied + conflicts."""
    ctx = _ensure_ctx()
    yaml_patch = arguments.get("yaml_patch") or ""
    module_id = (arguments.get("module_id") or "").strip()
    apply = bool(arguments.get("apply", False))

    if not yaml_patch:
        return [types.TextContent(type="text", text="Error: yaml_patch is required")]
    if not module_id:
        return [types.TextContent(type="text", text="Error: module_id is required")]

    # 反查 module MD 路径 · 走 state.json 的 modules[].path 字段(build 输出时写了 absolute path)
    try:
        state = json.loads(ctx.state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return [
            types.TextContent(
                type="text",
                text=f"Error: cannot read state.json: {e}",
            )
        ]
    module = next(
        (m for m in (state.get("modules") or []) if m.get("id") == module_id), None
    )
    if module is None:
        return [
            types.TextContent(
                type="text", text=f"Error: module {module_id} not found"
            )
        ]
    md_path_str = module.get("path")
    if not md_path_str:
        return [
            types.TextContent(
                type="text",
                text=f"Error: module {module_id} has no source path in state.json",
            )
        ]
    md_path = pathlib.Path(md_path_str)
    if not md_path.exists():
        return [
            types.TextContent(
                type="text", text=f"Error: source MD not found: {md_path}"
            )
        ]

    from .apply_patch import PatchFormatError, apply_patch_to_file

    try:
        result = apply_patch_to_file(yaml_patch, md_path, apply=apply)
    except PatchFormatError as e:
        return [
            types.TextContent(type="text", text=f"Patch parse error: {e}")
        ]

    summary = {
        "target": str(md_path),
        "applied_ids": result["applied_ids"],
        "conflicts": result["conflicts"],
        "wrote": result["wrote"],
        "bak_path": result["bak_path"],
        "diff": result["diff"],
    }
    return [
        types.TextContent(
            type="text", text=json.dumps(summary, ensure_ascii=False, indent=2)
        )
    ]


async def _handle_cockpit_apply_body_checklist_patch(
    arguments: dict[str, Any]
) -> list[types.TextContent]:
    """0.18.0 · gap #2 · 调 body_patch.apply_body_patch_to_file backend.

    跟 cockpit_apply_patch 区别:
    - cockpit_apply_patch · frontmatter `subtasks:` Form A · id-keyed object merge
    - 本 tool · body `## 待办` checklist · inline @code / @docs annotation 行级 edit
    """
    ctx = _ensure_ctx()
    yaml_patch = arguments.get("yaml_patch") or ""
    apply = bool(arguments.get("apply", False))

    if not yaml_patch:
        return [types.TextContent(type="text", text="Error: yaml_patch is required")]

    # body patch 自带 `module: <id>` 字段 · 不需要再单独传 module_id 参数
    # 反查 module MD 路径走 state.json 的 modules[].path
    from .body_patch import BodyPatchFormatError, apply_body_patch_to_file, parse_body_patch

    # 先 parse 拿 module id · 再去 state.json 找 path
    try:
        parsed = parse_body_patch(yaml_patch)
    except BodyPatchFormatError as e:
        return [types.TextContent(type="text", text=f"Patch parse error: {e}")]
    module_id = parsed["module"]

    try:
        state = json.loads(ctx.state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return [
            types.TextContent(
                type="text",
                text=f"Error: cannot read state.json: {e}",
            )
        ]
    module = next(
        (m for m in (state.get("modules") or []) if m.get("id") == module_id), None
    )
    if module is None:
        return [
            types.TextContent(
                type="text",
                text=(
                    f"Error: module {module_id} not found in state.json · "
                    f"did you run `cockpit_build` after creating it?"
                ),
            )
        ]
    md_path_str = module.get("path")
    if not md_path_str:
        return [
            types.TextContent(
                type="text",
                text=f"Error: module {module_id} has no source path in state.json",
            )
        ]
    md_path = pathlib.Path(md_path_str)
    if not md_path.exists():
        return [
            types.TextContent(
                type="text",
                text=f"Error: source MD not found: {md_path}",
            )
        ]

    try:
        result = apply_body_patch_to_file(yaml_patch, md_path, apply=apply)
    except BodyPatchFormatError as e:
        return [types.TextContent(type="text", text=f"Patch apply error: {e}")]

    summary = {
        "target": str(md_path),
        "module": module_id,
        "applied": result["applied"],
        "conflicts": result["conflicts"],
        "warnings": result["warnings"],
        "wrote": result["wrote"],
        "bak_path": result["bak_path"],
        "diff": result["diff"],
    }
    return [
        types.TextContent(
            type="text",
            text=json.dumps(summary, ensure_ascii=False, indent=2),
        )
    ]


async def _handle_cockpit_build(
    arguments: dict[str, Any]
) -> list[types.TextContent]:
    """0.18.0 · gap #1 · 重 build 看板 · 等价 `docs-cockpit build` CLI.

    用 `_build_lock` 串行化 · 副驾连续调时排队 · 不并发写 state.json / index.html。
    跑同步 `cmd_build` 用 asyncio.to_thread 包成 awaitable · 不阻塞 event loop。
    """
    ctx = _ensure_ctx()
    strict = bool(arguments.get("strict", False))

    import datetime as _dt

    async with _build_lock:
        start_ts = _dt.datetime.now()

        def _do_build() -> dict[str, Any]:
            """同步 build · 跑在 thread pool · 避免阻塞 stdio event loop.

            stdout 在 MCP transport 是 JSON-RPC 通道 · cmd_build 的 _safe_print
            会污染协议流 · 用 contextlib.redirect_stdout 捕走 · 保留 captured 字符串
            给调试用。stderr 不动(MCP 把 stderr 当 server log channel)。
            """
            import argparse as _ap
            import contextlib as _contextlib
            import io as _io

            from .build import cmd_build as _cmd_build

            ns = _ap.Namespace(
                config=str(ctx.config_path),
                debug=False,
                no_version_check=True,  # MCP 跑不需要弹版本 banner
                strict=strict,
            )
            captured = _io.StringIO()
            try:
                with _contextlib.redirect_stdout(captured):
                    exit_code = _cmd_build(ns)
            except Exception as e:  # noqa: BLE001 · 任何 build 异常都不该崩 MCP server
                return {
                    "ok": False,
                    "exit_code": -1,
                    "error": f"{type(e).__name__}: {e}",
                    "stdout_captured": captured.getvalue(),
                }
            return {
                "ok": exit_code == 0,
                "exit_code": exit_code,
                "error": None,
                "stdout_captured": captured.getvalue(),
            }

        try:
            result = await asyncio.to_thread(_do_build)
        except Exception as e:  # noqa: BLE001
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {"ok": False, "error": f"build dispatch failed: {e}"},
                        ensure_ascii=False,
                    ),
                )
            ]

        # 读刚写的 state.json · 拿 issues / 计数 · 拼 response payload
        summary: dict[str, Any] = {
            "ok": result["ok"],
            "exit_code": result["exit_code"],
            "last_build": start_ts.isoformat(),
            "state_uri": RESOURCE_COCKPIT_STATE,
            "state_path": str(ctx.state_path),
            "modules": 0,
            "concepts": 0,
            "system_docs": 0,
            "errors": 0,
            "warnings": 0,
            "hints": 0,
            "issues": [],
        }
        if result.get("error"):
            summary["error"] = result["error"]
        try:
            state = json.loads(ctx.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            summary["state_read_error"] = str(e)
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(summary, ensure_ascii=False, indent=2),
                )
            ]

        summary["modules"] = len(state.get("modules") or [])
        summary["concepts"] = len(state.get("concepts") or [])
        summary["system_docs"] = len(state.get("systemDocs") or [])
        issues_raw = state.get("issues") or []
        summary["issues"] = issues_raw
        summary["errors"] = sum(1 for i in issues_raw if i.get("severity") == "error")
        summary["warnings"] = sum(
            1 for i in issues_raw if i.get("severity") == "warn"
        )
        summary["hints"] = sum(1 for i in issues_raw if i.get("severity") == "hint")

        # --strict 时 · 任何 error issue 翻 ok=false(即使 exit_code=0 · build 本身按
        # 历史行为 warn / hint 不阻塞退出)。这里跟 CLI --strict 语义对齐。
        if strict and summary["errors"] > 0:
            summary["ok"] = False

        return [
            types.TextContent(
                type="text",
                text=json.dumps(summary, ensure_ascii=False, indent=2),
            )
        ]


# ─── Resource list + handler ──────────────────────────────────────────────


@server.list_resources()
async def list_resources() -> list[types.Resource]:
    """MCP client 拉 resource 清单 · 用于 attach context 时挑选."""
    return [
        types.Resource(
            uri=RESOURCE_COCKPIT_STATE,
            name="cockpit state",
            description=(
                "Full project state.json · modules / subtasks / concepts / "
                "systemDocs / issues. Same payload the dashboard reads."
            ),
            mimeType="application/json",
        ),
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    """M07-53a63a · 真实读 state.json · 返回内容字符串(MCP SDK 自动套 ResourceContents)."""
    if str(uri) != RESOURCE_COCKPIT_STATE:
        return json.dumps({"error": f"Unknown resource: {uri}"}, ensure_ascii=False)
    ctx = _ensure_ctx()
    try:
        return ctx.state_path.read_text(encoding="utf-8")
    except (OSError, FileNotFoundError) as e:
        return json.dumps(
            {
                "error": f"state.json not readable at {ctx.state_path}: {e}",
                "hint": "Run `docs-cockpit build` first.",
            },
            ensure_ascii=False,
        )


# ─── Entry points ──────────────────────────────────────────────────────────


async def run_stdio() -> None:
    """启动 stdio MCP server · 给 CLI 入口(M07-35e45a)和 python -m 调用复用."""
    ctx = _ensure_ctx()
    _log.info(
        "docs-cockpit MCP server starting · server_name=%s · config=%s · state=%s",
        SERVER_NAME,
        ctx.config_path,
        ctx.state_path,
    )
    # 启动时 reload 一次 · 让 ctx.state_path 跟 config.project.output 对齐
    ctx.reload()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def cmd_mcp_serve(args) -> int:
    """`docs-cockpit mcp-serve [-c <config>]` CLI dispatcher (M07-35e45a)."""
    global _ctx
    cfg_path = pathlib.Path(getattr(args, "config", None) or "docs-cockpit.yaml")
    if not cfg_path.exists():
        # 不强死 · stdio MCP server 起来后 handler 走 state.json 才会失败 ·
        # 但提前 warn 更友好
        import sys

        print(
            f"[mcp-serve] WARN: config not found at {cfg_path} · "
            f"using CWD anyway · handlers will report errors lazily",
            file=sys.stderr,
        )
    _ctx = _ServerContext(cfg_path)
    logging.basicConfig(
        level=os.getenv("DOCS_COCKPIT_MCP_LOG", "INFO").upper(),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    try:
        asyncio.run(run_stdio())
    except KeyboardInterrupt:
        _log.info("docs-cockpit MCP server stopped by KeyboardInterrupt")
    return 0


def main() -> None:
    """`python -m docs_cockpit.mcp_server` entrypoint · scaffold 自检用 · 走 CWD config."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    asyncio.run(run_stdio())


if __name__ == "__main__":  # pragma: no cover
    main()
