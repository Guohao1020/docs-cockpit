"""docs-cockpit · build engine.

读 YAML 配置 → 扫 MD 文件 → 解析 frontmatter → 渲染单文件 HTML 看板。
依赖:Python 3.10+ · pyyaml。跨平台(Windows / macOS / Linux)路径用 pathlib。

设计要点:
- **配置驱动**:groups / frontmatter / design 全在 YAML · 代码项目无关
- **路径变量**:{repo} / {home} / {main_repo} / {env:VAR} 在配置里展开
- **不抛异常**:文件缺失 / frontmatter 错 / status×progress 越界都只发 warning
  · 保证 build 永远 succeed · 让前端用 banner / chip 兜底
- **HTML 模板分离**:templates/index.html.tmpl 是 build artifact 用的占位符模板
  · build.py 只做字符串替换 · 不引 Jinja 类重依赖
"""

from __future__ import annotations

import argparse
import datetime as _dt
import glob as _glob
import json
import os
import pathlib
import re
import sys
from typing import Any

import yaml

# 0.11.0-alpha.1:schema 层独立 · plan-eng-review 1A 决策 · build.py 减肥
from .schema import (
    DEFAULT_STATUS_RANGES,
    Issue,
    VALID_DOC_TYPES,
    VALID_STATUSES,
    _DOCS_SECTION_RE,
    _SUBTASK_SECTION_RE,
    extract_docs_from_body,
    extract_subtasks_from_body,
    slugify,
    split_frontmatter,
    validate_meta,
)

# 0.11.0-alpha.1:path / fs IO / docs path resolution 已搬到 paths.py
#   (plan-eng-review 1A · build.py 减肥)
from .paths import (
    _build_vars,
    _expand,
    _resolve_and_embed_docs,
    _resolve_doc_path,
    _resolve_group_files,
    read_md,
)


# ── payload 组装 (0.2.0 dashboard 形状) ──────────────────────────────
def _build_card(
    title: str,
    path: pathlib.Path,
    meta: dict,
    mtime: str | None,
    body: str = "",
    *,
    full: bool,
    vars_: dict[str, str] | None = None,
) -> dict | None:
    """从 frontmatter 拼一张 card · None = 跳过(无 id / 占位 id).

    full=True → modules 用 · 含 desc / docs / subtasks / manualProgress 等扩展字段
    full=False → concepts 用 · 仅核心 5 字段(id/title/status/sprint/progress)

    0.4.0 起 · 当 full=True 且 frontmatter 缺 subtasks/docs 时 · 自动从 body
    扫 `## 待办` / `## 关联` 等 section 提取(见 extract_subtasks_from_body /
    extract_docs_from_body)。
    """
    doc_id = meta.get("id")
    if not doc_id:
        return None
    # 跳过模板占位 ID
    if isinstance(doc_id, str) and ("XX" in doc_id or doc_id.endswith("XXX")):
        return None

    card = {
        "id": doc_id,
        "title": meta.get("title") or title,
        "status": meta.get("status") or "not-started",
        "sprint": meta.get("sprint") or "",
        "progress": meta.get("progress") if isinstance(meta.get("progress"), (int, float)) else 0,
    }
    if full:
        # subtasks · docs · 0.4.0:frontmatter 缺则从 body 提取
        subtasks = meta.get("subtasks")
        if not subtasks and body:
            subtasks = extract_subtasks_from_body(body)
        card["subtasks"] = subtasks or []

        docs = meta.get("docs")
        if not docs and body:
            docs = extract_docs_from_body(body)
        # 0.7.1:解析 path → 绝对路径 + 内嵌 MD 文本(便于 drawer 内联渲染)
        if vars_ is not None:
            repo_root = pathlib.Path(vars_.get("repo", "."))
            card["docs"] = _resolve_and_embed_docs(docs or [], path, repo_root, vars_)
        else:
            # 兜底:没拿到 vars_ 走老形状(只有 title/path)· 不该走到这条
            card["docs"] = docs or []

        card["desc"] = meta.get("desc") or ""
        card["manualProgress"] = bool(meta.get("manualProgress"))
        # 额外 metadata · status skill 读 state.json 时也能拿到
        card["path"] = str(path)
        card["mtime"] = mtime
        # 0.8.0:body 前 1500 字摘要 · 给 "Copy prompt to write docs" 功能用
        # 让 AI 编辑器(Claude Code / Cursor / Codex)收到提示词时有足够上下文
        # 知道这个 module 在做什么 · 不至于盲目编 spec/plan
        if body:
            stripped = body.strip()
            card["bodyExcerpt"] = (
                stripped[:1500] + ("…" if len(stripped) > 1500 else "")
            )
        else:
            card["bodyExcerpt"] = ""
        card["owner"] = meta.get("owner") or ""
        card["prd_ref"] = meta.get("prd_ref") or ""
        card["depends_on"] = meta.get("depends_on") or []
        card["blocks"] = meta.get("blocks") or []
        card["updated_at"] = meta.get("updated_at") or ""
    return card


