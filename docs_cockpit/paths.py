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


# ── v0.11 W1 · resolve_code_anchor + defensive IO (plan §6.1 + 3A + 4A) ──
#
# 0.11 subtask 的 `code:` 字段把 subtask 跟代码 anchor 起来。例如:
#   subtasks:
#     - id: M09-S1
#       title: BrowserVendor abstraction
#       code: sourcery/worker/browser_vendor.py:42-89
#
# resolve_code_anchor:
#   - 解析 `path:start-end` / `path:single` / `path` 三种格式
#   - 走 _resolve_doc_path 三步 fallback 拿绝对路径
#   - defensive IO(plan-eng-review 3A):
#       OSError / PermissionError / UnicodeDecodeError / binary / >5MB / 行越界
#       → warn + None preview · build 不炸
#   - 读 ±5 行(plan §6.1)· hard cap 800 字符
#   - vscode:// 深链 + 可选 GitHub URL fallback
# Performance(plan-eng-review 4A):
#   _read_code_lines(path, start, end) 用 @functools.lru_cache(maxsize=256)
#   多 subtask 引用同 path:lines 不重复读 fs · 1.5-3x 加速

import functools

_CODE_ANCHOR_RE = re.compile(r"^(.+?)(?::(\d+)(?:-(\d+))?)?$")
_MAX_CODE_FILE_BYTES = 5 * 1024 * 1024   # 5MB · 超过 skip 防 build 卡
_CODE_PREVIEW_CHARS = 800                  # plan §6.1 hard cap · 截断 + `…` 标记
_CODE_CONTEXT_LINES = 5                    # ±5 行 · plan §6.1


def _parse_code_ref(raw: str) -> tuple[str, int | None, int | None]:
    r"""解析 `path:start-end` / `path:single` / `path` 三种格式.

    返 (path, start_line, end_line):
    - `x.py:42-89`     → ("x.py", 42, 89)
    - `x.py:42`        → ("x.py", 42, 42)
    - `x.py`           → ("x.py", None, None)

    Windows backslash: `x\y.py:42` 兼容(把 `\` 视作 path 一部分)。
    """
    raw = raw.strip()
    if not raw:
        return "", None, None
    m = _CODE_ANCHOR_RE.match(raw)
    if not m:
        return raw, None, None
    path, start_s, end_s = m.group(1), m.group(2), m.group(3)
    start = int(start_s) if start_s else None
    end = int(end_s) if end_s else start
    return path, start, end


@functools.lru_cache(maxsize=256)
def _read_code_lines(
    abs_path: str, start: int | None, end: int | None
) -> tuple[str, str]:
    """读 abs_path 的 [start-CTX, end+CTX] 行 · 返 (preview, warning).

    warning 非空表示读不完整(binary / encoding / 越界 / 巨大文件 等) ·
    caller 根据 warning 决定 emit Issue 或者直接 skip preview。

    @lru_cache 让多 subtask 引用同 path:lines 不重复读(plan-eng-review 4A)。
    args 必须 hashable · 所以用 abs_path str + int|None。
    """
    p = pathlib.Path(abs_path)
    try:
        size = p.stat().st_size
    except OSError as e:
        return "", f"stat failed: {e}"
    if size > _MAX_CODE_FILE_BYTES:
        kb = size // 1024
        return "", f"file too large ({kb} KB · max {_MAX_CODE_FILE_BYTES // 1024} KB · skipped to keep build fast)"

    # binary detect: 前 1024 字节有 null byte
    try:
        with open(p, "rb") as f:
            head = f.read(1024)
        if b"\x00" in head:
            return "", "binary file detected (null byte in first 1KB) · preview skipped"
    except OSError as e:
        return "", f"open failed: {e}"

    # 读全文 · 按行切
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        return "", f"not utf-8 ({e.encoding} decode failed at pos {e.start}) · preview skipped"
    except OSError as e:
        return "", f"read failed: {e}"

    lines = text.splitlines()
    total = len(lines)
    if start is None:
        # 整个文件预览 · 但 hard cap 800 字符
        snippet = text[:_CODE_PREVIEW_CHARS]
        if len(text) > _CODE_PREVIEW_CHARS:
            snippet += f"\n… [truncated · {total} lines total]"
        return snippet, ""

    # 行号越界
    if start > total:
        return "", f"start line {start} > file total {total} · preview skipped"

    # 计算窗口
    win_start = max(1, start - _CODE_CONTEXT_LINES)
    win_end = min(total, (end or start) + _CODE_CONTEXT_LINES)
    chunk = "\n".join(lines[win_start - 1 : win_end])
    if len(chunk) > _CODE_PREVIEW_CHARS:
        chunk = chunk[:_CODE_PREVIEW_CHARS] + "\n… [truncated]"
    return chunk, ""


