"""单元测试 · docs_cockpit.schema · plan-eng-review 4A 测试 ambition.

测 schema.py 的核心 API:Issue / validate_meta / extract_subtasks_from_body /
extract_docs_from_body / split_frontmatter / slugify。

0.11.0-alpha.1:Step 1 引入 pytest 时第一批单元测试。
v0.11 W1 加 normalize_subtasks / validate_subtask_schema 时 · 这里继续扩。
"""

from __future__ import annotations

import pathlib

import pytest

from docs_cockpit.schema import (
    DEFAULT_STATUS_RANGES,
    VALID_DOC_TYPES,
    VALID_STATUSES,
    Issue,
    extract_docs_from_body,
    extract_subtasks_from_body,
    slugify,
    split_frontmatter,
    validate_meta,
)


# ── slugify ────────────────────────────────────────────────────
class TestSlugify:
    def test_basic_lowercase(self):
        assert slugify("Hello World") == "hello-world"

    def test_special_chars_collapse(self):
        assert slugify("foo!@#$bar") == "foo-bar"

    def test_chinese_preserved(self):
        # _SLUG_RE 保留中文 · 用于 url hash
        assert slugify("看板与子任务") == "看板与子任务"

    def test_empty_returns_doc(self):
        assert slugify("") == "doc"
        assert slugify("---") == "doc"


# ── split_frontmatter ─────────────────────────────────────────
class TestSplitFrontmatter:
    def test_no_frontmatter_returns_empty_meta(self):
        meta, body = split_frontmatter("# Just a heading\n\ntext")
        assert meta == {}
        assert body == "# Just a heading\n\ntext"

    def test_basic_frontmatter(self):
        content = "---\nid: M01\nstatus: in-progress\n---\n# Body\n"
        meta, body = split_frontmatter(content)
        assert meta == {"id": "M01", "status": "in-progress"}
        assert body == "# Body\n"

    def test_malformed_yaml_returns_empty(self):
        content = "---\nid: [unclosed\n---\n# Body\n"
        meta, body = split_frontmatter(content)
        assert meta == {}
        # body 是原 content(没切)
        assert "# Body" in body

    def test_dates_stringified(self):
        content = "---\ncreated: 2026-05-18\n---\n"
        meta, _ = split_frontmatter(content)
        assert isinstance(meta["created"], str)
        assert meta["created"].startswith("2026-05-18")


# ── extract_subtasks_from_body ────────────────────────────────
class TestExtractSubtasks:
    def test_simple_todo_section(self):
        body = "## TODO\n\n- [x] done item\n- [ ] todo item\n"
        out = extract_subtasks_from_body(body)
        assert len(out) == 2
        assert out[0] == {"title": "done item", "done": True}
        assert out[1] == {"title": "todo item", "done": False}

    def test_chinese_section_header(self):
        body = "## 待办\n\n- [x] 完成项\n- [ ] 待办项\n"
        out = extract_subtasks_from_body(body)
        assert len(out) == 2

    def test_numbered_section_header_3_dot(self):
        # `## 3 · 待办` 这种 numbered + dot · 在 dogfood 时实测要支持
        body = "## 3 · 待办\n\n- [x] item\n"
        out = extract_subtasks_from_body(body)
        assert len(out) == 1
        assert out[0]["done"] is True

    def test_no_section_returns_empty(self):
        body = "# Just text\n\nNo TODO here.\n"
        assert extract_subtasks_from_body(body) == []

    def test_stops_at_next_h2(self):
        body = "## TODO\n\n- [x] first\n\n## Other\n\n- [ ] should not match\n"
        out = extract_subtasks_from_body(body)
        assert len(out) == 1
        assert out[0]["title"] == "first"


# ── extract_docs_from_body ────────────────────────────────────
class TestExtractDocs:
    def test_related_section_extracts_md_links(self):
        body = "## Related\n\n- [Plan](docs/plans/x.md)\n- [Spec](docs/spec/y.md)\n"
        out = extract_docs_from_body(body)
        assert len(out) == 2
        assert out[0] == {"title": "Plan", "path": "docs/plans/x.md"}

    def test_skips_anchor_links(self):
        body = "## Related\n\n- [Section](#foo)\n- [Real](docs/x.md)\n"
        out = extract_docs_from_body(body)
        assert len(out) == 1
        assert out[0]["path"] == "docs/x.md"

    def test_chinese_section(self):
        body = "## 关联\n\n- [设计](docs/design.md)\n"
        out = extract_docs_from_body(body)
        assert len(out) == 1


