"""docs-cockpit bundle · v0.14 M17 · batch-driver backend.

跨 module 选 N 个 subtask · 渲染一份聚合 prompt(共享上下文一次给 · subtask 清单
按推荐顺序列出)· 跟 M10 suggest 互补:
- suggest · 给一个 module 出软建议 prompt
- bundle  · 给 N 个 subtask 出一份**执行** prompt(串行 / 并行 hint)

Cohesion / conflict heuristic(轻量启发式 · 不调 LLM · M17 §4):

| Dimension              | Cohesion +/- |
|------------------------|--------------|
| 同 module              | +3           |
| 同 code file (path_only)| +2          |
| 同 doc anchor path     | +1           |
| depends_on chain       | +2(序贯 bundle)|
| 同 file lines 重叠     | -5(red flag)|
| 跨 sprint              | -1           |

Bundle score = avg pairwise cohesion - max pairwise conflict。

CLI:
    docs-cockpit prompt --bundle M07-f75501,M07-53a63a,M11-S1
    docs-cockpit prompt --bundle M07-f75501,M07-53a63a --copy
"""

from __future__ import annotations

import itertools
import pathlib
import re
from typing import Any

try:
    import jinja2
    from jinja2.sandbox import SandboxedEnvironment

    _JINJA2_AVAILABLE = True
except ImportError:  # pragma: no cover
    _JINJA2_AVAILABLE = False
    jinja2 = None  # type: ignore


# ─── Subtask lookup helpers ───────────────────────────────────────────────


