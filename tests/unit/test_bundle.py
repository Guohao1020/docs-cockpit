"""Unit tests for M17 bundle (`docs_cockpit/bundle.py`).

覆盖:cohesion / conflict scoring · recommended_order · render_bundle_prompt ·
render_bundle_meta sidecar shape · CLI dispatch path.
"""

from __future__ import annotations

import pathlib

import pytest

from docs_cockpit.bundle import (
    _index_subtasks,
    bundle_score,
    cohesion_score,
    conflict_score,
    recommended_order,
    render_bundle_meta,
    render_bundle_prompt,
)


def _mk_module(mid, sprint="0.14", depends_on=None, subtasks=None):
    return {
        "id": mid,
        "title": f"Module {mid}",
        "status": "in-progress",
        "progress": 30,
        "desc": f"{mid} test module",
        "sprint": sprint,
        "depends_on": depends_on or [],
        "subtasks": subtasks or [],
    }


def _mk_subtask(sid, title, code=None, docs=None):
    s = {"id": sid, "title": title, "status": "not-started", "done": False}
    if code:
        s["code_anchors"] = [
            {"path": c, "path_only": c.split(":", 1)[0], "lines": (c.split(":", 1)[1] if ":" in c else None), "exists": True}
            for c in code
        ]
    if docs:
        s["doc_anchors"] = [
            {"raw": d, "path": d.split(":", 1)[0].split("#", 1)[0], "exists": True}
            for d in docs
        ]
    return s


# ─── cohesion_score ──────────────────────────────────────────────────


class TestCohesionScore:
    def test_same_module(self):
        modules = [_mk_module("M07", subtasks=[
            _mk_subtask("M07-A", "a"),
            _mk_subtask("M07-B", "b"),
        ])]
        idx = _index_subtasks(modules)
        assert cohesion_score(idx["M07-A"], idx["M07-B"]) == 3

    def test_same_code_file(self):
        modules = [
            _mk_module("M07", subtasks=[_mk_subtask("M07-A", "a", code=["worker/x.py:1-10"])]),
            _mk_module("M08", subtasks=[_mk_subtask("M08-A", "a", code=["worker/x.py:20-30"])]),
        ]
        idx = _index_subtasks(modules)
        # different modules · same code file → +2
        assert cohesion_score(idx["M07-A"], idx["M08-A"]) == 2

    def test_same_doc_anchor(self):
        modules = [
            _mk_module("M07", subtasks=[_mk_subtask("M07-A", "a", docs=["plan.md#§1"])]),
            _mk_module("M08", subtasks=[_mk_subtask("M08-A", "a", docs=["plan.md:88-100"])]),
        ]
        idx = _index_subtasks(modules)
        # different modules · same doc file (after stripping anchor) → +1
        assert cohesion_score(idx["M07-A"], idx["M08-A"]) == 1

    def test_depends_on_chain(self):
        modules = [
            _mk_module("M07", subtasks=[_mk_subtask("M07-A", "a")]),
            _mk_module("M08", depends_on=["M07"], subtasks=[_mk_subtask("M08-A", "a")]),
        ]
        idx = _index_subtasks(modules)
        # M08 depends_on M07 → bidirectional cohesion +2
        assert cohesion_score(idx["M07-A"], idx["M08-A"]) == 2

    def test_compounding(self):
        # same module + same file + same doc → 3 + 2 + 1 = 6
        modules = [_mk_module("M07", subtasks=[
            _mk_subtask("M07-A", "a", code=["x.py"], docs=["plan.md"]),
            _mk_subtask("M07-B", "b", code=["x.py"], docs=["plan.md"]),
        ])]
        idx = _index_subtasks(modules)
        assert cohesion_score(idx["M07-A"], idx["M07-B"]) == 3 + 2 + 1

    def test_zero_unrelated(self):
        modules = [
            _mk_module("M07", sprint="0.11", subtasks=[_mk_subtask("M07-A", "a", code=["a.py"])]),
            _mk_module("M08", sprint="0.12", subtasks=[_mk_subtask("M08-A", "a", code=["b.py"])]),
        ]
        idx = _index_subtasks(modules)
        assert cohesion_score(idx["M07-A"], idx["M08-A"]) == 0