# ── Issue ──────────────────────────────────────────────────────
class TestIssue:
    def test_as_dict_shape(self):
        path = pathlib.Path("docs/spec/module/M01.md")
        i = Issue("error", path, "id", "missing", suggestion="add it", reference="§2.1")
        d = i.as_dict()
        assert d["severity"] == "error"
        assert d["field"] == "id"
        assert d["message"] == "missing"
        assert "M01.md" in d["path"]

    def test_format_for_terminal_has_three_sections(self):
        path = pathlib.Path("M01.md")
        i = Issue("error", path, "id", "msg", suggestion="fix", reference="§2.1")
        out = i.format_for_terminal()
        assert "❌" in out
        assert "💡 fix:" in out
        assert "📚 see:" in out


# ── validate_meta ──────────────────────────────────────────────
class TestValidateMeta:
    def _path(self):
        return pathlib.Path("docs/spec/module/M01.md")

    def test_missing_id_is_error(self):
        issues = validate_meta(self._path(), {}, DEFAULT_STATUS_RANGES)
        id_issues = [i for i in issues if i.field == "id"]
        assert len(id_issues) == 1
        assert id_issues[0].severity == "error"

    def test_placeholder_id_is_warn(self):
        issues = validate_meta(self._path(), {"id": "MXX"}, DEFAULT_STATUS_RANGES)
        id_warns = [i for i in issues if i.field == "id" and i.severity == "warn"]
        assert len(id_warns) == 1

    def test_unknown_status_is_error(self):
        issues = validate_meta(
            self._path(),
            {"id": "M01", "status": "wonky"},
            DEFAULT_STATUS_RANGES,
        )
        status_errors = [i for i in issues if i.field == "status" and i.severity == "error"]
        assert len(status_errors) == 1

    def test_progress_out_of_range_for_planned(self):
        # planned 允许 [0, 15] · 80 越界 → warn
        issues = validate_meta(
            self._path(),
            {"id": "M01", "status": "planned", "progress": 80, "desc": "x"},
            DEFAULT_STATUS_RANGES,
        )
        prog_warns = [i for i in issues if i.field == "progress" and i.severity == "warn"]
        assert len(prog_warns) == 1

    def test_progress_non_numeric_is_error(self):
        issues = validate_meta(
            self._path(),
            {"id": "M01", "status": "in-progress", "progress": "80%", "desc": "x"},
            DEFAULT_STATUS_RANGES,
        )
        prog_errors = [i for i in issues if i.field == "progress" and i.severity == "error"]
        assert len(prog_errors) == 1

    def test_missing_desc_is_hint(self):
        issues = validate_meta(
            self._path(),
            {"id": "M01", "status": "in-progress", "progress": 50},
            DEFAULT_STATUS_RANGES,
        )
        desc_hints = [i for i in issues if i.field == "desc" and i.severity == "hint"]
        assert len(desc_hints) == 1

    def test_unknown_type_is_warn(self):
        issues = validate_meta(
            self._path(),
            {"id": "M01", "status": "done", "progress": 100, "desc": "x", "type": "wonky"},
            DEFAULT_STATUS_RANGES,
        )
        type_warns = [i for i in issues if i.field == "type" and i.severity == "warn"]
        assert len(type_warns) == 1

    def test_all_good_no_issues(self):
        issues = validate_meta(
            self._path(),
            {
                "id": "M01",
                "status": "in-progress",
                "progress": 50,
                "desc": "Build engine pipeline",
                "type": "module",
                "docs": [{"title": "x", "path": "docs/x.md"}],
            },
            DEFAULT_STATUS_RANGES,
        )
        assert issues == []


