"""docs-cockpit · frontmatter schema 校验 + body section 提取.

把 build.py 里的 schema 相关逻辑(Issue / validate_meta / body extraction regex
和函数 / frontmatter parsing)提到独立模块 · 便于 unit test 和 v0.11 W1
subtask schema 演进(plan §6.1)。

无 fs 依赖(除了 pathlib.Path 类型签名)· 所有 IO 由 build.py / paths.py 完成 ·
本模块只对已读入内存的 meta dict 和 body string 做校验和提取。

0.11.0-alpha.1:从 build.py 拆出(plan-eng-review 1A)。
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import pathlib
import re
from typing import Any

import yaml


# ── frontmatter parsing ─────────────────────────────────────────────
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


# ── MD body section detection (0.4.0 · frontmatter 缺字段时从正文提取) ──
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
# 0.11.0-alpha.2 · plan §6.1 内联 `@code:<path>[:lines]` / `@docs:<ref>`
# 终止符是空格或行尾 · 允许 path 内有 / 和 \ · lines 用 :42 / :42-89
_INLINE_CODE_RE = re.compile(r"@code:(\S+)")
_INLINE_DOCS_RE = re.compile(r"@docs:(\S+)")


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
    """扫 ## 待办/TODO/Subtasks 段 · 提 `- [x]` / `- [ ]` 行为 subtasks.

    0.11.0-alpha.2 · plan §6.1 增强:支持内联 `@code:path[:lines]` 和
    `@docs:ref`(都可多次)· 例如:
      - [x] Lane A · BrowserVendor abstraction @code:sourcery/x.py:42-89 @docs:M09-spec
    会切出:
      title = "Lane A · BrowserVendor abstraction"
      code = ["sourcery/x.py:42-89"]
      docs = ["M09-spec"]
    """
    section = _section_after(body, _SUBTASK_SECTION_RE)
    if not section:
        return []
    out: list[dict] = []
    for line in section.split("\n"):
        m = _CHECKBOX_LINE_RE.match(line)
        if not m:
            continue
        done = m.group(1).lower() == "x"
        text = m.group(2).strip()
        if not text:
            continue
        # 0.11.0-alpha.2:提取内联 @code:... 和 @docs:...
        code_refs = _INLINE_CODE_RE.findall(text)
        docs_refs = _INLINE_DOCS_RE.findall(text)
        # title = 去掉所有 @code / @docs annotation 后的余文
        cleaned = _INLINE_CODE_RE.sub("", text)
        cleaned = _INLINE_DOCS_RE.sub("", cleaned)
        title = " ".join(cleaned.split()).strip()
        if not title:
            continue
        entry: dict[str, Any] = {"title": title, "done": done}
        if code_refs:
            entry["code"] = code_refs if len(code_refs) > 1 else code_refs[0]
        if docs_refs:
            entry["docs"] = docs_refs if len(docs_refs) > 1 else docs_refs[0]
        out.append(entry)
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


# ── v0.11 W1 subtask schema · plan §6.1 + §6.4 + plan-eng-review 1A ──
#
# 0.10 subtask 是字符串数组(列表 / `[x]` body checkbox)· 没 id / 没 code
# anchor / 没 docs 引用 · 跨 build 不稳定(localStorage 用 index 为 key ·
# 用户加新 subtask 状态全错位)。
#
# 0.11 把 subtask 升为对象:{id, title, status, code?, docs?} · id 用
# `<module-id>-<sha1(title)[:6]>` 算法 · title 没变 id 就稳。
# string 输入仍然兼容 · normalize 时自动补 id / status="not-started"。

VALID_SUBTASK_STATUSES = {"not-started", "in-progress", "done", "blocked"}


def _subtask_id_for(module_id: str, title: str) -> str:
    """生成 stable subtask id · `<module-id>-<sha1(title)[:6]>`.

    plan §6.1 + plan-eng-review issue #3 决策:不用 body index 算 id(因为用户
    在中间插入新 subtask 会让所有后续 id shift · 破坏 localStorage 持久化)。
    Hash-of-title trade-off:用户改 title = 改任务定义 = id 变 = localStorage
    状态丢 · acceptable。
    """
    if not module_id:
        module_id = "X"
    digest = hashlib.sha1(title.encode("utf-8", errors="replace")).hexdigest()[:6]
    return f"{module_id}-{digest}"


def _coerce_status(raw: Any) -> str:
    """旧 done:true/false 兼容 · 不抛 · 落不在枚举里 statuc 留给 validator 报."""
    if raw is True or raw == "done":
        return "done"
    if raw is False or raw is None or raw == "":
        return "not-started"
    return str(raw)


def normalize_subtasks(raw: Any, module_id: str) -> list[dict]:
    """把 frontmatter `subtasks:` 字段统一成对象数组.

    输入 raw 可能是:
    - None / [] → 返 []
    - list[str](v0.10 旧 · 或 body fallback `- [x] title`)· title 即 string ·
      status 看不出来 → 默认 not-started
    - list[dict] · v0.10 form A `{title, done}` · 也可能 v0.11 完整 `{id, title, status, code, docs}`
    - 混合 list[str | dict]

    输出 list[dict] · 每条至少含 {id, title, status} · 可选含 `code` / `docs`。

    id 算法:`<module-id>-<sha1(title)[:6]>`(plan §6.1)。dict 显式给 id 用
    用户的 · 自动算的不覆盖。

    v0.10 form A `{title, done: bool}` 兼容:`done=True` → status=done ·
    `done=False` → status=not-started · 保 done 字段(前端老 JS 可能读)。
    """
    if not raw:
        return []
    out: list[dict] = []
    for item in raw:
        if isinstance(item, str):
            # v0.10 string form / body checkbox(已被 extract_subtasks_from_body
            # 转 dict 了 · 这里兜底)
            title = item.strip()
            if not title:
                continue
            out.append({
                "id": _subtask_id_for(module_id, title),
                "title": title,
                "status": "not-started",
                "done": False,
            })
        elif isinstance(item, dict):
            title = (item.get("title") or "").strip()
            if not title:
                continue
            # status:优先显式 status · 没 status 看 done · 都没默认 not-started
            if "status" in item:
                status = _coerce_status(item["status"])
            elif "done" in item:
                status = "done" if item["done"] else "not-started"
            else:
                status = "not-started"
            entry = {
                "id": item.get("id") or _subtask_id_for(module_id, title),
                "title": title,
                "status": status,
                "done": status == "done",  # 兼容前端老 JS 字段
            }
            # 可选字段透传 · code / docs 由 paths.py resolver 后续处理
            if "code" in item:
                entry["code"] = item["code"]
            if "docs" in item:
                entry["docs"] = item["docs"]
            out.append(entry)
        # 其他类型(int / None / 嵌套 list)忽略 · validator 会报 warn
    return out


def validate_subtask_schema(
    subtasks: list[dict],
    module_id: str,
    path: pathlib.Path,
) -> list[Issue]:
    """校验 normalize 后的 subtask 列表 · 不校 fs(path / code 由 paths.py 校).

    校:
    - id 唯一性(单 module 内) · error
    - status enum · error
    - title 存在 · error

    plan §6.1 决策的 fs-level 校验(code path 存在性 + 行号合法性)在
    `paths.py::_resolve_code_anchor()` 里走 · severity=warn · 不阻塞 build。
    """
    issues: list[Issue] = []
    seen_ids: set[str] = set()
    for i, sub in enumerate(subtasks):
        # title 必须有
        title = (sub.get("title") or "").strip()
        if not title:
            issues.append(Issue(
                "error", path, f"subtasks[{i}].title",
                "missing — subtask without title is invisible in drawer",
                suggestion="add `title: \"<one-line description>\"` to the subtask object",
                reference="docs-cockpit-author · §2.4 subtask schema",
            ))
            continue

        # id 唯一
        sub_id = sub.get("id") or ""
        if not sub_id:
            issues.append(Issue(
                "error", path, f"subtasks[{i}].id",
                f"missing id for `{title[:40]}` — localStorage status persistence will break",
                suggestion=f"add `id: \"{module_id}-S1\"` (or use normalize_subtasks auto-gen)",
                reference="docs-cockpit-author · §2.4 subtask schema",
            ))
        elif sub_id in seen_ids:
            issues.append(Issue(
                "error", path, f"subtasks[{i}].id",
                f"duplicate id `{sub_id}` — only the first will show in drawer",
                suggestion="rename one · ids must be unique within a module",
                reference="docs-cockpit-author · §2.4 subtask schema",
            ))
        else:
            seen_ids.add(sub_id)

        # status enum
        status = sub.get("status") or "not-started"
        if status not in VALID_SUBTASK_STATUSES:
            valid = " · ".join(sorted(VALID_SUBTASK_STATUSES))
            issues.append(Issue(
                "error", path, f"subtasks[{i}].status",
                f"unknown status `{status}` for `{title[:40]}`",
                suggestion=f"pick one of: {valid}",
                reference="docs-cockpit-author · §2.4 subtask schema",
            ))

    return issues
