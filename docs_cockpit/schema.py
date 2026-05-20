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
VALID_DOC_TYPES = {
    "module", "concept", "plan", "rfc", "spec", "memory", "roadmap",
    "sprint-plan",        # 0.19.0 · agile sprint plan(每个 sprint 一份 · 描述 backlog + DoR/DoD)
    "subtask-plan",       # 0.16.0 · per-subtask plan(复杂 subtask 必写)· 加这里让 validate_meta 不报 unknown
}


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


# ── 0.19.0 · sprint-plan schema + sprint-readiness lint ─────────────────
#
# 用户 Sourcery dogfood 反馈:24 个 module 都填了 `sprint: "0.7"` / `"M1.5.a"` ·
# 但没有任何一个文档描述「sprint 0.7 这个版本要做什么 · 做完算什么」· 版本
# 视角缺失。v0.19 引入 sprint-plan 一等公民 + DoR/DoD 校验门。
#
# 设计 spec · docs/plans/P-v0.19-agile-version-planning.md · §3 + §4。

# required:缺 → error(阻断 build)
_SPRINT_PLAN_REQUIRED_FIELDS = ("id", "type", "title", "status", "window", "goals")
# recommended:缺 → warn(允许 tooling-only sprint · 没动 module backlog)
_SPRINT_PLAN_RECOMMENDED_FIELDS = ("in_scope", "prd_refs", "dor", "dod")
_SPRINT_PLAN_OPTIONAL_FIELDS = (
    "progress", "out_of_scope", "docs", "retro", "desc", "owner",
    "depends_on", "blocks", "sprint", "prd_ref", "manualProgress", "updated_at",
)
_SPRINT_PLAN_STATUSES = frozenset({"planned", "in-progress", "done", "blocked"})


def _normalize_sprint_id(raw: str) -> str:
    """规整 sprint id · 兼容 `V0.19` / `0.19` / `v0.19` 三种写法 · 内部统一 `V0.19`."""
    if not isinstance(raw, str):
        return ""
    s = raw.strip()
    if not s:
        return ""
    if s[0] in ("V", "v"):
        s = s[1:]
    return "V" + s


