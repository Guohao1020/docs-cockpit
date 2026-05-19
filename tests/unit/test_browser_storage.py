"""Unit tests for M09-b23cac / M13 browser_storage.py.

覆盖 Firefox SQLite reader · Chrome stub error · find_profile_dir 跨平台。
"""

from __future__ import annotations

import json
import pathlib
import sqlite3

import pytest


# ─── find_profile_dir · cross-platform path resolution ───────────────────


class TestFindProfileDir:
    def test_unsupported_browser_raises(self):
        from docs_cockpit.browser_storage import (
            BrowserStorageError,
            find_profile_dir,
        )

        with pytest.raises(BrowserStorageError):
            find_profile_dir("safari")

    def test_returns_none_when_no_profile(self, monkeypatch, tmp_path: pathlib.Path):
        # 强制让所有平台 base path 指向空临时 dir · find 不到 default profile
        from docs_cockpit import browser_storage as bs

        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "noexist"))
        monkeypatch.setenv("APPDATA", str(tmp_path / "noexist"))
        monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: tmp_path / "fake_home"))
        result = bs.find_profile_dir("chrome")
        assert result is None


# ─── Firefox SQLite reader · 完整测试 ────────────────────────────────────


def _make_firefox_sqlite(profile_dir: pathlib.Path, kv: dict[str, str]) -> pathlib.Path:
    """构造 fixture Firefox webappsstore.sqlite · 含 cockpit override JSON."""
    sqlite_path = profile_dir / "webappsstore.sqlite"
    conn = sqlite3.connect(str(sqlite_path))
    conn.execute(
        "CREATE TABLE webappsstore2("
        "originAttributes TEXT, originKey TEXT, scope TEXT, "
        "key TEXT, value TEXT)"
    )
    for k, v in kv.items():
        conn.execute(
            "INSERT INTO webappsstore2 VALUES(?, ?, ?, ?, ?)",
            ("", ":file", "scope", k, v),
        )
    conn.commit()
    conn.close()
    return sqlite_path


class TestFirefoxLocalStorage:
    def test_reads_cockpit_storage_key(self, tmp_path: pathlib.Path):
        from docs_cockpit.browser_storage import (
            STORAGE_KEY,
            read_firefox_localstorage,
        )

        # build fixture profile
        profile = tmp_path / "abc.default-release"
        profile.mkdir()
        override = {"_built_at": "2026-05-19", "M07__st__M07-a": True}
        _make_firefox_sqlite(profile, {STORAGE_KEY: json.dumps(override)})

        result = read_firefox_localstorage(profile)
        assert result == override

    def test_no_match_returns_empty_dict(self, tmp_path: pathlib.Path):
        from docs_cockpit.browser_storage import read_firefox_localstorage

        profile = tmp_path / "abc.default-release"
        profile.mkdir()
        _make_firefox_sqlite(profile, {"some-other-key": '{"foo":1}'})
        result = read_firefox_localstorage(profile)
        assert result == {}

    def test_missing_sqlite_raises(self, tmp_path: pathlib.Path):
        from docs_cockpit.browser_storage import (
            BrowserStorageError,
            read_firefox_localstorage,
        )

        profile = tmp_path / "empty"
        profile.mkdir()
        with pytest.raises(BrowserStorageError):
            read_firefox_localstorage(profile)


# ─── Chrome stub · MVP returns informative error ─────────────────────────


class TestChromeStub:
    def test_chrome_returns_helpful_error(self, tmp_path: pathlib.Path):
        from docs_cockpit.browser_storage import (
            BrowserStorageError,
            read_chrome_localstorage,
        )

        profile = tmp_path / "chrome-profile"
        ldb = profile / "Local Storage" / "leveldb"
        ldb.mkdir(parents=True)
        with pytest.raises(BrowserStorageError) as exc:
            read_chrome_localstorage(profile)
        assert "not yet implemented" in str(exc.value)
        assert "Export" in str(exc.value)

    def test_chrome_missing_leveldb_dir(self, tmp_path: pathlib.Path):
        from docs_cockpit.browser_storage import (
            BrowserStorageError,
            read_chrome_localstorage,
        )

        with pytest.raises(BrowserStorageError) as exc:
            read_chrome_localstorage(tmp_path / "noexist-profile")
        assert "LevelDB not found" in str(exc.value)


# ─── Top-level dispatch ─────────────────────────────────────────────────


class TestReadLocalstorageFromBrowser:
    def test_unsupported_browser_top_level(self):
        from docs_cockpit.browser_storage import (
            BrowserStorageError,
            read_localstorage_from_browser,
        )

        # Even if profile is None · top-level dispatch errors before find_profile_dir
        # (because find_profile_dir itself errors for safari before resolving)
        with pytest.raises(BrowserStorageError):
            read_localstorage_from_browser("safari")
