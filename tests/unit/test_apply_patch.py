"""Unit tests for M08 apply-patch (`docs_cockpit/apply_patch.py`).

覆盖:parse_patch 校验 / Path 1 frontmatter merge / Path 2 body checklist /
diff 生成 / 文件写回 + .bak / 冲突场景。
"""

from __future__ import annotations

import pathlib

import pytest

from docs_cockpit.apply_patch import (
    ALLOWED_FIELDS,
    PatchFormatError,
    apply_patch_to_file,
    apply_to_md,
    compute_diff,
    parse_patch,
)


# ─── parse_patch ──────────────────────────────────────────────────────


class TestParsePatch:
    def test_minimal_valid(self):
        text = """
subtasks:
  - id: M07-9db754
    status: done
"""
        result = parse_patch(text)
        assert result["subtasks"] == [{"id": "M07-9db754", "status": "done"}]
        assert result["_warnings"] == []

    def test_code_and_docs_lists(self):
        text = """
subtasks:
  - id: M07-a
    code: ["a.py:1-10", "b.py:5-9"]
    docs: ["plan.md#§1"]
"""
        result = parse_patch(text)
        assert result["subtasks"][0]["code"] == ["a.py:1-10", "b.py:5-9"]
        assert result["subtasks"][0]["docs"] == ["plan.md#§1"]

    def test_disallowed_field_filtered_with_warning(self):
        text = """
subtasks:
  - id: M07-a
    title: "trying to rewrite title"
    status: done
"""
        result = parse_patch(text)
        # title 不在白名单 · drop + warn
        assert "title" not in result["subtasks"][0]
        assert result["subtasks"][0]["status"] == "done"
        assert any("title" in w for w in result["_warnings"])

    def test_missing_id_skipped(self):
        text = """
subtasks:
  - status: done
  - id: M07-good
    status: done
"""
        result = parse_patch(text)
        assert len(result["subtasks"]) == 1
        assert result["subtasks"][0]["id"] == "M07-good"
        assert any("missing string 'id'" in w for w in result["_warnings"])

    def test_empty_id_skipped(self):
        text = """
subtasks:
  - id: ""
    status: done
"""
        result = parse_patch(text)
        assert result["subtasks"] == []
        assert any("missing string 'id'" in w for w in result["_warnings"])

    def test_top_level_not_dict_raises(self):
        with pytest.raises(PatchFormatError):
            parse_patch("- just\n- a\n- list\n")

    def test_no_subtasks_key_raises(self):
        with pytest.raises(PatchFormatError):
            parse_patch("not_subtasks: foo\n")

    def test_subtasks_not_list_raises(self):
        with pytest.raises(PatchFormatError):
            parse_patch("subtasks: foo\n")

    def test_invalid_yaml_raises(self):
        with pytest.raises(PatchFormatError):
            parse_patch("subtasks:\n  - id: x\n :::malformed")

    def test_allowed_fields_set(self):
        # canary · 任何人加 ALLOWED_FIELDS 都要顺手加 doc + 测试
        assert ALLOWED_FIELDS == frozenset({"status", "code", "docs", "desc"})


# ─── apply_to_md · Path 1 frontmatter ──────────────────────────────────


class TestApplyFrontmatterPath:
    def test_merge_status(self):
        md = """---
id: M01
title: Demo
subtasks:
  - id: M01-S1
    title: foo
    status: not-started
---
body
"""
        patch = {"subtasks": [{"id": "M01-S1", "status": "done"}], "_warnings": []}
        new_text, applied, conflicts = apply_to_md(patch, md)
        assert "M01-S1" in applied
        assert conflicts == []
        assert "status: done" in new_text
        assert "status: not-started" not in new_text

    def test_merge_code_and_docs(self):
        md = """---
id: M01
subtasks:
  - id: M01-S1
    title: foo
    status: not-started
---
"""
        patch = {
            "subtasks": [
                {
                    "id": "M01-S1",
                    "code": ["sourcery/x.py:42-89"],
                    "docs": ["plan.md#§1"],
                }
            ],
            "_warnings": [],
        }
        new_text, applied, _ = apply_to_md(patch, md)
        assert "M01-S1" in applied
        assert "sourcery/x.py:42-89" in new_text
        assert "plan.md#§1" in new_text

    def test_unknown_id_conflict(self):
        md = """---
id: M01
subtasks:
  - id: M01-S1
    title: foo
---
"""
        patch = {"subtasks": [{"id": "M01-NOPE", "status": "done"}], "_warnings": []}
        _, applied, conflicts = apply_to_md(patch, md)
        assert applied == []
        assert any("M01-NOPE" in c for c in conflicts)


# ─── apply_to_md · Path 2 body checklist ───────────────────────────────


