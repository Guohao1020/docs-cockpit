"""Integration tests for M07 MCP server (`docs_cockpit/mcp_server.py`).

In-process tests · 不起真 stdio subprocess · 走 server.request_handlers dispatch
直接调 handler。覆盖:
- list_tools / list_resources 拓扑
- cockpit_prompt(module_id) 拿第一个未完成 subtask 的 prompt
- cockpit_prompt(module_id, subtask_id, template) 显式参数
- cockpit_state resource 读 state.json
- cockpit_apply_patch dry-run · 走 M08 backend
- error case · 不存在的 module / 缺 yaml_patch
- mcp 包没装时 import 错误清晰
"""

from __future__ import annotations

import asyncio
import json
import pathlib

import pytest

# 跳过整个模块 if mcp not installed (optional dep)
mcp = pytest.importorskip("mcp")


def _run(coro):
    """Sync helper · 给 pytest 用(避免每个 test 都 @pytest.mark.asyncio)."""
    return asyncio.run(coro)


@pytest.fixture
def server_ctx(tmp_path: pathlib.Path):
    """Build a fixture project · run docs-cockpit build · spin up mcp_server ctx."""
    import shutil
    import sys

    # 复制本 repo 的 docs-cockpit.yaml + docs/spec/ 作 fixture(用 repo 自身做 fixture)
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    yaml_path = tmp_path / "docs-cockpit.yaml"
    shutil.copy(repo_root / "docs-cockpit.yaml", yaml_path)
    shutil.copytree(repo_root / "docs" / "spec", tmp_path / "docs" / "spec")
    # 也需要 plans / system_docs 引用 · 简单复制整个 docs(不大)
    if (repo_root / "docs" / "plans").exists():
        shutil.copytree(
            repo_root / "docs" / "plans", tmp_path / "docs" / "plans"
        )
    # 复制 build 需要 read 的 CLAUDE.md / README.md / skills(system_docs)
    for f in ("CLAUDE.md", "README.md"):
        if (repo_root / f).exists():
            shutil.copy(repo_root / f, tmp_path / f)
    if (repo_root / "skills").exists():
        shutil.copytree(repo_root / "skills", tmp_path / "skills")
    if (repo_root / "references").exists():
        shutil.copytree(repo_root / "references", tmp_path / "references")

    # 跑 build
    sys.path.insert(0, str(repo_root))
    try:
        from docs_cockpit.cli import main as cli_main

        rc = cli_main(["build", "-c", str(yaml_path)])
        assert rc == 0, "fixture build failed"
    finally:
        sys.path.pop(0)

    # 启 ctx
    from docs_cockpit import mcp_server as m

    m._ctx = m._ServerContext(yaml_path)
    m._ctx.reload()
    yield m
    m._ctx = None


def test_list_tools_topology(server_ctx):
    import mcp.types as types

    tools_resp = _run(
        server_ctx.server.request_handlers[types.ListToolsRequest](
            types.ListToolsRequest(method="tools/list")
        )
    )
    names = [t.name for t in tools_resp.root.tools]
    assert "cockpit_prompt" in names
    assert "cockpit_apply_patch" in names
    # input schemas have 'module_id' as required
    cp = next(t for t in tools_resp.root.tools if t.name == "cockpit_prompt")
    assert "module_id" in cp.inputSchema.get("required", [])


def test_list_resources_topology(server_ctx):
    import mcp.types as types

    resp = _run(
        server_ctx.server.request_handlers[types.ListResourcesRequest](
            types.ListResourcesRequest(method="resources/list")
        )
    )
    uris = [str(r.uri) for r in resp.root.resources]
    assert "cockpit://state" in uris


def test_cockpit_prompt_auto_picks_first_not_done(server_ctx):
    """No subtask_id → returns first not-done subtask's prompt.

    用 M09(sync-status · all not-started)避免依赖 dogfood 模块当前完成度。
    """
    r = _run(
        server_ctx._handle_cockpit_prompt({"module_id": "M09"})
    )
    text = r[0].text
    assert "M09" in text
    assert "Error" not in text
    # 必然含 caller-aware sync 段(0.11.2+ vibe-agent template)
    assert "完成 + 同步驾驶舱" in text or "完成 / 同步" in text


def test_cockpit_prompt_all_done_module(server_ctx):
    """If all subtasks done → graceful 'nothing to prompt for' (not error)."""
    # 找一个所有 subtask 都 done 的 module(M01 / M02 都是 v0.11 完成的)
    r = _run(server_ctx._handle_cockpit_prompt({"module_id": "M01"}))
    text = r[0].text
    # 要么含 prompt(还有未完成)· 要么含 "are done"(graceful message)
    assert "M01" in text
    assert "Error" not in text


def test_cockpit_prompt_explicit_subtask_and_template(server_ctx):
    r = _run(
        server_ctx._handle_cockpit_prompt(
            {
                "module_id": "M07",
                "subtask_id": "M07-f75501",
                "template": "feature",
            }
        )
    )
    text = r[0].text
    assert "M07-f75501" in text
    # feature template 特定要求
    assert "feature" in text.lower()


def test_cockpit_prompt_unknown_module(server_ctx):
    r = _run(
        server_ctx._handle_cockpit_prompt({"module_id": "M999"})
    )
    assert "not found" in r[0].text.lower()


def test_cockpit_prompt_missing_module_id(server_ctx):
    r = _run(server_ctx._handle_cockpit_prompt({}))
    assert "required" in r[0].text.lower()


def test_cockpit_state_resource_reads_state_json(server_ctx):
    text = _run(server_ctx.read_resource("cockpit://state"))
    parsed = json.loads(text)
    assert "modules" in parsed
    assert "project" in parsed
    assert any(m.get("id") == "M07" for m in parsed.get("modules", []))


def test_cockpit_state_unknown_uri(server_ctx):
    text = _run(server_ctx.read_resource("cockpit://nonsense"))
    parsed = json.loads(text)
    assert "error" in parsed


def test_cockpit_apply_patch_dry_run(server_ctx):
    """M07-fbe944 + M08 backend · dry-run · 加 code anchor 但不写文件."""
    patch = (
        "subtasks:\n"
        "  - id: M07-fbe944\n"
        "    code: [\"docs_cockpit/mcp_server.py:222-286\"]\n"
    )
    r = _run(
        server_ctx._handle_cockpit_apply_patch(
            {"yaml_patch": patch, "module_id": "M07", "apply": False}
        )
    )
    summary = json.loads(r[0].text)
    assert summary["applied_ids"] == ["M07-fbe944"]
    assert summary["wrote"] is False
    assert "diff" in summary


def test_cockpit_apply_patch_missing_yaml(server_ctx):
    r = _run(
        server_ctx._handle_cockpit_apply_patch(
            {"module_id": "M07", "apply": False}
        )
    )
    assert "yaml_patch is required" in r[0].text


def test_cockpit_apply_patch_unknown_module(server_ctx):
    r = _run(
        server_ctx._handle_cockpit_apply_patch(
            {
                "yaml_patch": "subtasks:\n  - id: X-1\n",
                "module_id": "M999",
                "apply": False,
            }
        )
    )
    assert "M999" in r[0].text
    assert "not found" in r[0].text.lower()


def test_call_tool_dispatcher_unknown(server_ctx):
    r = _run(server_ctx.call_tool("nonsense_tool", {}))
    assert "Unknown tool" in r[0].text


def test_server_name_constant():
    # canary · plugin.json::mcpServers["docs-cockpit"] 跟这个名字对应
    from docs_cockpit import mcp_server as m

    assert m.SERVER_NAME == "docs-cockpit"
