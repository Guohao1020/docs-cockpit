"""docs-cockpit portfolio · 多项目注册表 + 周快照机制 (0.10.0+).

注册表: ~/.docs-cockpit/projects.yaml
快照:   ~/.docs-cockpit/snapshots/<project-name>/<YYYY-MM-DD>.json

为什么用户级注册表(而不是项目级):
- 用户机器上往往同时维护多个 docs-cockpit 项目(work + personal)
- 注册表本身没必要进任何项目仓库 · 也不该跨项目改来改去
- snapshot 是给"本周变化"周报用的 · 自然也是用户级
- 跟 Claude Code 路径解耦 · 装不装 plugin 都能 standalone 用

CLI 设计: `docs-cockpit portfolio <sub>` · 跟 `migrate` / `upgrade` 同层 · 含
  add(默认 CWD) / list(表格输出含 state mtime stale 警告) /
  remove / tag(+- 加减) / snapshot(weekly diff 数据源)

skill 端: docs-cockpit-portfolio · 读注册表 → 让用户挑项目 → 跟最近的
≥5 天 snapshot 对比 → 出多项目 Markdown 周报。
"""

from __future__ import annotations

import argparse
import datetime as _dt
import pathlib
import shutil
import sys
from typing import Any

import yaml


# ── 路径常量 ─────────────────────────────────────────────────────
# pathlib.Path.home() 跨平台:Windows → C:\Users\<name>\ · POSIX → /home/<name>/
PORTFOLIO_DIR = pathlib.Path.home() / ".docs-cockpit"
REGISTRY_PATH = PORTFOLIO_DIR / "projects.yaml"
SNAPSHOTS_DIR = PORTFOLIO_DIR / "snapshots"


