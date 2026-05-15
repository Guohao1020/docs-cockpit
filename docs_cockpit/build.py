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


# ── frontmatter governance 校验 (0.9.0 大改 · 接 docs-cockpit-author 规范) ──
#
# 0.8.x 之前 validator 只校验 status 与 progress 区间 · 输出形如
# "M01.md: progress=80 out of range" 这种干瘪的 warning · 用户实测说"光看
# warning 不知道该怎么改"。0.9.0 配套 docs-cockpit-author skill 把规范固化:
#   - REQUIRED 字段:id · 不写就拿不到看板位置
#   - RECOMMENDED 字段:status · sprint · 没有 status drawer 显示 not-started
#   - OPTIONAL but high-value:desc · docs · subtasks
# Issue 输出结构化(severity / field / message / suggestion / reference) · CLI
# 端打印成"❌ M01: missing required `id` · 💡 add `id: M01-Web` to frontmatter
# · 📚 docs-cockpit-author §2.1" 这种"问题 + 修法 + 引用"三段式。
#
# severity 分 3 档:
#   error · 看板根本接不住 · build 仍写 HTML 但 --strict 模式下 exit 1
#   warn  · 看板能接住但用户体验差(no status / progress 越界 / 关键字段缺失)
#   hint  · 锦上添花(没 desc · 没 docs · subtasks 全在 body 没在 frontmatter)
#
# 默认 status × progress 区间 · 给 status × progress 一致性校验用
DEFAULT_STATUS_RANGES = {
    "not-started": (0, 0),
    "planned": (0, 15),
    "in-progress": (5, 95),
    "blocked": (0, 100),
    "done": (100, 100),
    "deferred": (0, 100),
}

# Status enum · 写错值会被 validator 抓出来(unknown status)
VALID_STATUSES = set(DEFAULT_STATUS_RANGES.keys())

# 文档类型 enum · 用于 type 字段一致性校验
VALID_DOC_TYPES = {"module", "concept", "plan", "rfc", "spec", "memory", "roadmap"}


class Issue:
    """单条 frontmatter 校验问题 · 结构化便于 CLI / IDE / CI 消费.

    severity 决定 build / lint / --strict 的退出行为:
      error · MUST fix · --strict 下退出码非零 · 看板接不住或会渲染错
      warn  · SHOULD fix · 用户体验问题 · 仍能 build
      hint  · COULD fix · 锦上添花 · 不影响 build
    """

    __slots__ = ("severity", "path", "field", "message", "suggestion", "reference")

    def __init__(
        self,
        severity: str,
        path: pathlib.Path,
        field: str,
        message: str,
        suggestion: str = "",
        reference: str = "",
    ):
        self.severity = severity
        self.path = path
        self.field = field
        self.message = message
        self.suggestion = suggestion
        self.reference = reference

    def as_dict(self) -> dict:
        return {
            "severity": self.severity,
            "path": str(self.path),
            "field": self.field,
            "message": self.message,
            "suggestion": self.suggestion,
            "reference": self.reference,
        }

    def format_for_terminal(self) -> str:
        """三段式 CLI 输出:❌/⚠️/💡 message · 💡 suggestion · 📚 reference."""
        glyph = {"error": "❌", "warn": "⚠️ ", "hint": "💡"}.get(self.severity, "·")
        parts = [f"{glyph} {self.path.name} · {self.field}: {self.message}"]
        if self.suggestion:
            parts.append(f"   💡 fix: {self.suggestion}")
        if self.reference:
            parts.append(f"   📚 see: {self.reference}")
        return "\n".join(parts)


