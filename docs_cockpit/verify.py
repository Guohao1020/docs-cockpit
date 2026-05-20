"""docs-cockpit verify · v0.17.0 · LLM 二次确认每个 subtask 的 anchor 是否真指到对的代码 / 文档.

跟 lint / suggest / refine 的区别(三个互补):

- `lint  · lint_subtask_anchors`(0.17.0 新)· 死规则 · subtask 0 anchor → warn
                                              · 不调 LLM · 跑 build 时自动出
- `suggest · anchor-completeness.md.j2`     · 软建议 · 列出缺 anchor 的 subtask
                                              · 让 LLM 给「补什么 anchor」建议(浅)
- `verify · verify.md.j2`(0.17.0 新)       · LLM 二次确认 · 每个现有 anchor
                                              · LLM Read 真文件 + line range · 给 4 档 verdict
                                              · (✅ accurate / ⚠️ partial / ❌ wrong / ❓ missing)
                                              · 输出 YAML patch · 可灌 apply-patch
- `refine · refine.md.j2`                   · 精度 refine · 把 anchor 升级到 file:lines 级
                                              · (跟 verify 互补 · verify 抓错的 · refine 让对的更准)

用户反馈 0.16.0 dogfood 之后(M01 截图):「子任务和文档关联未通过大模型进行二次确认 ·
关联的文档和代码有缺失」· verify 收口这条心理诉求 · 跟 lint(catch 缺失)联动。

CLI:
    docs-cockpit verify M03                  # 渲染 M03 的 verify prompt
    docs-cockpit verify M03 --copy           # 进剪贴板
    docs-cockpit verify --all                # 跑所有 module(慎用 · prompt 体量大)
"""

from __future__ import annotations

import pathlib
from typing import Any

try:
    import jinja2
    from jinja2.sandbox import SandboxedEnvironment

    _JINJA2_AVAILABLE = True
except ImportError:  # pragma: no cover
    _JINJA2_AVAILABLE = False
    jinja2 = None  # type: ignore


def _builtin_prompt_templates_dir() -> pathlib.Path:
    return pathlib.Path(__file__).parent / "templates" / "prompts"


def _build_verify_env(repo_root: pathlib.Path) -> Any:
    """SandboxedEnvironment + ChoiceLoader · 复用 prompts/ 目录 · user override 走 docs/prompts/."""
    if not _JINJA2_AVAILABLE:
        raise RuntimeError(
            "Jinja2 not installed · `pip install jinja2` to use docs-cockpit verify"
        )
    user_dir = repo_root / "docs" / "prompts"
    loaders = []
    if user_dir.exists():
        loaders.append(jinja2.FileSystemLoader(str(user_dir)))
    loaders.append(jinja2.FileSystemLoader(str(_builtin_prompt_templates_dir())))
    return SandboxedEnvironment(
        loader=jinja2.ChoiceLoader(loaders),
        undefined=jinja2.Undefined,
        autoescape=False,
        keep_trailing_newline=True,
    )


def render_verify_prompt(
    module: dict[str, Any],
    repo_root: pathlib.Path,
    linked_docs: list[dict[str, Any]] | None = None,
) -> str:
    """渲染单 module 的 verify prompt."""
    env = _build_verify_env(repo_root)
    template = env.get_template("verify.md.j2")
    return template.render(
        module=module,
        subtasks=module.get("subtasks") or [],
        linked_docs=linked_docs or [],
        repo_root=str(repo_root),
    )


def cmd_verify(args) -> int:
    """`docs-cockpit verify [module_id] [--all] [--copy]`."""
    import json
    import sys

    cfg_path = pathlib.Path(getattr(args, "config", None) or "docs-cockpit.yaml")
    if not cfg_path.exists():
        print(f"[ERR] config not found: {cfg_path}", file=sys.stderr)
        return 2

    state_path = cfg_path.parent / "docs" / "state.json"
    if not state_path.exists():
        print(
            f"[ERR] state.json not found at {state_path} · run `docs-cockpit build` first",
            file=sys.stderr,
        )
        return 2

    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[ERR] state.json parse failed: {e}", file=sys.stderr)
        return 2

    modules = state.get("modules") or []
    module_filter = getattr(args, "module_id", None)
    if module_filter and not getattr(args, "all_modules", False):
        modules = [m for m in modules if m.get("id") == module_filter]
        if not modules:
            print(f"[ERR] module {module_filter} not found in state.json", file=sys.stderr)
            return 2
    elif not getattr(args, "all_modules", False) and not module_filter:
        print(
            "[ERR] provide module_id or --all · 例: `docs-cockpit verify M03`",
            file=sys.stderr,
        )
        return 2

    repo_root = cfg_path.parent.resolve()
    out_parts: list[str] = []

    for module in modules:
        mid = module.get("id", "?")
        linked_docs = []
        for d in module.get("docs") or []:
            linked_docs.append(
                {
                    "title": d.get("title", ""),
                    "path": d.get("path", ""),
                    "summary": (d.get("content") or "")[:2000],
                }
            )
        try:
            text = render_verify_prompt(module, repo_root, linked_docs=linked_docs)
        except Exception as e:  # template missing / jinja syntax / etc
            print(f"[ERR] render failed for {mid}: {e}", file=sys.stderr)
            return 3
        out_parts.append(f"\n{'='*72}\n# {mid} · verify\n{'='*72}\n")
        out_parts.append(text)

    combined = "".join(out_parts)

    if getattr(args, "copy", False):
        try:
            import pyperclip

            pyperclip.copy(combined)
            print(
                f"[verify] {len(modules)} prompt(s) copied to clipboard · "
                f"paste to Claude / Codex / browser LLM",
                file=sys.stderr,
            )
        except ImportError:
            print(
                "[verify] pyperclip not installed · falling back to stdout",
                file=sys.stderr,
            )
            print(combined)
    else:
        print(combined)

    return 0