# ── enum 完整性 ────────────────────────────────────────────────
class TestEnums:
    def test_valid_statuses_match_ranges(self):
        assert VALID_STATUSES == set(DEFAULT_STATUS_RANGES.keys())

    def test_all_status_ranges_are_tuples_of_2(self):
        for status, rng in DEFAULT_STATUS_RANGES.items():
            assert len(rng) == 2
            assert 0 <= rng[0] <= rng[1] <= 100, f"{status} range {rng} is malformed"

    def test_done_progress_is_locked_100(self):
        assert DEFAULT_STATUS_RANGES["done"] == (100, 100)

    def test_not_started_progress_is_locked_0(self):
        assert DEFAULT_STATUS_RANGES["not-started"] == (0, 0)

    def test_valid_doc_types_has_expected(self):
        assert "module" in VALID_DOC_TYPES
        assert "plan" in VALID_DOC_TYPES
        assert "rfc" in VALID_DOC_TYPES
        assert "spec" in VALID_DOC_TYPES


# ── v0.11 W1 · normalize_subtasks ─────────────────────────────
from docs_cockpit.schema import (
    VALID_SUBTASK_STATUSES,
    _subtask_id_for,
    normalize_subtasks,
    validate_subtask_schema,
)


class TestNormalizeSubtasks:
    def test_empty_input(self):
        assert normalize_subtasks(None, "M01") == []
        assert normalize_subtasks([], "M01") == []

    def test_string_list_v010(self):
        out = normalize_subtasks(["Lane A", "Lane B"], "M09")
        assert len(out) == 2
        assert out[0]["title"] == "Lane A"
        assert out[0]["status"] == "not-started"
        assert out[0]["done"] is False
        assert out[0]["id"].startswith("M09-")

    def test_dict_with_done_true(self):
        out = normalize_subtasks([{"title": "wire FSM", "done": True}], "M07")
        assert out[0]["status"] == "done"
        assert out[0]["done"] is True

    def test_dict_with_done_false(self):
        out = normalize_subtasks([{"title": "wire FSM", "done": False}], "M07")
        assert out[0]["status"] == "not-started"
        assert out[0]["done"] is False

    def test_v011_explicit_status_wins_over_done(self):
        # status 优先 done
        out = normalize_subtasks(
            [{"title": "x", "status": "in-progress", "done": True}], "M07"
        )
        assert out[0]["status"] == "in-progress"
        # done 字段反映 status
        assert out[0]["done"] is False

    def test_v011_full_schema_preserves_code_and_docs(self):
        out = normalize_subtasks([{
            "id": "M09-S1",
            "title": "Lane A",
            "status": "done",
            "code": "sourcery/x.py:42-89",
            "docs": ["docs/spec/x.md"],
        }], "M09")
        assert out[0]["id"] == "M09-S1"
        assert out[0]["code"] == "sourcery/x.py:42-89"
        assert out[0]["docs"] == ["docs/spec/x.md"]

    def test_mixed_list(self):
        out = normalize_subtasks(
            ["str item", {"title": "dict item", "done": True}, "another str"],
            "M09",
        )
        assert len(out) == 3
        assert out[0]["title"] == "str item"
        assert out[1]["status"] == "done"
        assert out[2]["title"] == "another str"

    def test_empty_title_skipped(self):
        out = normalize_subtasks(["", "   ", {"title": ""}], "M09")
        assert out == []

    def test_non_string_non_dict_ignored(self):
        out = normalize_subtasks([42, None, "valid"], "M09")
        assert len(out) == 1
        assert out[0]["title"] == "valid"

    def test_id_stable_for_same_title(self):
        out1 = normalize_subtasks(["Lane A"], "M09")
        out2 = normalize_subtasks(["Lane A"], "M09")
        assert out1[0]["id"] == out2[0]["id"]

    def test_id_changes_with_title(self):
        out1 = normalize_subtasks(["Lane A"], "M09")
        out2 = normalize_subtasks(["Lane B"], "M09")
        assert out1[0]["id"] != out2[0]["id"]

    def test_id_changes_with_module(self):
        out1 = normalize_subtasks(["Lane A"], "M09")
        out2 = normalize_subtasks(["Lane A"], "M07")
        assert out1[0]["id"] != out2[0]["id"]


class TestSubtaskIdFor:
    def test_format(self):
        out = _subtask_id_for("M09", "Lane A")
        assert out.startswith("M09-")
        assert len(out) == len("M09-") + 6  # 6 char sha1

    def test_chinese_title(self):
        out = _subtask_id_for("M01", "测试一下")
        assert out.startswith("M01-")

    def test_empty_module_id_uses_X(self):
        out = _subtask_id_for("", "title")
        assert out.startswith("X-")