def validate_meta(
    path: pathlib.Path,
    meta: dict,
    ranges: dict[str, tuple[int, int]],
    *,
    body: str = "",
) -> list[Issue]:
    """返结构化 Issue 列表 · 不抛 · 让 build 继续.

    docs-cockpit-author skill 是 spec 的规范来源 · 这里只把 frontmatter
    跟规范对齐 · 不增不减 · 改 skill 同步改这里。
    """
    issues: list[Issue] = []
    name = path.name

    # ── REQUIRED: id ─────────────────────────────────────
    doc_id = meta.get("id")
    if not doc_id:
        issues.append(Issue(
            "error", path, "id",
            "missing required field — module/concept won't appear in dashboard",
            suggestion=f'add `id: M01-{path.stem[:8]}` (or your project ID convention) to frontmatter',
            reference="docs-cockpit-author · §2.1 required frontmatter",
        ))
    elif isinstance(doc_id, str) and ("XX" in doc_id or doc_id.endswith("XXX")):
        issues.append(Issue(
            "warn", path, "id",
            f"id `{doc_id}` looks like a template placeholder · this entry will be skipped",
            suggestion="replace XX/XXX with a concrete identifier (e.g. M07, RFC-002, C03)",
            reference="docs-cockpit-author · §2.1 required frontmatter",
        ))

    # ── RECOMMENDED: status · drawer 的状态指示靠它 ──────
    status = meta.get("status")
    if status is None:
        issues.append(Issue(
            "warn", path, "status",
            "missing — dashboard will treat this as `not-started`",
            suggestion='set `status: planned` / `in-progress` / `done` etc.',
            reference="docs-cockpit-author · §2.2 status enum",
        ))
    elif status not in VALID_STATUSES:
        valid = " · ".join(sorted(VALID_STATUSES))
        issues.append(Issue(
            "error", path, "status",
            f"unknown status `{status}` — dashboard renders fallback dot",
            suggestion=f"pick one of: {valid}",
            reference="docs-cockpit-author · §2.2 status enum",
        ))

    # ── status × progress 区间一致性 ─────────────────────
    progress = meta.get("progress")
    if isinstance(progress, (int, float)) and status in ranges:
        lo, hi = ranges[status]
        if not (lo <= progress <= hi):
            issues.append(Issue(
                "warn", path, "progress",
                f"progress={progress} out of range [{lo}, {hi}] for status=`{status}`",
                suggestion=(
                    "either move status forward (e.g. `in-progress`) "
                    f"or bring progress back to the {lo}-{hi} band"
                ),
                reference="docs-cockpit-author · §2.3 status × progress invariants",
            ))
    elif progress is not None and not isinstance(progress, (int, float)):
        issues.append(Issue(
            "error", path, "progress",
            f"progress must be a number 0-100 · got {type(progress).__name__} `{progress!r}`",
            suggestion="use `progress: 75` (integer 0-100), not strings or percentages",
            reference="docs-cockpit-author · §2.3 status × progress invariants",
        ))

    # ── type 字段(可选 · 但写错会让 author skill 困惑)──
    doc_type = meta.get("type")
    if doc_type is not None and doc_type not in VALID_DOC_TYPES:
        valid = " · ".join(sorted(VALID_DOC_TYPES))
        issues.append(Issue(
            "warn", path, "type",
            f"unknown type `{doc_type}` — won't affect rendering but breaks doc-type filters",
            suggestion=f"pick one of: {valid}",
            reference="docs-cockpit-author · §2.4 doc type enum",
        ))

    # ── HINTS · 锦上添花 ────────────────────────────────
    if not meta.get("desc"):
        issues.append(Issue(
            "hint", path, "desc",
            "no description — drawer shows '(empty)' and copy-prompt has less context",
            suggestion='add `desc: "<one-line summary>"` so AI editors can generate better plans',
            reference="docs-cockpit-author · §2.5 recommended fields",
        ))

    docs_field = meta.get("docs")
    docs_in_body = bool(body) and bool(_DOCS_SECTION_RE.search(body))
    if not docs_field and not docs_in_body:
        # 只在 active 状态下提醒(done / not-started / deferred 不催)
        if status in ("in-progress", "planned", "blocked"):
            issues.append(Issue(
                "hint", path, "docs",
                "no docs link · dashboard shows the 'copy prompt' CTA on active modules",
                suggestion="add a `docs:` list or a `## Related` body section once a plan/RFC exists",
                reference="docs-cockpit-author · §3 cross-doc references",
            ))

    return issues


