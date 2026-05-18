"""docs-cockpit · 路径变量展开 + 文件源解析 + docs 路径解析与内容嵌入.

把 build.py 里的 path / fs IO 相关函数(_build_vars / _expand /
_resolve_group_files / read_md / _resolve_doc_path / _resolve_and_embed_docs)
提到独立模块。

v0.11 W1 在这里新增 `_resolve_code_anchor()`(plan §6.1)· 把 subtask 的
`code:` 字段解析为绝对路径 + line range + content preview · 走同一份
defensive IO error handling(plan-eng-review 3A)。

0.11.0-alpha.1:从 build.py 拆出(plan-eng-review 1A)。
"""

from __future__ import annotations

import datetime as _dt
import glob as _glob
import os
import pathlib
import re
from typing import Any

from .schema import split_frontmatter


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


# ── docs 路径解析 + 内容嵌入 (0.7.1) ─────────────────────────────────
#
# 0.7.0 之前:`docs:` frontmatter 的 path 原样塞进 state.json · 前端 <a href>
# 直接当 URL 用 · 在 file:// 上下文里相对路径以"看板 HTML 自己的位置"为根 ·
# 导致 frontmatter 写 `docs/plans/foo.md`(repo-relative) · 看板放在
# <repo>/docs/index.html → 实际请求成了 <repo>/docs/docs/plans/foo.md ·
# 浏览器报 ERR_FILE_NOT_FOUND。
#
# 0.7.1 修法:build 阶段把每个 doc path 解析成绝对路径(候选:绝对 → 相对
# MD 自身目录 → 相对 repo 根) · 并把 MD 文本一同内嵌到 payload(≤100KB) ·
# 前端拿到 content 直接 marked.parse 渲染(看板内 drawer 预览 · 不再走 file://
# 浏览器原生展开)。
_MAX_EMBED_BYTES = 100 * 1024  # 100KB per doc · 超过截断 + 提示


def _resolve_doc_path(
    raw_path: str,
    module_path: pathlib.Path,
    repo_root: pathlib.Path,
    vars_: dict[str, str],
) -> pathlib.Path | None:
    """把 docs 条目的 path 解析成绝对路径 · 找不到返回 None.

    顺序:
    1. 先展开 {repo}/{home}/{env:X} 等变量
    2. 绝对路径 → 直接用
    3. 相对路径 → 依次尝试 [module 同级目录, repo 根]
    """
    if not raw_path:
        return None
    expanded = _expand(raw_path, vars_)
    p = pathlib.Path(expanded)
    if p.is_absolute():
        return p if p.exists() else None
    for base in (module_path.parent, repo_root):
        cand = (base / p).resolve()
        if cand.exists():
            return cand
    return None


def _resolve_and_embed_docs(
    docs_list: list[dict],
    module_path: pathlib.Path,
    repo_root: pathlib.Path,
    vars_: dict[str, str],
) -> list[dict]:
    """把 frontmatter `docs:` 列表增强:解析 path + 内嵌 MD 文本.

    输入条目 {title, path} · 输出每条多 4 个字段:
      resolved · 绝对路径字符串 · 找不到时空串
      exists   · 文件是否存在(bool)
      content  · MD 文本 · 仅当 .md/.markdown 且 ≤100KB 时填 · 否则空串
      mtime    · YYYY-MM-DD HH:MM · 找不到为 None
    """
    out: list[dict] = []
    for d in docs_list or []:
        title = (d.get("title") or "").strip()
        raw_path = (d.get("path") or "").strip()
        resolved = _resolve_doc_path(raw_path, module_path, repo_root, vars_)
        entry: dict[str, Any] = {
            "title": title,
            "path": raw_path,                         # 保留用户原始写法 · 不破坏老前端
            "resolved": str(resolved) if resolved else "",
            "exists": bool(resolved),
            "content": "",
            "mtime": None,
        }
        if resolved and resolved.is_file():
            try:
                entry["mtime"] = _dt.datetime.fromtimestamp(
                    resolved.stat().st_mtime
                ).strftime("%Y-%m-%d %H:%M")
                # 只内嵌 .md / .markdown · 图片 / PDF 等让浏览器自己处理(走 resolved 路径)
                if resolved.suffix.lower() in (".md", ".markdown"):
                    raw_text = resolved.read_text(encoding="utf-8", errors="replace")
                    # 0.7.2:剥掉 YAML frontmatter · 否则会被 marked 渲染成一坨文本
                    # 影响预览观感(用户在 0.7.1 实测反馈)
                    meta, body = split_frontmatter(raw_text)
                    entry["meta"] = meta  # 留一份给前端做"显示 frontmatter 摘要"用 · 暂未消费
                    body_bytes = body.encode("utf-8")
                    if len(body_bytes) <= _MAX_EMBED_BYTES:
                        entry["content"] = body
                    else:
                        truncated = body_bytes[:_MAX_EMBED_BYTES].decode(
                            "utf-8", errors="replace"
                        )
                        kb = len(body_bytes) // 1024
                        entry["content"] = (
                            truncated
                            + f"\n\n---\n\n*[Content truncated · body is {kb} KB · "
                            f"embed limit 100 KB. Open the file directly to read the rest.]*\n"
                        )
            except (OSError, UnicodeError):
                pass
        out.append(entry)
    return out
