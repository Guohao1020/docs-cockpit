"""Unit tests for v0.15.0 alias system (`docs_cockpit/build.py::_build_aliases`).

覆盖:
- alias 基本解析 (canonical_id + source path 展开)
- 路径 fallback(absolute / repo-relative / home-relative)
- title / desc / icon override
- 不存在的 source 仍 emit entry(exists=False)· 不抛
- canonical_type → icon 默认映射
- 跟 system_docs 并排融合到 systemDocs[]
- alias 字段被标 alias=True · 给 standup / portfolio skill 区分
"""

from __future__ import annotations

import pathlib

import pytest

from docs_cockpit.build import (
    _build_aliases,
    _icon_for_canonical_type,
    build_payload,
)


# ─── _icon_for_canonical_type ─────────────────────────────────────────


class TestIconMapping:
    def test_known_types_map(self):
        assert _icon_for_canonical_type("plan") == "plan"
        assert _icon_for_canonical_type("rfc") == "doc"
        assert _icon_for_canonical_type("spec") == "doc"
        assert _icon_for_canonical_type("concept-doc") == "design"
        assert _icon_for_canonical_type("memory") == "memory"
        assert _icon_for_canonical_type("roadmap") == "plan"

    def test_unknown_type_falls_back_doc(self):
        assert _icon_for_canonical_type("randomthing") == "doc"
        assert _icon_for_canonical_type("") == "doc"


# ─── _build_aliases · 基本解析 ────────────────────────────────────────


class TestBuildAliases:
    def test_empty_or_none_returns_empty(self):
        assert _build_aliases(None, {}, pathlib.Path(".")) == []
        assert _build_aliases([], {}, pathlib.Path(".")) == []

    def test_missing_canonical_id_skipped(self, tmp_path):
        entries = [{"source": str(tmp_path / "x.md")}]
        out = _build_aliases(entries, {"repo": str(tmp_path)}, tmp_path)
        assert out == []

    def test_resolves_repo_relative_path(self, tmp_path):
        src = tmp_path / "docs" / "superpowers" / "plans" / "p.md"
        src.parent.mkdir(parents=True)
        src.write_text("# Some plan\n\nbody content\n", encoding="utf-8")
        entries = [
            {
                "canonical_id": "P-v0.15-test",
                "canonical_type": "plan",
                "source": "docs/superpowers/plans/p.md",
                "title": "Canonical Title Override",
                "desc": "test desc",
            }
        ]
        out = _build_aliases(entries, {"repo": str(tmp_path)}, tmp_path)
        assert len(out) == 1
        item = out[0]
        assert item["id"] == "P-v0.15-test"
        assert item["title"] == "Canonical Title Override"
        assert item["desc"] == "test desc"
        assert item["exists"] is True
        assert "body content" in item["content"]
        assert item["alias"] is True
        assert item["canonical_type"] == "plan"
        assert item["icon"] == "plan"  # auto from canonical_type

    def test_resolves_home_expansion(self, tmp_path, monkeypatch):
        # 模拟 home dir 在 tmp_path 下
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        src = fake_home / ".gstack" / "projects" / "demo" / "design.md"
        src.parent.mkdir(parents=True)
        src.write_text("# gstack-style design\n", encoding="utf-8")
        monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: fake_home))
        entries = [
            {
                "canonical_id": "P-v0.15-from-gstack",
                "canonical_type": "plan",
                "source": "{home}/.gstack/projects/demo/design.md",
            }
        ]
        out = _build_aliases(
            entries,
            {"home": str(fake_home), "repo": str(tmp_path)},
            tmp_path,
        )
        assert len(out) == 1
        assert out[0]["exists"] is True
        assert "gstack-style design" in out[0]["content"]

    def test_missing_source_returns_exists_false(self, tmp_path):
        entries = [
            {
                "canonical_id": "P-stale",
                "canonical_type": "plan",
                "source": "docs/no/such/file.md",
            }
        ]
        out = _build_aliases(entries, {"repo": str(tmp_path)}, tmp_path)
        assert len(out) == 1
        assert out[0]["exists"] is False
        assert out[0]["content"] == ""
        # id / title 仍要 emit · 给 dashboard 显 stale 状态
        assert out[0]["id"] == "P-stale"
        assert out[0]["alias"] is True

    def test_id_field_alternative_to_canonical_id(self, tmp_path):
        # 老用户用 `id:` 也行 · 跟 canonical_id 等价(向后兼容 system_docs entry shape)
        src = tmp_path / "x.md"
        src.write_text("body\n", encoding="utf-8")
        entries = [{"id": "P-alt", "source": str(src)}]
        out = _build_aliases(entries, {"repo": str(tmp_path)}, tmp_path)
        assert len(out) == 1
        assert out[0]["id"] == "P-alt"

    def test_frontmatter_stripped_from_content(self, tmp_path):
        src = tmp_path / "p.md"
        src.write_text(
            "---\nid: ORIGINAL\nstatus: planned\n---\n\n# Heading\nbody text\n",
            encoding="utf-8",
        )
        entries = [{"canonical_id": "P-strip", "source": str(src)}]
        out = _build_aliases(entries, {"repo": str(tmp_path)}, tmp_path)
        # frontmatter not in content · only body
        assert "id: ORIGINAL" not in out[0]["content"]
        assert "Heading" in out[0]["content"]
        assert "body text" in out[0]["content"]

    def test_explicit_icon_override(self, tmp_path):
        src = tmp_path / "x.md"
        src.write_text("body\n", encoding="utf-8")
        entries = [
            {
                "canonical_id": "X",
                "canonical_type": "plan",  # default would be "plan" icon
                "source": str(src),
                "icon": "memory",  # explicit override
            }
        ]
        out = _build_aliases(entries, {"repo": str(tmp_path)}, tmp_path)
        assert out[0]["icon"] == "memory"

    def test_non_md_file_no_content_embed(self, tmp_path):
        # 非 .md / .markdown 文件 · exists=True 但 content 空
        src = tmp_path / "image.png"
        src.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        entries = [
            {"canonical_id": "I1", "source": str(src), "canonical_type": "doc"}
        ]
        out = _build_aliases(entries, {"repo": str(tmp_path)}, tmp_path)
        assert out[0]["exists"] is True
        assert out[0]["content"] == ""

    def test_source_path_preserved_in_metadata(self, tmp_path):
        src = tmp_path / "p.md"
        src.write_text("body\n", encoding="utf-8")
        entries = [
            {
                "canonical_id": "P1",
                "source": "{repo}/p.md",
            }
        ]
        out = _build_aliases(entries, {"repo": str(tmp_path)}, tmp_path)
        # path 是展开后的绝对路径 · source_path 是 raw 用户输入
        assert "p.md" in out[0]["path"]
        assert out[0]["source_path"] == "{repo}/p.md"