# ─── conflict_score ──────────────────────────────────────────────────


class TestConflictScore:
    def test_same_file_lines_overlap(self):
        modules = [
            _mk_module("M07", subtasks=[
                _mk_subtask("M07-A", "a", code=["x.py:10-20"]),
                _mk_subtask("M07-B", "b", code=["x.py:15-25"]),
            ])
        ]
        idx = _index_subtasks(modules)
        # 同 file lines 重叠 → +5 (red flag)
        assert conflict_score(idx["M07-A"], idx["M07-B"]) >= 5

    def test_same_file_disjoint_lines_no_conflict(self):
        modules = [
            _mk_module("M07", subtasks=[
                _mk_subtask("M07-A", "a", code=["x.py:10-20"]),
                _mk_subtask("M07-B", "b", code=["x.py:30-40"]),
            ])
        ]
        idx = _index_subtasks(modules)
        # disjoint lines → no overlap conflict
        assert conflict_score(idx["M07-A"], idx["M07-B"]) == 0

    def test_cross_sprint(self):
        modules = [
            _mk_module("M07", sprint="0.11", subtasks=[_mk_subtask("M07-A", "a")]),
            _mk_module("M08", sprint="0.13", subtasks=[_mk_subtask("M08-A", "a")]),
        ]
        idx = _index_subtasks(modules)
        assert conflict_score(idx["M07-A"], idx["M08-A"]) == 1


# ─── recommended_order ───────────────────────────────────────────────


class TestRecommendedOrder:
    def test_depends_on_chain_ordering(self):
        # M07 → M08 → M09 (M09 depends_on M08, M08 depends_on M07)
        modules = [
            _mk_module("M07", subtasks=[_mk_subtask("M07-A", "a")]),
            _mk_module("M08", depends_on=["M07"], subtasks=[_mk_subtask("M08-A", "a")]),
            _mk_module("M09", depends_on=["M08"], subtasks=[_mk_subtask("M09-A", "a")]),
        ]
        idx = _index_subtasks(modules)
        order = recommended_order([idx["M09-A"], idx["M07-A"], idx["M08-A"]])
        # 上游先 · M07 → M08 → M09
        assert order.index("M07-A") < order.index("M08-A") < order.index("M09-A")

    def test_independent_stable_sort(self):
        modules = [_mk_module("M07", subtasks=[
            _mk_subtask("M07-B", "b"),
            _mk_subtask("M07-A", "a"),
        ])]
        idx = _index_subtasks(modules)
        # 无 dep · 同 module · 走 id 字母序
        order = recommended_order([idx["M07-B"], idx["M07-A"]])
        assert order == ["M07-A", "M07-B"]


# ─── bundle_score ────────────────────────────────────────────────────


class TestBundleScore:
    def test_single_subtask_verdict(self):
        modules = [_mk_module("M07", subtasks=[_mk_subtask("M07-A", "a")])]
        idx = _index_subtasks(modules)
        r = bundle_score([idx["M07-A"]])
        assert r["verdict"] == "single"
        assert r["n"] == 1

    def test_highly_cohesive_verdict(self):
        modules = [_mk_module("M07", subtasks=[
            _mk_subtask("M07-A", "a", code=["x.py:1-10"], docs=["plan.md#§1"]),
            _mk_subtask("M07-B", "b", code=["x.py:20-30"], docs=["plan.md#§2"]),
        ])]
        idx = _index_subtasks(modules)
        r = bundle_score([idx["M07-A"], idx["M07-B"]])
        # 同 module(3) + 同 code file(2) + 同 doc path(1) = 6
        assert r["avg_cohesion"] >= 4
        assert r["verdict"] == "highly cohesive"

    def test_conflict_verdict(self):
        modules = [_mk_module("M07", subtasks=[
            _mk_subtask("M07-A", "a", code=["x.py:10-20"]),
            _mk_subtask("M07-B", "b", code=["x.py:15-25"]),
        ])]
        idx = _index_subtasks(modules)
        r = bundle_score([idx["M07-A"], idx["M07-B"]])
        assert r["verdict"] == "conflict"
        assert r["max_conflict"] >= 5

    def test_weak_verdict(self):
        modules = [
            _mk_module("M07", sprint="0.11", subtasks=[_mk_subtask("M07-A", "a")]),
            _mk_module("M08", sprint="0.14", subtasks=[_mk_subtask("M08-A", "a")]),
        ]
        idx = _index_subtasks(modules)
        r = bundle_score([idx["M07-A"], idx["M08-A"]])
        assert r["verdict"] == "weak"


