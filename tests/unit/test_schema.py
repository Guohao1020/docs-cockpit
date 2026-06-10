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
    validate_health_report,
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


# ── v0.11 alpha.4 · status × subtasks 一致性 cross-field validator ──
class TestStatusSubtasksConsistency:
    def _path(self):
        return pathlib.Path("docs/spec/module/M01.md")

    def test_done_but_subtasks_incomplete_warns(self):
        # 用户实测反馈:status=done 但 subtask 3/9 done · dashboard 显示矛盾
        issues = validate_meta(
            self._path(),
            {
                "id": "M01", "status": "done", "progress": 100, "desc": "x",
                "subtasks": [
                    {"title": "A", "done": True},
                    {"title": "B", "done": True},
                    {"title": "C", "done": True},
                    {"title": "D", "done": False},
                    {"title": "E", "done": False},
                ],
            },
            DEFAULT_STATUS_RANGES,
        )
        warns = [i for i in issues if i.field == "status" and "subtasks" in i.message]
        assert len(warns) == 1
        assert "3/5" in warns[0].message

    def test_done_with_all_subtasks_done_no_issue(self):
        issues = validate_meta(
            self._path(),
            {
                "id": "M01", "status": "done", "progress": 100, "desc": "x",
                "subtasks": [
                    {"title": "A", "done": True},
                    {"title": "B", "done": True},
                ],
            },
            DEFAULT_STATUS_RANGES,
        )
        # 应该没有 status × subtasks 一致性问题
        warns = [i for i in issues if i.field == "status" and "subtasks" in i.message]
        assert len(warns) == 0

    def test_not_started_but_some_done_warns(self):
        issues = validate_meta(
            self._path(),
            {
                "id": "M01", "status": "not-started", "progress": 0, "desc": "x",
                "subtasks": [
                    {"title": "A", "done": True},
                    {"title": "B", "done": False},
                ],
            },
            DEFAULT_STATUS_RANGES,
        )
        warns = [i for i in issues if i.field == "status" and "already done" in i.message]
        assert len(warns) == 1

    def test_in_progress_with_partial_done_no_status_warn(self):
        # in-progress + 3/5 done · 是合理状态 · 不应该 warn
        issues = validate_meta(
            self._path(),
            {
                "id": "M01", "status": "in-progress", "progress": 60, "desc": "x",
                "subtasks": [
                    {"title": "A", "done": True}, {"title": "B", "done": True},
                    {"title": "C", "done": True}, {"title": "D", "done": False},
                    {"title": "E", "done": False},
                ],
            },
            DEFAULT_STATUS_RANGES,
        )
        warns = [i for i in issues if i.field == "status" and ("subtasks" in i.message or "already done" in i.message)]
        assert len(warns) == 0

    def test_v011_object_subtasks_with_status_done(self):
        # 新格式 dict with status:done · 跟 done:True 一样算
        issues = validate_meta(
            self._path(),
            {
                "id": "M01", "status": "done", "progress": 100, "desc": "x",
                "subtasks": [
                    {"id": "S1", "title": "A", "status": "done"},
                    {"id": "S2", "title": "B", "status": "in-progress"},
                ],
            },
            DEFAULT_STATUS_RANGES,
        )
        warns = [i for i in issues if i.field == "status" and "1/2" in i.message]
        assert len(warns) == 1

    def test_empty_subtasks_no_check(self):
        # 没 subtask 就不该 trigger 这条
        issues = validate_meta(
            self._path(),
            {"id": "M01", "status": "done", "progress": 100, "desc": "x"},
            DEFAULT_STATUS_RANGES,
        )
        warns = [i for i in issues if i.field == "status" and "subtasks" in i.message]
        assert len(warns) == 0


# ─── 0.14.3 M12 · subtask section heading regex 放宽 ────────────────


