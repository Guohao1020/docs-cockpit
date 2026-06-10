"""docs-cockpit sync-status · v0.12 M09 · 浏览器 override → MD 反向同步.

闭环 v0.11 plan §1 缺口 3「任务清单状态控制不闭环」。配合 0.11.3 build-time-aware
override invalidation:
    - 0.11.3 解决「source MD → dashboard」漂移(build 后老 override 自动失效)
    - 0.12 M09 解决「dashboard → source MD」漂移(用户在 dashboard 勾的状态写回 MD)

工作流:

  Path 1 · dashboard export JSON(本 module 的主路径 · MVP 完整支持)
    用户在 dashboard 点 footer「Export status overrides」· 下载 JSON
    docs-cockpit sync-status --import overrides.json           # dry-run
    docs-cockpit sync-status --import overrides.json --apply   # 写回 MD + .bak

  Path 2 · 直读浏览器 profile localStorage(v0.13 候选)
    docs-cockpit sync-status --from-browser chrome   # 当前阶段 stub · 报错指向 Path 1

优先级规则(对每个 subtask 决策):

  +--------------------+---------------------+----------------+
  | localStorage 状态  | source MD 状态     | 谁赢            |
  +--------------------+---------------------+----------------+
  | done               | not-done            | localStorage   |
  | not-done           | done                | MD             |
  | not record         | done / not-done     | MD             |
  | done               | subtask 不存在      | warn + skip    |
  +--------------------+---------------------+----------------+

(MVP 简化:复用 apply_to_md merge backend · localStorage `done=true` → 走 patch · `done=false`
不强 force-untick · 用户取消勾选时如果 MD 里是 done · 默认信 MD · 见 §3 表第二行。)

实施:复用 schema.apply_to_md(v1.0 起从已删的 apply_patch.py 收编到 schema.py)·
不重复造 frontmatter / body checklist merge 轮子。
"""

from __future__ import annotations

import datetime as _dt
import json
import pathlib
import re
import sys
from typing import Any

from .schema import (
    PatchFormatError,
    apply_to_md,
    compute_diff,
)


# 0.12 M09 · localStorage key format · 跟 templates/index.html.tmpl:1867 一致:
#   `<module_id>__st__<subtask_id>`
# subtask_id 本身可能含 dash 跟特殊字符 · 模块 id 不含 underscore(M01-M99 规约)
_LS_SUBTASK_KEY_RE = re.compile(r"^([^_]+)__st__(.+)$")


class SyncStatusError(Exception):
    """sync-status flow 出错的 wrap class · CLI catch 走 stderr 报错."""


# ─── parse_overrides ──────────────────────────────────────────────────────


def parse_overrides(json_text: str) -> dict[str, dict[str, bool]]:
    """Parse dashboard exported JSON · 返回 {module_id: {subtask_id: done_bool, ...}}.

    JSON shape 跟 localStorage 一致(dashboard 直接 dump):

      {
        "_built_at": "2026-05-19 12:10",
        "_exported_at": "...",                          # 可选 · 用于 stale check
        "M07__st__M07-9db754": true,
        "M07__st__M07-f75501": false,
        "M03": {"status": "done", "progress": 100}      # module 级 · MVP 忽略
      }

    Returns:
        grouped: {"M07": {"M07-9db754": True, "M07-f75501": False}, ...}

    Raises:
        SyncStatusError: JSON 解析失败 / 顶层不是 dict
    """
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise SyncStatusError(f"JSON parse failed: {e}") from e
    if not isinstance(data, dict):
        raise SyncStatusError(
            f"overrides JSON must be a top-level object · got {type(data).__name__}"
        )

    grouped: dict[str, dict[str, bool]] = {}
    for k, v in data.items():
        if k.startswith("_"):
            continue
        if not isinstance(v, bool):
            # module 级 override(dict)或异常值 · MVP 跳过
            continue
        m = _LS_SUBTASK_KEY_RE.match(k)
        if not m:
            continue
        module_id, subtask_id = m.group(1), m.group(2)
        grouped.setdefault(module_id, {})[subtask_id] = v
    return grouped


# ─── merge_to_md ──────────────────────────────────────────────────────────


