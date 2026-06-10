"""Unit tests for v0.16.0 doc_language + subtask title lint(`docs_cockpit/schema.py`).

覆盖:
- detect_doc_language 启发式判定 (zh-CN / en / 混合)
- _has_mixed_language 跨 project lang 检测
- _title_has_anchor_ref 抓 §N.M / 文件名 / 行号 / 函数名
- lint_subtask_titles 产 doc-lang-mix + title-has-anchor Issue
- 白名单 tech token 不触发 mix warning
"""

from __future__ import annotations

import pathlib

import pytest

from docs_cockpit.schema import (
    Issue,
    _has_mixed_language,
    _title_has_anchor_ref,
    detect_doc_language,
    lint_subtask_titles,
)


# ─── detect_doc_language ──────────────────────────────────────────────


class TestDetectDocLanguage:
    def test_empty_modules_default_en(self):
        assert detect_doc_language([]) == "en"
        assert detect_doc_language(None) == "en"

    def test_all_chinese_titles_zh(self):
        modules = [
            {"title": "看板模块"},
            {"title": "导出工具"},
            {"title": "权限管理"},
        ]
        assert detect_doc_language(modules) == "zh-CN"

    def test_all_english_titles_en(self):
        modules = [
            {"title": "Module Kanban"},
            {"title": "Export Tool"},
        ]
        assert detect_doc_language(modules) == "en"

    def test_majority_zh_with_some_en_terms(self):
        # CJK 占比超 30% 算 zh-CN
        modules = [
            {"title": "MCP server 接入"},      # CJK 优势
            {"title": "用户数据导出 API"},      # CJK 优势
            {"title": "权限校验"},
        ]
        assert detect_doc_language(modules) == "zh-CN"

    def test_majority_en_with_some_cjk(self):
        modules = [
            {"title": "Build Engine"},
            {"title": "Apply Patch CLI"},
            {"title": "MCP server"},
            {"title": "导出工具"},  # 只 1 个 zh · 不到 30%
        ]
        assert detect_doc_language(modules) == "en"


# ─── _has_mixed_language ──────────────────────────────────────────────


class TestHasMixedLanguage:
    def test_zh_project_pure_chinese_ok(self):
        assert _has_mixed_language("实现资源池借还机制", "zh-CN") is False

    def test_zh_project_with_whitelist_tokens_ok(self):
        # API / MCP / CLI 等白名单 token 不触发 mix
        assert _has_mixed_language("实现 MCP server 的 stdio 接入", "zh-CN") is False
        assert _has_mixed_language("升级 CLI 到 JSON 输出", "zh-CN") is False

    def test_zh_project_with_single_loanword_ok(self):
        # 单个非白名单 loanword(server / stdio / cockpit 等)不算混 · 这是自然中文-技术写法
        assert _has_mixed_language("实现 MCP server 的接入", "zh-CN") is False
        assert _has_mixed_language("把 cockpit 接通", "zh-CN") is False

    def test_zh_project_with_english_prose_word_warns(self):
        # 含 English prose 词(implement / the / of / when 等)= 真混 · 不是 loanword
        assert _has_mixed_language("实现 implement 资源池", "zh-CN") is True
        assert _has_mixed_language("the resource pool 借还", "zh-CN") is True
        assert _has_mixed_language("处理 when 接收 packet", "zh-CN") is True

    def test_en_project_pure_english_ok(self):
        assert _has_mixed_language("Implement resource pool", "en") is False

    def test_en_project_with_cjk_warns(self):
        assert _has_mixed_language("Implement 资源池 borrow/return", "en") is True

    def test_empty_title_no_warn(self):
        assert _has_mixed_language("", "zh-CN") is False
        assert _has_mixed_language("", "en") is False


# ─── _title_has_anchor_ref ────────────────────────────────────────────