# ── v0.11 alpha.8 · subtask docs anchor resolver(plan §6.6 · UI 右栏需要 slice) ──
#
# subtask 的 `docs:` 字段是 string list,形如:
#   "CLAUDE.md:88-100"          → 行范围 anchor
#   "docs/plans/p.md#§6.2"      → heading slug anchor
#   "docs/RFC/foo.md"           → 整 file(MVP 退化为 split_frontmatter 后 body)
# UI 右栏要 marked.js 渲染 · 所以 build 阶段就把 slice 切好放进 content · 前端不再
# 算 line → HTML 映射(那是 unreliable 的)。
_SUBTASK_DOC_REF_RE = re.compile(
    r"^(?P<path>[^:#]+?)"
    r"(?::(?P<lines>\d+(?:-\d+)?))?"
    r"(?:#(?P<heading>.+?))?$"
)
_HEADING_LINE_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def _parse_subtask_doc_ref(raw: str) -> tuple[str, str | None, str | None]:
    """Parse 'path[:lines][#heading]' → (path, lines, heading)."""
    if not raw:
        return "", None, None
    m = _SUBTASK_DOC_REF_RE.match(raw.strip())
    if not m:
        return raw.strip(), None, None
    return (
        (m.group("path") or "").strip(),
        m.group("lines"),
        m.group("heading"),
    )


def _slice_by_lines(raw_text: str, lines_spec: str) -> str:
    """按 'start-end' / 'single' 切片(1-indexed · 含两端)."""
    parts = lines_spec.split("-", 1)
    try:
        start = int(parts[0])
        end = int(parts[1]) if len(parts) == 2 else start
    except ValueError:
        return raw_text
    if start < 1:
        start = 1
    if end < start:
        end = start
    all_lines = raw_text.splitlines()
    return "\n".join(all_lines[start - 1 : end])


def _slice_by_heading(raw_text: str, heading_slug: str) -> tuple[str, str]:
    """从 heading 匹配位置切到下一同/更高级 heading · 返回 (slice, found_title).

    匹配规则:lines 里任意 ## 级 heading 的 title 包含 slug 字符串(case-insensitive)
    即命中。子任务 docs 写 `#§6.2` 我们就找标题里有 `§6.2` 的行 · 比 markdown URL
    slug 化更直观 · 跟用户在源文件 grep 的思路一致。
    """
    slug = (heading_slug or "").strip()
    if not slug:
        return "", ""
    slug_low = slug.lower()
    lines = raw_text.splitlines()
    found_idx: int | None = None
    found_level = 0
    found_title = ""
    for i, line in enumerate(lines):
        m = _HEADING_LINE_RE.match(line)
        if not m:
            continue
        title = m.group(2)
        if slug_low in title.lower():
            found_idx = i
            found_level = len(m.group(1))
            found_title = title.strip()
            break
    if found_idx is None:
        return "", ""
    end_idx = len(lines)
    for j in range(found_idx + 1, len(lines)):
        m = _HEADING_LINE_RE.match(lines[j])
        if m and len(m.group(1)) <= found_level:
            end_idx = j
            break
    return "\n".join(lines[found_idx:end_idx]), found_title