def _build_card_list(
    group_cfg: dict | None,
    vars_: dict[str, str],
    fm_enabled: bool,
    ranges: dict[str, tuple[int, int]],
    issues: list[Issue],
    *,
    full: bool,
) -> list[dict]:
    """从 modules: / concepts: block 解析出 card 列表 · 0.9.0:issues 收 Issue 对象."""
    if not group_cfg:
        return []
    out: list[dict] = []
    for title, path in _resolve_group_files(group_cfg, vars_):
        content, meta, mtime, exists = read_md(path)
        if not exists:
            continue
        # 0.4.0:把 body 单独切出来 · _build_card 用它做 subtasks/docs 兜底提取
        _, body = split_frontmatter(content)
        if fm_enabled:
            # 0.9.0:把 body 一起传给 validator · 让它能判"docs 在 frontmatter 还是在 body section"
            issues.extend(validate_meta(path, meta, ranges, body=body))
        # 0.7.1:vars_ 透传 · _build_card 用 repo_root 解析 docs 相对路径
        card = _build_card(title, path, meta, mtime, body, full=full, vars_=vars_)
        if card is not None:
            out.append(card)
    return out


def _build_system_docs(
    entries: list[dict] | None, vars_: dict[str, str]
) -> list[dict]:
    """system_docs: 手挑列表 · 仅展开 path 变量 · 不读 MD 内容."""
    if not entries:
        return []
    out: list[dict] = []
    for entry in entries:
        out.append({
            "id": entry.get("id") or slugify(entry.get("title", "")),
            "title": entry.get("title", ""),
            "path": _expand(entry.get("path", ""), vars_),
            "desc": entry.get("desc", ""),
            "icon": entry.get("icon", "doc"),
        })
    return out


def build_payload(
    config: dict, vars_: dict[str, str], build_time: str
) -> tuple[dict, list[Issue]]:
    """返 (payload, issues) · 0.2.0 dashboard 形状 · 0.9.0:issues 是 Issue 对象.

    Payload 结构:
    {
      "project": {name, tagline, eyebrow, mark, lastBuild},
      "systemDocs": [{id, title, path, desc, icon}],
      "modules": [{id, title, status, sprint, progress, desc, docs, subtasks, ...}],
      "concepts": [{id, title, status, sprint, progress}],
    }
    """
    issues: list[Issue] = []

    fm_cfg = config.get("frontmatter", {}) or {}
    fm_enabled = fm_cfg.get("enabled", True)
    ranges_cfg = fm_cfg.get("status_progress_ranges") or DEFAULT_STATUS_RANGES
    ranges = {k: tuple(v) for k, v in ranges_cfg.items()}

    # Project meta(含 build_time → lastBuild)
    project = config.get("project", {}) or {}
    payload_project = {
        "name": project.get("name") or "MyProject",
        "tagline": project.get("tagline") or "",
        "eyebrow": project.get("eyebrow") or "",
        "mark": (project.get("mark") or project.get("glyph") or "·"),
        "lastBuild": build_time,
    }

    system_docs = _build_system_docs(config.get("system_docs"), vars_)
    modules = _build_card_list(
        config.get("modules"), vars_, fm_enabled, ranges, issues, full=True
    )
    concepts = _build_card_list(
        config.get("concepts"), vars_, fm_enabled, ranges, issues, full=False
    )

    payload = {
        "project": payload_project,
        "systemDocs": system_docs,
        "modules": modules,
        "concepts": concepts,
    }
    return payload, issues


# ── 渲染 HTML ─────────────────────────────────────────────────────
TEMPLATE_PATH = pathlib.Path(__file__).parent / "templates" / "index.html.tmpl"