class TestValidateSubtaskSchema:
    def _path(self):
        import pathlib
        return pathlib.Path("docs/spec/module/M09.md")

    def test_missing_title_is_error(self):
        issues = validate_subtask_schema(
            [{"id": "M09-S1", "status": "done"}], "M09", self._path()
        )
        errors = [i for i in issues if "title" in i.field]
        assert len(errors) == 1
        assert errors[0].severity == "error"

    def test_missing_id_is_error(self):
        issues = validate_subtask_schema(
            [{"title": "Lane A", "status": "done"}], "M09", self._path()
        )
        errors = [i for i in issues if i.field.endswith(".id")]
        assert len(errors) == 1
        assert errors[0].severity == "error"

    def test_duplicate_id_is_error(self):
        issues = validate_subtask_schema(
            [
                {"id": "M09-S1", "title": "A", "status": "done"},
                {"id": "M09-S1", "title": "B", "status": "done"},
            ],
            "M09",
            self._path(),
        )
        dupes = [i for i in issues if "duplicate" in i.message]
        assert len(dupes) == 1

    def test_unknown_status_is_error(self):
        issues = validate_subtask_schema(
            [{"id": "M09-S1", "title": "A", "status": "wonky"}],
            "M09",
            self._path(),
        )
        status_errs = [i for i in issues if i.field.endswith(".status")]
        assert len(status_errs) == 1
        assert status_errs[0].severity == "error"

    def test_all_4_statuses_valid(self):
        for s in VALID_SUBTASK_STATUSES:
            issues = validate_subtask_schema(
                [{"id": "X-1", "title": "T", "status": s}], "X", self._path()
            )
            status_errs = [i for i in issues if i.field.endswith(".status")]
            assert len(status_errs) == 0, f"status `{s}` should be valid"

    def test_all_good_no_issues(self):
        issues = validate_subtask_schema(
            [
                {"id": "M09-S1", "title": "A", "status": "done"},
                {"id": "M09-S2", "title": "B", "status": "in-progress"},
            ],
            "M09",
            self._path(),
        )
        assert issues == []

    def test_valid_subtask_statuses_enum(self):
        # plan §6.1 lock 4 个
        assert VALID_SUBTASK_STATUSES == {
            "not-started", "in-progress", "done", "blocked"
        }


# ── v0.11 W1 · body inline @code @docs syntax ─────────────
class TestInlineCodeDocsSyntax:
    def test_inline_code_single(self):
        body = "## TODO\n- [x] Title @code:src/x.py:42\n"
        out = extract_subtasks_from_body(body)
        assert out[0]["title"] == "Title"
        assert out[0]["code"] == "src/x.py:42"

    def test_inline_code_multiple_becomes_list(self):
        body = "## TODO\n- [ ] Title @code:src/x.py @code:src/y.py\n"
        out = extract_subtasks_from_body(body)
        assert out[0]["code"] == ["src/x.py", "src/y.py"]

    def test_inline_docs(self):
        body = "## TODO\n- [x] Title @docs:M09-spec\n"
        out = extract_subtasks_from_body(body)
        assert out[0]["docs"] == "M09-spec"

    def test_inline_both_code_and_docs(self):
        body = "## TODO\n- [x] Lane A @code:src/x.py:42-89 @docs:M09-spec\n"
        out = extract_subtasks_from_body(body)
        assert out[0]["title"] == "Lane A"
        assert out[0]["code"] == "src/x.py:42-89"
        assert out[0]["docs"] == "M09-spec"

    def test_no_inline_falls_back_to_plain_title(self):
        body = "## TODO\n- [x] Plain title\n"
        out = extract_subtasks_from_body(body)
        assert out[0]["title"] == "Plain title"
        assert "code" not in out[0]
        assert "docs" not in out[0]

    def test_chinese_title_with_inline(self):
        body = "## 待办\n- [x] 拆模块 @code:src/x.py\n"
        out = extract_subtasks_from_body(body)
        assert out[0]["title"] == "拆模块"
        assert out[0]["code"] == "src/x.py"

    def test_title_strip_extra_whitespace(self):
        body = "## TODO\n- [ ]   Title   with   spaces   @code:x.py\n"
        out = extract_subtasks_from_body(body)
        assert out[0]["title"] == "Title with spaces"
