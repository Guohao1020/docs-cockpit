"""单元测试 · v0.11.0-alpha.6 systemDocs content embed(plan §6.7).

把 _build_system_docs 从「仅展开 path」升级到「展开 path + embed content」·
让 split-view 右栏能直接 marked.js 渲染。
"""

from __future__ import annotations

import pathlib

import pytest

from docs_cockpit.build import (
    _MAX_SYSDOC_EMBED_BYTES,
    _build_system_docs,
)


class TestBuildSystemDocs:
    def test_empty_returns_empty(self, tmp_path):
        assert _build_system_docs(None, {}, tmp_path) == []
        assert _build_system_docs([], {}, tmp_path) == []

    def test_basic_entry_with_content(self, tmp_path):
        target = tmp_path / "CLAUDE.md"
        target.write_text("# Heading\n\nbody text\n", encoding="utf-8")
        entries = [
            {
                "id": "claude-md",
                "title": "CLAUDE.md",
                "path": str(target),
                "desc": "test desc",
                "icon": "memory",
            },
        ]
        out = _build_system_docs(entries, {"repo": str(tmp_path)}, tmp_path)
        assert len(out) == 1
        e = out[0]
        assert e["id"] == "claude-md"
        assert e["title"] == "CLAUDE.md"
        assert e["desc"] == "test desc"
        assert e["icon"] == "memory"
        assert e["exists"] is True
        assert e["content"] == "# Heading\n\nbody text\n"
        assert e["mtime"] is not None

    def test_strips_frontmatter(self, tmp_path):
        target = tmp_path / "spec.md"
        target.write_text(
            "---\nid: M01\nstatus: done\n---\n# Real Body\n\ntext\n",
            encoding="utf-8",
        )
        entries = [{"title": "spec", "path": str(target)}]
        out = _build_system_docs(entries, {"repo": str(tmp_path)}, tmp_path)
        # content 不应含 frontmatter
        assert "---" not in out[0]["content"][:5]
        assert "id: M01" not in out[0]["content"]
        assert "# Real Body" in out[0]["content"]

    def test_missing_file_exists_false(self, tmp_path):
        entries = [
            {"title": "Missing", "path": str(tmp_path / "nope.md")},
        ]
        out = _build_system_docs(entries, {"repo": str(tmp_path)}, tmp_path)
        assert out[0]["exists"] is False
        assert out[0]["content"] == ""

    def test_var_expansion(self, tmp_path):
        target = tmp_path / "x.md"
        target.write_text("# X", encoding="utf-8")
        entries = [{"title": "X", "path": "{repo}/x.md"}]
        out = _build_system_docs(entries, {"repo": str(tmp_path)}, tmp_path)
        assert out[0]["exists"] is True
        # path 已展开
        assert out[0]["path"] == str(tmp_path) + "/x.md" or out[0]["path"] == str(tmp_path) + "\\x.md"

    def test_non_md_extension_no_content_embed(self, tmp_path):
        # PDF 等非 MD · 不 embed content · 但 exists 仍 True
        target = tmp_path / "spec.pdf"
        target.write_bytes(b"%PDF-1.7 fake content")
        entries = [{"title": "PDF spec", "path": str(target)}]
        out = _build_system_docs(entries, {"repo": str(tmp_path)}, tmp_path)
        assert out[0]["exists"] is True
        assert out[0]["content"] == ""
        assert out[0]["mtime"] is not None

    def test_large_file_truncated(self, tmp_path):
        target = tmp_path / "big.md"
        # 100KB body · 超过 50KB cap
        target.write_text("# Big\n\n" + ("x" * 100_000), encoding="utf-8")
        entries = [{"title": "Big", "path": str(target)}]
        out = _build_system_docs(entries, {"repo": str(tmp_path)}, tmp_path)
        assert out[0]["exists"] is True
        assert len(out[0]["content"]) < 100_000  # 截断了
        assert "truncated" in out[0]["content"].lower()

    def test_id_auto_generated_from_title(self, tmp_path):
        target = tmp_path / "x.md"
        target.write_text("# X", encoding="utf-8")
        entries = [{"title": "My System Doc", "path": str(target)}]
        out = _build_system_docs(entries, {"repo": str(tmp_path)}, tmp_path)
        # 没显式 id · 用 slugify(title)
        assert out[0]["id"] != ""

    def test_max_embed_bytes_is_50kb(self):
        assert _MAX_SYSDOC_EMBED_BYTES == 50 * 1024