class TestSectionRegex_v0_14_3:
    """0.14.3 M12 · _SUBTASK_SECTION_RE / _DOCS_SECTION_RE 接受 § / 三级 heading / tab."""

    @pytest.mark.parametrize(
        "section_heading",
        [
            "## 待办",
            "## TODO",
            "## Subtasks",
            "## Tasks",
            "## 任务",
            "## 3 · 待办",
            "## 3.待办",
            "## 3-待办",
            # 0.14.3 新增 · § 前缀
            "## §4 · 待办",
            "## §3.2 · 待办",
            "## §4 待办",
            # 0.14.3 新增 · 三级 heading
            "### 待办",
            "### §4 · 待办",
            "#### 待办",
            # 0.14.3 新增 · tab 空格
            "##\t待办",
            "##\t§4 · 待办",
            # case insensitive
            "## todo",
            "## Subtask",
        ],
    )
    def test_subtask_section_matches_various_headings(self, section_heading):
        from docs_cockpit.schema import extract_subtasks_from_body

        body = section_heading + "\n\n- [ ] foo\n- [x] bar\n"
        subs = extract_subtasks_from_body(body)
        assert len(subs) == 2, f"failed for heading: {section_heading!r}"
        assert subs[0]["title"] == "foo"
        assert subs[1]["title"] == "bar"

    @pytest.mark.parametrize(
        "bad_heading",
        [
            "# 待办",           # h1 · 不应匹配(只 2-6 级)
            "##待办",            # 没空格分隔(必须 \s+)
            "## description",   # 不是 keyword
            "regular text",
            "**待办**",
        ],
    )
    def test_subtask_section_rejects_non_matching(self, bad_heading):
        from docs_cockpit.schema import extract_subtasks_from_body

        body = bad_heading + "\n\n- [ ] foo\n"
        subs = extract_subtasks_from_body(body)
        assert subs == [], f"should not match: {bad_heading!r}"

    @pytest.mark.parametrize(
        "docs_heading",
        [
            "## 关联文档",
            "## 关联",
            "## Related",
            "## Related docs",
            "## Docs",
            "## See also",
            "## 参考",
            "## 链接",
            "## Links",
            # 0.14.3 新增 · § 前缀
            "## §5 · 关联文档",
            "## §5 关联",
            # 三级
            "### 关联文档",
            "### Related",
        ],
    )
    def test_docs_section_matches_various_headings(self, docs_heading):
        from docs_cockpit.schema import extract_docs_from_body

        body = docs_heading + "\n\n- [Title](path/to/doc.md)\n"
        docs = extract_docs_from_body(body)
        assert len(docs) == 1, f"failed for heading: {docs_heading!r}"
        assert docs[0]["path"] == "path/to/doc.md"


# ── apply_to_md / compute_diff(v1.0 从 test_apply_patch.py 搬入 ·
#    backend 随认知 CLI 删除从 apply_patch.py 收编进 schema.py)────────


class TestApplyToMdFrontmatterPath:
    def test_merge_status(self):
        from docs_cockpit.schema import apply_to_md

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
        from docs_cockpit.schema import apply_to_md

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
        from docs_cockpit.schema import apply_to_md

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


class TestApplyToMdBodyChecklistPath:
    def test_tick_checkbox(self):
        # id derivation 走 _subtask_id_for(module_id, title)
        from docs_cockpit.schema import _subtask_id_for, apply_to_md

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
        from docs_cockpit.schema import _subtask_id_for, apply_to_md

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
        from docs_cockpit.schema import _subtask_id_for, apply_to_md

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
        from docs_cockpit.schema import apply_to_md

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
        from docs_cockpit.schema import _subtask_id_for, apply_to_md

        # 用户改了 title · id 不再 derive 自原 title · 反查失败
        md = """---
id: M09
---

## 待办

- [ ] Lane A NEW NAME
"""
        sid_old = _subtask_id_for("M09", "Lane A")
        patch = {"subtasks": [{"id": sid_old, "status": "done"}], "_warnings": []}
        _, applied, conflicts = apply_to_md(patch, md)
        assert applied == []
        assert any(sid_old in c for c in conflicts)


class TestComputeDiff:
    def test_no_change_empty_diff(self):
        from docs_cockpit.schema import compute_diff

        assert compute_diff("abc\n", "abc\n") == ""

    def test_simple_change_present(self):
        from docs_cockpit.schema import compute_diff

        diff = compute_diff("foo\n", "bar\n", label="test.md")
        assert "test.md" in diff
        assert "-foo" in diff
        assert "+bar" in diff


# ── load_sprint_plans(v1.0 从 sprint.py 收编 · 删 CLI 时首次补测试)──


class TestLoadSprintPlans:
    def _write_plan(self, repo: pathlib.Path, name: str, text: str) -> None:
        plans = repo / "docs" / "plans"
        plans.mkdir(parents=True, exist_ok=True)
        (plans / name).write_text(text, encoding="utf-8")

    def test_no_plans_dir_returns_empty(self, tmp_path: pathlib.Path):
        from docs_cockpit.schema import load_sprint_plans

        assert load_sprint_plans(tmp_path) == []

    def test_loads_sprint_plan_with_meta_and_body(self, tmp_path: pathlib.Path):
        from docs_cockpit.schema import load_sprint_plans

        self._write_plan(tmp_path, "V0.19-test.md", """---
type: sprint-plan
id: V0.19
title: "Sprint 0.19"
status: planned
---

# goal
""")
        plans = load_sprint_plans(tmp_path)
        assert len(plans) == 1
        assert plans[0]["meta"]["id"] == "V0.19"
        assert "# goal" in plans[0]["body"]
        assert "_validate_issues" in plans[0]

    def test_skips_non_sprint_plan_type(self, tmp_path: pathlib.Path):
        from docs_cockpit.schema import load_sprint_plans

        self._write_plan(tmp_path, "V1.0-ordinary.md", """---
type: plan
id: P-x
---

普通 plan · 不是 sprint-plan · 跳过
""")
        assert load_sprint_plans(tmp_path) == []

    def test_skips_files_not_matching_glob(self, tmp_path: pathlib.Path):
        from docs_cockpit.schema import load_sprint_plans

        self._write_plan(tmp_path, "P-not-a-version.md", """---
type: sprint-plan
id: V9.9
---
""")
        assert load_sprint_plans(tmp_path) == []


# ── v1.1.0 · validate_health_report(docs/HEALTH.md frontmatter 校验)──


