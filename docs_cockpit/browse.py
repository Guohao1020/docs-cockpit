"""docs-cockpit browse · 单 HTML markdown 浏览器.

适用场景:你想读项目的 docs/ 散落 MD + ~/.claude/ 下的 plans/memory
散落 MD · 不要 dashboard · 就要个树形侧边栏 + marked.js 渲染。

CLI:
  docs-cockpit browse                              # 默认扫:项目 + ~/.claude
  docs-cockpit browse --dir docs/adrs              # 限定扫某子目录
  docs-cockpit browse --output docs/adrs.html      # 自定义输出
  docs-cockpit browse --no-claude                  # 不扫 ~/.claude/

输出:单 HTML · 树形侧边栏(按目录嵌套)+ marked.js 渲染 + 搜索 +
localStorage 记上次看哪个 + 折叠/展开状态持久化。
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import pathlib
import re

from .build import _safe_print

TEMPLATE_PATH = (
    pathlib.Path(__file__).parent / "templates" / "browse.html.tmpl"
)


def _sanitize_cwd_key(cwd: pathlib.Path) -> str:
    """对应 Claude 的 ~/.claude/projects/<key>/ 命名 · 把 / : 替换成 -."""
    s = str(cwd).replace(":", "").replace("\\", "/")
    s = re.sub(r"[^a-zA-Z0-9一-鿿]+", "-", s).strip("-")
    return s


def _scan_md_files(
    root: pathlib.Path,
    top_level_only: bool = False,
    max_size: int = 2_000_000,
) -> list[dict]:
    """扫 root 下所有 *.md · 返回 [{path, content, mtime, size}].

    path 是相对 root 的 posix 路径(便于树形展示)。
    跳过 _foo.md / README.md(可选 · 默认保留 README)。
    """
    if not root.exists() or not root.is_dir():
        return []
    out: list[dict] = []
    pattern = "*.md" if top_level_only else "**/*.md"
    for p in sorted(root.glob(pattern)):
        if not p.is_file():
            continue
        try:
            size = p.stat().st_size
        except OSError:
            continue
        if size > max_size:
            content = (
                f"_File too large to embed ({size:,} bytes > {max_size:,})_\n\n"
                f"`{p}`"
            )
        else:
            try:
                content = p.read_text(encoding="utf-8")
            except Exception as exc:
                content = f"_Read failed: {exc}_\n\n`{p}`"
        mtime = _dt.datetime.fromtimestamp(p.stat().st_mtime).strftime(
            "%Y-%m-%d %H:%M"
        )
        try:
            rel = p.relative_to(root).as_posix()
        except ValueError:
            rel = p.name
        out.append({
            "path": rel,
            "content": content,
            "mtime": mtime,
            "size": size,
        })
    return out


def _build_roots(
    repo_root: pathlib.Path,
    explicit_dirs: list[str] | None,
    include_claude: bool,
) -> list[dict]:
    """组装 roots 列表 · 每个 root = {id, label, base, files[]}."""
    roots: list[dict] = []

    if explicit_dirs:
        # 用户指定了 --dir · 只扫这些
        for d in explicit_dirs:
            dir_path = pathlib.Path(d).expanduser().resolve()
            if not dir_path.exists():
                _safe_print(f"[WARN] dir not found: {dir_path}")
                continue
            label = dir_path.name + "/" if dir_path.is_dir() else dir_path.name
            roots.append({
                "id": _sanitize_cwd_key(dir_path),
                "label": label,
                "base": str(dir_path),
                "files": _scan_md_files(dir_path),
            })
        return roots

    # 默认扫:项目 root · docs/ · 然后 ~/.claude/
    # 1) 项目根级 *.md(只顶层 · 避免 deep search)
    top_files = _scan_md_files(repo_root, top_level_only=True)
    if top_files:
        roots.append({
            "id": "project-root",
            "label": f"{repo_root.name} (root)",
            "base": str(repo_root),
            "files": top_files,
        })

    # 2) 项目 docs/ 递归
    docs_dir = repo_root / "docs"
    if docs_dir.is_dir():
        docs_files = _scan_md_files(docs_dir)
        if docs_files:
            roots.append({
                "id": "project-docs",
                "label": f"{repo_root.name}/docs",
                "base": str(docs_dir),
                "files": docs_files,
            })

    if not include_claude:
        return roots

    # 3) ~/.claude/plans/<project-name>/
    home = pathlib.Path(
        os.environ.get("USERPROFILE") or os.environ.get("HOME") or "~"
    ).expanduser()

    claude_plans = home / ".claude" / "plans" / repo_root.name
    if claude_plans.is_dir():
        f = _scan_md_files(claude_plans)
        if f:
            roots.append({
                "id": "claude-plans",
                "label": f"~/.claude/plans/{repo_root.name}",
                "base": str(claude_plans),
                "files": f,
            })

    # 也试小写 / 其他 sanitize 后的名字
    for candidate in [repo_root.name.lower(), _sanitize_cwd_key(repo_root)]:
        if candidate == repo_root.name:
            continue
        p = home / ".claude" / "plans" / candidate
        if p.is_dir():
            f = _scan_md_files(p)
            if f:
                roots.append({
                    "id": f"claude-plans-{candidate}",
                    "label": f"~/.claude/plans/{candidate}",
                    "base": str(p),
                    "files": f,
                })

    # 4) ~/.claude/projects/<sanitized-cwd>/memory/
    claude_memory_key = _sanitize_cwd_key(repo_root)
    claude_memory = home / ".claude" / "projects" / claude_memory_key / "memory"
    if claude_memory.is_dir():
        f = _scan_md_files(claude_memory)
        if f:
            roots.append({
                "id": "claude-memory",
                "label": f"~/.claude/projects/.../memory",
                "base": str(claude_memory),
                "files": f,
            })

    return roots


def cmd_browse(args: argparse.Namespace) -> int:
    repo_root = pathlib.Path(args.repo or ".").resolve()
    if not repo_root.is_dir():
        _safe_print(f"[ERR] not a directory: {repo_root}")
        return 1

    if not TEMPLATE_PATH.exists():
        _safe_print(f"[ERR] template missing: {TEMPLATE_PATH}")
        return 2

    explicit_dirs = list(args.dir) if args.dir else None
    include_claude = not args.no_claude

    roots = _build_roots(repo_root, explicit_dirs, include_claude)
    total_files = sum(len(r["files"]) for r in roots)
    if total_files == 0:
        _safe_print("[WARN] no .md files found.")
        if explicit_dirs:
            _safe_print(f"       scanned: {explicit_dirs}")
        else:
            _safe_print(f"       default scan: {repo_root}/, {repo_root}/docs/")
            if include_claude:
                _safe_print(f"                     + ~/.claude/plans/{repo_root.name}/")
                _safe_print(f"                     + ~/.claude/projects/.../memory/")
        return 1

    build_time = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    payload = {
        "project": args.project or repo_root.name,
        "mark": (args.project or repo_root.name)[0].upper(),
        "build_time": build_time,
        "roots": roots,
    }

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    docs_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    html = template.replace("__DOCS_JSON__", docs_json)

    output_path = pathlib.Path(args.output or "docs/browse.html")
    if not output_path.is_absolute():
        output_path = (repo_root / output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    _safe_print(f"[OK] Browse HTML: {output_path}")
    _safe_print(f"     files: {total_files} across {len(roots)} root(s)")
    for r in roots:
        _safe_print(f"       · {r['label']:<40} {len(r['files'])} files")
    _safe_print(f"     HTML size: {output_path.stat().st_size:,} bytes")
    _safe_print(f"     build time: {build_time}")
    _safe_print("")
    _safe_print("Open in browser (Claude Code: 点击对应系统的代码块右上角 run 一键执行):")
    _safe_print("")
    _safe_print("```bash")
    _safe_print(f"start {output_path}")
    _safe_print("```")
    _safe_print("")
    _safe_print("```bash")
    _safe_print(f"open {output_path}")
    _safe_print("```")
    _safe_print("")
    _safe_print("```bash")
    _safe_print(f"xdg-open {output_path}")
    _safe_print("```")
    return 0
