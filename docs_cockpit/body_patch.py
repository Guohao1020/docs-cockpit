"""docs-cockpit body checklist patch · v0.18.0 gap #2 · MCP cockpit_apply_body_checklist_patch.

跟 frontmatter YAML patch(apply_patch.py · M08)互补:

| 模块 | 目标 | 输入 |
|---|---|---|
| `apply_patch.py`(M08)| frontmatter `subtasks:` Form A | object schema · id-keyed merge |
| `body_patch.py`(本文件 · 0.18.0)| body `## 待办` checklist · inline `@code:` / `@docs:` | edit ops · 行级精确 add / replace / remove |

为什么不复用 apply_patch.py:
- frontmatter patch 是 declarative replace(整个 object 重写)· body patch 是 imperative edit(行级 op)
- frontmatter 只 add 不删 · body patch 三种 action(add / replace / remove)需要新语义
- 一个 module 多次 build 之间 · LLM 想 verify 后挪 anchor(replace + remove)· 走 frontmatter patch 表达不出
- 把两种 schema 塞进同一个 tool 让 LLM 选错(也是 gap #2 设计阶段已决定开新 tool)

Patch YAML format:

```yaml
module: M07
edits:
  - subtask: M07-f75501
    action: add_annotation                  # add_annotation | replace_annotation | remove_annotation
    annotation_type: code                   # code | docs
    value: "sourcery/mcp.py:42-89"
  - subtask: M07-53a63a
    action: replace_annotation
    annotation_type: docs
    value: "docs/RFC/007.md#§3"             # 同 type 下所有现存 anchor 清空 · 写入这一个 value
  - subtask: M07-9adb12
    action: remove_annotation
    annotation_type: code
    value: "old/stale.py"                   # 精确匹配 · 找不到报 conflict
```

Idempotency 保证:
- `add_annotation` · value 已存在 → no-op(不重复加)
- `replace_annotation` · 同 type 下所有 anchor 删 → 重新加 value · 第二次跑 value 已是唯一 → no-op
- `remove_annotation` · value 不存在 → conflict(显式报 · 不静默忽略)

CLI 入口 cmd_apply_body_patch + MCP tool handler 都调本模块 apply_body_patch_to_file。
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


# 跟 apply_patch.py 同款 inline annotation regex(集中一处避免漂移)
_INLINE_CODE_RE = re.compile(r"@code:(\S+)")
_INLINE_DOCS_RE = re.compile(r"@docs:(\S+)")

VALID_ACTIONS = frozenset({"add_annotation", "replace_annotation", "remove_annotation"})
VALID_ANNOTATION_TYPES = frozenset({"code", "docs"})


class BodyPatchFormatError(ValueError):
    """body patch 解析或 schema 校验失败 · CLI / MCP 用 catch 走 stderr 输出."""


def parse_body_patch(text: str) -> dict[str, Any]:
    """Parse YAML body patch · 返回 normalized {module, edits: [...], _warnings: [...]}.

    严格校验:
    - 顶层必须是 dict
    - 必须有 string `module`
    - 必须有 `edits: list` · 不能空
    - 每个 edit 必须有 string `subtask` / `action` / `annotation_type` / `value`
    - action 必须在 VALID_ACTIONS · annotation_type 必须在 VALID_ANNOTATION_TYPES
    - 不合法的 edit 归入 _warnings · 跳过
    """
    if yaml is None:
        raise BodyPatchFormatError("PyYAML not installed · run `pip install pyyaml`")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise BodyPatchFormatError(f"YAML parse failed: {e}") from e
    if not isinstance(data, dict):
        raise BodyPatchFormatError(
            f"body patch must be a YAML dict at top level · got {type(data).__name__}"
        )
    module_id = data.get("module")
    if not isinstance(module_id, str) or not module_id.strip():
        raise BodyPatchFormatError(
            "body patch missing required top-level `module: <id>` field"
        )
    module_id = module_id.strip()

    edits_raw = data.get("edits")
    if not isinstance(edits_raw, list) or not edits_raw:
        raise BodyPatchFormatError(
            "body patch missing required `edits: list` field (or list is empty)"
        )

    edits: list[dict[str, Any]] = []
    warnings: list[str] = []
    for i, e in enumerate(edits_raw):
        if not isinstance(e, dict):
            warnings.append(f"edits[{i}] is not a dict · skipped")
            continue
        subtask = e.get("subtask")
        action = e.get("action")
        ann_type = e.get("annotation_type")
        value = e.get("value")
        if not isinstance(subtask, str) or not subtask.strip():
            warnings.append(f"edits[{i}] missing string `subtask` field · skipped")
            continue
        if action not in VALID_ACTIONS:
            warnings.append(
                f"edits[{i}].action={action!r} invalid · "
                f"must be one of {sorted(VALID_ACTIONS)} · skipped"
            )
            continue
        if ann_type not in VALID_ANNOTATION_TYPES:
            warnings.append(
                f"edits[{i}].annotation_type={ann_type!r} invalid · "
                f"must be one of {sorted(VALID_ANNOTATION_TYPES)} · skipped"
            )
            continue
        if not isinstance(value, str) or not value.strip():
            warnings.append(f"edits[{i}] missing string `value` field · skipped")
            continue
        edits.append({
            "subtask": subtask.strip(),
            "action": action,
            "annotation_type": ann_type,
            "value": value.strip(),
        })

    return {
        "module": module_id,
        "edits": edits,
        "_warnings": warnings,
    }


def _find_subtask_line(
    body_lines: list[str], module_id: str, subtask_id: str,
    section_start: int, section_end: int,
) -> int | None:
    """在 body checklist 找出对应 subtask_id 的行 · 找不到返 None.

    跟 apply_patch._apply_body_checklist_path 的反查逻辑一致 · 走
    `_subtask_id_for(module_id, clean_title)` 反推 sha1[:6] hash。
    """
    for i in range(section_start + 1, section_end):
        m = _CHECKBOX_LINE_RE.match(body_lines[i])
        if not m:
            continue
        text = m.group(2).strip()
        cleaned = _INLINE_CODE_RE.sub("", text)
        cleaned = _INLINE_DOCS_RE.sub("", cleaned)
        base_title = " ".join(cleaned.split()).strip()
        if not base_title:
            continue
        if _subtask_id_for(module_id, base_title) == subtask_id:
            return i
    return None


def _apply_one_edit(
    line: str, action: str, ann_type: str, value: str
) -> tuple[str, str | None]:
    """对单行执行一个 edit · 返回 (new_line, conflict_msg).

    conflict_msg = None 表示成功 · 字符串表示这条 edit 没生效的原因(remove 找不到目标等)。
    """
    pattern = _INLINE_CODE_RE if ann_type == "code" else _INLINE_DOCS_RE
    annotation_prefix = "@code:" if ann_type == "code" else "@docs:"
    existing = pattern.findall(line)

    if action == "add_annotation":
        if value in existing:
            return line, None  # idempotent · 已存在 · no-op
        return line + " " + annotation_prefix + value, None

    if action == "replace_annotation":
        # 删掉同 type 所有 anchor · 加 value
        new_line = pattern.sub("", line)
        # 清掉 trailing 空格(annotation 删后留 doubled spaces)
        new_line = re.sub(r"\s+", " ", new_line).rstrip()
        new_line = new_line + " " + annotation_prefix + value
        if new_line == line:
            return line, None  # value 已是唯一 → no-op
        return new_line, None

    if action == "remove_annotation":
        if value not in existing:
            return line, (
                f"value {value!r} not found in existing {ann_type} anchors "
                f"({existing!r}) · cannot remove"
            )
        # 精确删除 · 注意 `@code:foo` 跟 `@code:foobar` 不能误伤 · 用 `(?:\s|$)` boundary
        # 也要清掉前导空格(否则 line 末多余空格)
        target = re.escape(annotation_prefix + value)
        new_line = re.sub(rf"\s*{target}(?=\s|$)", "", line)
        return new_line, None

    return line, f"unknown action {action!r}"


def apply_body_patch_to_text(
    patch: dict[str, Any], orig_text: str
) -> dict[str, Any]:
    """对原 MD text 应用 body patch · 返回 {new_text, applied[], conflicts[], unchanged: bool}.

    apply_body_patch_to_file 调本函数 · 也给 unit test 单独 import 用。
    """
    module_id = patch["module"]
    edits = patch["edits"]

    meta, body = split_frontmatter(orig_text)
    body_lines = body.split("\n")

    # 定位 `## 待办` / `## TODO` section
    section_start = None
    section_end = None
    for i, line in enumerate(body_lines):
        if section_start is None and _SUBTASK_SECTION_RE.match(line):
            section_start = i
            continue
        if section_start is not None and i > section_start and _SECTION_BOUNDARY_RE.match(line):
            section_end = i
            break
    if section_start is None:
        # 整个 module MD 没 `## 待办` section · 所有 edit 都没 anchor
        return {
            "new_text": orig_text,
            "applied": [],
            "conflicts": [
                f"module {module_id} body has no `## 待办` / `## TODO` section · "
                f"all {len(edits)} edits skipped"
            ],
            "unchanged": True,
        }
    if section_end is None:
        section_end = len(body_lines)

    applied: list[dict[str, Any]] = []
    conflicts: list[str] = []

    for edit in edits:
        subtask_id = edit["subtask"]
        idx = _find_subtask_line(
            body_lines, module_id, subtask_id, section_start, section_end
        )
        if idx is None:
            conflicts.append(
                f"subtask {subtask_id} · body checklist 找不到 title 推导出该 id 的行 · "
                f"(title 变了?· title 变 → id 变 · 见 author skill §3.1.1)"
            )
            continue

        new_line, conflict_msg = _apply_one_edit(
            body_lines[idx], edit["action"], edit["annotation_type"], edit["value"]
        )
        if conflict_msg:
            conflicts.append(f"subtask {subtask_id} · {edit['action']} · {conflict_msg}")
            continue

        if new_line != body_lines[idx]:
            body_lines[idx] = new_line
            applied.append({
                "subtask": subtask_id,
                "action": edit["action"],
                "annotation_type": edit["annotation_type"],
                "value": edit["value"],
            })
        else:
            # idempotent no-op · 仍记为 applied 让用户知道这条没 conflict
            applied.append({
                "subtask": subtask_id,
                "action": edit["action"],
                "annotation_type": edit["annotation_type"],
                "value": edit["value"],
                "noop": True,
            })

    new_body = "\n".join(body_lines)
    # 拼回 frontmatter + new_body · 保留原 MD 的 frontmatter ↔ body 边界空行
    # (apply_patch._replace_body_in_text 有 bug · 用 "\n" 单换行而非原始的 "\n\n"
    # · 复用会在 diff 里多一行垃圾。这里 inline 自己写一份 · 不动那个 caller)
    new_text = _splice_body_preserve_layout(orig_text, new_body)

    return {
        "new_text": new_text,
        "applied": applied,
        "conflicts": conflicts,
        "unchanged": new_text == orig_text,
    }


def _splice_body_preserve_layout(orig_text: str, new_body: str) -> str:
    """把 new_body 接回 orig_text 的 frontmatter 块 · 保留原 frontmatter close 之后
    那一段空白 · 避免 diff 多删一行。

    无 frontmatter 走整个文档替换。
    """
    if not orig_text.startswith("---"):
        return new_body
    lines = orig_text.split("\n")
    # 找第二个 `---` (frontmatter close)
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return new_body
    # 找 frontmatter close 之后所有连续空白行的范围 · 这段原样保留
    blank_end = end_idx + 1
    while blank_end < len(lines) and lines[blank_end].strip() == "":
        blank_end += 1
    # frontmatter + blank lines + new body
    head = "\n".join(lines[:blank_end])
    return head + "\n" + new_body


def compute_diff(orig: str, patched: str, label: str = "md") -> str:
    """Unified diff · 跟 git diff 一致 · 给 CLI dry-run 输出."""
    diff = difflib.unified_diff(
        orig.splitlines(keepends=True),
        patched.splitlines(keepends=True),
        fromfile=f"a/{label}",
        tofile=f"b/{label}",
        n=3,
    )
    return "".join(diff)


def apply_body_patch_to_file(
    patch_text: str, md_path: pathlib.Path, apply: bool = False
) -> dict[str, Any]:
    """端到端 · parse patch + read MD + apply + (optional) write back with .bak.

    返回:
      {
        "applied": list[dict],         # 成功 edit 列表
        "conflicts": list[str],        # 没生效的 edit 解释
        "warnings": list[str],         # patch parse 阶段的 schema warning
        "diff": str,                   # unified diff(空串=没改动)
        "wrote": bool,                 # 真写回了 MD 吗
        "bak_path": str | None,        # .bak 文件路径(没写则 None)
      }
    """
    md_path = pathlib.Path(md_path)
    if not md_path.exists():
        raise BodyPatchFormatError(f"target MD not found: {md_path}")

    patch = parse_body_patch(patch_text)
    warnings = patch.pop("_warnings", [])

    orig = md_path.read_text(encoding="utf-8")
    result = apply_body_patch_to_text(patch, orig)
    diff = compute_diff(orig, result["new_text"], label=md_path.name)

    wrote = False
    bak_path = None
    if apply and not result["unchanged"]:
        bak = md_path.with_suffix(md_path.suffix + ".bak")
        shutil.copy2(md_path, bak)
        bak_path = str(bak)
        md_path.write_text(result["new_text"], encoding="utf-8")
        wrote = True

    return {
        "applied": result["applied"],
        "conflicts": result["conflicts"],
        "warnings": warnings,
        "diff": diff,
        "wrote": wrote,
        "bak_path": bak_path,
    }


def cmd_apply_body_patch(args) -> int:
    """`docs-cockpit apply-body-patch <md_path> [patch_file] [--apply]` CLI 入口.

    跟 cmd_apply_patch 同款 stdin / 文件输入 · 默认 dry-run。
    """
    import sys

    md_path = pathlib.Path(getattr(args, "md_path", ""))
    if not md_path.exists():
        print(f"[ERR] target MD not found: {md_path}", file=sys.stderr)
        return 2

    patch_file = getattr(args, "patch_file", None)
    if patch_file:
        patch_text = pathlib.Path(patch_file).read_text(encoding="utf-8")
    else:
        patch_text = sys.stdin.read()
    if not patch_text.strip():
        print("[ERR] empty patch (stdin or file)", file=sys.stderr)
        return 2

    try:
        result = apply_body_patch_to_file(
            patch_text, md_path, apply=getattr(args, "apply", False)
        )
    except BodyPatchFormatError as e:
        print(f"[ERR] {e}", file=sys.stderr)
        return 2

    if result["warnings"]:
        print("# patch parse warnings:", file=sys.stderr)
        for w in result["warnings"]:
            print(f"  - {w}", file=sys.stderr)

    if result["diff"]:
        print(result["diff"])
    else:
        print("[OK] no changes (patch is fully idempotent · all edits are no-ops)")

    if result["conflicts"]:
        print("\n# conflicts (these edits did not apply):", file=sys.stderr)
        for c in result["conflicts"]:
            print(f"  - {c}", file=sys.stderr)

    if result["wrote"]:
        print(
            f"\n[OK] wrote {md_path} · backup: {result['bak_path']} · "
            f"{len(result['applied'])} edit(s) applied",
            file=sys.stderr,
        )
    elif not getattr(args, "apply", False) and result["diff"]:
        print(
            "\n[hint] dry-run · re-run with --apply to write back",
            file=sys.stderr,
        )

    return 1 if result["conflicts"] else 0