class TestValidateHealthReport:
    """v1.1 体检报告 frontmatter 校验 · spec docs/plans/P-v1.1-health-check.md §4.

    规范节:references/schema.md · health-report schema。
    severity 分界:顶层/departments 问题 = error(看板健康面板接不住)·
    prescriptions 层面问题 = warn(一条坏处方不拖垮整份报告渲染)。
    """

    def _valid_meta(self) -> dict:
        """spec §4 示例的完整合法 frontmatter."""
        return {
            "type": "health-report",
            "date": "2026-06-10",
            "mode": "quick",
            "grade": "B+",
            "departments": [
                {
                    "id": "anchors",
                    "name": "关联",
                    "verdict": "warn",
                    "summary": "覆盖率 78% · 抽检 1❌",
                    "detail": "...",
                },
                {
                    "id": "structure",
                    "name": "结构",
                    "verdict": "pass",
                    "summary": "lint 0 error / 0 warn",
                },
            ],
            "prescriptions": [
                {
                    "id": "RX-001",
                    "severity": "high",
                    "bucket": "sprint",
                    "title": "M07-S2 锚指向已重构函数",
                    "root_cause": "fsm.py 重构后原函数移位 88-130",
                    "fix": "anchor 改指 fsm.py:88-130 · 改后 render 验证",
                    "anchors": ["sourcery/worker/fsm.py:42-89"],
                    "module": "M07",
                },
            ],
            "accepted_debts": [
                {
                    "item": "schema.py God file",
                    "reason": "post-1.0 已排期拆分",
                    "review": "2026-08",
                },
            ],
            "next_checkup": "本 sprint 收尾快检 · 30 天深检",
        }

    # 1 · 合法完整 frontmatter → 0 issue
    def test_valid_full_meta_zero_issues(self):
        issues = validate_health_report(self._valid_meta(), known_module_ids={"M07"})
        assert issues == []

    # 2 · 缺 grade → error · category="health-report"
    def test_missing_grade_is_error(self):
        meta = self._valid_meta()
        del meta["grade"]
        issues = validate_health_report(meta, known_module_ids={"M07"})
        grade_errors = [i for i in issues if i.field == "grade" and i.severity == "error"]
        assert len(grade_errors) == 1
        assert grade_errors[0].category == "health-report"
        assert grade_errors[0].reference == "references/schema.md · health-report schema"

    # 3 · mode 非法值 → error
    def test_invalid_mode_is_error(self):
        meta = self._valid_meta()
        meta["mode"] = "full"
        issues = validate_health_report(meta, known_module_ids={"M07"})
        assert any(i.field == "mode" and i.severity == "error" for i in issues)

    # 4 · department verdict 非法值 → error
    def test_invalid_department_verdict_is_error(self):
        meta = self._valid_meta()
        meta["departments"][0]["verdict"] = "ok"
        issues = validate_health_report(meta, known_module_ids={"M07"})
        assert any("verdict" in i.field and i.severity == "error" for i in issues)

    # 5 · 处方缺 root_cause → warn(Iron Law 的死规则面:查不出根因的不开药)
    def test_prescription_missing_root_cause_is_warn(self):
        meta = self._valid_meta()
        del meta["prescriptions"][0]["root_cause"]
        issues = validate_health_report(meta, known_module_ids={"M07"})
        rc = [i for i in issues if "root_cause" in i.field]
        assert len(rc) == 1
        assert rc[0].severity == "warn"
        assert rc[0].category == "health-report"

    # 6 · 处方 bucket 非法 → warn
    def test_prescription_invalid_bucket_is_warn(self):
        meta = self._valid_meta()
        meta["prescriptions"][0]["bucket"] = "someday"
        issues = validate_health_report(meta, known_module_ids={"M07"})
        assert any("bucket" in i.field and i.severity == "warn" for i in issues)

    # 7 · 处方 module 不在已知 module ids → warn
    def test_prescription_unknown_module_is_warn(self):
        meta = self._valid_meta()
        meta["prescriptions"][0]["module"] = "M99"
        issues = validate_health_report(meta, known_module_ids={"M07", "M08"})
        assert any("module" in i.field and i.severity == "warn" for i in issues)

    # 7b · known_module_ids=None(默认)→ 跳过 module 存在性检查
    def test_unknown_module_skipped_when_no_known_ids(self):
        meta = self._valid_meta()
        meta["prescriptions"][0]["module"] = "M99"
        assert validate_health_report(meta) == []

    # 8 · 最小合法(只必填 · 无 prescriptions)→ 0 issue
    def test_minimal_required_only_zero_issues(self):
        meta = {
            "type": "health-report",
            "date": "2026-06-10",
            "mode": "deep",
            "grade": "A",
            "departments": [
                {
                    "id": "structure",
                    "name": "结构",
                    "verdict": "pass",
                    "summary": "lint 0 error / 0 warn",
                },
            ],
        }
        assert validate_health_report(meta) == []

    # health-report 是合法 doc type(validate_meta 不报 unknown)
    def test_health_report_in_valid_doc_types(self):
        assert "health-report" in VALID_DOC_TYPES
