"""docs-cockpit suggest · v0.12 M10 · LLM-augmented soft document optimization.

跟 `docs-cockpit lint` 互补:
- `lint`  · 死规则校验(status × progress / id 缺失 / docs path 找不到)→ Issue(error / warn / hint)
- `suggest` · LLM 软建议(desc 太短 / subtask 拆解 / anchor 完整性 / cross-doc consistency)
                → 输出可执行 prompt · 用户 / AI 决定要不要执行

Implements plan §5 Approach W2 · v0.11 sprint 没做 · 留给 v0.12。

4 internal templates(`docs_cockpit/templates/suggest/`):
    desc-rewrite        · desc 短 / 空 / 过泛 → 生成补完 prompt
    subtask-recompose   · subtask 过细(>15)或过粗(<3) → 合并/拆分建议
    anchor-completeness · 哪些 subtask 没 code/docs anchor + 建议怎么补
    cross-doc-consistency · 走 author skill §12 self-check · 4 个 check 全跑

CLI:
    docs-cockpit suggest [module_id]              # 跑全部 4 个 template
    docs-cockpit suggest M03 --template desc-rewrite
    docs-cockpit suggest --all                    # 跑所有 module
    docs-cockpit suggest M03 --strict             # 任意 suggest 触发就 exit non-zero(CI 用)
    docs-cockpit suggest M03 --copy               # prompts → 剪贴板(需要 pyperclip)
"""

from __future__ import annotations

import pathlib
from typing import Any

try:
    import jinja2
    from jinja2.sandbox import SandboxedEnvironment

    _JINJA2_AVAILABLE = True
except ImportError:  # pragma: no cover · pyproject 已强依
    _JINJA2_AVAILABLE = False
    jinja2 = None  # type: ignore


BUILTIN_SUGGEST_TEMPLATES: tuple[str, ...] = (
    "desc-rewrite",
    "subtask-recompose",
    "anchor-completeness",
    "cross-doc-consistency",
)


# Heuristic thresholds(可走 frontmatter 配置 override · v0.13 候选)
_DESC_MIN_CHARS = 20
_SUBTASKS_MAX = 15
_SUBTASKS_MIN_FOR_MODULE = 3


def _builtin_suggest_templates_dir() -> pathlib.Path:
    return pathlib.Path(__file__).parent / "templates" / "suggest"


def list_builtin_suggest_templates() -> list[str]:
    """`docs-cockpit suggest --list-templates` 走的列表 · 跳过 `_*.md.j2` partial."""
    d = _builtin_suggest_templates_dir()
    if not d.exists():
        return list(BUILTIN_SUGGEST_TEMPLATES)
    return sorted(
        p.stem.replace(".md", "")
        for p in d.glob("*.md.j2")
        if not p.name.startswith("_")
    )


def _build_suggest_env(repo_root: pathlib.Path) -> Any:
    """SandboxedEnvironment + ChoiceLoader · user `docs/suggest/` overrides 内置."""
    if not _JINJA2_AVAILABLE:
        raise RuntimeError(
            "Jinja2 not installed · `pip install jinja2` to use docs-cockpit suggest"
        )
    user_dir = repo_root / "docs" / "suggest"
    loaders = []
    if user_dir.exists():
        loaders.append(jinja2.FileSystemLoader(str(user_dir)))
    loaders.append(jinja2.FileSystemLoader(str(_builtin_suggest_templates_dir())))
    return SandboxedEnvironment(
        loader=jinja2.ChoiceLoader(loaders),
        undefined=jinja2.Undefined,
        autoescape=False,
        keep_trailing_newline=True,
    )


# ─── Heuristic triggers · 判断 module 是否需要 suggest ────────────────────


def _trigger_desc_rewrite(module: dict[str, Any]) -> bool:
    desc = (module.get("desc") or "").strip()
    if not desc:
        return True
    if len(desc) < _DESC_MIN_CHARS:
        return True
    # 「too generic」启发式 · 都是关键词配比 · v0.13 可走 LLM 判断
    generic_phrases = ["TBD", "todo", "待补", "暂无", "placeholder"]
    if any(p.lower() in desc.lower() for p in generic_phrases):
        return True
    return False


def _trigger_subtask_recompose(module: dict[str, Any]) -> bool:
    subs = module.get("subtasks") or []
    n = len(subs)
    return n > _SUBTASKS_MAX or n < _SUBTASKS_MIN_FOR_MODULE


def _trigger_anchor_completeness(module: dict[str, Any]) -> bool:
    """有 subtask 缺 code anchor 或 docs anchor 就触发."""
    subs = module.get("subtasks") or []
    for s in subs:
        if not s.get("code") and not s.get("code_anchors"):
            return True
        if not s.get("docs") and not s.get("doc_anchors"):
            return True
    return False


