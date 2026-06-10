"""Integration tests · v1.1 render 解析 docs/HEALTH.md → payload["health"]（H-Task 3）.

设计 spec · docs/plans/P-v1.1-health-check.md。
HEALTH.md 走固定路径探测({repo}/docs/HEALTH.md)· 不进 config 扫描组 ·
build_payload 末段把 frontmatter 透传成 payload["health"](state.json 顶层新 key)。

覆盖:
- 合法 HEALTH.md → health key 全字段透传 + body(前端 marked 渲染用)
- 无 HEALTH.md → health 显式为 None(state.json additive-only · 消费者判空稳定)
- frontmatter 非法(缺 grade / 整个缺失)→ issues 含 category="health-report"
  且 health 仍 degraded 解析(体检报告坏了不能拖垮看板)
- YAML 原生 date → ISO 字符串(state.json JSON 可序列化)
- known_module_ids 接线 · 处方 module 反链指向未知 module → warn
- Watch 项:HEALTH.md 被误配进 modules scan 组 → 不崩 · 不进 modules ·
  validate_meta 报错存在(固化现状防回归 · 不要求去重逻辑)
"""

from __future__ import annotations

import json
import pathlib

import pytest

from docs_cockpit.build import build_payload


# ─── fixture 工具 · tmp 项目搭建 ──────────────────────────────────────

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


def _write_health(tmp_path: pathlib.Path, content: str) -> pathlib.Path:
    docs = tmp_path / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    p = docs / "HEALTH.md"
    p.write_text(content, encoding="utf-8")
    return p


def _config_with_module(tmp_path: pathlib.Path) -> dict:
    """最小项目 config · 含 1 个 id=M01 的 module(处方反链校验用)."""
    mod_dir = tmp_path / "modules"
    mod_dir.mkdir(parents=True, exist_ok=True)
    (mod_dir / "M01.md").write_text(
        "---\nid: M01\ntitle: Module One\nstatus: in-progress\nprogress: 50\n"
        "sprint: S1\ndesc: test module\n---\n\n# M01\n",
        encoding="utf-8",
    )
    return {
        "project": {"name": "health-test", "mark": "H"},
        "modules": {"files": [{"title": "M01", "path": str(mod_dir / "M01.md")}]},
    }


def _build(tmp_path: pathlib.Path, config: dict):
    return build_payload(config, {"repo": str(tmp_path)}, "2026-06-11 00:00")


# ─── 1 · 合法 HEALTH.md → health key 全字段透传 ───────────────────────


class TestValidHealthPassthrough:
    def test_health_key_present_and_dict(self, tmp_path):
        _write_health(tmp_path, VALID_HEALTH_MD)
        payload, _ = _build(tmp_path, _config_with_module(tmp_path))
        assert "health" in payload
        assert isinstance(payload["health"], dict)

    def test_all_fields_passthrough(self, tmp_path):
        _write_health(tmp_path, VALID_HEALTH_MD)
        payload, _ = _build(tmp_path, _config_with_module(tmp_path))
        h = payload["health"]
        assert h["grade"] == "B+"
        assert h["mode"] == "quick"
        assert h["date"] == "2026-06-10"
        assert isinstance(h["departments"], list) and len(h["departments"]) == 2
        assert h["departments"][0]["verdict"] == "pass"
        assert isinstance(h["prescriptions"], list) and len(h["prescriptions"]) == 1
        assert h["prescriptions"][0]["id"] == "RX-001"
        assert isinstance(h["accepted_debts"], list) and len(h["accepted_debts"]) == 1
        assert h["next_checkup"] == "本 sprint 收尾快检 · 30 天深检"

    def test_body_passthrough_frontmatter_stripped(self, tmp_path):
        # body = frontmatter 后原文 · 前端 marked 渲染用 · 不含 YAML 块
        _write_health(tmp_path, VALID_HEALTH_MD)
        payload, _ = _build(tmp_path, _config_with_module(tmp_path))
        body = payload["health"]["body"]
        assert "体检报告正文" in body
        assert "grade: B+" not in body
        assert "type: health-report" not in body

    def test_valid_report_no_health_issues(self, tmp_path):
        _write_health(tmp_path, VALID_HEALTH_MD)
        _, issues = _build(tmp_path, _config_with_module(tmp_path))
        health_issues = [i for i in issues if i.category == "health-report"]
        assert health_issues == []


# ─── 2 · 无 HEALTH.md → health 显式 None ─────────────────────────────


class TestNoHealthFile:
    def test_health_key_is_none(self, tmp_path):
        payload, issues = _build(tmp_path, _config_with_module(tmp_path))
        # key 必须显式存在(state.json additive-only · 消费者判空稳定)
        assert "health" in payload
        assert payload["health"] is None
        # 没有体检报告不是病 · 不产生 health-report issues
        assert [i for i in issues if i.category == "health-report"] == []


# ─── 3 · frontmatter 非法 → issues + degraded 解析 ────────────────────


