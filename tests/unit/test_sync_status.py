"""Unit tests for M09 sync-status (`docs_cockpit/sync_status.py`).

覆盖:parse_overrides JSON 解析 / module-grouping / merge_to_md 走 M08 backend /
compute_conflicts stale subtask 检测 / sync_to_repo end-to-end + .bak 写回 /
CLI Path 2 (--from-browser) stub 报错。
"""

from __future__ import annotations

import json
import pathlib

import pytest

from docs_cockpit.sync_status import (
    SyncStatusError,
    compute_conflicts,
    merge_to_md,
    parse_overrides,
    sync_to_repo,
)


# ─── parse_overrides ──────────────────────────────────────────────────


class TestParseOverrides:
    def test_minimal(self):
        text = json.dumps(
            {
                "_built_at": "2026-05-19 12:10",
                "M07__st__M07-9db754": True,
                "M07__st__M07-f75501": False,
            }
        )
        result = parse_overrides(text)
        assert result == {
            "M07": {"M07-9db754": True, "M07-f75501": False}
        }

    def test_multi_module(self):
        text = json.dumps(
            {
                "M01__st__M01-S1": True,
                "M07__st__M07-9db754": True,
            }
        )
        result = parse_overrides(text)
        assert "M01" in result and "M07" in result

    def test_module_level_override_ignored(self):
        # module-level dict value · MVP 跳过
        text = json.dumps(
            {
                "M07__st__M07-9db754": True,
                "M03": {"status": "done", "progress": 100},
            }
        )
        result = parse_overrides(text)
        assert "M03" not in result
        assert result["M07"] == {"M07-9db754": True}

    def test_underscore_keys_skipped(self):
        text = json.dumps({"_built_at": "x", "_exported_at": "y"})
        assert parse_overrides(text) == {}

    def test_invalid_json_raises(self):
        with pytest.raises(SyncStatusError):
            parse_overrides("{not json")

    def test_non_dict_top_level_raises(self):
        with pytest.raises(SyncStatusError):
            parse_overrides("[1,2,3]")


# ─── merge_to_md · 走 M08 apply_patch backend ─────────────────────────


class TestMergeToMd:
    def test_body_checklist_tick(self, tmp_path: pathlib.Path):
        from docs_cockpit.schema import _subtask_id_for

        sid = _subtask_id_for("M07", "do something")
        md = tmp_path / "M07.md"
        md.write_text(
            """---
id: M07
---

## 待办

- [ ] do something
""",
            encoding="utf-8",
        )
        result = merge_to_md("M07", {sid: True}, md)
        assert sid in result["applied_ids"]
        assert "- [x] do something" in result["new_text"]
        assert result["wrote"] is False  # merge_to_md never writes

    def test_done_false_is_noop(self, tmp_path: pathlib.Path):
        """优先级规则:localStorage done=false 不强 force-untick · 信 MD."""
        from docs_cockpit.schema import _subtask_id_for

        sid = _subtask_id_for("M07", "already done")
        md = tmp_path / "M07.md"
        md.write_text(
            """---
id: M07
---

## 待办

- [x] already done
""",
            encoding="utf-8",
        )
        result = merge_to_md("M07", {sid: False}, md)
        # done=false 在 MVP 里跳过 · 不构造 patch · 应该 0 applied
        assert result["applied_ids"] == []

    def test_missing_md_raises(self, tmp_path: pathlib.Path):
        with pytest.raises(SyncStatusError):
            merge_to_md("M07", {"x": True}, tmp_path / "nonexistent.md")


# ─── compute_conflicts ────────────────────────────────────────────────


class TestComputeConflicts:
    def test_module_not_in_state(self):
        overrides = {"M999": {"M999-x": True}}
        state = [{"id": "M07", "subtasks": [{"id": "M07-1"}]}]
        warnings = compute_conflicts(overrides, state)
        assert any("M999" in w for w in warnings)

    def test_subtask_not_in_module(self):
        overrides = {"M07": {"M07-stale": True}}
        state = [{"id": "M07", "subtasks": [{"id": "M07-other"}]}]
        warnings = compute_conflicts(overrides, state)
        assert any("M07-stale" in w for w in warnings)

    def test_clean_no_conflicts(self):
        overrides = {"M07": {"M07-1": True}}
        state = [{"id": "M07", "subtasks": [{"id": "M07-1"}]}]
        assert compute_conflicts(overrides, state) == []


# ─── sync_to_repo · E2E ───────────────────────────────────────────────