# ─── render_bundle_prompt ────────────────────────────────────────────


class TestRenderBundlePrompt:
    def test_renders_with_basic_fields(self, tmp_path):
        modules = [_mk_module("M07", subtasks=[
            _mk_subtask("M07-A", "first thing", code=["x.py:1-10"]),
            _mk_subtask("M07-B", "second thing", code=["x.py:20-30"]),
        ])]
        text = render_bundle_prompt(["M07-A", "M07-B"], modules, tmp_path)
        assert "M07-A" in text
        assert "M07-B" in text
        assert "first thing" in text
        assert "second thing" in text
        # 共享 code file 一次给
        assert "x.py" in text

    def test_missing_ids_reported(self, tmp_path):
        modules = [_mk_module("M07", subtasks=[_mk_subtask("M07-A", "a")])]
        text = render_bundle_prompt(["M07-A", "M99-NONEXISTENT"], modules, tmp_path)
        assert "M07-A" in text
        assert "M99-NONEXISTENT" in text  # 在 missing 列表里报

    def test_empty_bundle(self, tmp_path):
        text = render_bundle_prompt([], [], tmp_path)
        assert "empty" in text.lower()

    def test_all_missing_returns_error(self, tmp_path):
        text = render_bundle_prompt(["X-1", "X-2"], [], tmp_path)
        assert "error" in text.lower()


# ─── render_bundle_meta · sidecar shape ──────────────────────────────


class TestRenderBundleMeta:
    def test_emits_pairs_and_by_subtask(self):
        modules = [_mk_module("M07", subtasks=[
            _mk_subtask("M07-A", "a", code=["x.py:1-10"]),
            _mk_subtask("M07-B", "b", code=["x.py:20-30"]),
            _mk_subtask("M07-C", "c", code=["y.py:1-10"]),
        ])]
        meta = render_bundle_meta(modules)
        assert "pairs" in meta
        assert "by_subtask" in meta
        # A-B 同 file 同 module · pair entry exists
        key = "M07-A__M07-B"
        assert key in meta["pairs"]
        assert meta["pairs"][key]["cohesion"] >= 5  # module(3) + file(2)

    def test_zero_cohesion_pairs_skipped(self):
        # 完全独立 · cohesion=0 conflict=0 · pair 应被省略(sparse)
        modules = [
            _mk_module("M07", sprint="0.14", subtasks=[_mk_subtask("M07-A", "a")]),
            _mk_module("M08", sprint="0.14", subtasks=[_mk_subtask("M08-A", "a")]),
        ]
        meta = render_bundle_meta(modules)
        # M07-A, M08-A · 同 sprint(无 conflict)· 跨 module 无 code/doc 共用 = 0
        assert f"M07-A__M08-A" not in meta["pairs"]

    def test_by_subtask_top_cohesive(self):
        modules = [_mk_module("M07", subtasks=[
            _mk_subtask("M07-A", "a", code=["x.py:1-10"]),
            _mk_subtask("M07-B", "b", code=["x.py:20-30"]),
            _mk_subtask("M07-C", "c", code=["x.py:40-50"]),
        ])]
        meta = render_bundle_meta(modules)
        # M07-A 的 top_cohesive 应含 M07-B 和 M07-C(都是高分 pair)
        assert "M07-A" in meta["by_subtask"]
        assert set(meta["by_subtask"]["M07-A"]["top_cohesive"]) == {"M07-B", "M07-C"}