class TestTitleHasAnchorRef:
    def test_section_number_caught(self):
        ok, sample = _title_has_anchor_ref("Lane F · DATA_SCHEMA §3.1 同步")
        assert ok is True
        assert sample == "§3.1"

    def test_multi_section_caught(self):
        ok, sample = _title_has_anchor_ref("加 §1.2.3 + §4.5 章节")
        assert ok is True
        assert sample.startswith("§")

    def test_file_path_md_caught(self):
        ok, sample = _title_has_anchor_ref("更新 DATA_SCHEMA.md 字段")
        assert ok is True
        assert "DATA_SCHEMA.md" in sample

    def test_file_path_py_caught(self):
        ok, sample = _title_has_anchor_ref("修 sourcery/worker/pool.py 的逻辑")
        assert ok is True
        assert "pool.py" in sample

    def test_line_range_caught(self):
        ok, sample = _title_has_anchor_ref("修 something at :42-89 处")
        assert ok is True
        assert ":42-89" in sample

    def test_function_name_caught(self):
        ok, sample = _title_has_anchor_ref("调用 borrow_resource() 时加 retry")
        assert ok is True
        assert "borrow_resource()" in sample

    def test_clean_title_passes(self):
        assert _title_has_anchor_ref("实现资源池借还机制")[0] is False
        assert _title_has_anchor_ref("Implement resource pool borrow/return")[0] is False

    def test_empty_title_passes(self):
        assert _title_has_anchor_ref("")[0] is False


# ─── lint_subtask_titles ──────────────────────────────────────────────


class TestLintSubtaskTitles:
    def _mk(self, title: str, mid: str = "M01", sid: str = "M01-S1"):
        return {
            "id": mid,
            "title": "Module",
            "path": f"docs/spec/module/{mid}.md",
            "subtasks": [{"id": sid, "title": title}],
        }

    def test_clean_title_no_issues(self):
        m = self._mk("实现资源池借还机制")
        issues = lint_subtask_titles([m], "zh-CN")
        assert issues == []

    def test_zh_mix_warns(self):
        # English prose 词 'the' 触发 mix
        m = self._mk("实现 the resource pool 借还机制")
        issues = lint_subtask_titles([m], "zh-CN")
        kinds = [i.message for i in issues]
        assert any("mixes languages" in msg for msg in kinds)

    def test_anchor_in_title_warns(self):
        m = self._mk("Lane F · DATA_SCHEMA.md §3.1 同步")
        issues = lint_subtask_titles([m], "zh-CN")
        # 命中 anchor(DATA_SCHEMA.md + §3.1)+ 可能命中 mix(Lane / F)
        assert any("anchor-like ref" in i.message for i in issues)

    def test_both_warns_together(self):
        # 同时含 English prose ('implement') + anchor (§3.1)
        m = self._mk("implement 同步 §3.1 schema 的逻辑")
        issues = lint_subtask_titles([m], "zh-CN")
        msgs = [i.message for i in issues]
        assert any("mixes languages" in msg for msg in msgs)
        assert any("anchor-like ref" in msg for msg in msgs)

    def test_severity_is_warn(self):
        m = self._mk("M1.2 Lane F · DATA_SCHEMA.md §3.1 同步")
        issues = lint_subtask_titles([m], "zh-CN")
        for i in issues:
            assert i.severity == "warn"

    def test_reference_points_to_title_rules(self):
        # v1.0 · author skill 删除后 reference 改指 references/schema.md 的现存节
        m = self._mk("Lane F · §3.1 同步")
        issues = lint_subtask_titles([m], "zh-CN")
        for i in issues:
            assert "references/schema.md" in i.reference
            assert "subtask title 4 法则" in i.reference

    def test_en_project_mix_with_cjk(self):
        m = self._mk("Implement 资源池 borrow/return")
        issues = lint_subtask_titles([m], "en")
        assert any("mixes languages" in i.message for i in issues)

    def test_empty_modules_no_crash(self):
        assert lint_subtask_titles(None, "zh-CN") == []
        assert lint_subtask_titles([], "zh-CN") == []