def render_html(template: str, payload: dict) -> str:
    r"""0.2.0:模板只需一个占位符替换 · JS 从 payload 渲染其他一切.

    0.10.1 fix:
    - payload 里 `</script>` 字面串(用户 spec / plan 引用 script 示例代码 · 比如
      讨论 docs-cockpit 自身 v0.11 design 时引用 `<script type="application/json">...</script>`)
      会让浏览器在解析 `<script>` tag 时遇到 close token 提前关闭 · 剩余 JSON
      溢出到 HTML body · `JSON.parse` 拿不到完整数据 · 整个 dashboard 白屏。
      Fix:把 payload JSON 里 `</script>` 字面替换为 `<\/script>`(JSON spec
      允许 forward-slash escape · 浏览器 + JSON.parse 都识别)。
    - `str.replace` 不带 count 默认替换 ALL occurrences · 实际 single-pass 不递归 ·
      但 payload 内字面 `__DOCS_JSON__` 出现会让 substitution 意图模糊 ·
      明确传 count=1 防 paranoia。

    v0.11 W1 会改 sidecar(prompts.js / code_previews.js)+ `<script type="application/json">`
    包裹 · 本 fix 在 v0.11 之后仍是 defense-in-depth。

    0.11.0-alpha.1:docstring 改 raw string · 修 Python 3.12+ `SyntaxWarning: invalid escape sequence '\/'`
    """
    docs_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    docs_json = docs_json.replace("</script>", "<\\/script>")
    return template.replace("__DOCS_JSON__", docs_json, 1)


