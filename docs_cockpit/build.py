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

# ── 路径变量展开 ────────────────────────────────────────────────────
# 配置里的 path 字符串支持:
#   {repo}        → paths.repo 解析后的绝对路径(默认 config 文件所在目录)
#   {home}        → 用户 home(USERPROFILE / HOME)
#   {main_repo}   → 如果 {repo} 在 git worktree 内 · 上溯到 main · 否则 == {repo}
#   {env:NAME}    → 环境变量 NAME · 找不到则空串
# 未知变量原样保留 · 不抛异常 · 便于排查
_VAR_RE = re.compile(r"\{([a-z_][a-z0-9_]*)(:[^}]*)?\}", re.IGNORECASE)


def _detect_main_repo(start: pathlib.Path) -> pathlib.Path:
    """如果 start 在 git worktree 内 · 上溯到 main repo · 否则原样返回.

    Worktree 标识:`.git` 是文件(`gitdir: ...`)而非目录;
    路径形态约定:`<main>/.claude/worktrees/<wt-name>/` · cur.parent.name == 'worktrees'。
    """
    cur = start.resolve()
    git_marker = cur / ".git"
    if git_marker.is_file() and cur.parent.name == "worktrees":
        candidate = cur.parent.parent.parent
        if (candidate / ".git").exists():
            return candidate
    return cur


def _build_vars(config_path: pathlib.Path, paths_cfg: dict) -> dict[str, str]:
    """组装路径变量字典.

    repo 默认 config 文件所在目录(不是 CWD · 让 build 跨调用目录稳定)。
    """
    repo_raw = paths_cfg.get("repo", ".")
    repo = pathlib.Path(repo_raw).expanduser()
    if not repo.is_absolute():
        repo = (config_path.parent / repo).resolve()
    home = pathlib.Path(
        os.environ.get("USERPROFILE") or os.environ.get("HOME") or "~"
    ).expanduser()
    main_repo = _detect_main_repo(repo)
    vars_ = {
        "repo": str(repo),
        "home": str(home),
        "main_repo": str(main_repo),
    }
    # 允许 paths.* 里定义额外变量 · 比如 paths.plans: "{home}/.claude/plans/foo"
    for k, v in (paths_cfg or {}).items():
        if k in vars_ or not isinstance(v, str):
            continue
        vars_[k] = _expand(v, vars_)
    return vars_


def _expand(text: str, vars_: dict[str, str]) -> str:
    """展开 {var} / {env:KEY} · 未知变量保留原样."""

    def sub(m: re.Match) -> str:
        name = m.group(1).lower()
        arg = m.group(2)
        if name == "env" and arg:
            return os.environ.get(arg[1:], "")
        return vars_.get(name, m.group(0))

    return _VAR_RE.sub(sub, text)


# ── title transforms · 把文件名翻译成展示标题 ──────────────────
def _transform_stem(p: pathlib.Path, base: pathlib.Path) -> str:
    return p.stem


def _transform_prefix_dot_titlecase(p: pathlib.Path, base: pathlib.Path) -> str:
    """C03-site-adapter → C03 · Site Adapter · M07-job-fsm → M07 · Job Fsm."""
    stem = p.stem
    if "-" in stem:
        prefix, rest = stem.split("-", 1)
        return f"{prefix} · {rest.replace('-', ' ').title()}"
    return stem


def _transform_path_slash(p: pathlib.Path, base: pathlib.Path) -> str:
    """递归扫时把子目录前缀加进 title · roadmap/00-master.md → roadmap / 00-master."""
    rel = p.relative_to(base)
    if len(rel.parts) > 1:
        return " / ".join(rel.parts[:-1] + (rel.stem,))
    return rel.stem


TRANSFORMS = {
    "stem": _transform_stem,
    "prefix-dot-titlecase": _transform_prefix_dot_titlecase,
    "path-slash": _transform_path_slash,
}


