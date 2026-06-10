"""docs-cockpit · v0.11 W3 prompt scaffolding · plan §6.2.

把 module + subtask + 关联文档 + code anchor 拼成可执行 prompt · 让用户从
cockpit 直接复制提示词到 Claude / Cursor / Codex 跑。

v1.0 起本模块只服务渲染期的 prompts.js sidecar(dashboard 「Copy prompt」
按钮数据源)· `docs-cockpit prompt` CLI 与 refine prompt 生成已随认知层删除。

设计要点(plan §6.2):
- Jinja2 SandboxedEnvironment · 防 `{% include '/etc/passwd' %}` 路径穿越
- ChoiceLoader 优先 user override(`docs/prompts/<custom>.md.j2`)
  · 再回退内置 `docs_cockpit/templates/prompts/*.md.j2`
- Context vars stability contract(plan-eng-review 2A):
  - v0.11 提供 5 个:module / subtask / linked_docs / repo_root / current_branch
  - 后续 minor 加新 var 必须 `{{ var | default('') }}` 守护 · 老用户 template 不破
- git not available 时 current_branch=None · template 用 `{% if current_branch %}` 守护
- linked_docs 单 doc 摘要 hard cap 2000 char · 防 memory dir 撑爆 prompt

0.11.0-alpha.3:首发。
"""

from __future__ import annotations

import pathlib
import subprocess
from typing import Any

try:
    import jinja2
    from jinja2.sandbox import SandboxedEnvironment
    _JINJA2_AVAILABLE = True
except ImportError:
    _JINJA2_AVAILABLE = False
    jinja2 = None  # type: ignore
    SandboxedEnvironment = None  # type: ignore


# 内置 template 类型枚举(plan §6.2)
BUILTIN_TEMPLATES = ("generic", "feature", "fix", "refactor")

# linked_docs 单 doc 摘要硬上限(plan §6.2 + reviewer round-2)
_LINKED_DOC_SUMMARY_MAX = 2000


def _builtin_templates_dir() -> pathlib.Path:
    """返回包内置 prompt templates 目录."""
    return pathlib.Path(__file__).parent / "templates" / "prompts"


def _get_current_branch(repo_root: pathlib.Path) -> str | None:
    """Lazy + try/except 拿当前 git branch · CI / shallow / 非 git 场景返 None.

    plan §6.2 + plan-eng-review issue #6 决策。
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            return branch or None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def _truncate_summary(text: str) -> str:
    """linked_docs body 摘要 · hard cap 2000 char + 截断标记."""
    if not text:
        return ""
    if len(text) <= _LINKED_DOC_SUMMARY_MAX:
        return text
    return text[:_LINKED_DOC_SUMMARY_MAX] + f"\n… [truncated · {len(text)} chars total]"


def _build_jinja_env(repo_root: pathlib.Path) -> Any:
    """组装 Jinja2 SandboxedEnvironment + ChoiceLoader.

    Loader 优先 user override `<repo>/docs/prompts/<name>.md.j2` · 再回退
    docs_cockpit/templates/prompts/<name>.md.j2 内置。
    """
    if not _JINJA2_AVAILABLE:
        raise RuntimeError(
            "Jinja2 not installed · run `pip install jinja2` to render prompt sidecars"
        )
    user_dir = repo_root / "docs" / "prompts"
    loaders = []
    if user_dir.exists():
        loaders.append(jinja2.FileSystemLoader(str(user_dir)))
    loaders.append(jinja2.FileSystemLoader(str(_builtin_templates_dir())))
    env = SandboxedEnvironment(
        loader=jinja2.ChoiceLoader(loaders),
        undefined=jinja2.Undefined,  # 不严格 · undefined var 渲染为空 · 老 template 升级时不破
        autoescape=False,             # MD 不是 HTML · 不需要 escape
        keep_trailing_newline=True,
    )
    return env


def _resolve_template_name(
    module: dict, subtask: dict, explicit: str | None
) -> str:
    """决定用哪个 template · plan §6.2 寻找顺序:

    1. 显式 `--template <name>` (CLI)
    2. subtask frontmatter `prompt: <name>`
    3. module frontmatter `prompt_kind: feature | fix | refactor`
    4. fallback `generic`
    """
    if explicit:
        return explicit
    sub_prompt = subtask.get("prompt") if isinstance(subtask, dict) else None
    if sub_prompt:
        return str(sub_prompt)
    mod_prompt = module.get("prompt_kind") if isinstance(module, dict) else None
    if mod_prompt and mod_prompt in BUILTIN_TEMPLATES:
        return str(mod_prompt)
    return "generic"


def render_prompt(
    module: dict,
    subtask: dict,
    repo_root: pathlib.Path,
    *,
    template_name: str | None = None,
    linked_docs: list[dict] | None = None,
) -> str:
    """渲染 prompt 字符串 · 给 build sidecar 调.

    Args:
        module: module 完整 dict(含 id / title / status / sprint / desc / docs ...)
        subtask: subtask 完整 dict(含 id / title / status · 可选 code_anchors)
        repo_root: 用于 git branch detection 和 Loader sandbox 边界
        template_name: 显式 override 模板名(优先级最高 · 见 _resolve_template_name)
        linked_docs: 关联文档 list(每条含 title / path / content)· 不传则空

    Returns:
        渲染后的 prompt 字符串 · 不抛(template 错也只返 fallback 提示)
    """
    if not _JINJA2_AVAILABLE:
        return f"# Prompt for {subtask.get('id', '?')}\n\n(Jinja2 not installed · run `pip install jinja2` for full prompt)"

    name = _resolve_template_name(module, subtask, template_name)
    file_name = f"{name}.md.j2"

    # 摘要 linked_docs · hard cap
    docs_for_template = []
    for d in linked_docs or []:
        if not isinstance(d, dict):
            continue
        docs_for_template.append({
            "title": d.get("title") or d.get("path") or "(untitled)",
            "path": d.get("path") or "",
            "summary": _truncate_summary(d.get("content") or ""),
        })

    env = _build_jinja_env(repo_root)
    try:
        tmpl = env.get_template(file_name)
    except jinja2.TemplateNotFound:
        return (
            f"# Prompt template not found: {file_name}\n\n"
            f"Built-in available: {', '.join(BUILTIN_TEMPLATES)}.\n"
            f"User override location: {repo_root}/docs/prompts/{file_name}\n"
        )

    branch = _get_current_branch(repo_root)
    try:
        return tmpl.render(
            module=module,
            subtask=subtask,
            linked_docs=docs_for_template,
            repo_root=str(repo_root),
            current_branch=branch,
        )
    except jinja2.TemplateError as e:
        return (
            f"# Prompt render failed (template {file_name})\n\n"
            f"```\n{e}\n```\n"
        )


def render_all_subtask_prompts(
    modules: list[dict],
    repo_root: pathlib.Path,
) -> dict[str, str]:
    """给所有 module 的所有 subtask 渲染 prompt · 返 {subtask_id: prompt_str}.

    build_payload 用这个生成 prompts.js sidecar(plan §6.3)。
    """
    out: dict[str, str] = {}
    for mod in modules:
        subs = mod.get("subtasks", []) or []
        # 用 module 的 docs 字段作为 linked_docs(0.7.1 已经把 content embed 进去)
        linked = mod.get("docs", []) or []
        for sub in subs:
            sub_id = sub.get("id")
            if not sub_id:
                continue
            out[sub_id] = render_prompt(mod, sub, repo_root, linked_docs=linked)
    return out
