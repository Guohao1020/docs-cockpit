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

    category(v0.18.0+ · 默认空串向后兼容)· 给 cmd_lint --include / --exclude 用 ·
    每条 lint 落 1 个稳定 string ID · 跟 message 文本解耦:
      frontmatter-schema    · validate_meta 出的所有 schema 校验(id / status / progress / etc)
      title-has-anchor      · lint_subtask_titles · title 含 §N.M / 文件路径
      doc-lang-mix          · lint_subtask_titles · title 跨 project_lang 界混 prose
      subtask-missing-anchors · lint_subtask_anchors · subtask 0 anchor
      prompt-template       · cmd_lint --prompts · Jinja2 syntax error
      (老 Issue 默认空 category · CLI 显示为 'uncategorized' · 不影响 filter)
    """

    __slots__ = ("severity", "path", "field", "message", "suggestion", "reference", "category")

    def __init__(
        self,
        severity: str,
        path: pathlib.Path,
        field: str,
        message: str,
        suggestion: str = "",
        reference: str = "",
        category: str = "",
    ):
        self.severity = severity
        self.path = path
        self.field = field
        self.message = message
        self.suggestion = suggestion
        self.reference = reference
        self.category = category

    def as_dict(self) -> dict:
        return {
            "severity": self.severity,
            "path": str(self.path),
            "field": self.field,
            "message": self.message,
            "suggestion": self.suggestion,
            "reference": self.reference,
            "category": self.category,
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


# ── 0.16.0 · doc_language detect + subtask title lint ───────────────────
#
# 用户反馈 · subtask title 中英混 / 含 §N.M 编号 / 含文件名 · 不读
# 治理走 author skill §16(规则)+ python lint(detect)二段。这里是 detect 部分。

# CJK Unicode 范围(简体 / 繁体 / 日韩共用 ideograph + 汉字补充)
_CJK_RE = re.compile(
    r"[一-鿿"      # CJK Unified Ideographs
    r"㐀-䶿"        # CJK Extension A
    r"豈-﫿"        # CJK Compatibility
    r"　-〿"        # CJK Symbols and Punctuation(中文标点)
    r"＀-￯"        # Halfwidth/Fullwidth Forms
    r"]"
)

# title 里出现下面任一 · 报 title-has-anchor(应走 anchor 字段不是 title):
#   §1 / §1.2 / §1.2.3            heading 编号引用
#   foo/bar.md  / foo.py:42-89    文件路径 / 行号
#   function_name() / Class.foo   函数 / 方法标识(下划线 + 大写驼峰是 hint)
_ANCHOR_IN_TITLE_RE = re.compile(
    r"§\d+(?:\.\d+)*"            # §1.2 类编号
    r"|[\w\-./]+\.(?:md|py|ts|js|tsx|jsx|yaml|yml|toml|json|sql)"  # 文件路径
    r"|:\d+(?:-\d+)?\b"          # :42 / :42-89 line range
    r"|\b[a-z_][a-z_0-9]+\(\)"   # function_name() · snake_case
)

# 技术 token 白名单 · 不参与中英混判定(这些是 cross-lingual 通用术语)
_TECH_TOKEN_WHITELIST = {
    "API", "CLI", "MCP", "RFC", "HTTP", "HTTPS", "URL", "URI", "JSON", "YAML",
    "TOML", "XML", "HTML", "CSS", "JS", "TS", "MD", "PDF", "PNG", "JPG", "GIF",
    "REST", "GraphQL", "gRPC", "OAuth", "JWT", "SSO", "RBAC", "ACL",
    "SDK", "IDE", "OS", "CPU", "GPU", "RAM", "SSD", "I/O", "DB", "SQL",
    "TDD", "BDD", "CI", "CD", "PR", "MR", "DSL", "ORM",
    "AI", "ML", "LLM", "NLP", "CV", "RL", "ETA", "TTL",
    "Claude", "Cursor", "Codex", "Continue", "Aider", "GPT", "Anthropic", "OpenAI",
    "GitHub", "GitLab", "git", "Linux", "macOS", "Windows", "Mac",
    "Python", "TypeScript", "JavaScript", "Rust", "Go", "Java", "Ruby",
    "Postgres", "MySQL", "SQLite", "Redis", "Kafka", "Docker",
    "TODO", "FIXME", "XXX",  # 编码注释惯用
}

_LATIN_WORD_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_-]+\b")

# 0.16.0 · English prose 词 · 出现 = 真混 prose · 不是 loanword
# 中文技术写作里 loanword(server / stdio / runtime / pool / proxy)算正常·
# prose 词(the / of / and / is / implement / when / which)算混
_ENGLISH_PROSE_WORDS = frozenset({
    # 冠词 / 限定词
    "the", "a", "an", "this", "that", "these", "those",
    # 介词
    "of", "to", "in", "on", "at", "by", "for", "with", "from", "into", "onto",
    "through", "between", "across", "after", "before", "during",
    # 连词
    "and", "or", "but", "nor", "yet", "so", "as",
    # 代词
    "it", "its", "this", "we", "they", "their", "them", "you", "your", "i",
    # be 动词
    "is", "are", "was", "were", "be", "been", "being", "am",
    # 助动词
    "do", "does", "did", "have", "has", "had", "will", "would",
    "can", "could", "should", "may", "might", "must",
    # 否定 / 副词
    "not", "no", "yes", "very", "more", "less", "much", "many", "few",
    # 常见 prose 动词(非技术名词)
    "implement", "implements", "implementing", "implemented",
    "when", "which", "while", "where", "whether", "if",
    "make", "makes", "made", "making",
    "use", "uses", "used", "using",
    "ensure", "ensures", "verify", "verifies",
})


def detect_doc_language(modules: list[dict] | None) -> str:
    """启发式 detect 项目主语言 · 看 module title 的 CJK 字符占比.

    > 30% CJK → "zh-CN" · else "en"。空 / 不确定 → "en"(英文默认)。
    """
    if not modules:
        return "en"
    cjk_chars = 0
    total_chars = 0
    for m in modules:
        title = (m.get("title") or "")
        for ch in title:
            if ch.isspace() or not ch.isprintable():
                continue
            total_chars += 1
            if _CJK_RE.match(ch):
                cjk_chars += 1
    if total_chars == 0:
        return "en"
    return "zh-CN" if (cjk_chars / total_chars) > 0.30 else "en"


def _has_mixed_language(title: str, project_lang: str) -> bool:
    """判 title 是否中英混(超出 project_lang 锁定范围).

    zh-CN project · title 含 CJK + 任一 English prose 词(the / of / and / when / implement
                   等)→ mixed。技术 loanword(server / stdio / runtime / pool · 即使
                   不在白名单)不算混 · 这是自然中文-技术写作惯例。
    en project    · title 含 CJK 字符 → mixed
    """
    if not title:
        return False
    has_cjk = bool(_CJK_RE.search(title))

    if project_lang == "zh-CN":
        # 看是否有 English prose 词 · 是 = mixed prose · 否 = loanword 算正常
        latin_words = [
            w.lower() for w in _LATIN_WORD_RE.findall(title)
            if w not in _TECH_TOKEN_WHITELIST and not w.isdigit()
        ]
        has_prose_word = any(w in _ENGLISH_PROSE_WORDS for w in latin_words)
        return has_cjk and has_prose_word
    elif project_lang == "en":
        # en project · 不允许 title 含 CJK
        return has_cjk
    return False


def _title_has_anchor_ref(title: str) -> tuple[bool, str]:
    """判 title 是否含 anchor 信息(§N / 文件名 / 行号 / 函数名).

    Returns (offending: bool, sample: str) · sample 是命中的具体片段 · 报错给参考。
    """
    if not title:
        return False, ""
    m = _ANCHOR_IN_TITLE_RE.search(title)
    if m:
        return True, m.group(0)
    return False, ""


def lint_subtask_titles(
    modules: list[dict] | None,
    project_lang: str,
) -> list[Issue]:
    """v0.16.0 · 给 build_payload 调 · 出 2 类新 Issue:
        - doc-lang-mix  warn   · title 跨 project_lang 界混语言
        - title-has-anchor warn · title 含 anchor 信息(应走 code/docs 字段)

    Reference · 都指向 author skill §16(本 sprint 新加)。
    """
    out: list[Issue] = []
    if not modules:
        return out
    for m in modules:
        mid = m.get("id", "?")
        mpath_str = m.get("path") or ""
        mpath = pathlib.Path(mpath_str) if mpath_str else pathlib.Path(mid + ".md")
        for sub in m.get("subtasks") or []:
            sid = sub.get("id", "?")
            title = (sub.get("title") or "").strip()
            if not title:
                continue
            # 1) language mix check
            if _has_mixed_language(title, project_lang):
                out.append(
                    Issue(
                        severity="warn",
                        path=mpath,
                        field=f"subtasks[{sid}].title",
                        message=(
                            f"title mixes languages outside project doc_language={project_lang!r}: "
                            f"{title!r}"
                        ),
                        suggestion=(
                            "Rewrite in a single language matching project.doc_language · "
                            "tech tokens like 'API' / 'MCP' / 'CLI' are whitelist-OK"
                        ),
                        reference="docs-cockpit-author · §16.2 title style 黄金法则",
                        category="doc-lang-mix",
                    )
                )
            # 2) anchor-in-title check
            offending, sample = _title_has_anchor_ref(title)
            if offending:
                out.append(
                    Issue(
                        severity="warn",
                        path=mpath,
                        field=f"subtasks[{sid}].title",
                        message=(
                            f"title contains anchor-like ref {sample!r} · "
                            f"these belong in `code:` / `docs:` fields not title"
                        ),
                        suggestion=(
                            "Move §N / file paths / line numbers / function names to "
                            "code_anchors[].path or doc_anchors[].raw · title should say WHAT user gets"
                        ),
                        reference="docs-cockpit-author · §16.2 title style 黄金法则",
                        category="title-has-anchor",
                    )
                )
    return out


def lint_subtask_anchors(modules: list[dict] | None) -> list[Issue]:
    """v0.17.0 · 给 build_payload 调 · 出 1 类新 Issue:
        - subtask-missing-anchors warn · subtask 既无 @code: 也无 @docs: annotation

    用户反馈(0.16.0 dogfood 之后):lint 只看 title style · 不看 anchor 数量 ·
    导致 M01 「3 个 subtask · 0 anchor」这种空架子 build 不报警 · LLM 跟用户拉不到上下文。

    阈值:`code_anchors` + `doc_anchors` 同时为空才报警。任有一边 = 有上下文锚点 ·
    不报警(允许 doc-only / code-only subtask)。

    Reference · 指向 author skill §16.3 anchor 完整性 SOP。
    """
    out: list[Issue] = []
    if not modules:
        return out
    for m in modules:
        mid = m.get("id", "?")
        mpath_str = m.get("path") or ""
        mpath = pathlib.Path(mpath_str) if mpath_str else pathlib.Path(mid + ".md")
        for sub in m.get("subtasks") or []:
            sid = sub.get("id", "?")
            # 同时支持新(code_anchors / doc_anchors object list)跟老(code / docs 字符串 list)schema
            has_code = bool(sub.get("code_anchors")) or bool(sub.get("code"))
            has_docs = bool(sub.get("doc_anchors")) or bool(sub.get("docs"))
            if not has_code and not has_docs:
                title_snippet = (sub.get("title") or "").strip()[:60] or "(空 title)"
                out.append(
                    Issue(
                        severity="warn",
                        path=mpath,
                        field=f"subtasks[{sid}].anchors",
                        message=(
                            f"subtask 既无 @code: 也无 @docs: annotation · "
                            f"LLM 跟用户都拉不到上下文 · title={title_snippet!r}"
                        ),
                        suggestion=(
                            f"在 body checklist 行末加 @code:path/file.py:N-M 跟 / 或 @docs:path.md#§N.M · "
                            f"或跑 `docs-cockpit verify {mid}` 让 LLM 帮你诊断 + 建议补什么 anchor"
                        ),
                        reference="docs-cockpit-author · §16.6 anchor 完整性 SOP + LLM verify",
                        category="subtask-missing-anchors",
                    )
                )
    return out



# ── MD body section detection (0.4.0 · frontmatter 缺字段时从正文提取) ──
#
# 用户常常已经在 MD body 里维护 `## 待办` + `- [ ]` checklist 或 `## 关联`
# section 列相关文档 link · 但 frontmatter 没有 subtasks/docs 字段。这里
# 提供 fallback:frontmatter 缺这俩字段时 · 扫 body 自动提。
#
# 优先级:frontmatter 字段 > body 提取。用户想精控直接写 frontmatter 接管。

# 0.14.3 M12 · regex 放宽接受 § 前缀 / 三级 heading / tab 空格
# 旧:`^##\s+(?:\d+\s*[·.\-]?\s*)?(?:待办|TODO|...)\b` 只接 `## 3 · 待办` / `## 待办`
# 新:`^#{2,6}[\s\t]+(?:[§\d]+[\s\t]*[·.\-]?[\s\t]*)?(?:待办|TODO|...)\b`
#   ## §4 · 待办 / ### 待办 / ##\t待办 / ## §3.2 · 待办 都接受
# M08/M09/M10 dogfood 实拍踩过 · 之前 work around 是手工去 § 前缀
_SUBTASK_SECTION_RE = re.compile(
    r"^#{2,6}[\s\t]+(?:[§\d][§\d.]*\s*[·.\-]?[\s\t]*)?(?:待办|TODO|To[- ]?do|Subtasks?|Tasks?|任务)\b",
    re.MULTILINE | re.IGNORECASE,
)
_DOCS_SECTION_RE = re.compile(
    r"^#{2,6}[\s\t]+(?:[§\d][§\d.]*\s*[·.\-]?[\s\t]*)?"
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

    # ── 0.11.0-alpha.4:status × subtasks 一致性(用户实测反馈)──
    # 用户能写 `status: done` 但 subtasks 还有 [ ] 未做 · validator 不报 ·
    # dashboard 显示"已完成"但子任务列表 3/9 · 这是数据完整性漏洞。
    # 这里把 status 跟 subtasks 实际比例对一遍。
    raw_subtasks = meta.get("subtasks") or []
    if isinstance(raw_subtasks, list) and raw_subtasks:
        # 统一算法 · 兼容 v0.10 list[str] / list[dict{title,done}] / v0.11 list[dict{status}]
        sub_total = 0
        sub_done = 0
        for s in raw_subtasks:
            if isinstance(s, str):
                sub_total += 1
                # str 默认 not-started · 不算 done
            elif isinstance(s, dict):
                sub_total += 1
                # status 优先 · 没 status 看 done · 都没默认 not-started
                sub_status = s.get("status")
                if sub_status == "done":
                    sub_done += 1
                elif sub_status is None and s.get("done") is True:
                    sub_done += 1
        if sub_total > 0:
            if status == "done" and sub_done < sub_total:
                issues.append(Issue(
                    "warn", path, "status",
                    f"status=`done` but subtasks {sub_done}/{sub_total} done · 数据不一致",
                    suggestion=(
                        f"把剩余 {sub_total - sub_done} 个 subtask 勾上 · 或把 module status 调回 in-progress"
                    ),
                    reference="docs-cockpit-author · §2.3 status × subtasks invariants",
                ))
            elif status == "not-started" and sub_done > 0:
                issues.append(Issue(
                    "warn", path, "status",
                    f"status=`not-started` but {sub_done}/{sub_total} subtask(s) already done",
                    suggestion="bump status to `in-progress` to reflect actual state",
                    reference="docs-cockpit-author · §2.3 status × subtasks invariants",
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