# ── 文件源解析(files / scan / glob 三种) ──────────────────────
def _resolve_group_files(
    group: dict, vars_: dict[str, str]
) -> list[tuple[str, pathlib.Path]]:
    """返回 [(title, path), ...] · 同时支持 files + scan + glob 三块."""
    files: list[tuple[str, pathlib.Path]] = []

    # 1. 显式列表 ──────────────────────────────────────
    for entry in group.get("files", []) or []:
        title = entry["title"]
        path = pathlib.Path(_expand(entry["path"], vars_))
        files.append((title, path))

    # 2. 目录扫 ───────────────────────────────────────
    scan = group.get("scan")
    if scan:
        base = pathlib.Path(_expand(scan["dir"], vars_))
        pattern = scan.get("pattern", "*.md")
        recursive = scan.get("recursive", False)
        exclude_underscores = scan.get("exclude_underscores", True)
        # 默认 transform · 递归扫时用 path-slash 把子目录加进 title
        transform_name = scan.get(
            "title_transform", "path-slash" if recursive else "stem"
        )
        transform = TRANSFORMS.get(transform_name, _transform_stem)
        if base.exists():
            glob_pattern = f"**/{pattern}" if recursive else pattern
            for p in sorted(
                base.glob(glob_pattern),
                key=lambda x: x.relative_to(base).as_posix(),
            ):
                if not p.is_file():
                    continue
                if exclude_underscores and (
                    p.name.startswith("_") or p.stem.upper() == "README"
                ):
                    continue
                files.append((transform(p, base), p))

    # 3. glob 模式 ────────────────────────────────────
    for pat in group.get("glob", []) or []:
        expanded = _expand(pat, vars_)
        for raw in sorted(_glob.glob(expanded, recursive=True)):
            p = pathlib.Path(raw)
            if not p.is_file():
                continue
            files.append((p.stem, p))

    return files


# ── MD 读 + frontmatter 切 ──────────────────────────────────────
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_SLUG_RE = re.compile(r"[^a-z0-9一-鿿]+")