class TestDegradedParsing:
    def test_missing_grade_reports_issue_but_health_survives(self, tmp_path):
        broken = VALID_HEALTH_MD.replace("grade: B+\n", "")
        _write_health(tmp_path, broken)
        payload, issues = _build(tmp_path, _config_with_module(tmp_path))
        health_issues = [i for i in issues if i.category == "health-report"]
        assert any(i.field == "grade" and i.severity == "error" for i in health_issues)
        # degraded:缺啥给 None · 其余字段照常解析 · 不抛异常不阻断渲染
        h = payload["health"]
        assert h is not None
        assert h["grade"] is None
        assert h["mode"] == "quick"
        assert len(h["departments"]) == 2

    def test_issue_path_points_at_health_file(self, tmp_path):
        broken = VALID_HEALTH_MD.replace("grade: B+\n", "")
        health_path = _write_health(tmp_path, broken)
        _, issues = _build(tmp_path, _config_with_module(tmp_path))
        health_issues = [i for i in issues if i.category == "health-report"]
        assert health_issues
        assert all(
            pathlib.Path(str(i.path)).name == health_path.name for i in health_issues
        )

    def test_no_frontmatter_at_all_still_degraded(self, tmp_path):
        # 整个 frontmatter 缺失 → error issue · health 仍是 dict(全 None/[])
        _write_health(tmp_path, "# 只有正文没有 frontmatter\n\n内容。\n")
        payload, issues = _build(tmp_path, _config_with_module(tmp_path))
        health_issues = [i for i in issues if i.category == "health-report"]
        assert any(i.severity == "error" for i in health_issues)
        h = payload["health"]
        assert h is not None
        assert h["grade"] is None
        assert h["departments"] == []
        assert h["prescriptions"] == []
        assert h["accepted_debts"] == []
        assert "只有正文没有 frontmatter" in h["body"]

    def test_unknown_module_backlink_warns(self, tmp_path):
        # known_module_ids 接线证明:处方 module 指向不存在的 module → warn
        bad_link = VALID_HEALTH_MD.replace("module: M01", "module: M-GHOST")
        _write_health(tmp_path, bad_link)
        _, issues = _build(tmp_path, _config_with_module(tmp_path))
        assert any(
            i.category == "health-report"
            and i.severity == "warn"
            and "M-GHOST" in i.message
            for i in issues
        )


# ─── 4 · YAML 原生 date → ISO 字符串(JSON 可序列化)──────────────────


class TestDateSerialization:
    def test_native_yaml_date_becomes_iso_string(self, tmp_path):
        # VALID_HEALTH_MD 的 `date: 2026-06-10` 不带引号 · yaml.safe_load
        # 解析成 datetime.date · 透传后必须是 ISO 字符串
        _write_health(tmp_path, VALID_HEALTH_MD)
        payload, _ = _build(tmp_path, _config_with_module(tmp_path))
        d = payload["health"]["date"]
        assert isinstance(d, str)
        assert d == "2026-06-10"

    def test_payload_json_serializable(self, tmp_path):
        # state.json 写出依赖 json.dumps · health 子树不得混入非序列化对象
        _write_health(tmp_path, VALID_HEALTH_MD)
        payload, _ = _build(tmp_path, _config_with_module(tmp_path))
        json.dumps(payload["health"], ensure_ascii=False)  # 不抛即过


# ─── 5 · Watch 项:HEALTH.md 被误配进 modules scan 组 ─────────────────


class TestHealthInScanGroup:
    """用户把 modules scan 指到 docs/(HEALTH.md 所在目录)· 固化现状:
    build 不崩 · HEALTH.md 无 id 不进 modules · validate_meta 报错存在 ·
    health key 照常解析(不要求去重逻辑)。"""

    @pytest.fixture()
    def scan_payload_issues(self, tmp_path):
        _write_health(tmp_path, VALID_HEALTH_MD)
        config = {
            "project": {"name": "scan-test", "mark": "S"},
            "modules": {"scan": {"dir": str(tmp_path / "docs")}},
        }
        return _build(tmp_path, config)

    def test_build_does_not_crash_and_health_parsed(self, scan_payload_issues):
        payload, _ = scan_payload_issues
        assert isinstance(payload["health"], dict)
        assert payload["health"]["grade"] == "B+"

    def test_health_md_not_rendered_as_module(self, scan_payload_issues):
        # HEALTH.md frontmatter 无 id → _build_card 返 None → 不进 modules
        payload, _ = scan_payload_issues
        assert all(
            "HEALTH" not in str(m.get("path", "")) for m in payload["modules"]
        )

    def test_validate_meta_complains_but_build_survives(self, scan_payload_issues):
        # 现状:validate_meta 把 HEALTH.md 当普通 module 校验 → 报缺 id 等
        # 这是可接受的提示(用户配错了扫描组)· 不是 crash
        _, issues = scan_payload_issues
        non_health = [
            i for i in issues
            if i.category != "health-report"
            and pathlib.Path(str(i.path)).name == "HEALTH.md"
        ]
        assert non_health, "expected validate_meta issues for misconfigured HEALTH.md"