class TestApplyBodyChecklistPath:
    def test_tick_checkbox(self):
        # id derivation 走 _subtask_id_for(module_id, title)
        # title="Lane A" + module_id="M09" → sha1("Lane A")[:6]
        from docs_cockpit.schema import _subtask_id_for

        sid = _subtask_id_for("M09", "Lane A")
        md = """---
id: M09
---

## 3 · 待办

- [ ] Lane A
- [ ] Lane B
"""
        patch = {"subtasks": [{"id": sid, "status": "done"}], "_warnings": []}
        new_text, applied, conflicts = apply_to_md(patch, md)
        assert applied == [sid]
        assert conflicts == []
        assert "- [x] Lane A" in new_text
        assert "- [ ] Lane B" in new_text  # 不动其它

    def test_append_code_and_docs_annotations(self):
        from docs_cockpit.schema import _subtask_id_for

        sid = _subtask_id_for("M09", "Lane A")
        md = """---
id: M09
---

## 待办

- [ ] Lane A
"""
        patch = {
            "subtasks": [
                {
                    "id": sid,
                    "code": ["worker/a.py:10-30"],
                    "docs": ["plan.md#§2"],
                }
            ],
            "_warnings": [],
        }
        new_text, applied, _ = apply_to_md(patch, md)
        assert applied == [sid]
        assert "@code:worker/a.py:10-30" in new_text
        assert "@docs:plan.md#§2" in new_text

    def test_dedupe_existing_annotation(self):
        from docs_cockpit.schema import _subtask_id_for

        sid = _subtask_id_for("M09", "Lane A")
        md = """---
id: M09
---

## 待办

- [ ] Lane A @code:existing.py:1-10
"""
        patch = {
            "subtasks": [{"id": sid, "code": ["existing.py:1-10", "new.py:5-9"]}],
            "_warnings": [],
        }
        new_text, _, _ = apply_to_md(patch, md)
        # existing.py 只能出现 1 次 · new.py 加进来
        assert new_text.count("@code:existing.py:1-10") == 1
        assert "@code:new.py:5-9" in new_text

    def test_no_section_conflict(self):
        # MD 没 `## 待办` section 也没 frontmatter subtasks → 全部 conflict
        md = """---
id: M09
---

无 待办 section · 也无 frontmatter subtasks
"""
        patch = {"subtasks": [{"id": "M09-xxx", "status": "done"}], "_warnings": []}
        _, applied, conflicts = apply_to_md(patch, md)
        assert applied == []
        assert any("M09-xxx" in c for c in conflicts)

    def test_title_changed_conflict(self):
        # 用户改了 title · id 不再 derive 自原 title · 反查失败
        md = """---
id: M09
---

## 待办

- [ ] Lane A NEW NAME
"""
        from docs_cockpit.schema import _subtask_id_for

        sid_old = _subtask_id_for("M09", "Lane A")
        patch = {"subtasks": [{"id": sid_old, "status": "done"}], "_warnings": []}
        _, applied, conflicts = apply_to_md(patch, md)
        assert applied == []
        assert any(sid_old in c for c in conflicts)


# ─── compute_diff ─────────────────────────────────────────────────────


class TestComputeDiff:
    def test_no_change_empty_diff(self):
        assert compute_diff("abc\n", "abc\n") == ""

    def test_simple_change_present(self):
        diff = compute_diff("foo\n", "bar\n", label="test.md")
        assert "test.md" in diff
        assert "-foo" in diff
        assert "+bar" in diff


# ─── apply_patch_to_file (E2E with tmp_path) ──────────────────────────


class TestApplyPatchToFile:
    def test_dry_run_no_write(self, tmp_path: pathlib.Path):
        md = tmp_path / "M01.md"
        md.write_text(
            """---
id: M01
subtasks:
  - id: M01-S1
    title: foo
    status: not-started
---
""",
            encoding="utf-8",
        )
        result = apply_patch_to_file(
            "subtasks:\n  - id: M01-S1\n    status: done\n", md, apply=False
        )
        assert result["wrote"] is False
        assert result["bak_path"] is None
        assert result["applied_ids"] == ["M01-S1"]
        # MD 内容没动
        assert "status: not-started" in md.read_text(encoding="utf-8")

    def test_apply_writes_with_bak(self, tmp_path: pathlib.Path):
        md = tmp_path / "M01.md"
        original = """---
id: M01
subtasks:
  - id: M01-S1
    title: foo
    status: not-started
---
"""
        md.write_text(original, encoding="utf-8")
        result = apply_patch_to_file(
            "subtasks:\n  - id: M01-S1\n    status: done\n", md, apply=True
        )
        assert result["wrote"] is True
        assert result["bak_path"] is not None
        # MD 已改
        assert "status: done" in md.read_text(encoding="utf-8")
        # .bak 是原内容
        bak = pathlib.Path(result["bak_path"])
        assert bak.exists()
        assert bak.read_text(encoding="utf-8") == original

    def test_missing_file_raises(self, tmp_path: pathlib.Path):
        with pytest.raises(FileNotFoundError):
            apply_patch_to_file(
                "subtasks:\n  - id: x\n    status: done\n",
                tmp_path / "nope.md",
                apply=False,
            )

    def test_no_change_no_bak(self, tmp_path: pathlib.Path):
        # patch 指向不存在的 id · 0 applied · 即便 --apply 也不写 + 不 .bak
        md = tmp_path / "M01.md"
        md.write_text(
            """---
id: M01
subtasks:
  - id: M01-S1
    title: foo
---
""",
            encoding="utf-8",
        )
        result = apply_patch_to_file(
            "subtasks:\n  - id: M01-NOPE\n    status: done\n", md, apply=True
        )
        assert result["wrote"] is False
        assert result["bak_path"] is None
        assert (md.parent / "M01.md.bak").exists() is False
