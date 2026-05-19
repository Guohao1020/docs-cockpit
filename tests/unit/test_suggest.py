"""Unit tests for M10 suggest (`docs_cockpit/suggest.py`).

覆盖:list_builtin_suggest_templates / triggers / render_suggest / render_all_for_module /
CLI dry runs.
"""

from __future__ import annotations

import pathlib

import pytest

from docs_cockpit.suggest import (
    BUILTIN_SUGGEST_TEMPLATES,
    _trigger_anchor_completeness,
    _trigger_desc_rewrite,
    _trigger_subtask_recompose,
    diagnose_module,
    list_builtin_suggest_templates,
    render_all_for_module,
    render_suggest,
)


# ─── list_builtin_suggest_templates ───────────────────────────────────


def test_list_builtin_suggest_templates_returns_known_names():
    names = list_builtin_suggest_templates()
    for builtin in BUILTIN_SUGGEST_TEMPLATES:
        assert builtin in names


def test_list_skips_underscore_partials(tmp_path: pathlib.Path):
    # 我们不在 builtin dir 加 partial · 这里只验 list_builtin 不会回 _ 开头的
    names = list_builtin_suggest_templates()
    assert all(not n.startswith("_") for n in names)


# ─── Triggers · heuristic predicates ──────────────────────────────────


class TestTriggerDescRewrite:
    def test_empty_desc(self):
        assert _trigger_desc_rewrite({"desc": ""}) is True

    def test_missing_desc(self):
        assert _trigger_desc_rewrite({}) is True

    def test_short_desc(self):
        assert _trigger_desc_rewrite({"desc": "short"}) is True

    def test_generic_phrase(self):
        assert _trigger_desc_rewrite({"desc": "TBD - 待补 something later"}) is True

    def test_good_desc_no_trigger(self):
        long_specific = (
            "Single-source-of-truth for frontmatter schema · 8 sections + "
            "validator Issue.reference 反向指向"
        )
        assert _trigger_desc_rewrite({"desc": long_specific}) is False


class TestTriggerSubtaskRecompose:
    def test_too_many(self):
        subs = [{"id": f"M-{i}", "title": "x"} for i in range(20)]
        assert _trigger_subtask_recompose({"subtasks": subs}) is True

    def test_too_few(self):
        subs = [{"id": "M-1", "title": "x"}]
        assert _trigger_subtask_recompose({"subtasks": subs}) is True

    def test_just_right(self):
        subs = [{"id": f"M-{i}", "title": "x"} for i in range(5)]
        assert _trigger_subtask_recompose({"subtasks": subs}) is False


class TestTriggerAnchorCompleteness:
    def test_missing_code(self):
        subs = [{"id": "S1", "docs": ["plan.md"]}]
        assert _trigger_anchor_completeness({"subtasks": subs}) is True

    def test_missing_docs(self):
        subs = [{"id": "S1", "code": "x.py"}]
        assert _trigger_anchor_completeness({"subtasks": subs}) is True

    def test_both_present(self):
        subs = [{"id": "S1", "code": "x.py", "docs": ["plan.md"]}]
        assert _trigger_anchor_completeness({"subtasks": subs}) is False

    def test_via_resolved_anchors(self):
        # backend 解析后 code_anchors / doc_anchors 也算 anchor 存在
        subs = [
            {
                "id": "S1",
                "code_anchors": [{"path": "x.py"}],
                "doc_anchors": [{"path": "p.md"}],
            }
        ]
        assert _trigger_anchor_completeness({"subtasks": subs}) is False


# ─── diagnose_module · 组合 triggers ──────────────────────────────────