def validate_sprint_plan(
    path: pathlib.Path, meta: dict
) -> list[Issue]:
    """v0.19.0 · 校验 sprint-plan 类型 doc 的 frontmatter schema.

    跟 validate_meta 分开 · 因为 sprint-plan 字段集跟 module / concept 完全不同 ·
    塞一个函数里 if-else 太脏。build.py 在识别 type=sprint-plan 时 dispatch 到本函数。
    """
    issues: list[Issue] = []
    if not isinstance(meta, dict):
        issues.append(
            Issue(
                severity="error",
                path=path,
                field="frontmatter",
                message="sprint-plan frontmatter must be a YAML dict",
                reference="docs-cockpit-author · §17 sprint-plan schema",
                category="sprint-schema",
            )
        )
        return issues

    # required fields · 缺 → error
    for f in _SPRINT_PLAN_REQUIRED_FIELDS:
        if f not in meta or meta[f] in (None, "", [], {}):
            issues.append(
                Issue(
                    severity="error",
                    path=path,
                    field=f,
                    message=f"sprint-plan missing required field `{f}`",
                    suggestion=(
                        f"add `{f}` to frontmatter · see template at "
                        f"`docs_cockpit/templates/sprint-plan.md.j2`"
                    ),
                    reference="docs-cockpit-author · §17 sprint-plan schema",
                    category="sprint-schema",
                )
            )
    # recommended fields · 区分两种情况:
    #   - 字段没出现(用户忘了)→ warn
    #   - 字段在但值是 None / "" / {} → warn
    #   - 字段在且值是 explicit empty list [] → OK(用户显式声明 tooling sprint · 看过了决定空)
    for f in _SPRINT_PLAN_RECOMMENDED_FIELDS:
        if f not in meta:
            missing = True
        else:
            v = meta[f]
            # explicit empty list 视为用户已 review · 不报警
            missing = v is None or v == "" or v == {}
        if missing:
            issues.append(
                Issue(
                    severity="warn",
                    path=path,
                    field=f,
                    message=(
                        f"sprint-plan missing recommended `{f}` · "
                        f"tooling sprint 可显式 `{f}: []` 标记已 review"
                    ),
                    suggestion=(
                        f"see template `docs_cockpit/templates/sprint-plan.md.j2` · "
                        f"`{f}` semantics defined in author skill §17"
                    ),
                    reference="docs-cockpit-author · §17 sprint-plan schema",
                    category="sprint-schema",
                )
            )

    # status enum
    status = meta.get("status")
    if status is not None and status not in _SPRINT_PLAN_STATUSES:
        issues.append(
            Issue(
                severity="error",
                path=path,
                field="status",
                message=(
                    f"sprint-plan.status={status!r} invalid · must be one of "
                    f"{sorted(_SPRINT_PLAN_STATUSES)}"
                ),
                reference="docs-cockpit-author · §17 sprint-plan schema",
                category="sprint-schema",
            )
        )

    # in_scope must be list of {module, subtasks?}
    in_scope = meta.get("in_scope")
    if in_scope is not None:
        if not isinstance(in_scope, list):
            issues.append(
                Issue(
                    severity="error",
                    path=path,
                    field="in_scope",
                    message=f"in_scope must be a list · got {type(in_scope).__name__}",
                    category="sprint-schema",
                )
            )
        else:
            for i, entry in enumerate(in_scope):
                if not isinstance(entry, dict):
                    issues.append(
                        Issue(
                            severity="error",
                            path=path,
                            field=f"in_scope[{i}]",
                            message=f"each in_scope entry must be a dict · got {type(entry).__name__}",
                            category="sprint-schema",
                        )
                    )
                    continue
                if not isinstance(entry.get("module"), str) or not entry.get("module").strip():
                    issues.append(
                        Issue(
                            severity="error",
                            path=path,
                            field=f"in_scope[{i}].module",
                            message="in_scope entry missing required string `module` field",
                            category="sprint-schema",
                        )
                    )
                subs = entry.get("subtasks")
                if subs is not None and not isinstance(subs, list):
                    issues.append(
                        Issue(
                            severity="error",
                            path=path,
                            field=f"in_scope[{i}].subtasks",
                            message=(
                                f"subtasks must be a list of subtask id strings · "
                                f"got {type(subs).__name__}"
                            ),
                            category="sprint-schema",
                        )
                    )

    # dor / dod at least 1 item each (warn · not error · 给老 sprint-plan 兼容空)
    for f in ("dor", "dod"):
        if f in meta and isinstance(meta[f], list) and not meta[f]:
            issues.append(
                Issue(
                    severity="warn",
                    path=path,
                    field=f,
                    message=f"sprint-plan.{f} is empty · at least 1 item recommended",
                    suggestion=(
                        f"see template · {f} = Definition of "
                        f"{'Ready (DoR · 开干前条件)' if f == 'dor' else 'Done (DoD · 完成标准)'}"
                    ),
                    reference="docs-cockpit-author · §17 sprint-plan schema",
                    category="sprint-schema",
                )
            )

    return issues