class TestSyncToRepo:
    def _setup_fixture(self, tmp_path: pathlib.Path):
        """Build a minimal docs-cockpit project + state.json by hand."""
        from docs_cockpit.schema import _subtask_id_for

        cfg = tmp_path / "docs-cockpit.yaml"
        cfg.write_text(
            """project:
  name: Test
  output: docs/index.html
paths:
  repo: "."
modules:
  files:
    - docs/spec/module/M07.md
""",
            encoding="utf-8",
        )
        md_dir = tmp_path / "docs" / "spec" / "module"
        md_dir.mkdir(parents=True)
        sid = _subtask_id_for("M07", "lane a")
        md = md_dir / "M07.md"
        md.write_text(
            """---
id: M07
title: Test Module
sprint: "0.12"
status: not-started
progress: 0
---

## 待办

- [ ] lane a
- [ ] lane b
""",
            encoding="utf-8",
        )
        # hand-craft state.json (跳过 build · 单元测试不依赖完整 build pipeline)
        state = {
            "modules": [
                {
                    "id": "M07",
                    "path": str(md),
                    "subtasks": [
                        {"id": sid, "title": "lane a", "done": False},
                    ],
                }
            ]
        }
        state_path = tmp_path / "docs" / "state.json"
        state_path.write_text(json.dumps(state), encoding="utf-8")
        return cfg, md, sid

    def test_dry_run(self, tmp_path: pathlib.Path):
        cfg, md, sid = self._setup_fixture(tmp_path)
        json_text = json.dumps({f"M07__st__{sid}": True})
        result = sync_to_repo(json_text, cfg, apply=False)
        assert len(result["per_module"]) == 1
        assert result["per_module"][0]["applied_ids"] == [sid]
        assert result["wrote_files"] == []
        # MD 没动
        assert "- [ ] lane a" in md.read_text(encoding="utf-8")

    def test_apply_writes_with_bak(self, tmp_path: pathlib.Path):
        cfg, md, sid = self._setup_fixture(tmp_path)
        json_text = json.dumps({f"M07__st__{sid}": True})
        result = sync_to_repo(json_text, cfg, apply=True)
        assert len(result["wrote_files"]) == 1
        # MD 改了
        assert "- [x] lane a" in md.read_text(encoding="utf-8")
        # .bak 存在 + 是原内容
        bak = md.with_suffix(".md.bak")
        assert bak.exists()
        assert "- [ ] lane a" in bak.read_text(encoding="utf-8")

    def test_missing_state_json_raises(self, tmp_path: pathlib.Path):
        cfg = tmp_path / "docs-cockpit.yaml"
        cfg.write_text("project: {}\n", encoding="utf-8")
        with pytest.raises(SyncStatusError):
            sync_to_repo("{}", cfg)

    def test_stale_subtask_ref_global_warning(self, tmp_path: pathlib.Path):
        cfg, md, sid = self._setup_fixture(tmp_path)
        # override 引用一个不存在的 subtask id
        json_text = json.dumps({"M07__st__M07-stale": True})
        result = sync_to_repo(json_text, cfg, apply=False)
        assert any("M07-stale" in w for w in result["global_warnings"])


# ─── CLI Path 2 · from-browser(0.14.3 M09-b23cac · Chrome stub · Firefox 完整)─


class TestCmdFromBrowser:
    def test_from_browser_chrome_stub_returns_error(self, capsys, tmp_path: pathlib.Path):
        """Chrome 是 MVP stub · 报指向 Export workflow 的错(M09-b23cac partial · v0.15 候选)."""
        from docs_cockpit.sync_status import cmd_sync_status

        # 构造一个 fake chrome profile · 让 find_profile_dir 找得到 · 进入 read_chrome
        # 报「not yet implemented」错(读不了 Chrome LevelDB · pure-stdlib limitation)
        fake_profile = tmp_path / "Default"
        ldb = fake_profile / "Local Storage" / "leveldb"
        ldb.mkdir(parents=True)
        # 模拟 Chrome LOCALAPPDATA 环境(Windows)· 让 find_profile_dir 找到上面这个
        # macOS/Linux:home/Library or .config · 难 mock · 简化测试改成直接 patch
        from docs_cockpit import browser_storage as bs
        import unittest.mock as _mock

        with _mock.patch.object(bs, "find_profile_dir", return_value=fake_profile):
            class A:
                from_browser = "chrome"
                import_path = None
                apply = False
                config = "docs-cockpit.yaml"
                profile = None

            rc = cmd_sync_status(A())
            assert rc == 2
            captured = capsys.readouterr()
            assert "not yet implemented" in captured.err.lower()
            assert "Export" in captured.err

    def test_no_import_no_browser(self, capsys):
        from docs_cockpit.sync_status import cmd_sync_status

        class A:
            from_browser = None
            import_path = None
            apply = False
            config = "docs-cockpit.yaml"

        rc = cmd_sync_status(A())
        assert rc == 2
        captured = capsys.readouterr()
        assert "required" in captured.err.lower()
