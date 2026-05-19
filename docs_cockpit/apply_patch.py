"""docs-cockpit apply-patch · v0.12 M08 · LLM YAML patch → MD frontmatter merge.

收口 v0.11 alpha.7 Refine with AI 流程模式 B(浏览器 LLM 输出 YAML patch · 用户复制
回 MD)的最后一公里:把粘贴 + 手改 MD 这个手工活换成一条 CLI。

支持两种 MD subtask 表达(跟 docs-cockpit-author §3.1 的 Form A / Form C 对齐):

  Path 1 · frontmatter `subtasks:` list[dict]
      - 直接 merge by id · YAML 序列化写回
      - patch 字段在 ALLOWED_FIELDS 白名单内(status / code / docs / desc)

  Path 2 · body checklist + inline `@code:` / `@docs:`(本 repo dogfood 风格)
      - 反查 subtask id = `<module-id>-<sha1(title)[:6]>`
      - 改 `[ ]` ↔ `[x]` 按 patch.status
      - 行尾追 `@code:...` / `@docs:...` annotation(去重 · 不复加)

接口:

    docs-cockpit apply-patch path/to/M07-mcp-server.md < patch.yaml       # dry-run · print unified diff
    docs-cockpit apply-patch path/to/M07-mcp-server.md --apply < patch.yaml  # write back + .bak 备份

被 M07 MCP server 的 `cockpit_apply_patch` tool 复用 · 模式 1 (MCP) 也走这条 backend。
"""

from __future__ import annotations

import difflib
import pathlib
import re
import shutil
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover · pyyaml 是核心 dep
    yaml = None  # type: ignore

from .schema import (
    _CHECKBOX_LINE_RE,
    _SECTION_BOUNDARY_RE,
    _SUBTASK_SECTION_RE,
    _subtask_id_for,
    split_frontmatter,
)


# 0.12 M08 · patch 白名单 · LLM 输出超出范围的字段一律跳过 · 防御越权改动
# (例如 LLM 想改 title / id / sprint · 这些 out of scope 字段会被 silently dropped)
ALLOWED_FIELDS: frozenset[str] = frozenset(
    {"status", "code", "docs", "desc"}
)


class PatchFormatError(ValueError):
    """Patch YAML 解析或 schema 校验失败 · CLI 用 catch 走 stderr 输出."""


# 内联 @code:val / @docs:val 提取(跟 schema.py::extract_subtasks_from_body 同语义)
_INLINE_CODE_RE = re.compile(r"@code:(\S+)")
_INLINE_DOCS_RE = re.compile(r"@docs:(\S+)")


def parse_patch(text: str) -> dict[str, Any]:
    """Parse YAML patch · 返回 normalized {subtasks: [...], _warnings: [...]}.

    严格校验:
    - 顶层必须是 dict(YAML object) · 否则抛 PatchFormatError
    - 必须有 `subtasks: list` · 否则抛 PatchFormatError
    - 每条 subtask 必须有 string `id` · 否则归入 _warnings · 跳过
    - 其它字段(status / code / docs / desc 之外)归入 _warnings · 不进 normalized output
    """
    if yaml is None:
        raise PatchFormatError("PyYAML not installed · run `pip install pyyaml`")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise PatchFormatError(f"YAML parse failed: {e}") from e
    if not isinstance(data, dict):
        raise PatchFormatError(
            f"patch must be a YAML dict at top level · got {type(data).__name__}"
        )
    subs = data.get("subtasks")
    if not isinstance(subs, list):
        raise PatchFormatError(
            "patch must have a 'subtasks' list (跟 refine.md.j2 输出格式对齐)"
        )

    warnings: list[str] = []
    out_subs: list[dict[str, Any]] = []
    for i, s in enumerate(subs):
        if not isinstance(s, dict):
            warnings.append(f"subtasks[{i}] not a dict · skipped")
            continue
        sid = s.get("id")
        if not isinstance(sid, str) or not sid.strip():
            warnings.append(f"subtasks[{i}] missing string 'id' · skipped")
            continue
        clean: dict[str, Any] = {"id": sid.strip()}
        for k, v in s.items():
            if k == "id":
                continue
            if k in ALLOWED_FIELDS:
                clean[k] = v
            else:
                warnings.append(
                    f"subtasks[{sid}] field '{k}' not in allowed list "
                    f"{sorted(ALLOWED_FIELDS)} · skipped"
                )
        out_subs.append(clean)

    return {"subtasks": out_subs, "_warnings": warnings}