def lint_sprint_readiness(
    modules: list[dict] | None,
    sprint_plans: list[dict] | None,
    enforce: bool = False,
) -> list[Issue]:
    """v0.19.0 · sprint-readiness DoR 校验.

    对每个 status=planned 或 in-progress 的 sprint-plan 跑两组校验:
      A) 需求对齐 · 每个 in_scope subtask 有 prd_ref 或 @docs anchor 指向 prd_refs
      B) LLM 参考文档 · 每个 in_scope subtask 有 @code 或 @docs anchor

    `enforce=False` 默认 · 只对显式存在 sprint-plan 的 sprint 报 issue
    `enforce=True`(yaml `project.enforce_sprint_plans: true`)· 任何 module.sprint
                  没对应 sprint-plan 也报 warn(强制规范化)

    Reference · author skill §17。
    """
    out: list[Issue] = []
    if not sprint_plans:
        return out

    # build module / subtask 索引(by id)便于查 in_scope 反查
    module_by_id: dict[str, dict] = {}
    if modules:
        for m in modules:
            mid = m.get("id")
            if mid:
                module_by_id[mid] = m

    for sp in sprint_plans:
        meta = sp.get("meta") or {}
        path = pathlib.Path(sp.get("path") or "sprint-plan.md")
        sprint_id = meta.get("id") or path.stem
        status = meta.get("status", "")
        if status not in ("planned", "in-progress"):
            continue  # done / blocked sprint · 不跑 readiness

        prd_refs = meta.get("prd_refs") or []
        prd_paths = {
            r.get("path", "").strip()
            for r in prd_refs
            if isinstance(r, dict) and r.get("path")
        }

        for entry in meta.get("in_scope") or []:
            if not isinstance(entry, dict):
                continue
            mid = entry.get("module", "")
            if not mid:
                continue
            module = module_by_id.get(mid)
            if module is None:
                out.append(
                    Issue(
                        severity="warn",
                        path=path,
                        field=f"in_scope.module={mid}",
                        message=(
                            f"sprint {sprint_id} 引用的 module `{mid}` 在 state.json 找不到 · "
                            f"是不是 module id typo · 或者还没 build?"
                        ),
                        suggestion="跑 `docs-cockpit build` 后再 `docs-cockpit sprint check`",
                        reference="docs-cockpit-author · §17 sprint-readiness",
                        category="sprint-readiness",
                    )
                )
                continue

            # 拿目标 subtask 集合 · 不指定 = 整个 module 所有 subtask
            target_subs = entry.get("subtasks") or []
            all_subs = module.get("subtasks") or []
            subs_by_id = {s.get("id"): s for s in all_subs if s.get("id")}

            if target_subs:
                checking = []
                for sid in target_subs:
                    if sid in subs_by_id:
                        checking.append(subs_by_id[sid])
                    else:
                        out.append(
                            Issue(
                                severity="warn",
                                path=path,
                                field=f"in_scope.module={mid}.subtasks={sid}",
                                message=(
                                    f"sprint {sprint_id} 引用的 subtask `{sid}` 在 "
                                    f"module `{mid}` 找不到 · title 改了导致 id 漂移?"
                                ),
                                suggestion=(
                                    f"看 `docs-cockpit prompt {mid}` 列出 module 内所有 "
                                    f"subtask · 找对应 id 修正本 sprint-plan"
                                ),
                                reference="docs-cockpit-author · §17 sprint-readiness",
                                category="sprint-readiness",
                            )
                        )
            else:
                checking = all_subs

            for sub in checking:
                sid = sub.get("id", "?")
                title_snippet = (sub.get("title") or "").strip()[:60]
                has_code = bool(sub.get("code_anchors")) or bool(sub.get("code"))
                has_docs = bool(sub.get("doc_anchors")) or bool(sub.get("docs"))

                # 校验 B) LLM 参考文档 · 至少一边 anchor
                if not has_code and not has_docs:
                    out.append(
                        Issue(
                            severity="warn",
                            path=path,
                            field=f"in_scope.module={mid}.subtask={sid}",
                            message=(
                                f"sprint {sprint_id} · subtask `{sid}` ({title_snippet!r}) "
                                f"既无 @code 也无 @docs · LLM 开干时拿不到上下文 · DoR 未满足"
                            ),
                            suggestion=(
                                f"给 subtask 加 @code:path/file.py:N-M 跟 / 或 "
                                f"@docs:path.md#§N · 或跑 `docs-cockpit verify {mid}`"
                            ),
                            reference="docs-cockpit-author · §17 sprint-readiness (大模型参考文档)",
                            category="sprint-readiness",
                        )
                    )

                # 校验 A) 需求对齐 · 看 subtask 是否能 trace 到 prd_refs
                if prd_paths:
                    # 拿 subtask 的 docs anchor target paths
                    docs_paths: set[str] = set()
                    for da in sub.get("doc_anchors") or []:
                        if isinstance(da, dict):
                            p = da.get("path") or da.get("raw")
                            if p:
                                # 提取 path · 去掉 #§N anchor / :line 部分
                                docs_paths.add(_strip_anchor_suffix(p))
                    for d in sub.get("docs") or []:
                        if isinstance(d, str):
                            docs_paths.add(_strip_anchor_suffix(d))

                    # 也接受 subtask.prd_ref 字段(rare · subtask 级显式 PRD 引用)
                    if sub.get("prd_ref"):
                        docs_paths.add("__has_prd_ref__")

                    aligned = "__has_prd_ref__" in docs_paths or any(
                        any(p in dp or dp in p for dp in docs_paths)
                        for p in prd_paths if p
                    )
                    if not aligned:
                        out.append(
                            Issue(
                                severity="warn",
                                path=path,
                                field=f"in_scope.module={mid}.subtask={sid}",
                                message=(
                                    f"sprint {sprint_id} · subtask `{sid}` 没 trace 到 "
                                    f"prd_refs 任何一条 · 需求对齐 DoR 未满足"
                                ),
                                suggestion=(
                                    f"在 subtask 加 @docs anchor 指向 sprint-plan.prd_refs "
                                    f"里列的 PRD/RFC · 例:@docs:" + (next(iter(prd_paths)) if prd_paths else "docs/PRD/...")
                                ),
                                reference=(
                                    "docs-cockpit-author · §17 sprint-readiness (需求对齐)"
                                ),
                                category="sprint-readiness",
                            )
                        )

        # 校验 prd_refs 文件本身存在
        for r in prd_refs:
            if not isinstance(r, dict):
                continue
            ref_path = (r.get("path") or "").strip()
            if not ref_path:
                continue
            # 用 path 自己判断是否在 file system(这里只接 relative path · 不解析 vars)
            ref_resolved = pathlib.Path(ref_path)
            if not ref_resolved.is_absolute():
                # 走 sprint-plan 文件相对 repo root 推断 · path 已存 build 时的 string
                # 这里粗略检查 · build 时已被 resolve_doc_path 处理过的 anchor 是绝对路径
                # 用户手写的 prd_refs.path 可能相对 · 这里跳过 strict 校验避免误报
                continue
            if not ref_resolved.exists():
                out.append(
                    Issue(
                        severity="warn",
                        path=path,
                        field="prd_refs",
                        message=(
                            f"sprint {sprint_id} · prd_refs path `{ref_path}` 找不到文件 · "
                            f"链路断了"
                        ),
                        suggestion="检查 path 是否拼错 · 或者文件改名后没更新",
                        reference="docs-cockpit-author · §17 sprint-readiness",
                        category="sprint-readiness",
                    )
                )

    # enforce mode · module.sprint 没对应 sprint-plan 也报警
    if enforce and modules:
        known_sprint_ids = {
            _normalize_sprint_id((sp.get("meta") or {}).get("id", "") or "")
            for sp in sprint_plans
        }
        seen_orphans: set[str] = set()
        for m in modules:
            ms = (m.get("sprint") or "").strip()
            if not ms:
                continue
            normalized = _normalize_sprint_id(ms)
            if normalized in known_sprint_ids or normalized in seen_orphans:
                continue
            seen_orphans.add(normalized)
            out.append(
                Issue(
                    severity="warn",
                    path=pathlib.Path(m.get("path") or m.get("id", "module") + ".md"),
                    field=f"sprint={ms}",
                    message=(
                        f"module 引用 sprint `{ms}` · 但 docs/plans/ 找不到 "
                        f"对应 sprint-plan(enforce_sprint_plans=true)"
                    ),
                    suggestion=f"跑 `docs-cockpit sprint init {ms}` scaffold 一份",
                    reference="docs-cockpit-author · §17 sprint-readiness (enforce)",
                    category="sprint-readiness",
                )
            )

    return out


def _strip_anchor_suffix(path_str: str) -> str:
    """剥掉 anchor 后缀 · `path.md#§3.1` → `path.md` · `path.py:42-89` → `path.py`."""
    if not isinstance(path_str, str):
        return ""
    # 优先 split 第一个 # (heading anchor)
    if "#" in path_str:
        path_str = path_str.split("#", 1)[0]
    # 再 split 最后一个 `:`(line range · 但不能误伤 `docs/foo:bar/x.py`)
    # 用 regex: `:<digits>[-<digits>]$` 才剥
    m = re.search(r":(\d+(?:-\d+)?)\s*$", path_str)
    if m:
        path_str = path_str[: m.start()]
    return path_str.strip()


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