def _safe_print(msg: str) -> None:
    """Windows GBK 控制台兼容 · 不丢字符."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode("ascii"))


# ── 注册表读写 ───────────────────────────────────────────────────
def load_registry() -> dict:
    """读 ~/.docs-cockpit/projects.yaml · 不存在返回空骨架 · 解析失败 sys.exit."""
    if not REGISTRY_PATH.exists():
        return {"projects": []}
    try:
        data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        _safe_print(f"[ERR] failed to parse {REGISTRY_PATH}: {exc}")
        sys.exit(2)
    if not isinstance(data, dict):
        data = {}
    data.setdefault("projects", [])
    return data


def save_registry(data: dict) -> None:
    """写 ~/.docs-cockpit/projects.yaml · 父目录自动创建."""
    PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )


# ── state.json 路径推断 ──────────────────────────────────────────
def find_state_json(project_path: pathlib.Path) -> pathlib.Path | None:
    """从项目根推 state.json · 优先级:
    1. docs-cockpit.yaml 里 `project.output` 解析出的目录 + state.json
    2. <project>/docs/state.json (默认 output 约定)
    3. <project>/state.json (扁平布局)
    找不到返回 None。
    """
    candidates: list[pathlib.Path] = []
    cfg_path = project_path / "docs-cockpit.yaml"
    if cfg_path.exists():
        try:
            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            output = (cfg.get("project") or {}).get("output")
            if isinstance(output, str) and output:
                op = pathlib.Path(output)
                if not op.is_absolute():
                    op = project_path / op
                candidates.append(op.parent / "state.json")
        except (yaml.YAMLError, OSError):
            pass
    candidates.append(project_path / "docs" / "state.json")
    candidates.append(project_path / "state.json")
    for c in candidates:
        if c.exists():
            return c.resolve()
    return None


# ── CLI 子命令 ───────────────────────────────────────────────────
def cmd_portfolio_add(args: argparse.Namespace) -> int:
    """把当前目录(或指定路径)注册成一个 portfolio 项目.

    重复 name 会更新 state/repo/tags · 不报错(让 add 幂等 · 方便 ci/script)。
    """
    raw = args.path or "."
    project_path = pathlib.Path(raw).expanduser().resolve()
    if not project_path.is_dir():
        _safe_print(f"[ERR] not a directory: {project_path}")
        return 1

    state_path = find_state_json(project_path)
    if not state_path:
        _safe_print(f"[ERR] no docs/state.json found under {project_path}")
        _safe_print("      run `docs-cockpit build` in that project first · then re-add")
        return 1

    name = args.name or project_path.name
    tags = [t.strip() for t in (args.tags or "active").split(",") if t.strip()]

    data = load_registry()
    existing = next((p for p in data["projects"] if p.get("name") == name), None)
    if existing:
        _safe_print(f"[WARN] project `{name}` already in registry · refreshing fields")
        existing["state"] = str(state_path)
        existing["repo"] = str(project_path)
        existing["tags"] = tags
    else:
        data["projects"].append({
            "name": name,
            "state": str(state_path),
            "repo": str(project_path),
            "tags": tags,
            "added": _dt.date.today().isoformat(),
        })
    save_registry(data)
    _safe_print(f"[OK] {'updated' if existing else 'added'} `{name}`")
    _safe_print(f"     state: {state_path}")
    _safe_print(f"     repo:  {project_path}")
    _safe_print(f"     tags:  {', '.join(tags) if tags else '(none)'}")
    _safe_print(f"     registry: {REGISTRY_PATH}")
    return 0


def cmd_portfolio_list(args: argparse.Namespace) -> int:
    """列注册表 · 表格输出 · state.json mtime + stale 警告(>7d)."""
    data = load_registry()
    projects = data.get("projects") or []
    if not projects:
        _safe_print(f"[ ] no projects registered yet · registry: {REGISTRY_PATH}")
        _safe_print("    add one with: docs-cockpit portfolio add [path]")
        return 0

    now = _dt.datetime.now()
    rows = []
    for p in projects:
        name = p.get("name", "?")
        state_str = p.get("state", "")
        state = pathlib.Path(state_str) if state_str else None
        tags = ", ".join(p.get("tags") or [])
        if state and state.exists():
            mtime = _dt.datetime.fromtimestamp(state.stat().st_mtime)
            age_days = (now - mtime).days
            stale_mark = " ⚠️" if age_days > 7 else ""
            mtime_str = f"{mtime.strftime('%Y-%m-%d %H:%M')} ({age_days}d ago){stale_mark}"
        else:
            mtime_str = "MISSING ❌  (state.json gone · re-build or remove)"
        rows.append({
            "name": name,
            "tags": tags or "(none)",
            "mtime": mtime_str,
        })

    name_w = max(len(r["name"]) for r in rows + [{"name": "Project"}])
    tags_w = max(len(r["tags"]) for r in rows + [{"tags": "Tags"}])
    _safe_print(f"{'Project'.ljust(name_w)}  {'Tags'.ljust(tags_w)}  Last build")
    _safe_print(f"{'-' * name_w}  {'-' * tags_w}  {'-' * 40}")
    for r in rows:
        _safe_print(f"{r['name'].ljust(name_w)}  {r['tags'].ljust(tags_w)}  {r['mtime']}")
    _safe_print("")
    _safe_print(f"Registry · {REGISTRY_PATH}")
    _safe_print(f"Total · {len(projects)} project(s)")
    return 0


def cmd_portfolio_remove(args: argparse.Namespace) -> int:
    """从注册表移除一个项目 · snapshot 保留(让你能恢复 / 翻历史)."""
    data = load_registry()
    name = args.name
    before = len(data["projects"])
    data["projects"] = [p for p in data["projects"] if p.get("name") != name]
    if len(data["projects"]) == before:
        _safe_print(f"[ERR] project `{name}` not found in registry")
        _safe_print(f"      registered names: {[p.get('name') for p in data['projects']]}")
        return 1
    save_registry(data)
    _safe_print(f"[OK] removed `{name}` from registry")
    snap_dir = SNAPSHOTS_DIR / name
    if snap_dir.exists():
        _safe_print(f"     note: snapshots kept at {snap_dir} (delete manually if unwanted)")
    return 0


def cmd_portfolio_tag(args: argparse.Namespace) -> int:
    """加/减标签 · 用法:tag <name> +work -archived 或 tag <name> work."""
    data = load_registry()
    name = args.name
    proj = next((p for p in data["projects"] if p.get("name") == name), None)
    if not proj:
        _safe_print(f"[ERR] project `{name}` not found")
        return 1
    tags = set(proj.get("tags") or [])
    for token in args.changes:
        if token.startswith("+"):
            tags.add(token[1:])
        elif token.startswith("-"):
            tags.discard(token[1:])
        else:
            tags.add(token)
    proj["tags"] = sorted(tags)
    save_registry(data)
    _safe_print(f"[OK] `{name}` tags: {', '.join(proj['tags']) if proj['tags'] else '(none)'}")
    return 0


def cmd_portfolio_snapshot(args: argparse.Namespace) -> int:
    """给每个注册项目的 state.json 拷贝一份到 snapshots/<name>/<YYYY-MM-DD>.json.

    用途:portfolio skill 算"本周变化"时用 · 把今天的 state 跟 ~7 天前的
    snapshot 对比 · 算 newly-done / newly-blocked / 进度跳跃 / 新增模块。

    设计:
    - 同一天多次跑 · 后写覆盖(避免多个版本污染)· 反正一天内多次 build 数据相近
    - 失败的项目(state.json 不存在)跳过 + warn · 不阻塞剩下的
    - 留存策略:第一版不自动 prune · 一个项目 52 张快照 ≈ 几 MB · 用户级目录扛得住
      日后可以加 `--prune --keep N`
    """
    data = load_registry()
    projects = data.get("projects") or []
    if not projects:
        _safe_print("[ ] no projects registered · run `docs-cockpit portfolio add` first")
        return 0

    today = _dt.date.today().isoformat()
    saved = 0
    skipped = 0
    for p in projects:
        name = p.get("name", "?")
        state_str = p.get("state", "")
        state = pathlib.Path(state_str) if state_str else None
        if not state or not state.exists():
            _safe_print(f"[SKIP] {name}: state.json missing at {state} · run build first")
            skipped += 1
            continue
        snap_dir = SNAPSHOTS_DIR / name
        snap_dir.mkdir(parents=True, exist_ok=True)
        snap_path = snap_dir / f"{today}.json"
        shutil.copy2(state, snap_path)
        _safe_print(f"[OK] {name} · {snap_path.relative_to(PORTFOLIO_DIR)}")
        saved += 1
    _safe_print("")
    _safe_print(f"Snapshot summary · {saved} saved · {skipped} skipped")
    _safe_print(f"Snapshots dir · {SNAPSHOTS_DIR}")
    if saved:
        _safe_print("")
        _safe_print("Next: ask Claude for a weekly report.")
        _safe_print("      portfolio skill auto-loads snapshots for week-over-week diff.")
    return 0


# ── argparse wiring · build.py 在 main() 里调 add_portfolio_parser(sub) ──
def add_portfolio_parser(sub: "argparse._SubParsersAction") -> None:
    """挂 `docs-cockpit portfolio ...` 系列子命令 · 跟 migrate/upgrade 同层."""
    pf_p = sub.add_parser(
        "portfolio",
        help="0.10.0+ 多项目注册表 · weekly snapshot · 跨项目周报数据源",
    )
    pf_sub = pf_p.add_subparsers(dest="portfolio_cmd", required=True)

    add_p = pf_sub.add_parser("add", help="把当前目录或指定路径加进注册表")
    add_p.add_argument("path", nargs="?", default=".",
                      help="项目根 · 默认当前目录")
    add_p.add_argument("--name",
                      help="注册名(默认取目录名)· 重复 name 会更新")
    add_p.add_argument("--tags", default="active",
                      help="逗号分隔标签 · 默认 active · 例:work,personal")
    add_p.set_defaults(func=cmd_portfolio_add)

    list_p = pf_sub.add_parser("list", help="列注册表 · 显示 state.json mtime + stale 警告")
    list_p.set_defaults(func=cmd_portfolio_list)

    rm_p = pf_sub.add_parser("remove", help="从注册表移除一个项目(snapshot 保留)")
    rm_p.add_argument("name")
    rm_p.set_defaults(func=cmd_portfolio_remove)

    tag_p = pf_sub.add_parser(
        "tag",
        help="加/减标签 · 例:tag Sourcery +work -archived",
    )
    tag_p.add_argument("name")
    tag_p.add_argument("changes", nargs="+",
                      help="+tag 加 · -tag 删 · tag 直接加")
    tag_p.set_defaults(func=cmd_portfolio_tag)

    snap_p = pf_sub.add_parser(
        "snapshot",
        help="给每个注册项目的 state.json 存今日快照(给 weekly diff 用)",
    )
    snap_p.set_defaults(func=cmd_portfolio_snapshot)