def merge_to_md(
    module_id: str,
    sub_overrides: dict[str, bool],
    md_path: pathlib.Path,
) -> dict[str, Any]:
    """Merge 单 module 的 subtask overrides 到对应 MD · 走 schema.apply_to_md backend.

    优先级规则(MVP):
    - localStorage `done=true` → patch `status: done` · 走 apply_to_md
    - localStorage `done=false` → 不主动 force-untick · 信 MD(避免反向同步过激
      把用户在 MD 里手动标 done 的 subtask 弹回)· 见模块 docstring 表第二行

    Returns:
        {
          "applied_ids": list[str],
          "conflicts": list[str],
          "diff": str,
          "new_text": str,
          "wrote": False,  # CLI 决定是否写
        }
    """
    if not md_path.exists():
        raise SyncStatusError(f"MD file not found: {md_path}")

    patch_subs = []
    for sid, done in sub_overrides.items():
        if done:
            patch_subs.append({"id": sid, "status": "done"})
        # else: 信 MD · 不动 · 见 docstring 优先级规则第二行

    if not patch_subs:
        return {
            "applied_ids": [],
            "conflicts": [],
            "diff": "",
            "new_text": "",
            "wrote": False,
        }

    md_text = md_path.read_text(encoding="utf-8")
    patch = {"subtasks": patch_subs, "_warnings": []}
    new_text, applied, conflicts = apply_to_md(patch, md_text, module_id)
    diff = compute_diff(md_text, new_text, label=md_path.name)

    return {
        "applied_ids": applied,
        "conflicts": conflicts,
        "diff": diff,
        "new_text": new_text,
        "wrote": False,
    }


# ─── compute_conflicts ────────────────────────────────────────────────────


def compute_conflicts(
    overrides_by_module: dict[str, dict[str, bool]],
    state_modules: list[dict[str, Any]],
) -> list[str]:
    """检测「localStorage 引用了 subtask · 但 state.json / MD 里不存在」类冲突.

    Args:
        overrides_by_module: parse_overrides() 输出
        state_modules: state.json 的 modules[] list

    Returns:
        warning string list · 每条描述一个 stale subtask 引用
    """
    warnings: list[str] = []
    state_lookup = {
        m.get("id"): {s.get("id") for s in (m.get("subtasks") or [])}
        for m in state_modules
        if isinstance(m, dict)
    }
    for mid, subs in overrides_by_module.items():
        known = state_lookup.get(mid)
        if known is None:
            warnings.append(f"module {mid} in overrides but not in state.json · skipped")
            continue
        for sid in subs:
            if sid not in known:
                warnings.append(
                    f"subtask {sid} (module {mid}) in overrides but not in state.json · "
                    f"likely subtask was deleted / renamed"
                )
    return warnings


# ─── End-to-end orchestrator ──────────────────────────────────────────────


def sync_to_repo(
    json_text: str,
    config_path: pathlib.Path,
    apply: bool = False,
) -> dict[str, Any]:
    """Top-level · parse JSON + locate MDs via state.json + merge into each MD.

    Returns:
        {
          "per_module": [{"module_id": ..., "applied_ids": ..., "conflicts": ..., "diff": ...}],
          "global_warnings": list[str] (stale subtask refs),
          "wrote_files": list[str] (only when apply=True),
        }
    """
    overrides = parse_overrides(json_text)

    # 通过 state.json 拿 module path
    state_path = config_path.parent / "docs" / "state.json"
    if not state_path.exists():
        raise SyncStatusError(
            f"state.json not found at {state_path} · "
            f"run `docs-cockpit build` first"
        )
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SyncStatusError(f"state.json parse failed: {e}") from e

    modules = state.get("modules") or []
    md_lookup = {m.get("id"): m.get("path") for m in modules if isinstance(m, dict)}

    global_warnings = compute_conflicts(overrides, modules)

    per_module: list[dict[str, Any]] = []
    wrote: list[str] = []
    import shutil

    for mid, sub_overrides in overrides.items():
        md_path_str = md_lookup.get(mid)
        if not md_path_str:
            # already in global_warnings · 跳过
            continue
        md_path = pathlib.Path(md_path_str)
        try:
            r = merge_to_md(mid, sub_overrides, md_path)
        except (SyncStatusError, PatchFormatError) as e:
            global_warnings.append(f"module {mid}: {e}")
            continue
        r["module_id"] = mid
        r["md_path"] = str(md_path)
        if apply and r["applied_ids"] and r["new_text"]:
            bak = md_path.with_suffix(md_path.suffix + ".bak")
            shutil.copy2(md_path, bak)
            md_path.write_text(r["new_text"], encoding="utf-8")
            r["wrote"] = True
            r["bak_path"] = str(bak)
            wrote.append(str(md_path))
        # 不嵌 new_text 到 final output(可能很大)
        r.pop("new_text", None)
        per_module.append(r)

    return {
        "per_module": per_module,
        "global_warnings": global_warnings,
        "wrote_files": wrote,
    }


