"""docs-cockpit upgrade · one-command CLI + plugin upgrade · gstack-inspired.

What's wrong with the old "upgrade skill" flow:
- Two-layer model(CLI + plugin)· users had to do both manually
- Cache clear + restart treated as two steps · users paused between → "ghost state"
- Skill教 Claude 分两步说 · 用户被截胡

What this does differently:
- ONE command · detects install backend + checks both layers + decides
- If only CLI changed: pip/uv upgrade · NO restart needed · done
- If plugin SKILL.md changed too: auto cache clear + ATOMIC restart instruction
- Cache clear runs IMMEDIATELY before the restart prompt · no separation window

Convention:
- patch (0.x.Y → 0.x.Y+1) · CLI-only changes · no restart
- minor (0.X → 0.X+1) · plugin SKILL.md / commands changed · needs restart
- major (X → X+1) · breaking config schema · needs restart + migrate

CLI:
  docs-cockpit upgrade                # interactive · auto-detect backend
  docs-cockpit upgrade --dry-run      # print plan · no changes
  docs-cockpit upgrade --no-clear-cache  # skip auto cache-clear · user does manually
  docs-cockpit upgrade --skip-changelog  # don't print CHANGELOG diff
  docs-cockpit upgrade --yes          # non-interactive · just do it
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import urllib.request

from .build import _safe_print

_REMOTE_PLUGIN_JSON = (
    "https://raw.githubusercontent.com/Guohao1020/docs-cockpit/main/"
    ".claude-plugin/plugin.json"
)
_REMOTE_CHANGELOG = (
    "https://raw.githubusercontent.com/Guohao1020/docs-cockpit/main/CHANGELOG.md"
)


def _fetch_remote(url: str, timeout: int = 10) -> str | None:
    """Fetch a URL · return text or None on failure."""
    try:
        from . import __version__ as ver
        req = urllib.request.Request(
            url, headers={"User-Agent": f"docs-cockpit/{ver}"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except Exception:
        return None


def _fetch_remote_version() -> str | None:
    body = _fetch_remote(_REMOTE_PLUGIN_JSON)
    if not body:
        return None
    try:
        return json.loads(body).get("version")
    except Exception:
        return None


def _claude_root() -> pathlib.Path:
    home = pathlib.Path(
        os.environ.get("USERPROFILE") or os.environ.get("HOME") or "~"
    ).expanduser()
    return home / ".claude"


def _find_plugin_cache_paths() -> list[tuple[pathlib.Path, pathlib.Path]]:
    """Walk ~/.claude/plugins/cache/ for docs-cockpit-containing dirs.

    Returns list of (plugin_root_dir, plugin_json_path).
    """
    cache_root = _claude_root() / "plugins" / "cache"
    if not cache_root.is_dir():
        return []
    out: list[tuple[pathlib.Path, pathlib.Path]] = []
    seen: set[pathlib.Path] = set()
    # Look 1-2 levels deep
    for entry in cache_root.iterdir():
        if entry in seen or not entry.is_dir():
            continue
        seen.add(entry)
        if "docs-cockpit" in entry.name.lower():
            pj = entry / ".claude-plugin" / "plugin.json"
            if pj.exists():
                out.append((entry, pj))
            for sub in entry.iterdir():
                if sub.is_dir() and "docs-cockpit" in sub.name.lower():
                    spj = sub / ".claude-plugin" / "plugin.json"
                    if spj.exists():
                        out.append((sub, spj))
    return out


def _read_local_plugin_version() -> tuple[str | None, pathlib.Path | None]:
    paths = _find_plugin_cache_paths()
    if not paths:
        return None, None
    plugin_dir, plugin_json = paths[0]
    try:
        version = json.loads(
            plugin_json.read_text(encoding="utf-8")
        ).get("version")
        return version, plugin_dir
    except Exception:
        return None, plugin_dir


def _detect_install_backend() -> str:
    """Heuristic detection of CLI install backend · pip / uv / pipx / editable."""
    pkg_path = pathlib.Path(__file__).parent.resolve()
    pkg_str = str(pkg_path).lower().replace("\\", "/")

    if "/uv/tools/" in pkg_str or "/.local/uv/" in pkg_str:
        return "uv"
    if "/pipx/" in pkg_str:
        return "pipx"
    # Editable install from a git clone(`pip install -e .`)· just live-on-source
    if (pkg_path.parent / "pyproject.toml").exists():
        return "editable"
    return "pip"


def _run_cli_upgrade(backend: str, dry_run: bool = False) -> tuple[bool, str]:
    """Run the right upgrade command for the detected backend.

    Returns (succeeded, command_str).
    """
    repo = "git+https://github.com/Guohao1020/docs-cockpit.git"

    if backend == "uv":
        cmd: list[str] = ["uv", "tool", "upgrade", "docs-cockpit"]
    elif backend == "pipx":
        cmd = ["pipx", "upgrade", "docs-cockpit"]
    elif backend == "editable":
        # Editable mode · update via git pull from project root
        proj_root = pathlib.Path(__file__).parent.parent
        cmd = ["git", "-C", str(proj_root), "pull"]
    else:
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", repo]

    if dry_run:
        return True, " ".join(cmd) + "  (dry-run)"
    try:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if result.returncode == 0:
            return True, " ".join(cmd)
        # surface stderr tail
        err_tail = (result.stderr or result.stdout or "").splitlines()[-3:]
        _safe_print("  Backend stderr tail:")
        for line in err_tail:
            _safe_print(f"    {line}")
        return False, " ".join(cmd)
    except FileNotFoundError:
        return False, " ".join(cmd) + "  (executable not found)"


def _show_changelog_diff(from_v: str, to_v: str) -> None:
    """Print CHANGELOG entries between two versions."""
    changelog = _fetch_remote(_REMOTE_CHANGELOG)
    if not changelog:
        _safe_print("(Could not fetch CHANGELOG)")
        return
    lines = changelog.split("\n")
    printing = False
    found_any = False
    for line in lines:
        if line.startswith("## ["):
            # Stop when we hit the user's current (or older) version
            if from_v and from_v in line:
                break
            # Start printing once we hit the latest (or any newer) version section
            if not printing:
                printing = True
                found_any = True
        if printing:
            _safe_print(line)
    if not found_any:
        _safe_print(f"(No CHANGELOG entries found between {from_v} and {to_v})")


def _clear_plugin_cache(cache_paths: list) -> int:
    """Remove plugin cache directories · return count cleared."""
    n = 0
    for cache_dir, _ in cache_paths:
        target = cache_dir
        # If we're at a deep dir like cache/docs-cockpit/docs-cockpit/, clear the
        # OUTER container · safer for re-fetch
        while target.parent.name.lower() != "cache" and "docs-cockpit" in target.parent.name.lower():
            target = target.parent
        try:
            shutil.rmtree(target, ignore_errors=True)
            _safe_print(f"  ✓ cleared {target}")
            n += 1
        except Exception as exc:
            _safe_print(f"  ✗ failed to clear {target}: {exc}")
    return n


def cmd_upgrade(args: argparse.Namespace) -> int:
    """One-command upgrade · CLI + plugin · atomic restart instructions."""
    from . import __version__ as local_cli_version

    _safe_print("docs-cockpit upgrade")
    _safe_print("")

    # ── Step 1 · Detect current state ─────────────────────
    _safe_print("Current state:")
    _safe_print(f"  CLI version:    {local_cli_version}")

    local_plugin_v, plugin_dir = _read_local_plugin_version()
    if local_plugin_v:
        _safe_print(f"  Plugin layer:   {local_plugin_v}")
        _safe_print(f"                  {plugin_dir}")
    else:
        _safe_print("  Plugin layer:   not detected (not installed as Claude Code plugin?)")

    backend = _detect_install_backend()
    _safe_print(f"  Install backend: {backend}")
    _safe_print("")

    # ── Step 2 · Fetch remote latest ───────────────────────
    remote_v = _fetch_remote_version()
    if not remote_v:
        _safe_print("[ERR] Could not fetch remote version from GitHub.")
        _safe_print("      Check network / GitHub reachability and try again.")
        return 1
    _safe_print(f"  GitHub latest:  {remote_v}")
    _safe_print("")

    # ── Step 3 · Already up to date? ───────────────────────
    cli_current = (local_cli_version == remote_v)
    plugin_current = (local_plugin_v == remote_v) if local_plugin_v else True

    if cli_current and plugin_current:
        _safe_print("✓ Already up to date · nothing to do.")
        return 0

    # ── Step 4 · Show CHANGELOG diff ──────────────────────
    if not args.skip_changelog:
        _safe_print(f"CHANGELOG diff (your {local_cli_version} → latest {remote_v}):")
        _safe_print("─" * 64)
        _show_changelog_diff(local_cli_version, remote_v)
        _safe_print("─" * 64)
        _safe_print("")

    # ── Step 5 · Confirm (unless --yes / --dry-run) ───────
    if not args.yes and not args.dry_run:
        try:
            confirm = input("Proceed with upgrade? [Y/n] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            _safe_print("\nAborted.")
            return 130
        if confirm == "n":
            _safe_print("Aborted by user.")
            return 0

    # ── Step 6 · CLI upgrade ──────────────────────────────
    if not cli_current:
        _safe_print(f"Step 1/2 · Upgrading CLI ({local_cli_version} → {remote_v}) ...")
        if backend == "editable":
            _safe_print("  Editable install detected · running git pull from project root")
        ok, cmd = _run_cli_upgrade(backend, dry_run=args.dry_run)
        if args.dry_run:
            _safe_print(f"  Would run: {cmd}")
        elif ok:
            _safe_print(f"  ✓ CLI upgrade command succeeded")
            _safe_print(f"  (Note: this process still runs old code · new code on disk)")
        else:
            _safe_print(f"  ✗ Upgrade failed · manual command: {cmd}")
            return 2
        _safe_print("")
    else:
        _safe_print("Step 1/2 · CLI already current · skipping")
        _safe_print("")

    # ── Step 7 · Plugin layer ─────────────────────────────
    _safe_print("Step 2/2 · Checking plugin layer ...")

    if not local_plugin_v:
        _safe_print("  Plugin layer not detected · skipping")
        _safe_print("  (If you DO use Claude Code · the plugin may not have been installed)")
        _safe_print("")
        _safe_print("✓ Done. CLI is up to date.")
        return 0

    if plugin_current:
        _safe_print(f"  ✓ Plugin already at {local_plugin_v} · no restart needed")
        _safe_print("")
        _safe_print("✓ Done. CLI upgraded · plugin already current · no restart needed.")
        return 0

    # Plugin needs refresh
    _safe_print(f"  → Plugin layer needs refresh ({local_plugin_v} → {remote_v})")
    _safe_print("")

    if args.dry_run:
        cache_paths = _find_plugin_cache_paths()
        _safe_print(f"  Would clear {len(cache_paths)} cache director(y/ies):")
        for cache_dir, _ in cache_paths:
            _safe_print(f"    - {cache_dir}")
        _safe_print("  Would tell user to restart Claude Code")
        return 0

    if args.no_clear_cache:
        _safe_print("  --no-clear-cache · skipping auto cache clear")
        _safe_print(f"  Manual: remove cache dirs (see above) · then restart Claude Code")
        return 0

    _safe_print("  Auto-clearing plugin cache ...")
    cache_paths = _find_plugin_cache_paths()
    n_cleared = _clear_plugin_cache(cache_paths)
    if n_cleared == 0:
        _safe_print("  ⚠ No cache directories cleared · path detection may be off")
    _safe_print("")

    # ── Step 8 · ATOMIC restart instruction ───────────────
    bar = "━" * 64
    _safe_print(bar)
    _safe_print("⚠ ATOMIC NEXT STEP · DO THIS NOW · DO NOT DEFER")
    _safe_print(bar)
    _safe_print("")
    _safe_print("Plugin cache cleared. Claude Code is now in a transitional state —")
    _safe_print("MUST be restarted in the next 30 seconds, or you'll get a 'ghost state'")
    _safe_print("(plugin shown 'installed' in Directory but missing from sidebar).")
    _safe_print("")
    _safe_print("Quit Claude Code COMPLETELY (the whole app, not just the chat window):")
    _safe_print("  Windows: right-click Claude Code in system tray → Quit")
    _safe_print("  macOS:   Cmd+Q in Claude Code")
    _safe_print("  CLI:     Ctrl+C the `claude` process, then close terminal")
    _safe_print("")
    _safe_print("Then reopen Claude Code. Plugin will re-fetch from GitHub on startup.")
    _safe_print("")
    _safe_print("Verify post-restart:")
    _safe_print(f"  - /plugin UI shows docs-cockpit version: {remote_v}")
    _safe_print(f"  - Skills list shows {_remote_slash_command_count(remote_v)} slash commands")
    _safe_print(f"  - Re-running `docs-cockpit upgrade` says '✓ Already up to date'")
    return 0


def _remote_slash_command_count(remote_v: str) -> int:
    """Best-effort: how many slash commands the remote ships.

    Tries to count from the remote .claude-plugin or just falls back to a known
    historic number. Used only for verification hint output.
    """
    # Hardcoded knowledge of history(updated when adding new commands):
    #   0.1.3  · 3 commands  (build, status, update)
    #   0.3.0  · 4 commands  (+ migrate)
    #   0.5.0  · 5 commands  (+ browse)
    #   0.7.0  · 6 commands  (+ upgrade)
    try:
        major, minor, patch = (int(x) for x in remote_v.split(".")[:3])
    except Exception:
        return 5
    if (major, minor) >= (0, 7):
        return 6
    if (major, minor) >= (0, 5):
        return 5
    if (major, minor) >= (0, 3):
        return 4
    return 3
