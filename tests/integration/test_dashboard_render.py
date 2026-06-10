"""Lightweight integration test for dashboard render structure (M14-d865c1 / M14-022d30).

不走 pytest-playwright(避免引 browser binary dep)· 直接对 build 出的 HTML 做 string
+ DOM structure check。Hash router 行为(`#/module/X` 切 split-mode)是 client-side
JS · 这层只验静态 HTML 含必需元素 + CSS rules · 行为留 pytest-playwright (v0.15+)。

覆盖:
- backlog page / split page / bundle bar 三个新容器 default 状态 = hidden
- 各 hidden 元素都有显式 `[hidden] { display: none }` CSS override
- topbar 含 Backlog / Export 按钮
- 反向断言：bundle-meta.js / prompts-refine.js 不得再被引用（防 ghost 引用）
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


# ─── Sidecar script tags · v1.0 起只剩 prompts.js(Copy prompt CTA 数据源)─
# prompts-refine.js / bundle-meta.js 随认知 CLI 层删除 · 模板不得再引用(防 ghost 引用)


class TestSidecarScripts:
    def test_prompts_js_script_tag(self, built_html):
        assert 'src="prompts.js"' in built_html

    def test_removed_cognitive_sidecars_not_referenced(self, built_html):
        assert 'src="prompts-refine.js"' not in built_html
        assert 'src="bundle-meta.js"' not in built_html


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


# ─── v1.1 · Health badge + panel(H-Task 4)─────────────────────────────
# 模板是静态的(render_html 只换 __DOCS_JSON__)· 徽章/面板 DOM 由 JS 在
# RAW.health 非空时动态创建(el.id 属性赋值 · 不走 innerHTML 字面量)。
# 所以这层的断言锚点是:payload JSON(产物里唯一随 health 变化的部分)
# + JS 机件字面量 + i18n key 注册 —— 而「老项目零变化」的硬约束
# 翻译成静态断言就是:`id="health-badge"` 节点字面量永远不许出现在产物里。

VALID_HEALTH_MD = """\
---
type: health-report
date: 2026-06-10
mode: quick
grade: B+
departments:
  - id: dept-tests
    name: 测试
    verdict: pass
    summary: 全绿
  - id: dept-deps
    name: 依赖
    verdict: warn
    summary: 1 个过期依赖
    detail: requests 锁在 2.28 · 上游已 2.32
prescriptions:
  - id: RX-001
    severity: high
    bucket: now
    title: 修复依赖锁
    root_cause: lockfile 未跟随升级
    fix: 重新生成 lockfile
    anchors:
      - "pyproject.toml:1-20"
    module: M01
accepted_debts:
  - item: 老版本 yaml 解析器
    reason: 升级成本高于收益
    review: "2026-09-01"
next_checkup: "本 sprint 收尾快检 · 30 天深检"
---

# 体检报告正文

各科详情见上方 frontmatter。
"""


def _render_project_html(tmp_path: pathlib.Path, with_health: bool) -> str:
    """tmp 项目(1 个 module · 可选 HEALTH.md)→ build_payload → render_html 产物."""
    from docs_cockpit.build import TEMPLATE_PATH, build_payload, render_html

    mod_dir = tmp_path / "modules"
    mod_dir.mkdir(parents=True, exist_ok=True)
    (mod_dir / "M01.md").write_text(
        "---\nid: M01\ntitle: Module One\nstatus: in-progress\nprogress: 50\n"
        "sprint: S1\ndesc: test module\n---\n\n# M01\n",
        encoding="utf-8",
    )
    if with_health:
        docs = tmp_path / "docs"
        docs.mkdir(parents=True, exist_ok=True)
        (docs / "HEALTH.md").write_text(VALID_HEALTH_MD, encoding="utf-8")
    config = {
        "project": {"name": "health-ui-test", "mark": "H"},
        "modules": {"files": [{"title": "M01", "path": str(mod_dir / "M01.md")}]},
    }
    payload, _ = build_payload(config, {"repo": str(tmp_path)}, "2026-06-11 00:00")
    return render_html(TEMPLATE_PATH.read_text(encoding="utf-8"), payload)


@pytest.fixture()
def health_html(tmp_path) -> str:
    return _render_project_html(tmp_path, with_health=True)


@pytest.fixture()
def no_health_html(tmp_path) -> str:
    return _render_project_html(tmp_path, with_health=False)


class TestHealthPanelWithReport:
    """有 HEALTH.md:payload 注入 health 数据 + 模板带齐徽章/面板机件 + i18n 注册。"""

    def test_health_payload_embedded(self, health_html):
        # render_html 用 separators=(",", ":") · JSON 无空格
        assert '"health":{' in health_html
        assert '"grade":"B+"' in health_html

    def test_badge_and_drawer_machinery_present(self, health_html):
        # JS 侧创建徽章 / 面板 drawer 的 hook 字面量(el.id 属性赋值 + openDrawer 调用)
        assert "'health-badge'" in health_html
        assert "'health-drawer'" in health_html

    def test_rx_card_container_present(self, health_html):
        # 处方卡容器 + 卡片 class + H-Task 5 Copy 按钮挂载位
        assert 'id="hd-rx-list"' in health_html
        assert "rx-card" in health_html
        assert "rx-foot" in health_html

    def test_i18n_keys_registered_in_both_locales(self, health_html):
        # 每个 key 在 EN / 中 两本字典各注册一次 → 至少出现 2 次
        for key in (
            "health.badge_label",
            "health.dept_title",
            "health.rx_title",
            "health.bucket_all",
            "health.bucket_now",
            "health.bucket_sprint",
            "health.bucket_backlog",
            "health.bucket_watch",
            "health.bucket_accepted",
            "health.debts_title",
            "health.next_checkup",
            "health.full_report",
        ):
            assert health_html.count("'" + key + "'") >= 2, key


class TestHealthPanelBackwardCompat:
    """无 HEALTH.md:health 显式 null + 静态产物永不含徽章 DOM 节点(老项目零变化)。"""

    def test_health_null_in_payload(self, no_health_html):
        assert '"health":null' in no_health_html

    def test_no_static_badge_dom(self, no_health_html):
        assert 'id="health-badge"' not in no_health_html

    def test_badge_dom_never_static_even_with_health(self, health_html):
        # 防回归:徽章必须保持 JS 动态创建 · 不许有人塞静态节点进模板
        # (静态节点会让 health=null 的老项目长出死 DOM)
        assert 'id="health-badge"' not in health_html