def _trigger_cross_doc_consistency(module: dict[str, Any]) -> bool:
    """总是值得跑一次(author skill §12 self-check)· 但只对 in-progress / planned 触发."""
    return module.get("status") in ("in-progress", "planned", "not-started")


_TRIGGERS = {
    "desc-rewrite": _trigger_desc_rewrite,
    "subtask-recompose": _trigger_subtask_recompose,
    "anchor-completeness": _trigger_anchor_completeness,
    "cross-doc-consistency": _trigger_cross_doc_consistency,
}


def diagnose_module(module: dict[str, Any]) -> list[str]:
    """跑所有 trigger · 返回适用的 suggest template 名 list."""
    out = []
    for name, fn in _TRIGGERS.items():
        try:
            if fn(module):
                out.append(name)
        except Exception:  # noqa: BLE001 · heuristic 不该 crash 整个 suggest 流程
            continue
    return out


# ─── render_suggest · 单 module + 单 template ────────────────────────────


def render_suggest(
    module: dict[str, Any],
    template_name: str,
    repo_root: pathlib.Path,
    *,
    linked_docs: list[dict] | None = None,
) -> str:
    """Render 一个 suggest prompt · 跟 prompt.render_prompt 同款机制 · 不同 template 目录."""
    env = _build_suggest_env(repo_root)
    try:
        tmpl = env.get_template(f"{template_name}.md.j2")
    except jinja2.TemplateNotFound:
        # fallback · 列已知 templates 让用户知道写错了
        avail = ", ".join(list_builtin_suggest_templates())
        return (
            f"# Unknown suggest template: {template_name}\n"
            f"# Available: {avail}\n"
        )
    return tmpl.render(
        module=module,
        linked_docs=linked_docs or [],
        repo_root=str(repo_root),
        thresholds={
            "desc_min_chars": _DESC_MIN_CHARS,
            "subtasks_max": _SUBTASKS_MAX,
            "subtasks_min": _SUBTASKS_MIN_FOR_MODULE,
        },
    )


def render_all_for_module(
    module: dict[str, Any],
    repo_root: pathlib.Path,
    *,
    triggered_only: bool = True,
    linked_docs: list[dict] | None = None,
) -> dict[str, str]:
    """跑该 module 所有 triggered template(或全 4 个) · 返回 {template_name: prompt_text}."""
    if triggered_only:
        names = diagnose_module(module)
    else:
        names = list(BUILTIN_SUGGEST_TEMPLATES)
    return {
        name: render_suggest(module, name, repo_root, linked_docs=linked_docs)
        for name in names
    }


# ─── CLI entrypoint ──────────────────────────────────────────────────────


def cmd_suggest(args) -> int:
    """`docs-cockpit suggest [module] [--template T] [--all] [--strict] [--copy] [--list-templates]`."""
    import json
    import sys

    # --list-templates · 不需要 config / state.json
    if getattr(args, "list_templates", False):
        for name in list_builtin_suggest_templates():
            print(name)
        return 0

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

    template_filter = getattr(args, "template", None)
    repo_root = cfg_path.parent.resolve()

    all_prompts: list[tuple[str, str, str]] = []  # (module_id, template_name, prompt)
    any_triggered = False

    for module in modules:
        mid = module.get("id", "")
        linked_docs = []
        for d in module.get("docs") or []:
            linked_docs.append(
                {
                    "title": d.get("title", ""),
                    "path": d.get("path", ""),
                    "summary": d.get("content", "")[:2000],
                }
            )

        if template_filter:
            names = [template_filter]
        else:
            names = diagnose_module(module)

        if names:
            any_triggered = True
        for name in names:
            text = render_suggest(module, name, repo_root, linked_docs=linked_docs)
            all_prompts.append((mid, name, text))

    # 输出
    if not all_prompts:
        print("[suggest] no suggestions triggered for selected modules · all clean")
        return 0

    output_lines = []
    for mid, name, text in all_prompts:
        output_lines.append(f"\n{'='*72}\n# {mid} · {name}\n{'='*72}\n")
        output_lines.append(text)
    combined = "".join(output_lines)

    if getattr(args, "copy", False):
        try:
            import pyperclip

            pyperclip.copy(combined)
            print(
                f"[suggest] {len(all_prompts)} prompt(s) copied to clipboard · "
                f"paste to Claude / Codex",
                file=sys.stderr,
            )
        except ImportError:
            print(
                "[suggest] pyperclip not installed · falling back to stdout",
                file=sys.stderr,
            )
            print(combined)
    else:
        print(combined)

    # --strict · 任何 trigger 都 exit non-zero(CI 用)
    if getattr(args, "strict", False) and any_triggered:
        print(
            f"\n[suggest] --strict · {len(all_prompts)} suggestion(s) triggered "
            f"· exiting 1",
            file=sys.stderr,
        )
        return 1
    return 0