def _resolve_subtask_doc_anchor(
    raw: str,
    module_path: pathlib.Path,
    repo_root: pathlib.Path,
    vars_: dict[str, str],
) -> dict[str, Any]:
    """把 subtask `docs:` 的单条字符串解析为右栏 marked.js 可消费的 anchor entry.

    返回字段:
      raw       · 原始字符串(保留)
      path      · 切出来的纯路径
      lines     · "88-100" / "88" / None
      heading   · "§6.2" / None(取自 `#xxx` 后缀)
      resolved  · 绝对路径 · 失败 ""
      exists    · bool
      title     · heading 匹配上时取找到的 heading 文本 · 否则 ""
      content   · 切片后的 markdown 文本 · 非 MD / 失败为 ""
      mtime     · "YYYY-MM-DD HH:MM" · 失败 None
      warning   · 失败/降级原因 · 成功 ""
    """
    out: dict[str, Any] = {
        "raw": raw or "",
        # 0.14.3 · raw_with_anchor alias · 跟 code_anchors[].path 命名对称(都是 user raw 串)
        # 让 template / downstream 用 `raw` 或 `raw_with_anchor` 都行 · 自由切
        "raw_with_anchor": raw or "",
        "path": "",
        "lines": None,
        "heading": None,
        "title": "",
        "resolved": "",
        "exists": False,
        "content": "",
        "mtime": None,
        "warning": "",
    }
    if not raw:
        out["warning"] = "empty doc anchor"
        return out

    path_s, lines, heading = _parse_subtask_doc_ref(raw)
    out["path"] = path_s
    out["lines"] = lines
    out["heading"] = heading

    resolved = _resolve_doc_path(path_s, module_path, repo_root, vars_)
    if not resolved or not resolved.is_file():
        out["warning"] = (
            f"path not found: {path_s} (tried abs · relative to module · relative to repo)"
        )
        return out
    out["resolved"] = str(resolved)
    out["exists"] = True

    try:
        out["mtime"] = _dt.datetime.fromtimestamp(
            resolved.stat().st_mtime
        ).strftime("%Y-%m-%d %H:%M")
    except OSError:
        pass

    if resolved.suffix.lower() not in (".md", ".markdown"):
        # 非 MD 不嵌内容 · 前端走 vscode:// / file:// 外部打开
        return out

    try:
        raw_text = resolved.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeError) as e:
        out["warning"] = f"read failed: {e}"
        return out

    if lines:
        # 行号锚 · 直接对 raw 切(用户写行号默认就是源文件里的行 · 不剥 frontmatter)
        out["content"] = _slice_by_lines(raw_text, lines)
    elif heading:
        slice_text, found_title = _slice_by_heading(raw_text, heading)
        if slice_text:
            out["content"] = slice_text
            out["title"] = found_title
        else:
            out["warning"] = f"heading not found: {heading}"
            # 降级 · 退到整 body
            _, body = split_frontmatter(raw_text)
            out["content"] = body
    else:
        # 整 file · 剥 frontmatter 让 marked 渲染更干净(跟 _resolve_and_embed_docs 一致)
        _, body = split_frontmatter(raw_text)
        out["content"] = body

    # 大小护栏 · 跟 module 级 docs 一致 · 100KB 截断
    body_bytes = out["content"].encode("utf-8")
    if len(body_bytes) > _MAX_EMBED_BYTES:
        kb = len(body_bytes) // 1024
        out["content"] = body_bytes[:_MAX_EMBED_BYTES].decode(
            "utf-8", errors="replace"
        ) + (
            f"\n\n---\n\n*[Content truncated · body is {kb} KB · "
            f"embed limit 100 KB. Open the file directly to read the rest.]*\n"
        )

    return out


def _resolve_code_anchor(
    raw: str,
    module_path: pathlib.Path,
    repo_root: pathlib.Path,
    vars_: dict[str, str],
) -> dict[str, Any]:
    """把 subtask 的 `code:` 字段解析为完整 anchor entry.

    输入 raw 是字符串(`path:start-end` 或 `path:single` 或 `path`) ·
    输出 dict 含:
      path        · 用户原始写法(保留)
      lines       · "42-89" / "42" / None
      resolved    · 绝对路径字符串 · 找不到为 ""
      exists      · bool · 路径是否存在
      preview     · code snippet 字符串 · 失败为 ""
      warning     · 失败原因 · 成功为 ""
      vscode_url  · vscode://file/<abs>:<line> 深链 · 失败为 ""

    plan §6.1 + 3A defensive IO + 4A lru_cache 全部覆盖。
    """
    out = {
        "path": raw or "",
        # 0.14.3 · path_only · clean 路径(不含 :lines)· 跟 `doc_anchors[].path` 语义对齐
        # 解决 0.11.2 暴露的 `{{ ca.path }}:{{ ca.lines }}` 双拼 bug 的根 schema 不一致
        # 推荐 template 渲染端用 path_only · 老 path 字段保留 raw 串 stability
        "path_only": "",
        "lines": None,
        "resolved": "",
        "exists": False,
        "preview": "",
        "warning": "",
        "vscode_url": "",
    }
    if not raw:
        out["warning"] = "empty code anchor"
        return out

    path_s, start, end = _parse_code_ref(raw)
    out["path_only"] = path_s
    out["lines"] = f"{start}-{end}" if start and end and start != end else (str(start) if start else None)

    resolved = _resolve_doc_path(path_s, module_path, repo_root, vars_)
    if not resolved:
        out["warning"] = f"path not found: {path_s} (tried abs · relative to module · relative to repo)"
        return out

    out["resolved"] = str(resolved)
    out["exists"] = True

    # vscode:// 深链(start 默认 1)
    line_for_url = start or 1
    out["vscode_url"] = f"vscode://file/{resolved.as_posix()}:{line_for_url}"

    # 读 preview(走 lru_cache)
    preview, warning = _read_code_lines(str(resolved), start, end)
    out["preview"] = preview
    if warning:
        out["warning"] = warning
    return out