# ── MD body extraction (0.4.0 · 让 frontmatter 缺字段时自动从正文提取) ──
#
# 用户常常已经在 MD body 里维护 `## 待办` + `- [ ]` checklist 或 `## 关联`
# section 列相关文档 link · 但 frontmatter 没有 subtasks/docs 字段。这里
# 提供 fallback:frontmatter 缺这俩字段时 · 扫 body 自动提。
#
# 优先级:frontmatter 字段 > body 提取。用户想精控直接写 frontmatter 接管。

_SUBTASK_SECTION_RE = re.compile(
    r"^##\s+(?:\d+\s*[·.\-]?\s*)?(?:待办|TODO|To[- ]?do|Subtasks?|Tasks?|任务)\b",
    re.MULTILINE | re.IGNORECASE,
)
_DOCS_SECTION_RE = re.compile(
    r"^##\s+(?:\d+\s*[·.\-]?\s*)?"
    r"(?:关联(?:文档)?|Related(?:\s+(?:docs|documents))?|"
    r"Docs?|See\s+also|参考|链接|Links?)\b",
    re.MULTILINE | re.IGNORECASE,
)
# 任意 H1-H6 或 horizontal-rule(---/***/___) 作为 section 边界
_SECTION_BOUNDARY_RE = re.compile(r"^(#{1,6}\s|[-*_]{3,}\s*$)", re.MULTILINE)
_CHECKBOX_LINE_RE = re.compile(r"^\s*[-*+]\s+\[([ xX])\]\s+(.+?)\s*$")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _section_after(body: str, header_re: re.Pattern) -> str:
    """找到 header_re 匹配的 H2 · 返回该 section 的正文(到下一个边界为止)."""
    m = header_re.search(body)
    if not m:
        return ""
    section_start = body.find("\n", m.end()) + 1
    tail = body[section_start:]
    next_boundary = _SECTION_BOUNDARY_RE.search(tail)
    if next_boundary:
        return tail[: next_boundary.start()]
    return tail


def extract_subtasks_from_body(body: str) -> list[dict]:
    """扫 ## 待办/TODO/Subtasks 段 · 提 `- [x]` / `- [ ]` 行为 subtasks."""
    section = _section_after(body, _SUBTASK_SECTION_RE)
    if not section:
        return []
    out: list[dict] = []
    for line in section.split("\n"):
        m = _CHECKBOX_LINE_RE.match(line)
        if m:
            done = m.group(1).lower() == "x"
            title = m.group(2).strip()
            if title:
                out.append({"title": title, "done": done})
    return out


