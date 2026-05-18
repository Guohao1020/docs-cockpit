"""Integration tests · v0.11 W1 + W3 CLI 子命令 · plan §11 Step 3 + Step 4.

跑真 subprocess 调 `docs-cockpit prompt` / `docs-cockpit migrate-subtasks` ·
验证用户视角行为。

0.11.0-alpha.3:首发。
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess

import pytest


# Locate docs-cockpit binary · 优先用 uv tool 装的 launcher
_DOCS_COCKPIT = shutil.which("docs-cockpit")


def _run_docs_cockpit(args: list[str], cwd: pathlib.Path) -> subprocess.CompletedProcess:
    """跑 docs-cockpit · 返 CompletedProcess(stdout / stderr / returncode)."""
    if not _DOCS_COCKPIT:
        pytest.skip("docs-cockpit binary not on PATH · install with `uv tool install --editable .`")
    return subprocess.run(
        [_DOCS_COCKPIT, *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


@pytest.fixture
def fixture_project(tmp_path: pathlib.Path) -> pathlib.Path:
    """搭一个 minimal docs-cockpit 项目 · 1 个 module · 2 个 subtask."""
    (tmp_path / "docs" / "spec" / "module").mkdir(parents=True)
    (tmp_path / "docs-cockpit.yaml").write_text(
        """
project:
  name: TestProj
  mark: T
  tagline: "test"
  output: docs/index.html
paths:
  repo: "."
modules:
  scan:
    dir: "{repo}/docs/spec/module"
""",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "spec" / "module" / "M01-test.md").write_text(
        """---
id: M01
type: module
title: "Test Module"
status: in-progress
sprint: "test"
progress: 50
desc: "A test module"
subtasks:
  - id: M01-S1
    title: "First subtask"
    status: in-progress
  - id: M01-S2
    title: "Second subtask"
    status: done
---

# Test
""",
        encoding="utf-8",
    )
    return tmp_path


class TestPromptCLI:
    """`docs-cockpit prompt` 子命令(plan §6.2 · M02 subtask 4/5/6)."""

    def test_prompt_list_returns_builtin_templates(self, fixture_project):
        r = _run_docs_cockpit(["prompt", "--list"], fixture_project)
        assert r.returncode == 0, r.stderr
        assert "generic" in r.stdout
        assert "feature" in r.stdout
        assert "fix" in r.stdout
        assert "refactor" in r.stdout

    def test_prompt_no_args_lists_modules(self, fixture_project):
        r = _run_docs_cockpit(["prompt"], fixture_project)
        assert r.returncode == 0
        assert "M01" in r.stdout
        assert "Test Module" in r.stdout

    def test_prompt_module_id_lists_subtasks(self, fixture_project):
        r = _run_docs_cockpit(["prompt", "M01"], fixture_project)
        assert r.returncode == 0
        assert "M01-S1" in r.stdout
        assert "M01-S2" in r.stdout
        assert "First subtask" in r.stdout

    def test_prompt_full_renders_to_stdout(self, fixture_project):
        r = _run_docs_cockpit(["prompt", "M01", "M01-S1"], fixture_project)
        assert r.returncode == 0
        # Real Jinja render · contains key context vars
        assert "M01-S1" in r.stdout
        assert "First subtask" in r.stdout
        assert "Test Module" in r.stdout

    def test_prompt_unknown_module_errors(self, fixture_project):
        r = _run_docs_cockpit(["prompt", "NOPE"], fixture_project)
        assert r.returncode != 0
        assert "not found" in r.stdout.lower() or "not found" in r.stderr.lower()

    def test_prompt_unknown_subtask_errors(self, fixture_project):
        r = _run_docs_cockpit(["prompt", "M01", "NOPE-X1"], fixture_project)
        assert r.returncode != 0


class TestMigrateSubtasksCLI:
    """`docs-cockpit migrate-subtasks` 子命令(M02 subtask 7)."""

    def test_migrate_string_list_dry_run(self, tmp_path):
        md = tmp_path / "M01.md"
        md.write_text(
            """---
id: M01
title: "test"
subtasks:
  - "Lane A"
  - "Lane B"
---

# Body
""",
            encoding="utf-8",
        )
        r = _run_docs_cockpit(["migrate-subtasks", str(md)], tmp_path)
        assert r.returncode == 0
        assert "diff" in r.stdout.lower() or "before" in r.stdout.lower()
        assert "dry-run" in r.stdout.lower()
        # 没改文件
        assert "Lane A" in md.read_text(encoding="utf-8")
        assert "id: M01-" not in md.read_text(encoding="utf-8")

    def test_migrate_apply_writes_file_with_backup(self, tmp_path):
        md = tmp_path / "M01.md"
        original = """---
id: M01
title: "test"
subtasks:
  - "Lane A"
---

# Body
"""
        md.write_text(original, encoding="utf-8")
        r = _run_docs_cockpit(["migrate-subtasks", str(md), "--apply"], tmp_path)
        assert r.returncode == 0
        # 文件被改
        new_content = md.read_text(encoding="utf-8")
        assert "id: M01-" in new_content  # 新生成的 subtask id
        # 备份存在
        backup = md.with_suffix(".md.bak")
        assert backup.exists()
        assert backup.read_text(encoding="utf-8") == original

    def test_migrate_already_v011_no_change(self, tmp_path):
        md = tmp_path / "M01.md"
        md.write_text(
            """---
id: M01
title: "test"
subtasks:
  - id: M01-S1
    title: "Lane A"
    status: done
---

# Body
""",
            encoding="utf-8",
        )
        r = _run_docs_cockpit(["migrate-subtasks", str(md)], tmp_path)
        assert r.returncode == 0
        assert "already in v0.11 schema" in r.stdout


class TestLintPrompts:
    """`docs-cockpit lint --prompts` (M02 subtask 8)."""

    def test_lint_prompts_passes_with_builtin_only(self, fixture_project):
        r = _run_docs_cockpit(["lint", "--prompts"], fixture_project)
        # Built-in templates are syntactically valid · expect exit 0 unless
        # frontmatter has issues
        assert r.returncode == 0
