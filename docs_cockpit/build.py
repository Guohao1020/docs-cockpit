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
    VALID_SUBTASK_STATUSES,
    detect_doc_language,
    extract_docs_from_body,
    extract_subtasks_from_body,
    lint_subtask_anchors,
    lint_subtask_titles,
    normalize_subtasks,
    slugify,
    split_frontmatter,
    validate_meta,
    validate_subtask_schema,
)
# 0.11.0-alpha.1 / 0.11.0-alpha.2:path / fs IO / docs path resolution / W1 code anchor
#   (plan-eng-review 1A · build.py 减肥)
from .paths import (
    _build_vars,
    _expand,
    _resolve_and_embed_docs,
    _resolve_code_anchor,
    _resolve_subtask_doc_anchor,
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
        # 0.11.0-alpha.2:W1 schema · normalize 为对象数组 · 每条至少含
        # {id, title, status} · 可选 {code, docs} · plan §6.1
        module_id = meta.get("id") or "X"
        subtasks = normalize_subtasks(subtasks or [], module_id)
        # 0.11.0-alpha.2:W1 schema 校验 · 给 issues 列表追加 subtask 级 issues
        if path and meta.get("id"):
            _subtask_issues = validate_subtask_schema(subtasks, module_id, path)
            # _subtask_issues 在外层 _build_card_list 那里聚合 · 通过 caller 处理
            # 这里 attach 到 card 上 · _build_card_list iterates 时摘出来
            card["_pending_issues"] = _subtask_issues
        # 0.11.0-alpha.2:W1 code anchor · resolve subtask 的 code 字段 · plan §6.1
        # 每条 subtask 的 code 字段可能是 string 或 list[string] · 都 normalize 为
        # list[dict] · 含 path / lines / resolved / exists / preview / vscode_url / warning
        if vars_ and path:
            repo_root = pathlib.Path(vars_.get("repo", "."))
            for sub in subtasks:
                raw_code = sub.get("code")
                if not raw_code:
                    continue
                if isinstance(raw_code, str):
                    raw_code_list = [raw_code]
                elif isinstance(raw_code, list):
                    raw_code_list = [str(c) for c in raw_code if c]
                else:
                    continue
                sub["code_anchors"] = [
                    _resolve_code_anchor(c, path, repo_root, vars_)
                    for c in raw_code_list
                ]
            # 0.11.0-alpha.8:subtask docs anchor · path[:lines] / path#heading
            # 解析切片 · 给前端 marked.js 右栏渲染用(UI 缺口修复 · plan §6.6)
            for sub in subtasks:
                raw_docs = sub.get("docs")
                if not raw_docs:
                    continue
                if isinstance(raw_docs, str):
                    raw_docs_list = [raw_docs]
                elif isinstance(raw_docs, list):
                    raw_docs_list = [str(d) for d in raw_docs if d]
                else:
                    continue
                sub["doc_anchors"] = [
                    _resolve_subtask_doc_anchor(d, path, repo_root, vars_)
                    for d in raw_docs_list
                ]
        card["subtasks"] = subtasks

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
            # 0.11.0-alpha.2:摘出 _build_card 收集的 subtask 校验 issues 合到主列表
            if fm_enabled and "_pending_issues" in card:
                issues.extend(card.pop("_pending_issues"))
            out.append(card)
    return out


# 0.11.0-alpha.6:systemDocs 单 doc content hard cap(plan §6.7)
# 比 module docs 的 100KB 严格 · 防 memory 目录 / 大 spec 撑爆主 HTML
_MAX_SYSDOC_EMBED_BYTES = 50 * 1024  # 50KB


def _build_aliases(
    entries: list[dict] | None,
    vars_: dict[str, str],
    repo_root: pathlib.Path,
) -> list[dict]:
    """v0.15.0 · 读 yaml `aliases:` block · 把外部已生成的 plan/RFC/spec 文档(来自
    superpowers `docs/superpowers/plans/...` · gstack `~/.gstack/projects/...` · 或
    其它工具的散落位置)以 docs-cockpit canonical 命名注册进 systemDocs[] · 文件
    原地不动 · 只覆盖显示名 + 元数据。

    每条 entry 形如:
        - canonical_id: "P-v0.15-driver-seat-next"
          canonical_type: "plan"   # plan / rfc / spec / concept-doc · 当前都落 systemDocs
          source: "docs/superpowers/plans/2026-05-20-mcp.md"
          title: "v0.15 driver-seat 续作"      # 覆盖原 H1
          desc:  "..."
          icon:  "plan"

    解析:支持 `{home}` / `{repo}` / `{env:X}` 变量 · 跟 system_docs 一致 · 三步路径
    fallback(absolute → relative to config → relative to home)· embed body content
    · 50KB cap 跟 system_docs 一致。

    Returns:list of card dicts · 直接 extend 到 payload['systemDocs'] · 不进 modules
    Kanban(canonical_type=module/concept 留 v0.16 候选 · 当前 MVP 只支持 doc-style)。
    """
    if not entries:
        return []
    out: list[dict] = []
    for entry in entries:
        canonical_id = entry.get("canonical_id") or entry.get("id") or ""
        if not canonical_id:
            continue
        raw_source = entry.get("source") or entry.get("path") or ""
        expanded = _expand(raw_source, vars_)
        item = {
            "id": canonical_id,
            "title": entry.get("title", "") or canonical_id,
            "path": expanded,
            "desc": entry.get("desc", ""),
            "icon": entry.get("icon")
            or _icon_for_canonical_type(entry.get("canonical_type", "doc")),
            "content": "",
            "mtime": None,
            "exists": False,
            # 0.15.0 · alias 专属元数据 · 给 rebuild skill / CI 等 state.json 消费者读
            "alias": True,
            "canonical_type": entry.get("canonical_type", "doc"),
            "source_path": raw_source,
        }
        if not expanded:
            out.append(item)
            continue
        p = pathlib.Path(expanded)
        # 三步 path fallback(对齐 _resolve_doc_path)
        if not p.is_absolute() and not p.exists():
            for base in (repo_root, pathlib.Path.home()):
                cand = (base / p).resolve()
                if cand.exists():
                    p = cand
                    break
        if not p.exists():
            out.append(item)
            continue
        item["exists"] = True
        item["path"] = str(p)
        try:
            stat = p.stat()
            item["mtime"] = _dt.datetime.fromtimestamp(stat.st_mtime).strftime(
                "%Y-%m-%d %H:%M"
            )
            if p.is_file() and p.suffix.lower() in (".md", ".markdown"):
                raw_text = p.read_text(encoding="utf-8", errors="replace")
                _, body = split_frontmatter(raw_text)
                body_bytes = body.encode("utf-8")
                if len(body_bytes) <= _MAX_SYSDOC_EMBED_BYTES:
                    item["content"] = body
                else:
                    truncated = body_bytes[:_MAX_SYSDOC_EMBED_BYTES].decode(
                        "utf-8", errors="replace"
                    )
                    kb = len(body_bytes) // 1024
                    item["content"] = (
                        truncated
                        + f"\n\n---\n\n*[Content truncated · body is {kb} KB · "
                        f"embed limit {_MAX_SYSDOC_EMBED_BYTES // 1024} KB. "
                        f"Open the file directly to read the rest.]*\n"
                    )
        except (OSError, UnicodeError):
            pass
        out.append(item)
    return out


def _icon_for_canonical_type(ct: str) -> str:
    """canonical_type → icon 默认映射 · 给 alias entry 用."""
    return {
        "plan": "plan",
        "rfc": "doc",
        "spec": "doc",
        "concept-doc": "design",
        "memory": "memory",
        "roadmap": "plan",
    }.get(ct, "doc")


def _build_system_docs(
    entries: list[dict] | None, vars_: dict[str, str], repo_root: pathlib.Path
) -> list[dict]:
    """system_docs: 手挑列表 · 展开 path 变量 · embed MD content.

    0.11.0-alpha.6 (plan §6.7):给每条 system_doc 加 content/mtime/exists 字段
    · 让 split-view 右栏能直接 marked.js 渲染 · 不再走 `<a target="_blank">`
    新窗口 dump raw text。

    单 doc content hard cap 50KB(`_MAX_SYSDOC_EMBED_BYTES`) · 超过截断 + 提示
    · 防止 memory / 长 spec 撑爆主 HTML payload。
    """
    if not entries:
        return []
    out: list[dict] = []
    for entry in entries:
        raw_path = entry.get("path", "")
        expanded = _expand(raw_path, vars_)
        item = {
            "id": entry.get("id") or slugify(entry.get("title", "")),
            "title": entry.get("title", ""),
            "path": expanded,
            "desc": entry.get("desc", ""),
            "icon": entry.get("icon", "doc"),
            "content": "",
            "mtime": None,
            "exists": False,
        }
        if not expanded:
            out.append(item)
            continue
        p = pathlib.Path(expanded)
        if not p.exists():
            out.append(item)
            continue
        item["exists"] = True
        try:
            stat = p.stat()
            item["mtime"] = _dt.datetime.fromtimestamp(stat.st_mtime).strftime(
                "%Y-%m-%d %H:%M"
            )
            # 只 embed .md / .markdown 文件 · 其他扩展不读
            if p.is_file() and p.suffix.lower() in (".md", ".markdown"):
                raw_text = p.read_text(encoding="utf-8", errors="replace")
                # 剥掉 YAML frontmatter · 避免 marked 渲染成 raw text 块
                _, body = split_frontmatter(raw_text)
                body_bytes = body.encode("utf-8")
                if len(body_bytes) <= _MAX_SYSDOC_EMBED_BYTES:
                    item["content"] = body
                else:
                    truncated = body_bytes[:_MAX_SYSDOC_EMBED_BYTES].decode(
                        "utf-8", errors="replace"
                    )
                    kb = len(body_bytes) // 1024
                    item["content"] = (
                        truncated
                        + f"\n\n---\n\n*[Content truncated · body is {kb} KB · "
                        f"embed limit {_MAX_SYSDOC_EMBED_BYTES // 1024} KB. "
                        f"Open the file directly to read the rest.]*\n"
                    )
        except (OSError, UnicodeError):
            # Defensive · 文件存在但读不动 · exists 留 True 但 content 空
            pass
        out.append(item)
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
    # 0.12.2 · `{version}` / `{build_time}` placeholder · eyebrow / tagline
    # 编译时替换 · 让 yaml 写 "DOGFOOD · v{version}" 等模板字符串 ·
    # 升 version 之后 dashboard 自动跟着走 · 不用每个 release 手动改 yaml
    from . import __version__ as _cli_version

    def _expand_project_str(s: str) -> str:
        if not isinstance(s, str) or "{" not in s:
            return s
        return s.replace("{version}", _cli_version).replace(
            "{build_time}", build_time
        )

    project = config.get("project", {}) or {}
    # 0.16.0 · project.doc_language · 项目级文档语言锁 · zh-CN | en
    # 不填 → 后续 detect_doc_language(modules) 启发式判断 · stash 到 payload
    doc_language = project.get("doc_language", "").strip().lower() or None
    payload_project = {
        "name": project.get("name") or "MyProject",
        "tagline": _expand_project_str(project.get("tagline") or ""),
        "eyebrow": _expand_project_str(project.get("eyebrow") or ""),
        "mark": (project.get("mark") or project.get("glyph") or "·"),
        "lastBuild": build_time,
        "doc_language": doc_language,  # 可能 None · _build_card_list 后再 auto-detect
    }

    repo_root = pathlib.Path(vars_.get("repo", "."))
    system_docs = _build_system_docs(config.get("system_docs"), vars_, repo_root)
    # 0.15.0 · aliases · 把外部已生成的 plan/RFC/spec 注册进 systemDocs
    # 跟 system_docs 并排显示 · 文件原地不动 · canonical 命名仅展示层
    alias_cards = _build_aliases(config.get("aliases"), vars_, repo_root)
    if alias_cards:
        system_docs = system_docs + alias_cards
    modules = _build_card_list(
        config.get("modules"), vars_, fm_enabled, ranges, issues, full=True
    )
    concepts = _build_card_list(
        config.get("concepts"), vars_, fm_enabled, ranges, issues, full=False
    )

    # 0.16.0 · 如果 yaml 没显式设 doc_language · 启发式 detect
    if payload_project["doc_language"] is None:
        from .schema import detect_doc_language
        payload_project["doc_language"] = detect_doc_language(modules)

    # 0.16.0 · 跑 title style + doc-lang consistency lint(skill §16 references)
    # 仅 warn / hint · 不 reject build
    from .schema import lint_subtask_titles
    title_issues = lint_subtask_titles(modules, payload_project["doc_language"])
    issues.extend(title_issues)

    # 0.17.0 · 跑 anchor 完整性 lint · subtask 缺 @code: 跟 @docs: 都没 → warn
    # (skill §16.3 references · 用户反馈 0.16.0 lint 只看 title 不看 anchor 数量)
    from .schema import lint_subtask_anchors
    anchor_issues = lint_subtask_anchors(modules)
    issues.extend(anchor_issues)

    # 0.19.0 · agile sprint plan readiness lint · 找 docs/plans/V*.md sprint-plan
    # · 跑 lint_sprint_readiness 看 DoR 满不满足。默认 opt-in · 没 sprint-plan 不报警
    # · `project.enforce_sprint_plans: true` 时强制(module.sprint 没对应 plan 也报)
    try:
        from .schema import lint_sprint_readiness as _lint_sr
        from .schema import load_sprint_plans
        repo_root = pathlib.Path(vars_.get("repo", "."))
        sprint_plans = load_sprint_plans(repo_root)
        if sprint_plans or project.get("enforce_sprint_plans", False):
            sr_issues = _lint_sr(
                modules,
                sprint_plans,
                enforce=bool(project.get("enforce_sprint_plans", False)),
            )
            issues.extend(sr_issues)
            # 顺手把每个 sprint-plan 的 schema 校验 issues 也 surface
            for sp in sprint_plans:
                issues.extend(sp.get("_validate_issues") or [])
    except Exception:  # noqa: BLE001 · sprint feature 是 opt-in · 异常不该挂 build
        pass

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

    # ── sidecar state.json · 给 docs-cockpit-rebuild skill（Phase 1 状态叙事）读 ──
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

    # ── 0.11.0-alpha.3 · W3 sidecar:prompts.js (plan §6.3) ────────
    # 给所有 subtask 渲染 prompt · 输出 docs/prompts.js 让 drawer 「Copy
    # prompt」按钮 fetch · 主 HTML 不 inline 这些 · 保单文件体积稳定。
    # (v1.0 起这是渲染期唯一的 prompt sidecar · refine / bundle 认知 sidecar 已删)
    try:
        from .prompt import render_all_subtask_prompts
        repo_root = pathlib.Path(vars_.get("repo", "."))
        prompts_map = render_all_subtask_prompts(payload["modules"], repo_root)
        if prompts_map:
            prompts_js_path = output.parent / "prompts.js"
            prompts_json = json.dumps(prompts_map, ensure_ascii=False)
            prompts_js_path.write_text(
                f"window.__PROMPTS__ = {prompts_json};\n",
                encoding="utf-8",
            )
    except Exception as exc:  # noqa: BLE001
        _safe_print(f"     [warn] prompts.js sidecar 生成失败:{exc}")

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
        _safe_print("     → spec: references/schema.md (frontmatter + anchor 字段规范)")
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
    """校验 frontmatter + body 是否符合 references/schema.md 规范 · 不 build · 不写 HTML.

    退出码:
      0 · 全通过(可能仍有 hint · hint 不阻塞)
      0 · 仅有 warn / hint(默认) · 加 --strict-warn 升级
      1 · 至少 1 个 error · 一律退出 1

    v0.18.0(gap #3)· lint 跑跟 build 完全相同的 issue collection:
        validate_meta + lint_subtask_titles + lint_subtask_anchors
      只是不写 HTML / state.json。--include / --exclude 按 category filter ·
      --legacy-schema-only 回到 0.17 之前只跑 validate_meta 的老行为。
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
    # 顺手把 modules 攒一份 · 给 lint_subtask_titles / lint_subtask_anchors 用
    # (跟 build_payload 不同 · 这里只要 meta + body · 不 resolve linked docs · 不 embed content)
    modules_for_lint: list[dict] = []
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
            # 给 lint_subtask_titles / lint_subtask_anchors 攒最小 module dict
            if key == "modules":
                subtasks = extract_subtasks_from_body(body) if body else []
                # 没 body subtask 看 frontmatter 有没有 object 形式
                if not subtasks and isinstance(meta.get("subtasks"), list):
                    subtasks = [s for s in meta["subtasks"] if isinstance(s, dict)]
                modules_for_lint.append({
                    "id": meta.get("id", ""),
                    "title": meta.get("title", ""),
                    "path": str(path),
                    "subtasks": subtasks,
                })

    # 0.18.0 · lint 跟 build 跑同款 title / anchor lint(--legacy-schema-only 跳过)
    if not getattr(args, "legacy_schema_only", False):
        project = config.get("project", {}) or {}
        doc_language = (project.get("doc_language") or "").strip().lower() or None
        if doc_language is None:
            doc_language = detect_doc_language(modules_for_lint)
        issues.extend(lint_subtask_titles(modules_for_lint, doc_language))
        issues.extend(lint_subtask_anchors(modules_for_lint))

        # 0.19.0 · agile sprint readiness · 跟 build pipeline 对齐 · 默认 opt-in
        try:
            from .schema import lint_sprint_readiness as _lint_sr
            from .schema import load_sprint_plans
            repo_root = pathlib.Path(vars_.get("repo", "."))
            sprint_plans = load_sprint_plans(repo_root)
            if sprint_plans or project.get("enforce_sprint_plans", False):
                issues.extend(_lint_sr(
                    modules_for_lint,
                    sprint_plans,
                    enforce=bool(project.get("enforce_sprint_plans", False)),
                ))
                for sp in sprint_plans:
                    issues.extend(sp.get("_validate_issues") or [])
        except Exception:  # noqa: BLE001
            pass

    # 0.18.0 · --include / --exclude category filter
    # 空 category 视作 'frontmatter-schema'(向后兼容 0.17 之前的 validate_meta issues)
    def _issue_category(iss: Issue) -> str:
        return iss.category or "frontmatter-schema"

    include_csv = getattr(args, "include_categories", None)
    exclude_csv = getattr(args, "exclude_categories", None)
    if include_csv:
        include_set = {c.strip() for c in include_csv.split(",") if c.strip()}
        issues = [i for i in issues if _issue_category(i) in include_set]
    if exclude_csv:
        exclude_set = {c.strip() for c in exclude_csv.split(",") if c.strip()}
        issues = [i for i in issues if _issue_category(i) not in exclude_set]

    # 仅在 lint 时按 severity 排序 · error 在前 · 修起来按重要性
    severity_rank = {"error": 0, "warn": 1, "hint": 2}
    issues.sort(key=lambda i: (severity_rank.get(i.severity, 9), str(i.path)))

    errors = [i for i in issues if i.severity == "error"]
    warns = [i for i in issues if i.severity == "warn"]
    hints = [i for i in issues if i.severity == "hint"]

    if not issues:
        _safe_print("[OK] no frontmatter issues · all modules / concepts pass the spec (references/schema.md)")
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
        "Reference · references/schema.md (frontmatter schema + body conventions)"
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