def extract_docs_from_body(body: str) -> list[dict]:
    """扫 ## 关联/Related/Docs 段 · 提 MD link `[title](path)` 为 docs."""
    section = _section_after(body, _DOCS_SECTION_RE)
    if not section:
        return []
    out: list[dict] = []
    for m in _MD_LINK_RE.finditer(section):
        title = m.group(1).strip()
        path = m.group(2).strip()
        if title and path and not path.startswith("#"):  # 跳锚点链接
            out.append({"title": title, "path": path})
    return out


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
    """0.2.0:模板只需一个占位符替换 · JS 从 payload 渲染其他一切."""
    docs_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return template.replace("__DOCS_JSON__", docs_json)


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
    _safe_print("Open in browser:")
    _safe_print(f"  start {output}    # Windows")
    _safe_print(f"  open  {output}    # macOS")
    _safe_print(f"  xdg-open {output} # Linux")

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
    build_p.add_argument("--no-version-check", action="store_true",
                        help="跳过新版本检测(也可设 DOCS_COCKPIT_NO_VERSION_CHECK=1)")
    build_p.add_argument("--strict", action="store_true",
                        help="0.9.0:任何 frontmatter error 非零退出(CI 用 · warn/hint 不算)")
    build_p.set_defaults(func=cmd_build)

    # 0.9.0:lint 子命令 · 只校验不 build · 配合 docs-cockpit-author skill 使用
    lint_p = sub.add_parser(
        "lint",
        help="校验 frontmatter 是否符合 docs-cockpit-author 规范(不 build · CI / pre-commit 用)",
    )
    lint_p.add_argument("--config", "-c", default="docs-cockpit.yaml",
                       help="YAML 配置文件路径")
    lint_p.add_argument("--json", action="store_true",
                       help="JSON 输出 · 给 IDE / CI 消费")
    lint_p.add_argument("--strict-warn", action="store_true",
                       help="把 warning 也升级成 error(默认只 error 非零退出)")
    lint_p.set_defaults(func=cmd_lint)

    init_p = sub.add_parser("init", help="生成最小可用配置模板")
    init_p.add_argument("-o", "--output", default="docs-cockpit.yaml")
    init_p.add_argument("--force", action="store_true")
    init_p.set_defaults(func=cmd_init)

    mig_p = sub.add_parser(
        "migrate",
        help="一键迁移现有项目散落 MD → docs-cockpit canonical 布局",
    )
    mig_p.add_argument("--repo", default=".", help="目标项目根 · 默认当前目录")
    mig_p.add_argument(
        "--apply", action="store_true",
        help="真执行迁移(默认 dry-run · 只 print 计划不动文件)",
    )
    mig_p.add_argument(
        "--keep-originals", action="store_true",
        help="复制而非移动原文件(保留 docs/plans/ 等原 dir)",
    )
    from . import migrate as _migrate_mod
    mig_p.set_defaults(func=_migrate_mod.cmd_migrate)

    browse_p = sub.add_parser(
        "browse",
        help="生成单 HTML markdown 浏览器(树形侧边栏 + marked.js 渲染)",
    )
    browse_p.add_argument("--repo", default=".", help="项目根 · 默认当前目录")
    browse_p.add_argument(
        "--dir", action="append",
        help="指定扫描目录(可多次)· 不指定时默认扫项目+~/.claude",
    )
    browse_p.add_argument(
        "--no-claude", action="store_true",
        help="跳过 ~/.claude/{plans,projects} 扫描",
    )
    browse_p.add_argument(
        "-o", "--output", default=None,
        help="输出 HTML 路径(默认 docs/browse.html)",
    )
    browse_p.add_argument(
        "--project", default=None,
        help="项目名(显示在 topbar · 默认从 repo 目录名推)",
    )
    from . import browse as _browse_mod
    browse_p.set_defaults(func=_browse_mod.cmd_browse)

    up_p = sub.add_parser(
        "upgrade",
        help="一条命令升级 CLI + plugin (auto-detect backend · 智能判断要不要重启)",
    )
    up_p.add_argument(
        "--dry-run", action="store_true",
        help="只 print 升级计划 · 不执行 · 不动文件",
    )
    up_p.add_argument(
        "--yes", "-y", action="store_true",
        help="非交互模式 · 跳过 'Proceed? [Y/n]' 确认",
    )
    up_p.add_argument(
        "--no-clear-cache", action="store_true",
        help="不自动清 plugin cache · 让用户手工处理(给老姿势兜底)",
    )
    up_p.add_argument(
        "--skip-changelog", action="store_true",
        help="不 fetch + 显示 CHANGELOG diff(网络差时加速)",
    )
    from . import upgrade as _upgrade_mod
    up_p.set_defaults(func=_upgrade_mod.cmd_upgrade)

    args = parser.parse_args(argv)
    return args.func(args)