def _index_subtasks(modules: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """{subtask_id: subtask + injected module_id / sprint / depends_on}.

    在 module 上下文里查 subtask 时太繁琐 · index 一次给所有后续 helper 复用。
    """
    out: dict[str, dict[str, Any]] = {}
    for m in modules:
        mid = m.get("id", "")
        for s in m.get("subtasks") or []:
            sid = s.get("id")
            if not sid:
                continue
            enriched = dict(s)
            enriched["_module_id"] = mid
            enriched["_module_sprint"] = m.get("sprint", "")
            enriched["_module_depends_on"] = list(m.get("depends_on") or [])
            enriched["_module"] = m  # 整个 module dict · render_bundle_prompt 复用
            out[sid] = enriched
    return out


# ─── Cohesion / conflict scoring(轻量启发式 · build-time)──────────────────


def _code_files(subtask: dict[str, Any]) -> set[str]:
    """从 subtask 里收所有 code path(只 file part · 去 lines)· 用 0.13 M11 加的 path_only
    字段;fallback raw path split。"""
    out: set[str] = set()
    for ca in subtask.get("code_anchors") or []:
        po = ca.get("path_only") or (ca.get("path") or "").split(":", 1)[0]
        if po:
            out.add(po)
    return out


def _doc_files(subtask: dict[str, Any]) -> set[str]:
    """所有 doc anchor 的 clean path · 跟 _code_files 对称."""
    out: set[str] = set()
    for da in subtask.get("doc_anchors") or []:
        p = da.get("path") or ""
        if p:
            out.add(p)
    return out


def _code_line_ranges(subtask: dict[str, Any]) -> dict[str, list[tuple[int, int]]]:
    """{file_path: [(start, end), ...]} · 给 conflict overlap 检测用."""
    out: dict[str, list[tuple[int, int]]] = {}
    for ca in subtask.get("code_anchors") or []:
        po = ca.get("path_only") or (ca.get("path") or "").split(":", 1)[0]
        lines = ca.get("lines")
        if not po or not lines:
            continue
        m = re.match(r"^(\d+)(?:-(\d+))?$", str(lines))
        if not m:
            continue
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else start
        out.setdefault(po, []).append((start, end))
    return out


def _lines_overlap(a: list[tuple[int, int]], b: list[tuple[int, int]]) -> bool:
    """任一 range 对相交都返 True."""
    for s1, e1 in a:
        for s2, e2 in b:
            if not (e1 < s2 or e2 < s1):
                return True
    return False


def cohesion_score(a: dict[str, Any], b: dict[str, Any]) -> int:
    """Pairwise cohesion · 高 = 适合 bundle 一起跑。"""
    score = 0
    if a.get("_module_id") and a["_module_id"] == b.get("_module_id"):
        score += 3
    code_a = _code_files(a)
    code_b = _code_files(b)
    if code_a & code_b:
        score += 2
    doc_a = _doc_files(a)
    doc_b = _doc_files(b)
    if doc_a & doc_b:
        score += 1
    # depends_on chain · A 的 module 依赖 B 的 module(或反过来) · +2
    a_deps = set(a.get("_module_depends_on") or [])
    b_deps = set(b.get("_module_depends_on") or [])
    if (a.get("_module_id") in b_deps) or (b.get("_module_id") in a_deps):
        score += 2
    return score


def conflict_score(a: dict[str, Any], b: dict[str, Any]) -> int:
    """Pairwise conflict · 高 = 不该 bundle(merge 冲突 / 跨 sprint 等)。"""
    score = 0
    # same file lines overlap
    la = _code_line_ranges(a)
    lb = _code_line_ranges(b)
    for f in la.keys() & lb.keys():
        if _lines_overlap(la[f], lb[f]):
            score += 5
            break  # 一处冲突就够 red flag · 不累加多次
    # 跨 sprint
    if (
        a.get("_module_sprint")
        and b.get("_module_sprint")
        and a["_module_sprint"] != b["_module_sprint"]
    ):
        score += 1
    return score


def bundle_score(subtasks: list[dict[str, Any]]) -> dict[str, Any]:
    """整 bundle 的 cohesion + conflict 汇总 + 推荐顺序。

    Returns:
        {
          "n": int,
          "avg_cohesion": float,
          "max_conflict": int,
          "score": float (avg_cohesion - max_conflict),
          "verdict": "highly cohesive" | "ok" | "weak" | "conflict",
          "order": list[str] (subtask ids, 推荐执行顺序),
          "notes": list[str] (人话解释),
        }
    """
    n = len(subtasks)
    notes: list[str] = []
    if n < 2:
        return {
            "n": n,
            "avg_cohesion": 0.0,
            "max_conflict": 0,
            "score": 0.0,
            "verdict": "single",
            "order": [s.get("id") for s in subtasks],
            "notes": ["Single subtask · use `docs-cockpit prompt` instead of bundle"],
        }

    pairs = list(itertools.combinations(subtasks, 2))
    cohesions = [cohesion_score(a, b) for a, b in pairs]
    conflicts = [conflict_score(a, b) for a, b in pairs]
    avg_coh = sum(cohesions) / len(cohesions)
    max_conf = max(conflicts) if conflicts else 0
    score = avg_coh - max_conf

    if max_conf >= 5:
        verdict = "conflict"
        notes.append(
            "⚠ At least one pair edits overlapping line ranges in the same file · "
            "consider splitting this bundle to avoid merge conflicts"
        )
    elif avg_coh >= 4:
        verdict = "highly cohesive"
        notes.append(
            "✅ Strong cohesion · these subtasks share module / file / docs · "
            "good fit for a single batch"
        )
    elif avg_coh >= 2:
        verdict = "ok"
        notes.append(
            "Acceptable cohesion · bundle works but not particularly efficient"
        )
    else:
        verdict = "weak"
        notes.append(
            "Weak cohesion · these subtasks have little overlap · "
            "consider running them separately"
        )

    return {
        "n": n,
        "avg_cohesion": round(avg_coh, 2),
        "max_conflict": max_conf,
        "score": round(score, 2),
        "verdict": verdict,
        "order": recommended_order(subtasks),
        "notes": notes,
    }


def recommended_order(subtasks: list[dict[str, Any]]) -> list[str]:
    """Sort 推荐执行顺序:
    1. 走 depends_on chain · 上游 module 先(M07 in M08.depends_on → M07 先)
    2. 同 module · 沿 frontmatter 中的 subtask 顺序
    3. fallback · by subtask.id
    """
    # 简化 toposort · O(n^2) 够用(N 通常 <20)
    by_id = {s.get("id"): s for s in subtasks if s.get("id")}
    ids = list(by_id.keys())

    def depth(sid: str, visited: set[str]) -> int:
        """depends_on chain 深度 · upstream 在更浅层."""
        if sid in visited:
            return 0
        visited.add(sid)
        s = by_id[sid]
        deps = set(s.get("_module_depends_on") or [])
        # 在选中范围内的依赖
        scoped = [o for o in ids if by_id[o].get("_module_id") in deps]
        if not scoped:
            return 0
        return 1 + max(depth(o, visited) for o in scoped)

    return sorted(
        ids,
        key=lambda sid: (
            depth(sid, set()),
            by_id[sid].get("_module_id", ""),
            sid,
        ),
    )


# ─── Bundle prompt render ─────────────────────────────────────────────────


def _builtin_templates_dir() -> pathlib.Path:
    return pathlib.Path(__file__).parent / "templates" / "prompts"


def _build_jinja_env(repo_root: pathlib.Path) -> Any:
    if not _JINJA2_AVAILABLE:
        raise RuntimeError(
            "Jinja2 not installed · `pip install jinja2` to use docs-cockpit bundle"
        )
    user_dir = repo_root / "docs" / "prompts"
    loaders = []
    if user_dir.exists():
        loaders.append(jinja2.FileSystemLoader(str(user_dir)))
    loaders.append(jinja2.FileSystemLoader(str(_builtin_templates_dir())))
    return SandboxedEnvironment(
        loader=jinja2.ChoiceLoader(loaders),
        undefined=jinja2.Undefined,
        autoescape=False,
        keep_trailing_newline=True,
    )


def render_bundle_prompt(
    subtask_ids: list[str],
    modules: list[dict[str, Any]],
    repo_root: pathlib.Path,
) -> str:
    """Render bundle prompt · 给 CLI `--bundle <ids>` 或 sidecar 用.

    Args:
        subtask_ids: 用户选的 subtask id list(顺序不重要 · 内部走 recommended_order)
        modules: state.json 的 modules[] 完整 list
        repo_root: 跟其它 render_* 一致 · git branch / Loader sandbox 用

    Returns:
        bundle prompt 字符串 · 或 错误信息(找不到 subtask 等)
    """
    if not subtask_ids:
        return "# Bundle is empty · no subtasks selected."
    index = _index_subtasks(modules)
    selected = [index[sid] for sid in subtask_ids if sid in index]
    missing = [sid for sid in subtask_ids if sid not in index]
    if not selected:
        return (
            f"# Bundle error · no subtasks found in state.json.\n"
            f"# Missing ids: {missing}"
        )

    # 推荐顺序 + 评分
    order = recommended_order(selected)
    ordered = [index[sid] for sid in order]
    score = bundle_score(selected)

    # 收集共享上下文 · 每个 module 出现一次 / 每个 doc 出现一次
    seen_modules: dict[str, dict[str, Any]] = {}
    seen_code_files: dict[str, list[str]] = {}  # path → [subtask_id, ...]
    seen_doc_anchors: dict[str, list[str]] = {}  # raw → [subtask_id, ...]
    for s in ordered:
        m = s["_module"]
        seen_modules.setdefault(m["id"], m)
        for cf in _code_files(s):
            seen_code_files.setdefault(cf, []).append(s["id"])
        for da in s.get("doc_anchors") or []:
            raw = da.get("raw") or da.get("path") or ""
            if raw:
                seen_doc_anchors.setdefault(raw, []).append(s["id"])

    env = _build_jinja_env(repo_root)
    tmpl = env.get_template("bundle.md.j2")
    return tmpl.render(
        subtasks=ordered,
        modules=list(seen_modules.values()),
        shared_code_files=seen_code_files,
        shared_doc_anchors=seen_doc_anchors,
        score=score,
        missing=missing,
        repo_root=str(repo_root),
    )


# ─── Build-time sidecar · cohesion meta + common pre-rendered bundles ───


def render_bundle_meta(modules: list[dict[str, Any]]) -> dict[str, Any]:
    """给 backlog UI 用的 meta · 每对 subtask 的 cohesion / conflict 提前算好.

    Output:
        {
          "pairs": {"M07-A__M07-B": {"cohesion": 5, "conflict": 0}, ...},
          "by_subtask": {"M07-A": {"top_cohesive": ["M07-B", "M11-X", ...]}, ...},
        }

    JSON size:N subtask 平方 · N=80 → 3200 pair · ~150KB · 可接受。
    """
    index = _index_subtasks(modules)
    ids = sorted(index.keys())
    pairs: dict[str, dict[str, int]] = {}
    by_subtask: dict[str, dict[str, list[str]]] = {}
    for a_id, b_id in itertools.combinations(ids, 2):
        a, b = index[a_id], index[b_id]
        coh = cohesion_score(a, b)
        conf = conflict_score(a, b)
        if coh == 0 and conf == 0:
            continue  # 稀疏 · 0 不写入 sidecar 省体积
        key = f"{a_id}__{b_id}"
        pairs[key] = {"cohesion": coh, "conflict": conf}
        by_subtask.setdefault(a_id, {"top_cohesive": []})["top_cohesive"].append(b_id)
        by_subtask.setdefault(b_id, {"top_cohesive": []})["top_cohesive"].append(a_id)
    # 给 by_subtask top_cohesive 按 cohesion 排序裁前 5
    for sid, info in by_subtask.items():
        info["top_cohesive"] = sorted(
            info["top_cohesive"],
            key=lambda o: -(
                pairs.get(f"{min(sid, o)}__{max(sid, o)}", {}).get("cohesion", 0)
            ),
        )[:5]
    return {"pairs": pairs, "by_subtask": by_subtask}


# ─── CLI dispatch ────────────────────────────────────────────────────────


def cmd_bundle_prompt(args) -> int:
    """`docs-cockpit prompt --bundle <ids>` dispatcher · 被 build.py::cmd_prompt 接住。

    本函数被独立调用 · 也可被 cmd_prompt 内嵌(主 prompt subcommand 加 --bundle 路径)。
    """
    import json
    import sys

    raw = getattr(args, "bundle", None)
    if not raw:
        print("[ERR] --bundle <id1>,<id2>,... required", file=sys.stderr)
        return 2
    subtask_ids = [s.strip() for s in raw.split(",") if s.strip()]
    if not subtask_ids:
        print("[ERR] empty bundle · no subtask ids parsed", file=sys.stderr)
        return 2

    cfg_path = pathlib.Path(getattr(args, "config", None) or "docs-cockpit.yaml")
    state_path = cfg_path.parent / "docs" / "state.json"
    if not state_path.exists():
        print(
            f"[ERR] state.json not found at {state_path} · run `docs-cockpit build` first",
            file=sys.stderr,
        )
        return 2
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[ERR] state.json parse failed: {e}", file=sys.stderr)
        return 2
    text = render_bundle_prompt(
        subtask_ids, state.get("modules") or [], cfg_path.parent.resolve()
    )

    if getattr(args, "copy", False):
        try:
            import pyperclip

            pyperclip.copy(text)
            print(
                f"[bundle] {len(subtask_ids)} subtask prompt copied to clipboard · "
                f"paste to Claude / Codex",
                file=sys.stderr,
            )
        except ImportError:
            print(
                "[bundle] pyperclip not installed · falling back to stdout",
                file=sys.stderr,
            )
            print(text)
    else:
        print(text)
    return 0