# ── CLI ─────────────────────────────────────────────────────────────
def _safe_print(msg: str) -> None:
    """Windows GBK 控制台兼容 · 不丢字符."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode("ascii"))


# ── 版本检测(best-effort · 24h 缓存 · 网络失败静默) ───────────────
_VERSION_CHECK_URL = (
    "https://raw.githubusercontent.com/Guohao1020/docs-cockpit/main/"
    ".claude-plugin/plugin.json"
)


def _semver_parts(v: str) -> tuple[int, ...]:
    """把 "0.1.2" 拆成 (0,1,2) · 不规则的段返回空元组."""
    try:
        return tuple(int(p) for p in v.split(".") if p.isdigit())
    except (ValueError, AttributeError):
        return ()


def _check_for_updates(no_check: bool = False) -> None:
    """Best-effort 检查 GitHub main 上是否有更新版本.

    缓存 24h 在 ~/.cache/docs-cockpit/version-check.json。
    网络失败 / 解析失败一律静默 · 永远不阻塞 build。
    """
    if no_check or os.environ.get("DOCS_COCKPIT_NO_VERSION_CHECK"):
        return

    from . import __version__ as local_version

    cache_dir = pathlib.Path.home() / ".cache" / "docs-cockpit"
    cache_path = cache_dir / "version-check.json"
    now = _dt.datetime.now()
    remote_version: str | None = None

    # 1) 读缓存(24h TTL)
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            checked_at = _dt.datetime.fromisoformat(cached["checked_at"])
            if (now - checked_at).total_seconds() < 86400:
                remote_version = cached.get("remote_version")
        except (json.JSONDecodeError, KeyError, ValueError, OSError):
            pass

    # 2) 缓存 miss / stale → fetch
    if remote_version is None:
        try:
            import urllib.request
            req = urllib.request.Request(
                _VERSION_CHECK_URL,
                headers={"User-Agent": f"docs-cockpit/{local_version}"},
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read())
                remote_version = data.get("version")
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(
                json.dumps({
                    "checked_at": now.isoformat(),
                    "remote_version": remote_version,
                }),
                encoding="utf-8",
            )
        except Exception:
            return  # 静默

    # 3) 比较 · 只在 remote > local 时报
    if not remote_version:
        return
    if _semver_parts(remote_version) > _semver_parts(local_version):
        _safe_print(
            f"[!] docs-cockpit {remote_version} available "
            f"(current: {local_version})."
        )
        _safe_print(
            "    Update: pip install --upgrade "
            "git+https://github.com/Guohao1020/docs-cockpit.git"
        )
        _safe_print(
            "    Or ask Claude: \"update docs-cockpit\" "
            "(invokes docs-cockpit-update skill)."
        )


def cmd_build(args: argparse.Namespace) -> int:
    _check_for_updates(no_check=getattr(args, "no_version_check", False))

    config_path = pathlib.Path(args.config).resolve()
    if not config_path.exists():
        _safe_print(f"[ERR] config not found: {config_path}")
        return 1

    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    paths_cfg = config.get("paths", {}) or {}
    vars_ = _build_vars(config_path, paths_cfg)

    project = config.get("project", {}) or {}
    output_rel = project.get("output", "docs/index.html")
    output = pathlib.Path(output_rel)
    if not output.is_absolute():
        output = (pathlib.Path(vars_["repo"]) / output).resolve()

    if args.debug:
        _safe_print(f"[debug] config: {config_path}")
        _safe_print(f"[debug] vars: {vars_}")
        _safe_print(f"[debug] output: {output}")

    build_time = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    payload, issues = build_payload(config, vars_, build_time)

    if not TEMPLATE_PATH.exists():
        _safe_print(f"[ERR] template missing: {TEMPLATE_PATH}")
        return 2

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    html = render_html(template, payload)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")

    # ── sidecar state.json · 给 docs-cockpit-standup skill 读 ──
    # 0.9.0:warnings 字段保留(老 status skill 兼容)· issues 字段是新的
    # 结构化版本 · 含 severity / suggestion / reference · IDE 与 CI 消费
    state_path = output.parent / "state.json"
    state_payload = {
        **payload,
        "warnings": [issue.message for issue in issues],  # 兼容老 state.json 形状
        "issues": [issue.as_dict() for issue in issues],
    }
    state_path.write_text(
        json.dumps(state_payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    # ── 统计 + 输出 ───────────────────────────────────────────
    n_modules = len(payload["modules"])
    n_concepts = len(payload["concepts"])
    n_sysdocs = len(payload["systemDocs"])

    def _status_counts(cards: list[dict]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for c in cards:
            counts[c.get("status", "")] = counts.get(c.get("status", ""), 0) + 1
        return counts

    mod_counts = _status_counts(payload["modules"])
    overall = (
        round(sum(c.get("progress") or 0 for c in payload["modules"])
              / max(n_modules, 1), 1)
        if n_modules else 0
    )

    # 0.9.0:三段式输出 · ❌/⚠️/💡 + 修法 + 规范引用
    errors = [i for i in issues if i.severity == "error"]
    warns = [i for i in issues if i.severity == "warn"]
    hints = [i for i in issues if i.severity == "hint"]
    for issue in issues:
        _safe_print(issue.format_for_terminal())
    if n_modules == 0 and n_concepts == 0 and n_sysdocs == 0:
        _safe_print(
            "[WARN] 0 items · 检查 paths.repo 与 modules/concepts/system_docs 路径"
        )
    _safe_print(f"[OK] Built {output}")
    _safe_print(f"     state: {state_path}")
    _safe_print(
        f"     modules: {n_modules} | concepts: {n_concepts} | "
        f"system_docs: {n_sysdocs}"
    )
    if n_modules:
        _safe_print(
            f"     module status · done={mod_counts.get('done', 0)} "
            f"in-progress={mod_counts.get('in-progress', 0)} "
            f"planned={mod_counts.get('planned', 0)} "
            f"blocked={mod_counts.get('blocked', 0)} "
            f"not-started={mod_counts.get('not-started', 0)} "
            f"deferred={mod_counts.get('deferred', 0)}"
        )
        _safe_print(f"     overall progress: {overall}%")
    _safe_print(f"     HTML size: {output.stat().st_size:,} bytes")
    _safe_print(f"     build time: {build_time}")
    if issues:
        _safe_print(
            f"     [!] frontmatter issues · {len(errors)} error(s) · "
            f"{len(warns)} warning(s) · {len(hints)} hint(s)"
        )
        _safe_print("     → run `docs-cockpit lint` to see only issues without rebuilding")
        _safe_print("     → consult docs-cockpit-author skill for the spec")
    _safe_print("")
    _safe_print("Open in browser (Claude Code: 点击对应系统的代码块右上角 run 一键执行):")
    _safe_print("")
    _safe_print("```bash")
    _safe_print(f"start {output}")
    _safe_print("```")
    _safe_print("")
    _safe_print("```bash")
    _safe_print(f"open {output}")
    _safe_print("```")
    _safe_print("")
    _safe_print("```bash")
    _safe_print(f"xdg-open {output}")
    _safe_print("```")

    # 0.9.0:--strict · errors(任何 severity=error)非零退出 · CI 友好
    if getattr(args, "strict", False) and errors:
        _safe_print("")
        _safe_print(f"[ERR] --strict mode: {len(errors)} error(s) · failing build")
        return 3
    return 0


# ── 0.9.0 · docs-cockpit lint(只校验不 build · CI / pre-commit 用)──
def cmd_lint(args: argparse.Namespace) -> int:
    """校验 frontmatter + body 是否符合 docs-cockpit-author 规范 · 不 build · 不写 HTML.

    退出码:
      0 · 全通过(可能仍有 hint · hint 不阻塞)
      0 · 仅有 warn / hint(默认) · 加 --strict-warn 升级
      1 · 至少 1 个 error · 一律退出 1
    """
    config_path = pathlib.Path(args.config).resolve()
    if not config_path.exists():
        _safe_print(f"[ERR] config not found: {config_path}")
        return 2

    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    paths_cfg = config.get("paths", {}) or {}
    vars_ = _build_vars(config_path, paths_cfg)

    fm_cfg = config.get("frontmatter", {}) or {}
    fm_enabled = fm_cfg.get("enabled", True)
    ranges_cfg = fm_cfg.get("status_progress_ranges") or DEFAULT_STATUS_RANGES
    ranges = {k: tuple(v) for k, v in ranges_cfg.items()}

    issues: list[Issue] = []
    for key in ("modules", "concepts"):
        group_cfg = config.get(key)
        if not group_cfg:
            continue
        for _title, path in _resolve_group_files(group_cfg, vars_):
            content, meta, _mtime, exists = read_md(path)
            if not exists:
                continue
            _, body = split_frontmatter(content)
            if fm_enabled:
                issues.extend(validate_meta(path, meta, ranges, body=body))

    # 仅在 lint 时按 severity 排序 · error 在前 · 修起来按重要性
    severity_rank = {"error": 0, "warn": 1, "hint": 2}
    issues.sort(key=lambda i: (severity_rank.get(i.severity, 9), str(i.path)))

    errors = [i for i in issues if i.severity == "error"]
    warns = [i for i in issues if i.severity == "warn"]
    hints = [i for i in issues if i.severity == "hint"]

    if not issues:
        _safe_print("[OK] no frontmatter issues · all modules / concepts pass docs-cockpit-author spec")
        return 0

    # JSON 输出(CI / IDE 消费 · 通过 --json)
    if getattr(args, "json", False):
        _safe_print(json.dumps(
            {"issues": [i.as_dict() for i in issues],
             "summary": {"error": len(errors), "warn": len(warns), "hint": len(hints)}},
            ensure_ascii=False, indent=2,
        ))
        return 1 if errors else 0

    # 人类可读输出
    for issue in issues:
        _safe_print(issue.format_for_terminal())
        _safe_print("")

    _safe_print(
        f"Summary · {len(errors)} error(s) · {len(warns)} warning(s) · {len(hints)} hint(s)"
    )
    _safe_print(
        "Reference · docs-cockpit-author skill (frontmatter schema + body conventions)"
    )
    if errors:
        return 1
    # warn / hint 默认不退出非零 · 加 --strict-warn 让 warn 也变 error
    if warns and getattr(args, "strict_warn", False):
        return 1
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    """从 docs_cockpit/examples/minimal.yaml 拷一份模板到 ./docs-cockpit.yaml."""
    target = pathlib.Path(args.output).resolve()
    if target.exists() and not args.force:
        _safe_print(f"[ERR] {target} 已存在 · 加 --force 覆盖")
        return 1
    template_yaml = pathlib.Path(__file__).parent / "examples" / "minimal.yaml"
    if not template_yaml.exists():
        _safe_print(f"[ERR] template missing: {template_yaml}")
        return 2
    target.write_text(template_yaml.read_text(encoding="utf-8"), encoding="utf-8")
    _safe_print(f"[OK] wrote {target}")
    _safe_print("     edit, then run: docs-cockpit build")
    return 0


# 0.11.0-alpha.1:main() argparse dispatcher 已搬到 cli.py
#   (plan-eng-review 1A · build.py 减肥)
from .cli import main  # re-export · pyproject.toml entry-point 仍走 build:main

__all__ = [
    # schema 层(0.11.0-alpha.1 re-export)
    "Issue", "validate_meta", "split_frontmatter", "slugify",
    "extract_subtasks_from_body", "extract_docs_from_body",
    "DEFAULT_STATUS_RANGES", "VALID_STATUSES", "VALID_DOC_TYPES",
    # paths 层(0.11.0-alpha.1 re-export)
    "_build_vars", "_expand", "_resolve_doc_path",
    "_resolve_and_embed_docs", "_resolve_group_files", "read_md",
    # CLI(0.11.0-alpha.1 re-export)
    "main",
    # build engine 本体(留在 build.py)
    "build_payload", "render_html", "cmd_build", "cmd_lint", "cmd_init",
]