def _normalize_code_or_docs(value: Any) -> list[str]:
    """patch 里 code/docs 可能是 string 或 list[string] · 统一到 list."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value if v]
    return []


def _apply_frontmatter_path(
    meta: dict[str, Any], body: str, patch: dict[str, Any]
) -> tuple[str, list[str], list[str]]:
    """Path 1 · frontmatter subtasks (list[dict]) merge by id · 重序列化回 MD."""
    applied: list[str] = []
    conflicts: list[str] = []
    fm_subs = meta.get("subtasks") or []
    for psub in patch["subtasks"]:
        target = next(
            (s for s in fm_subs if isinstance(s, dict) and s.get("id") == psub["id"]),
            None,
        )
        if target is None:
            conflicts.append(
                f"subtask {psub['id']} not found in module frontmatter `subtasks:` (前提:Form A)"
            )
            continue
        for k, v in psub.items():
            if k == "id":
                continue
            target[k] = v
        applied.append(psub["id"])
    new_meta_yaml = yaml.safe_dump(
        meta, allow_unicode=True, sort_keys=False, default_flow_style=False
    )
    new_text = f"---\n{new_meta_yaml}---\n{body}"
    return new_text, applied, conflicts


def _replace_body_in_text(orig_text: str, new_body: str) -> str:
    """Body-only path · 保留原 frontmatter 块原样(quote / 缩进 / 注释 都不动)·
    只换 body 区。避免 PyYAML 重序列化导致 frontmatter diff 炸眼."""
    if not orig_text.startswith("---"):
        # 没 frontmatter · 整文档就是 body
        return new_body
    lines = orig_text.split("\n")
    # find second `---` (frontmatter close)
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return new_body
    return "\n".join(lines[: end_idx + 1]) + "\n" + new_body


def _apply_body_checklist_path(
    orig_text: str,
    meta: dict[str, Any],
    body: str,
    patch: dict[str, Any],
    module_id: str,
) -> tuple[str, list[str], list[str]]:
    """Path 2 · body `## 待办` checklist · 反查 id · 改 [x] · 追 @code/@docs.

    注意:本 path 不动 frontmatter · 用 _replace_body_in_text 保留原 quote 风格 ·
    diff 只显改的 checklist 行 · 用户阅读友好。
    """
    applied: list[str] = []
    conflicts: list[str] = []

    lines = body.split("\n")
    section_start = None
    section_end = None
    for i, line in enumerate(lines):
        if section_start is None and _SUBTASK_SECTION_RE.match(line):
            section_start = i
            continue
        if section_start is not None and i > section_start and _SECTION_BOUNDARY_RE.match(line):
            section_end = i
            break
    if section_start is None:
        for psub in patch["subtasks"]:
            conflicts.append(
                f"subtask {psub['id']} · MD has no `## 待办` / `## TODO` body section "
                f"(也没有 frontmatter `subtasks:` Form A) · 跳过"
            )
        return orig_text, [], conflicts
    if section_end is None:
        section_end = len(lines)

    for psub in patch["subtasks"]:
        target_id = psub["id"]
        match_idx = None
        for i in range(section_start + 1, section_end):
            m = _CHECKBOX_LINE_RE.match(lines[i])
            if not m:
                continue
            text = m.group(2).strip()
            cleaned = _INLINE_CODE_RE.sub("", text)
            cleaned = _INLINE_DOCS_RE.sub("", cleaned)
            base_title = " ".join(cleaned.split()).strip()
            if not base_title:
                continue
            if _subtask_id_for(module_id, base_title) == target_id:
                match_idx = i
                break
        if match_idx is None:
            conflicts.append(
                f"subtask {target_id} · body checklist 找不到 title 推导出该 id 的行 · "
                f"(检查 title 是否变了?· title 变 → id 变 · 见 author skill §3.1.1)"
            )
            continue

        new_line = lines[match_idx]

        # status → checkbox
        status = psub.get("status")
        if status == "done":
            new_line = re.sub(r"^(\s*[-*+]\s+)\[\s\]", r"\1[x]", new_line)
        elif status in ("not-started", "in-progress", "blocked"):
            new_line = re.sub(r"^(\s*[-*+]\s+)\[[xX]\]", r"\1[ ]", new_line)

        # @code/@docs append · 去重(case-sensitive 原样)
        existing_codes = set(_INLINE_CODE_RE.findall(new_line))
        for c in _normalize_code_or_docs(psub.get("code")):
            if c and c not in existing_codes:
                new_line = new_line + " @code:" + c
                existing_codes.add(c)
        existing_docs = set(_INLINE_DOCS_RE.findall(new_line))
        for d in _normalize_code_or_docs(psub.get("docs")):
            if d and d not in existing_docs:
                new_line = new_line + " @docs:" + d
                existing_docs.add(d)

        if new_line != lines[match_idx]:
            lines[match_idx] = new_line
            applied.append(target_id)
        else:
            # 没实际变化 · 视为 no-op · 不报 conflict
            applied.append(target_id)

    new_body = "\n".join(lines)
    return _replace_body_in_text(orig_text, new_body), applied, conflicts


def _reserialize(meta: dict[str, Any], body: str) -> str:
    """frontmatter dict + body string → 完整 MD text."""
    if not meta:
        return body
    meta_yaml = yaml.safe_dump(
        meta, allow_unicode=True, sort_keys=False, default_flow_style=False
    )
    return f"---\n{meta_yaml}---\n{body}"


def apply_to_md(
    patch: dict[str, Any],
    md_text: str,
    module_id: str | None = None,
) -> tuple[str, list[str], list[str]]:
    """Top-level apply · 自动检测 Path 1 (frontmatter) vs Path 2 (body checklist).

    优先级:frontmatter `subtasks:` 存在且非空 → Path 1 · 否则 Path 2。
    跟 schema.normalize_subtasks 的「frontmatter wins · 否则 body」语义一致。

    Args:
        patch: parse_patch() 返回值
        md_text: 完整 MD text
        module_id: 显式 module id · 不传则从 frontmatter `id:` 字段读

    Returns:
        (new_md_text, applied_ids, conflicts)
    """
    meta, body = split_frontmatter(md_text)
    mid = module_id or (meta.get("id") if isinstance(meta, dict) else "") or ""

    fm_subs = meta.get("subtasks") if isinstance(meta, dict) else None
    if (
        isinstance(fm_subs, list)
        and fm_subs
        and any(isinstance(s, dict) for s in fm_subs)
    ):
        return _apply_frontmatter_path(meta, body, patch)
    return _apply_body_checklist_path(md_text, meta or {}, body, patch, mid)


def compute_diff(orig: str, patched: str, label: str = "md") -> str:
    """git-style unified diff · for dry-run + log output."""
    lines = list(
        difflib.unified_diff(
            orig.splitlines(keepends=True),
            patched.splitlines(keepends=True),
            fromfile=f"a/{label}",
            tofile=f"b/{label}",
            n=3,
        )
    )
    return "".join(lines)


def apply_patch_to_file(
    patch_text: str,
    md_path: pathlib.Path,
    apply: bool = False,
) -> dict[str, Any]:
    """End-to-end · parse patch + load MD + apply + (optionally) write with .bak.

    Returns:
        {
            "diff": str (unified diff · empty if no changes),
            "applied_ids": list[str],
            "conflicts": list[str] (包含 parse_patch 的 _warnings),
            "wrote": bool,
            "bak_path": str | None,
        }
    """
    if not md_path.exists():
        raise FileNotFoundError(f"MD file not found: {md_path}")
    parsed = parse_patch(patch_text)
    orig = md_path.read_text(encoding="utf-8")
    new_text, applied, conflicts = apply_to_md(parsed, orig)
    diff = compute_diff(orig, new_text, label=md_path.name)
    result: dict[str, Any] = {
        "diff": diff,
        "applied_ids": applied,
        "conflicts": conflicts + parsed.get("_warnings", []),
        "wrote": False,
        "bak_path": None,
    }
    if apply and applied and new_text != orig:
        bak = md_path.with_suffix(md_path.suffix + ".bak")
        shutil.copy2(md_path, bak)
        md_path.write_text(new_text, encoding="utf-8")
        result["wrote"] = True
        result["bak_path"] = str(bak)
    return result


# ─── CLI entrypoint(被 cli.py::cmd_apply_patch 注册)──────────────────────


def cmd_apply_patch(args) -> int:
    """`docs-cockpit apply-patch <md_path> [patch_file] [--apply]` dispatcher.

    无 patch_file 时从 stdin 读 · 跟 git apply 的 streaming-friendly 模式一致。
    退出码:0=成功(无冲突)· 1=有冲突或 parse 失败 · 2=文件不存在。
    """
    import sys

    md_path = pathlib.Path(args.md_path).resolve()
    if not md_path.exists():
        print(f"[ERR] MD file not found: {md_path}", file=sys.stderr)
        return 2

    # patch 输入:文件或 stdin
    if getattr(args, "patch_file", None):
        patch_path = pathlib.Path(args.patch_file)
        if not patch_path.exists():
            print(f"[ERR] patch file not found: {patch_path}", file=sys.stderr)
            return 2
        patch_text = patch_path.read_text(encoding="utf-8")
        src_label = str(patch_path)
    else:
        if sys.stdin.isatty():
            print(
                "[ERR] no patch_file argument and stdin is a TTY · "
                "either pass a file path or pipe YAML to stdin",
                file=sys.stderr,
            )
            return 1
        patch_text = sys.stdin.read()
        src_label = "<stdin>"

    try:
        result = apply_patch_to_file(
            patch_text, md_path, apply=bool(getattr(args, "apply", False))
        )
    except PatchFormatError as e:
        print(f"[ERR] patch parse failed: {e}", file=sys.stderr)
        return 1

    # 报告
    print(f"[apply-patch] source: {src_label}")
    print(f"[apply-patch] target: {md_path}")
    applied = result.get("applied_ids", [])
    conflicts = result.get("conflicts", [])
    print(f"[apply-patch] applied: {len(applied)} subtask(s) · "
          f"conflicts: {len(conflicts)}")
    if applied:
        for sid in applied:
            print(f"  ✓ {sid}")
    if conflicts:
        for w in conflicts:
            print(f"  ⚠ {w}", file=sys.stderr)

    diff = result.get("diff", "")
    if diff:
        print()
        print(diff)
    else:
        print("[apply-patch] no diff · patch had no effect")

    if result.get("wrote"):
        print(
            f"\n[OK] wrote {md_path} · backup at {result.get('bak_path')}",
            file=sys.stderr,
        )
    elif getattr(args, "apply", False) and not applied:
        print(
            "\n[apply-patch] --apply set but no subtasks applied · "
            "MD unchanged · no .bak",
            file=sys.stderr,
        )
    else:
        print(
            "\n[apply-patch] dry-run · pass --apply to write back + create .bak",
            file=sys.stderr,
        )

    return 1 if conflicts else 0