def slugify(text: str) -> str:
    """URL hash 用 · 保留中文."""
    s = text.lower().strip()
    s = _SLUG_RE.sub("-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "doc"


def _stringify_dates(obj: Any) -> Any:
    """递归把 date / datetime 转 ISO 字符串 · 便于 JSON 序列化."""
    if isinstance(obj, dict):
        return {k: _stringify_dates(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_stringify_dates(v) for v in obj]
    if isinstance(obj, (_dt.date, _dt.datetime)):
        return obj.isoformat()
    return obj


def split_frontmatter(content: str) -> tuple[dict, str]:
    """切分 YAML frontmatter · 返 (meta_dict, body)."""
    m = _FRONTMATTER_RE.match(content)
    if not m:
        return {}, content
    try:
        meta = yaml.safe_load(m.group(1)) or {}
        if not isinstance(meta, dict):
            return {}, content
    except yaml.YAMLError:
        return {}, content
    return _stringify_dates(meta), content[m.end():]


def read_md(path: pathlib.Path) -> tuple[str, dict, str | None, bool]:
    """读 MD · 返 (content_with_frontmatter, meta, mtime_str, exists)."""
    if not path.exists():
        msg = (
            f"# 📭 文件缺失\n\n"
            f"`{path}`\n\n"
            f"该条目已在配置里 · 但实际文件不存在。\n\n"
            f"可能原因:文件名拼写错、尚未生成、在其他分支未 merge。\n\n"
            f"修复:创建该文件 · 或从 `docs-cockpit.yaml` 删掉这条 entry。\n"
        )
        return msg, {}, None, False
    try:
        content = path.read_text(encoding="utf-8")
        mtime = _dt.datetime.fromtimestamp(path.stat().st_mtime).strftime(
            "%Y-%m-%d %H:%M"
        )
        meta, _ = split_frontmatter(content)
        return content, meta, mtime, True
    except Exception as exc:
        return f"# ⚠️ 读取失败\n\n`{path}`\n\n```\n{exc}\n```", {}, None, False


# ── frontmatter governance 校验 ──────────────────────────────────
# 默认 status × progress 区间 · 用于文档治理一致性校验
DEFAULT_STATUS_RANGES = {
    "not-started": (0, 0),
    "planned": (0, 15),
    "in-progress": (5, 95),
    "blocked": (0, 100),
    "done": (100, 100),
    "deferred": (0, 100),
}


def validate_meta(
    path: pathlib.Path, meta: dict, ranges: dict[str, tuple[int, int]]
) -> list[str]:
    """返不合规的 warning 字符串 · 不抛 · 让 build 继续."""
    warnings: list[str] = []
    status = meta.get("status")
    progress = meta.get("progress")
    if status is not None and status not in ranges:
        warnings.append(f"{path.name}: unknown status '{status}'")
    if isinstance(progress, int) and status in ranges:
        lo, hi = ranges[status]
        if not (lo <= progress <= hi):
            warnings.append(
                f"{path.name}: progress={progress} out of range [{lo}, {hi}] "
                f"for status={status}"
            )
    return warnings


# ── payload 组装 ───────────────────────────────────────────────────
def build_payload(
    config: dict, vars_: dict[str, str]
) -> tuple[list[dict], list[dict], dict | None, list[str]]:
    """返 (groups_payload, cards, kpi, warnings).

    - groups_payload: 侧边栏 + 文档视图用 · 每个 group 含 items 列表
    - cards: 看板用 · 只挑 frontmatter 有 id + type 在 card_types 内的文档
    - kpi: 模块级汇总(默认 type=module · 可配)
    - warnings: frontmatter 不合规的提示
    """
    fm_cfg = config.get("frontmatter", {}) or {}
    fm_enabled = fm_cfg.get("enabled", True)
    ranges_cfg = fm_cfg.get("status_progress_ranges") or DEFAULT_STATUS_RANGES
    ranges = {k: tuple(v) for k, v in ranges_cfg.items()}

    out: list[dict] = []
    all_warnings: list[str] = []
    for group in config.get("groups", []):
        items: list[dict] = []
        for title, path in _resolve_group_files(group, vars_):
            content, meta, mtime, exists = read_md(path)
            if fm_enabled and exists:
                all_warnings.extend(validate_meta(path, meta, ranges))
            items.append({
                "slug": slugify(title),
                "title": title,
                "path": str(path),
                "mtime": mtime,
                "exists": exists,
                "content": content,
                "size": len(content),
                "meta": meta if fm_enabled else {},
            })
        out.append({
            "group": group["name"],
            "icon": group.get("icon", "·"),
            "color": group.get("color", "primary"),
            "items": items,
        })

    kanban_cfg = fm_cfg.get("kanban", {}) or {}
    kanban_enabled = fm_enabled and kanban_cfg.get("enabled", False)
    cards: list[dict] = []
    kpi: dict | None = None
    if kanban_enabled:
        card_types = set(kanban_cfg.get("card_types") or [])
        for g in out:
            for it in g["items"]:
                meta = it.get("meta") or {}
                doc_id = meta.get("id")
                if not meta or not doc_id:
                    continue
                # 跳过模板占位 ID(MXX / CXX / RFC-XXX 等)
                if isinstance(doc_id, str) and (
                    "XX" in doc_id or doc_id.endswith("XXX")
                ):
                    continue
                if card_types and meta.get("type") not in card_types:
                    continue
                cards.append({
                    "id": meta.get("id"),
                    "type": meta.get("type"),
                    "title": meta.get("title") or it["title"],
                    "status": meta.get("status"),
                    "progress": meta.get("progress"),
                    "sprint": meta.get("sprint"),
                    "prd_ref": meta.get("prd_ref"),
                    "owner": meta.get("owner"),
                    "depends_on": meta.get("depends_on") or [],
                    "blocks": meta.get("blocks") or [],
                    "updated_at": meta.get("updated_at"),
                    "slug": it["slug"],
                    "group": g["group"],
                })
        kpi_type = kanban_cfg.get("kpi_type", "module")
        kpi_cards = [c for c in cards if c["type"] == kpi_type]
        kpi = {
            "kpi_type": kpi_type,
            "total_modules": len(kpi_cards),
            "done": sum(1 for c in kpi_cards if c["status"] == "done"),
            "in_progress": sum(1 for c in kpi_cards if c["status"] == "in-progress"),
            "blocked": sum(1 for c in kpi_cards if c["status"] == "blocked"),
            "planned": sum(1 for c in kpi_cards if c["status"] == "planned"),
            "not_started": sum(1 for c in kpi_cards if c["status"] == "not-started"),
            "deferred": sum(1 for c in kpi_cards if c["status"] == "deferred"),
            "overall_progress": (
                round(sum((c["progress"] or 0) for c in kpi_cards)
                      / max(len(kpi_cards), 1), 1)
            ),
        }

    return out, cards, kpi, all_warnings


# ── 渲染 HTML ─────────────────────────────────────────────────────
TEMPLATE_PATH = pathlib.Path(__file__).parent / "templates" / "index.html.tmpl"


def render_html(
    template: str, project: dict, payload: dict, build_time: str, design: dict
) -> str:
    """占位符替换 · 注意 __DOCS_JSON__ 最后做 · MD content 可能撞到其他 placeholder 字面量."""
    docs_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    sprint_order_json = json.dumps(
        payload.get("sprint_order") or [], ensure_ascii=False
    )
    kanban_enabled = "true" if payload.get("kanban_enabled") else "false"

    out = template
    out = out.replace("__BUILD_TIME__", build_time)
    out = out.replace("__PROJECT_NAME__", project.get("name", "Project"))
    out = out.replace("__PROJECT_SUBTITLE__", project.get("subtitle", "Docs preview"))
    out = out.replace("__PROJECT_GLYPH__", project.get("glyph", "P"))
    out = out.replace(
        "__PROJECT_DESCRIPTION__",
        project.get("description", "Project documentation preview"),
    )
    # localStorage key 前缀 · 避免多个项目互相覆盖
    out = out.replace(
        "__STORAGE_KEY__", slugify(project.get("name", "project")) + "-docs"
    )
    out = out.replace("__SPRINT_ORDER_JSON__", sprint_order_json)
    out = out.replace("__KANBAN_ENABLED__", kanban_enabled)

    # design tokens override(可选)
    color_overrides = []
    for k, v in (design.get("colors") or {}).items():
        # 把 primary → --colors-primary 这样的 token name 写进 :root inline style
        color_overrides.append(f"--colors-{k}: {v};")
    out = out.replace(
        "/* __DESIGN_OVERRIDES__ */", "\n  ".join(color_overrides)
    )

    # docs payload 最后做 · MD content 里可能撞到上面的 placeholder 字面量
    out = out.replace("__DOCS_JSON__", docs_json)
    return out


# ── CLI ─────────────────────────────────────────────────────────────
def _safe_print(msg: str) -> None:
    """Windows GBK 控制台兼容 · 不丢字符."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode("ascii"))


def cmd_build(args: argparse.Namespace) -> int:
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

    groups, cards, kpi, warnings = build_payload(config, vars_)

    fm_cfg = config.get("frontmatter", {}) or {}
    kanban_cfg = fm_cfg.get("kanban", {}) or {}
    sprint_order = kanban_cfg.get("sprint_order") or []

    payload = {
        "groups": groups,
        "cards": cards,
        "kpi": kpi,
        "sprint_order": sprint_order,
        "kanban_enabled": kpi is not None,
    }

    if not TEMPLATE_PATH.exists():
        _safe_print(f"[ERR] template missing: {TEMPLATE_PATH}")
        return 2

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    build_time = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    html = render_html(
        template, project, payload, build_time, config.get("design", {}) or {}
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")

    total_docs = sum(len(g["items"]) for g in groups)
    total_existing = sum(1 for g in groups for i in g["items"] if i["exists"])
    missing = total_docs - total_existing
    total_chars = sum(sum(i["size"] for i in g["items"]) for g in groups)

    for w in warnings:
        _safe_print(f"[WARN] frontmatter: {w}")
    if total_existing == 0:
        _safe_print("[WARN] 0 docs exist · 检查 paths.repo 与 groups[*].* 路径")
    _safe_print(f"[OK] Built {output}")
    _safe_print(
        f"     groups: {len(groups)} | docs: {total_docs} "
        f"({total_existing} exist, {missing} missing) | {total_chars:,} chars"
    )
    if kpi:
        _safe_print(
            f"     cards: {len(cards)} (kpi type '{kpi['kpi_type']}': "
            f"{kpi['total_modules']})"
        )
        _safe_print(
            f"     KPI · done={kpi['done']} in-progress={kpi['in_progress']} "
            f"planned={kpi['planned']} blocked={kpi['blocked']} "
            f"not-started={kpi['not_started']} deferred={kpi['deferred']}"
        )
        _safe_print(f"     overall progress: {kpi['overall_progress']}%")
    _safe_print(f"     HTML size: {output.stat().st_size:,} bytes")
    _safe_print(f"     build time: {build_time}")
    if warnings:
        _safe_print(f"     [!] {len(warnings)} frontmatter warning(s) — see above")
    _safe_print("")
    _safe_print("Open in browser:")
    _safe_print(f"  start {output}    # Windows")
    _safe_print(f"  open  {output}    # macOS")
    _safe_print(f"  xdg-open {output} # Linux")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    """从 examples/minimal.yaml 拷一份模板到 ./docs-cockpit.yaml."""
    target = pathlib.Path(args.output).resolve()
    if target.exists() and not args.force:
        _safe_print(f"[ERR] {target} 已存在 · 加 --force 覆盖")
        return 1
    template_yaml = (
        pathlib.Path(__file__).parent.parent / "examples" / "minimal.yaml"
    )
    if not template_yaml.exists():
        _safe_print(f"[ERR] template missing: {template_yaml}")
        return 2
    target.write_text(template_yaml.read_text(encoding="utf-8"), encoding="utf-8")
    _safe_print(f"[OK] wrote {target}")
    _safe_print("     edit, then run: python -m docs_cockpit build")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        prog="docs-cockpit",
        description="把项目 MD 文档汇总成单文件 HTML 看板",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    build_p = sub.add_parser("build", help="按 config 生成 HTML 看板")
    build_p.add_argument("--config", "-c", default="docs-cockpit.yaml",
                        help="YAML 配置文件路径(默认:当前目录 docs-cockpit.yaml)")
    build_p.add_argument("--debug", action="store_true",
                        help="打印解析后的路径变量与每条 entry 的绝对路径")
    build_p.set_defaults(func=cmd_build)

    init_p = sub.add_parser("init", help="生成最小可用配置模板")
    init_p.add_argument("-o", "--output", default="docs-cockpit.yaml")
    init_p.add_argument("--force", action="store_true")
    init_p.set_defaults(func=cmd_init)

    args = parser.parse_args(argv)
    return args.func(args)