# ─── CLI entrypoint ──────────────────────────────────────────────────────


def cmd_sync_status(args) -> int:
    """`docs-cockpit sync-status --import <json> [--apply] [--from-browser <name>]`.

    Path 1(--import)· 主流程 · MVP 完整支持。
    Path 2(--from-browser)· stub · 报错指向 Path 1 + v0.13 ticket。
    """
    # 0.14.3 M13/M09-b23cac · Path 2 · 从浏览器 profile dir 直读 localStorage
    from_browser = getattr(args, "from_browser", None)
    if from_browser:
        from .browser_storage import (
            BrowserStorageError,
            read_localstorage_from_browser,
        )

        profile = getattr(args, "profile", None)
        try:
            stored = read_localstorage_from_browser(from_browser, profile=profile)
        except BrowserStorageError as e:
            print(f"[ERR] {e}", file=sys.stderr)
            return 2
        if not stored:
            print(
                f"[sync-status] no overrides found in {from_browser} localStorage · "
                f"open dashboard first OR check --profile <name>",
                file=sys.stderr,
            )
            return 0
        # 拿到 dict · 接着走跟 --import 一样的 sync_to_repo 路径
        cfg_path = pathlib.Path(getattr(args, "config", None) or "docs-cockpit.yaml")
        if not cfg_path.exists():
            print(f"[ERR] config not found: {cfg_path}", file=sys.stderr)
            return 2
        try:
            result = sync_to_repo(
                json.dumps(stored, ensure_ascii=False),
                cfg_path.resolve(),
                apply=bool(getattr(args, "apply", False)),
            )
        except SyncStatusError as e:
            print(f"[ERR] {e}", file=sys.stderr)
            return 1
        _print_sync_report(f"<{from_browser} profile>", cfg_path, result, args)
        return 1 if (
            any(r["conflicts"] for r in result["per_module"]) or result["global_warnings"]
        ) else 0

    json_path = getattr(args, "import_path", None)
    if not json_path:
        print(
            "[ERR] either --import <file> or --from-browser <name> required",
            file=sys.stderr,
        )
        return 2

    json_p = pathlib.Path(json_path)
    if not json_p.exists():
        print(f"[ERR] JSON file not found: {json_p}", file=sys.stderr)
        return 2

    cfg_path = pathlib.Path(getattr(args, "config", None) or "docs-cockpit.yaml")
    if not cfg_path.exists():
        print(f"[ERR] config not found: {cfg_path}", file=sys.stderr)
        return 2

    try:
        result = sync_to_repo(
            json_p.read_text(encoding="utf-8"),
            cfg_path.resolve(),
            apply=bool(getattr(args, "apply", False)),
        )
    except SyncStatusError as e:
        print(f"[ERR] {e}", file=sys.stderr)
        return 1

    # 报告
    _print_sync_report(str(json_p), cfg_path, result, args)
    return 1 if (any(r["conflicts"] for r in result["per_module"]) or result["global_warnings"]) else 0


def _print_sync_report(source_label: str, cfg_path: pathlib.Path, result: dict[str, Any], args) -> None:
    """共享报告打印逻辑 · --import / --from-browser 都用."""
    print(f"[sync-status] source: {source_label}")
    print(f"[sync-status] target repo: {cfg_path.parent.resolve()}")
    n_mod = len(result["per_module"])
    n_applied = sum(len(r["applied_ids"]) for r in result["per_module"])
    print(f"[sync-status] {n_applied} subtask(s) across {n_mod} module(s)")
    for r in result["per_module"]:
        if not r["applied_ids"] and not r["conflicts"]:
            continue
        print(f"\n  {r['module_id']} → {r['md_path']}")
        for sid in r["applied_ids"]:
            print(f"    [done] {sid}")
        for c in r["conflicts"]:
            print(f"    [warn] {c}", file=sys.stderr)
    if result["global_warnings"]:
        print("\nGlobal warnings:", file=sys.stderr)
        for w in result["global_warnings"]:
            print(f"  [warn] {w}", file=sys.stderr)

    for r in result["per_module"]:
        if r["diff"]:
            print()
            print(r["diff"])

    if result["wrote_files"]:
        print(
            f"\n[OK] wrote {len(result['wrote_files'])} file(s) · .bak siblings generated",
            file=sys.stderr,
        )
    elif getattr(args, "apply", False):
        print(
            "\n[sync-status] --apply set but nothing to write · no changes",
            file=sys.stderr,
        )
    else:
        print(
            "\n[sync-status] dry-run · pass --apply to write back + create .bak per MD",
            file=sys.stderr,
        )
