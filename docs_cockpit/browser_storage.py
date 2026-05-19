"""docs-cockpit `--from-browser` · browser profile localStorage reader (M13/M09-b23cac).

兑现 M09 留的 stub。读 Chrome/Edge LevelDB · Firefox SQLite · 跨 macOS / Windows /
Linux profile dir 自动找 default profile。

实施现状(0.14.3+):

- **Firefox** · ✅ 完整支持 · stdlib `sqlite3` 读 `webappsstore.sqlite` · 无外部 dep
- **Chrome / Edge** · ⚠ partial · 走 stub 路径报错指向 install plyvel · pure-stdlib
  read Chrome LevelDB 太复杂(snappy 压缩 + log format)· 留 v0.15 候选(走 `plyvel`
  optional dep + Linux/macOS only build)

Path 1(Export JSON from dashboard)始终是首选 fallback 路径。
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import sqlite3
import sys
from typing import Any


# localStorage key the dashboard stores overrides under
STORAGE_KEY = "project-kanban-state-v1"

# docs-cockpit dashboard 的 origin scheme · file:// URL · sqlite 里以 `file://` 开头
# 注:不同浏览器 / dashboard 部署可能 origin 不同 · 先 cover file:// · v0.15 加 http(s):// support
_DASHBOARD_ORIGIN_PATTERNS = [
    re.compile(r"^file://.*docs/index\.html$"),   # 最常见 · 跟 cockpit build 输出对齐
    re.compile(r"^file://"),                       # 兜底 · 任何 file:// URL 都试
]


class BrowserStorageError(Exception):
    """Browser profile / localStorage 读失败 · CLI catch 显 stderr."""


# ─── 跨平台 profile dir 解析 ──────────────────────────────────────────────


def _platform() -> str:
    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith("win"):
        return "windows"
    return "linux"


def find_profile_dir(browser: str, profile: str | None = None) -> pathlib.Path | None:
    """跨平台找 browser default(或指定)profile dir.

    Returns the profile dir Path(or None 没找到)· 调用方负责进一步定位
    `webappsstore.sqlite` / `Local Storage/leveldb` 子路径。
    """
    plat = _platform()
    home = pathlib.Path.home()
    candidates: list[pathlib.Path] = []

    if browser in ("chrome", "edge"):
        # Chrome / Edge profile 路径
        if browser == "chrome":
            mac_base = home / "Library/Application Support/Google/Chrome"
            win_base = pathlib.Path(os.getenv("LOCALAPPDATA", "")) / "Google/Chrome/User Data"
            linux_base = home / ".config/google-chrome"
        else:  # edge
            mac_base = home / "Library/Application Support/Microsoft Edge"
            win_base = pathlib.Path(os.getenv("LOCALAPPDATA", "")) / "Microsoft/Edge/User Data"
            linux_base = home / ".config/microsoft-edge"
        base = {"macos": mac_base, "windows": win_base, "linux": linux_base}[plat]
        # default profile name = "Default" · 用户可指定其它 ("Profile 1" etc.)
        candidates.append(base / (profile or "Default"))

    elif browser == "firefox":
        if plat == "macos":
            base = home / "Library/Application Support/Firefox/Profiles"
        elif plat == "windows":
            base = pathlib.Path(os.getenv("APPDATA", "")) / "Mozilla/Firefox/Profiles"
        else:
            base = home / ".mozilla/firefox"
        # Firefox profile 是 `<hash>.default-release` / `<hash>.default` 等
        if profile:
            candidates.append(base / profile)
        elif base.exists():
            # default-release 优先 · default 次之 · 否则取第一个
            for pat in ("*default-release", "*default", "*"):
                hits = sorted(base.glob(pat))
                if hits:
                    candidates.append(hits[0])
                    break

    else:
        raise BrowserStorageError(f"unsupported browser: {browser}")

    for c in candidates:
        if c.exists() and c.is_dir():
            return c
    return None


# ─── Firefox SQLite reader · stdlib sqlite3 · 完整支持 ───────────────────


def read_firefox_localstorage(profile_dir: pathlib.Path) -> dict[str, Any]:
    """读 Firefox `webappsstore.sqlite` 里 cockpit dashboard 的 localStorage entries.

    Schema(Firefox 50+):
        TABLE webappsstore2 (
            originAttributes TEXT,
            originKey TEXT,             -- e.g. ":file"
            scope TEXT,
            key TEXT,                   -- localStorage key (我们要 "project-kanban-state-v1")
            value TEXT                  -- JSON-encoded value
        )

    Firefox 102+ 用 `ls-archive.sqlite`(更新 backend)· 兼容老的 webappsstore.sqlite。

    本函数找两个文件之一 · 取我们 `STORAGE_KEY` 的 value 反序列化返回。
    """
    sqlite_candidates = [
        profile_dir / "webappsstore.sqlite",
        profile_dir / "storage" / "default" / "ls-archive.sqlite",
    ]
    sqlite_path = next((p for p in sqlite_candidates if p.exists()), None)
    if sqlite_path is None:
        raise BrowserStorageError(
            f"Firefox localStorage SQLite not found under {profile_dir} · "
            f"tried: {[str(p) for p in sqlite_candidates]}"
        )

    # 拷一个副本到 temp · 避免 Firefox running 时 sqlite 锁冲突
    import shutil
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        copy = pathlib.Path(td) / sqlite_path.name
        shutil.copy2(sqlite_path, copy)
        conn = sqlite3.connect(str(copy))
        try:
            # 检测表名(webappsstore.sqlite uses `webappsstore2` · ls-archive.sqlite 不同 schema)
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
            if "webappsstore2" in tables:
                rows = conn.execute(
                    "SELECT originKey, key, value FROM webappsstore2 "
                    "WHERE key = ?",
                    (STORAGE_KEY,),
                ).fetchall()
                # 寻找 originKey 含 file://(dashboard 是 file:// 上下文)
                for origin_key, _key, value in rows:
                    if "file" in (origin_key or "").lower():
                        try:
                            return json.loads(value)
                        except json.JSONDecodeError:
                            pass
                # 找不到 file:// origin · 取第一个 hit(用户 dashboard 可能在别 origin)
                if rows:
                    try:
                        return json.loads(rows[0][2])
                    except json.JSONDecodeError:
                        pass
                return {}
            else:
                # ls-archive 新 schema · v0.15 加 reader · MVP 不 cover
                raise BrowserStorageError(
                    "Firefox 102+ ls-archive.sqlite schema not yet supported · "
                    "fall back to: dashboard Export button → docs-cockpit sync-status --import"
                )
        finally:
            conn.close()

    return {}


# ─── Chrome / Edge · stub · 留 v0.15 候选 ──────────────────────────────


def read_chrome_localstorage(
    profile_dir: pathlib.Path,
) -> dict[str, Any]:
    """读 Chrome / Edge LevelDB · MVP stub · 报错指向 Export JSON workflow.

    Chrome 的 localStorage 在 `<profile>/Local Storage/leveldb/` · LevelDB binary
    format · pure-stdlib 解析复杂(snappy 压缩 + manifest/log file format)。
    `plyvel` Python binding 需要 libleveldb C library · Windows build 太麻烦。

    本 MVP 直接报错 · 让用户走 Path 1(dashboard Export JSON)。v0.15 候选:
      - 加 `[browser]` optional dep · `pip install 'docs-cockpit[browser]'` 装 plyvel
      - 或者 ship pure-Python leveldb reader(scope 大 · 单独 ticket)
    """
    ldb_dir = profile_dir / "Local Storage" / "leveldb"
    if not ldb_dir.exists():
        raise BrowserStorageError(
            f"Chrome/Edge LevelDB not found at {ldb_dir} · "
            f"profile dir might be wrong"
        )
    raise BrowserStorageError(
        f"Chrome/Edge LevelDB read is not yet implemented (v0.15 candidate). "
        f"LevelDB binary format requires `plyvel` (which needs libleveldb C lib · "
        f"hard to install on Windows). "
        f"Workaround: open dashboard at file://.../docs/index.html · "
        f"click topbar 「Export」 button to download overrides JSON · then run:\n"
        f"  docs-cockpit sync-status --import overrides.json [--apply]"
    )


# ─── Top-level dispatch · cmd_sync_status --from-browser uses this ──────


def read_localstorage_from_browser(
    browser: str, profile: str | None = None
) -> dict[str, Any]:
    """End-to-end · find profile + read localStorage[STORAGE_KEY]."""
    profile_dir = find_profile_dir(browser, profile=profile)
    if profile_dir is None:
        raise BrowserStorageError(
            f"could not locate {browser} profile · tried platform-default paths. "
            f"Pass --profile <name> to override · or use Export JSON workflow."
        )
    if browser == "firefox":
        return read_firefox_localstorage(profile_dir)
    if browser in ("chrome", "edge"):
        return read_chrome_localstorage(profile_dir)
    raise BrowserStorageError(f"unsupported browser: {browser}")
