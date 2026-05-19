"""Lightweight integration test for dashboard render structure (M14-d865c1 / M14-022d30).

不走 pytest-playwright(避免引 browser binary dep)· 直接对 build 出的 HTML 做 string
+ DOM structure check。Hash router 行为(`#/module/X` 切 split-mode)是 client-side
JS · 这层只验静态 HTML 含必需元素 + CSS rules · 行为留 pytest-playwright (v0.15+)。

覆盖:
- backlog page / split page / bundle bar 三个新容器 default 状态 = hidden
- 各 hidden 元素都有显式 `[hidden] { display: none }` CSS override
- topbar 含 Backlog / Export 按钮
- bundle-meta.js sidecar script tag
"""

from __future__ import annotations

import pathlib
import re
import sys

import pytest


@pytest.fixture(scope="module")
def built_html() -> str:
    """Build the dogfood project once and return generated HTML string."""
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root))
    try:
        from docs_cockpit.cli import main as cli_main

        rc = cli_main(["build", "-c", str(repo_root / "docs-cockpit.yaml")])
        assert rc == 0, "fixture build failed"
    finally:
        sys.path.pop(0)
    html_path = repo_root / "docs" / "index.html"
    assert html_path.exists(), "build did not produce docs/index.html"
    return html_path.read_text(encoding="utf-8")


# ─── Static HTML structure · M14-d865c1 ───────────────────────────────────


class TestDashboardRootStructure:
    """Default HTML(no JS evaluation)should have all dashboard sections visible
    by structure · split-page / backlog-page / bundle-bar all `hidden` attribute."""

    def test_kanban_section_in_html(self, built_html):
        assert 'id="kanban-section"' in built_html

    def test_sprints_section_in_html(self, built_html):
        assert 'id="sprints-section"' in built_html

    def test_hero_section_in_html(self, built_html):
        assert 'id="hero-section"' in built_html

    def test_split_page_hidden_by_default(self, built_html):
        # split-page is a sub-page · NOT visible on dashboard root · `hidden` attribute set
        assert re.search(
            r'<section[^>]*id="split-page"[^>]*\shidden\b',
            built_html,
        ) is not None

    def test_backlog_page_hidden_by_default(self, built_html):
        assert re.search(
            r'<section[^>]*id="backlog-page"[^>]*\shidden\b',
            built_html,
        ) is not None

    def test_bundle_bar_hidden_by_default(self, built_html):
        assert re.search(
            r'<aside[^>]*id="bundle-bar"[^>]*\shidden\b',
            built_html,
        ) is not None


# ─── CSS specificity safety · 4 hidden elements need explicit override ───


class TestCssHiddenOverrides:
    """0.12.1 暴露的 specificity bug · author CSS `.split-page { display: grid }` 跟
    UA `[hidden] { display: none }` specificity 同级 · 必须 explicit override。
    本测确保 v0.14.3 audit pass · 4 个 hidden 元素全有 explicit rule。"""

    @pytest.mark.parametrize(
        "selector",
        [
            r"\.back-btn\[hidden\]",
            r"\.split-page\[hidden\]",
            r"\.backlog-page\[hidden\]",
            r"\.bundle-bar\[hidden\]",
        ],
    )
    def test_explicit_hidden_override_present(self, built_html, selector):
        # 形如 `.split-page[hidden] { display: none; }` 必须出现在 CSS
        pattern = selector + r"\s*\{\s*display:\s*none"
        assert re.search(pattern, built_html) is not None, (
            f"Missing explicit [hidden] override for {selector} · CSS specificity bug risk"
        )


# ─── Topbar 入口 · backlog / export buttons ──────────────────────────────


class TestTopbarEntries:
    def test_backlog_button_in_topbar(self, built_html):
        assert 'id="open-backlog"' in built_html
        assert "Backlog" in built_html or "backlog" in built_html

    def test_export_button_in_topbar(self, built_html):
        assert 'id="export-overrides"' in built_html

    def test_sysdocs_button_in_topbar(self, built_html):
        assert 'id="open-docs"' in built_html


# ─── Sidecar script tags · prompts.js / prompts-refine.js / bundle-meta.js ─


class TestSidecarScripts:
    def test_prompts_js_script_tag(self, built_html):
        assert 'src="prompts.js"' in built_html

    def test_prompts_refine_js_script_tag(self, built_html):
        assert 'src="prompts-refine.js"' in built_html

    def test_bundle_meta_js_script_tag(self, built_html):
        # 0.14.0 M17 sidecar · 给 backlog UI cohesion verdict 用
        assert 'src="bundle-meta.js"' in built_html


# ─── Backlog filter bar elements ────────────────────────────────────────


class TestBacklogFilterBar:
    def test_filter_time_select_present(self, built_html):
        assert 'id="backlog-filter-time"' in built_html

    def test_filter_sprint_select_present(self, built_html):
        assert 'id="backlog-filter-sprint"' in built_html

    def test_filter_status_select_present(self, built_html):
        assert 'id="backlog-filter-status"' in built_html

    def test_filter_search_input_present(self, built_html):
        assert 'id="backlog-filter-search"' in built_html

    def test_filter_clear_button_present(self, built_html):
        assert 'id="backlog-filter-clear"' in built_html


# ─── Bundle bar controls ────────────────────────────────────────────────


class TestBundleBarControls:
    def test_bb_copy_button_present(self, built_html):
        assert 'id="bb-copy"' in built_html

    def test_bb_clear_button_present(self, built_html):
        assert 'id="bb-clear"' in built_html

    def test_bb_count_span_present(self, built_html):
        assert 'id="bb-count"' in built_html