# ─── 跟 build_payload 集成 ────────────────────────────────────────────


class TestAliasInPayload:
    def test_aliases_merged_into_systemDocs(self, tmp_path):
        # 1 个 system_doc + 1 个 alias · payload.systemDocs 含两条
        src_sys = tmp_path / "CLAUDE.md"
        src_sys.write_text("# CLAUDE\n", encoding="utf-8")
        src_alias = tmp_path / "external_plan.md"
        src_alias.write_text("# external plan body\n", encoding="utf-8")

        config = {
            "project": {"name": "test", "mark": "T"},
            "system_docs": [
                {"id": "claude-md", "title": "CLAUDE", "path": str(src_sys)}
            ],
            "aliases": [
                {
                    "canonical_id": "P-v0.15-alias",
                    "canonical_type": "plan",
                    "source": str(src_alias),
                    "title": "v0.15 aliased plan",
                }
            ],
            "modules": {"files": []},
        }
        payload, _ = build_payload(config, {"repo": str(tmp_path)}, "2026-01-01 00:00")
        sd_ids = [s["id"] for s in payload["systemDocs"]]
        assert "claude-md" in sd_ids
        assert "P-v0.15-alias" in sd_ids
        # alias 标记可见
        alias_entry = next(s for s in payload["systemDocs"] if s["id"] == "P-v0.15-alias")
        assert alias_entry.get("alias") is True
        assert alias_entry["canonical_type"] == "plan"
        assert "external plan body" in alias_entry["content"]
