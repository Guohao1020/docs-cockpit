"""单元测试 · docs_cockpit.paths · plan-eng-review 4A.

测 paths.py 的核心 API:_build_vars / _expand / _resolve_doc_path /
title transforms。

0.11.0-alpha.1:Step 1 引入 pytest 时第一批单元测试。
v0.11 W1 加 _resolve_code_anchor 时 · 这里继续扩(含 plan §6.1 + 3A 的
defensive IO error handling test matrix)。
"""

from __future__ import annotations

import os
import pathlib

import pytest

from docs_cockpit.paths import (
    TRANSFORMS,
    _build_vars,
    _expand,
    _resolve_doc_path,
    _transform_path_slash,
    _transform_prefix_dot_titlecase,
    _transform_stem,
)


# ── _expand · path 变量展开 ───────────────────────────────────
class TestExpand:
    def test_basic_var_substitution(self):
        out = _expand("{repo}/docs/x.md", {"repo": "/proj"})
        assert out == "/proj/docs/x.md"

    def test_unknown_var_preserved(self):
        out = _expand("{unknown}/x", {"repo": "/proj"})
        assert out == "{unknown}/x"

    def test_env_var_substitution(self, monkeypatch):
        monkeypatch.setenv("MY_TEST_VAR", "/test/path")
        out = _expand("{env:MY_TEST_VAR}/x", {})
        assert out == "/test/path/x"

    def test_env_var_missing_returns_empty(self, monkeypatch):
        monkeypatch.delenv("DEFINITELY_NOT_SET_VAR", raising=False)
        out = _expand("{env:DEFINITELY_NOT_SET_VAR}/x", {})
        assert out == "/x"

    def test_multiple_vars(self):
        out = _expand("{home}/repos/{repo_name}/docs", {"home": "/h", "repo_name": "foo"})
        assert out == "/h/repos/foo/docs"


# ── _build_vars · 配置文件路径变量 ────────────────────────────
class TestBuildVars:
    def test_repo_default_is_config_parent(self, tmp_path):
        config_path = tmp_path / "docs-cockpit.yaml"
        config_path.touch()
        vars_ = _build_vars(config_path, {})
        # 默认 repo = "." 相对 config_path · 解析到 tmp_path
        assert pathlib.Path(vars_["repo"]).resolve() == tmp_path.resolve()

    def test_explicit_repo_absolute(self, tmp_path):
        other = tmp_path / "other"
        other.mkdir()
        config_path = tmp_path / "docs-cockpit.yaml"
        config_path.touch()
        vars_ = _build_vars(config_path, {"repo": str(other)})
        assert pathlib.Path(vars_["repo"]).resolve() == other.resolve()

    def test_home_from_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", "/my/home")
        monkeypatch.delenv("USERPROFILE", raising=False)
        config_path = tmp_path / "docs-cockpit.yaml"
        config_path.touch()
        vars_ = _build_vars(config_path, {})
        # home 应该是 /my/home(POSIX) 或 expanduser 解析
        assert "home" in vars_

    def test_custom_vars_passed_through(self, tmp_path):
        config_path = tmp_path / "docs-cockpit.yaml"
        config_path.touch()
        vars_ = _build_vars(config_path, {"repo": str(tmp_path), "memory_dir": "{repo}/.memory"})
        # memory_dir 经过 _expand · 用 repo 替换
        assert vars_["memory_dir"] == str(tmp_path) + "/.memory"


# ── title transforms ──────────────────────────────────────────
class TestTransforms:
    def test_stem_returns_filename_without_ext(self, tmp_path):
        p = tmp_path / "M01-foo.md"
        assert _transform_stem(p, tmp_path) == "M01-foo"

    def test_prefix_dot_titlecase_basic(self, tmp_path):
        p = tmp_path / "M07-job-fsm.md"
        out = _transform_prefix_dot_titlecase(p, tmp_path)
        assert out == "M07 · Job Fsm"

    def test_prefix_dot_titlecase_concept(self, tmp_path):
        p = tmp_path / "C03-site-adapter.md"
        out = _transform_prefix_dot_titlecase(p, tmp_path)
        assert out == "C03 · Site Adapter"

    def test_prefix_dot_titlecase_no_dash_passthrough(self, tmp_path):
        p = tmp_path / "M01.md"
        out = _transform_prefix_dot_titlecase(p, tmp_path)
        assert out == "M01"

    def test_path_slash_subdir(self, tmp_path):
        sub = tmp_path / "roadmap"
        sub.mkdir()
        p = sub / "00-master.md"
        p.touch()
        out = _transform_path_slash(p, tmp_path)
        assert out == "roadmap / 00-master"

    def test_transforms_dict_complete(self):
        assert "stem" in TRANSFORMS
        assert "prefix-dot-titlecase" in TRANSFORMS
        assert "path-slash" in TRANSFORMS


# ── _resolve_doc_path · 三步 fallback ─────────────────────────
class TestResolveDocPath:
    def test_absolute_path_exists(self, tmp_path):
        target = tmp_path / "x.md"
        target.write_text("# X")
        module = tmp_path / "spec" / "M01.md"
        module.parent.mkdir(parents=True)
        module.touch()
        out = _resolve_doc_path(
            str(target), module, tmp_path, {"repo": str(tmp_path)}
        )
        assert out is not None
        assert out.resolve() == target.resolve()

    def test_absolute_path_missing_returns_none(self, tmp_path):
        module = tmp_path / "M01.md"
        module.touch()
        out = _resolve_doc_path(
            "/totally/missing/path.md", module, tmp_path, {}
        )
        assert out is None

    def test_relative_to_module(self, tmp_path):
        # source MD 同目录的 link
        module = tmp_path / "M01.md"
        module.touch()
        target = tmp_path / "x.md"
        target.write_text("# X")
        out = _resolve_doc_path("x.md", module, tmp_path, {})
        assert out is not None
        assert out.resolve() == target.resolve()

    def test_relative_to_repo_root(self, tmp_path):
        # source MD 在子目录 · target 在 repo 根 · 第三步 fallback
        sub = tmp_path / "spec" / "module"
        sub.mkdir(parents=True)
        module = sub / "M01.md"
        module.touch()
        target = tmp_path / "x.md"
        target.write_text("# X")
        out = _resolve_doc_path("x.md", module, tmp_path, {})
        # 找到了 repo 根的 x.md
        assert out is not None
        assert out.resolve() == target.resolve()

    def test_var_substitution_in_path(self, tmp_path):
        target = tmp_path / "ref.md"
        target.write_text("# Ref")
        module = tmp_path / "M01.md"
        module.touch()
        out = _resolve_doc_path(
            "{repo}/ref.md", module, tmp_path, {"repo": str(tmp_path)}
        )
        assert out is not None
        assert out.resolve() == target.resolve()

    def test_empty_path_returns_none(self, tmp_path):
        module = tmp_path / "M01.md"
        module.touch()
        assert _resolve_doc_path("", module, tmp_path, {}) is None