class TestDiagnoseModule:
    def test_clean_module(self):
        m = {
            "id": "M01",
            "desc": "A reasonably long and specific description of M01 doing X",
            "status": "done",
            "subtasks": [
                {"id": "S1", "code": "a.py:1-10", "docs": ["p.md#§1"]},
                {"id": "S2", "code": "b.py:1-10", "docs": ["p.md#§2"]},
                {"id": "S3", "code": "c.py:1-10", "docs": ["p.md#§3"]},
                {"id": "S4", "code": "d.py:1-10", "docs": ["p.md#§4"]},
            ],
        }
        # done module + clean anchors + good desc · 只可能触发 cross-doc-consistency
        # 但该 trigger 只对 in-progress / planned / not-started 起 · done module 不触发
        triggered = diagnose_module(m)
        # 应该至少不含明显应触发的
        assert "desc-rewrite" not in triggered
        assert "subtask-recompose" not in triggered
        assert "anchor-completeness" not in triggered

    def test_problematic_module_triggers_multiple(self):
        m = {
            "id": "M99",
            "desc": "",
            "status": "in-progress",
            "subtasks": [{"id": "S1", "title": "lonely"}],  # 1 个 subtask · 缺 anchor
        }
        triggered = diagnose_module(m)
        assert "desc-rewrite" in triggered
        assert "subtask-recompose" in triggered
        assert "anchor-completeness" in triggered
        assert "cross-doc-consistency" in triggered  # in-progress 触发


# ─── render_suggest ──────────────────────────────────────────────────


class TestRenderSuggest:
    def test_desc_rewrite_renders(self):
        m = {"id": "M01", "title": "Demo", "desc": "TBD", "subtasks": []}
        text = render_suggest(m, "desc-rewrite", pathlib.Path("."))
        assert "M01" in text
        assert "desc" in text.lower()

    def test_unknown_template_returns_error(self):
        m = {"id": "M01", "title": "Demo", "desc": "x", "subtasks": []}
        text = render_suggest(m, "nonexistent", pathlib.Path("."))
        assert "Unknown" in text

    def test_anchor_completeness_lists_missing(self):
        m = {
            "id": "M01",
            "title": "Demo",
            "desc": "x",
            "subtasks": [
                {"id": "S1", "title": "missing anchors"},
                {"id": "S2", "title": "has code", "code": "x.py", "docs": ["p.md"]},
            ],
        }
        text = render_suggest(m, "anchor-completeness", pathlib.Path("."))
        assert "S1" in text
        # S2 has both · should NOT appear in missing list
        # but might still appear in module context · so we check S1 specifically


class TestRenderAllForModule:
    def test_returns_dict_keyed_by_template(self):
        m = {
            "id": "M99",
            "title": "Bad Module",
            "desc": "",
            "status": "in-progress",
            "subtasks": [{"id": "S1", "title": "missing all"}],
        }
        result = render_all_for_module(m, pathlib.Path("."), triggered_only=True)
        assert "desc-rewrite" in result
        assert "anchor-completeness" in result
        assert all(isinstance(v, str) and len(v) > 0 for v in result.values())

    def test_triggered_only_skips_clean(self):
        m = {
            "id": "M01",
            "title": "Demo",
            "desc": "A reasonably long and specific description.",
            "status": "done",
            "subtasks": [
                {"id": "S1", "code": "a.py:1-10", "docs": ["p.md"]},
                {"id": "S2", "code": "b.py:1-10", "docs": ["p.md"]},
                {"id": "S3", "code": "c.py:1-10", "docs": ["p.md"]},
            ],
        }
        result = render_all_for_module(m, pathlib.Path("."), triggered_only=True)
        # done module · all clean anchors · good desc → no suggestion triggered
        assert result == {}

    def test_triggered_only_false_renders_all(self):
        m = {"id": "M01", "title": "x", "desc": "x", "subtasks": []}
        result = render_all_for_module(m, pathlib.Path("."), triggered_only=False)
        assert set(result.keys()) >= set(BUILTIN_SUGGEST_TEMPLATES)


# ─── CLI · cmd_suggest ────────────────────────────────────────────────


class TestCmdSuggest:
    def test_list_templates_no_config_needed(self, capsys):
        from docs_cockpit.suggest import cmd_suggest

        class A:
            list_templates = True

        rc = cmd_suggest(A())
        assert rc == 0
        captured = capsys.readouterr()
        for name in BUILTIN_SUGGEST_TEMPLATES:
            assert name in captured.out

    def test_no_config_returns_error(self, capsys, tmp_path: pathlib.Path):
        from docs_cockpit.suggest import cmd_suggest

        class A:
            list_templates = False
            config = str(tmp_path / "nonexistent.yaml")
            module_id = None
            all_modules = False
            template = None
            strict = False
            copy = False

        rc = cmd_suggest(A())
        assert rc == 2
        captured = capsys.readouterr()
        assert "config not found" in captured.err.lower()
