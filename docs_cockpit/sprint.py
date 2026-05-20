"""docs-cockpit sprint · v0.19.0 · agile sprint plan first-class.

实现 P-v0.19-agile-version-planning.md §5 列的三个 CLI subcommand:

    docs-cockpit sprint init <version> [--window ...] [--slug ...]
        从模板 scaffold 一份 sprint-plan MD · 默认从 state.json 反查该 sprint
        下哪些 module 自动填 in_scope[]

    docs-cockpit sprint check <version|--all> [--strict]
        跑 lint_sprint_readiness 输出报告 · CI 用 --strict 把 warn 升 error

    docs-cockpit sprint list [--status ...]
        列所有 sprint-plan + 状态 · 默认按 id 倒序

跟现有 lint / build 关系:
- build_payload 已经把 lint_sprint_readiness 进 issue pipeline(默认 opt-in)
- 本 module 的 sprint check 是个 focused entry point · 只跑 sprint 相关 lint
- sprint list 是 read-only · 不重 build

Sprint-plan 文件命名约定:`docs/plans/V<x.y>[-<slug>].md`
"""

from __future__ import annotations

import datetime as _dt
import json
import pathlib
import sys
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover · pyyaml 是核心 dep
    yaml = None  # type: ignore

from .schema import (
    Issue,
    _normalize_sprint_id,
    lint_sprint_readiness,
    split_frontmatter,
    validate_sprint_plan,
)


SPRINT_PLAN_DIR = "docs/plans"
SPRINT_PLAN_GLOB = "V*.md"


def load_sprint_plans(repo_root: pathlib.Path) -> list[dict]:
    """扫 docs/plans/V*.md · 返 [{path, meta, body, _validate_issues}, ...].

    每个 sprint-plan 文件:
    - frontmatter 必须有 type: sprint-plan(否则跳过 · 当成普通 plan)
    - validate_sprint_plan 跑一遍 · 结果挂在 _validate_issues 上
    """
    plans_dir = repo_root / SPRINT_PLAN_DIR
    if not plans_dir.exists():
        return []
    out: list[dict] = []
    for p in sorted(plans_dir.glob(SPRINT_PLAN_GLOB)):
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        meta, body = split_frontmatter(text)
        if not isinstance(meta, dict):
            continue
        if meta.get("type") != "sprint-plan":
            continue
        issues = validate_sprint_plan(p, meta)
        out.append({
            "path": str(p),
            "meta": meta,
            "body": body,
            "_validate_issues": issues,
        })
    return out


def _load_state(repo_root: pathlib.Path) -> dict[str, Any]:
    """读 docs/state.json · 拿 modules 给 lint_sprint_readiness 用."""
    state_path = repo_root / "docs" / "state.json"
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _config_repo_root(config_path: pathlib.Path) -> pathlib.Path:
    """从 config 路径推 repo_root · 默认是 config 所在目录."""
    return config_path.parent.resolve()


# ─── sprint init ─────────────────────────────────────────────────────────


def _scaffold_sprint_plan(
    sprint_id: str,
    window: str,
    slug: str,
    repo_root: pathlib.Path,
) -> str:
    """从 templates/sprint-plan.md.j2 渲染一份 scaffold · 自动从 state.json 反查
    sprint 下哪些 module · 填进 in_scope[]。"""
    # template 路径 · 跟 prompt.py 同款约定
    tpl_path = pathlib.Path(__file__).parent / "templates" / "sprint-plan.md.j2"
    if not tpl_path.exists():
        raise RuntimeError(f"sprint-plan template missing: {tpl_path}")

    state = _load_state(repo_root)
    modules = state.get("modules") or []

    # 反查 sprint 下的 module · `0.19` / `V0.19` / `0.19.0` 都尽量 match
    sprint_short = sprint_id.lstrip("Vv").strip()
    in_scope: list[dict] = []
    for m in modules:
        ms = (m.get("sprint") or "").strip()
        if not ms:
            continue
        if ms == sprint_short or _normalize_sprint_id(ms) == _normalize_sprint_id(sprint_id):
            in_scope.append({
                "module": m.get("id", ""),
                "subtasks": [],  # 默认 空 list · 用户自己挑哪些 in scope
            })

    # 简单的 Jinja2 渲染 · 不走 SandboxedEnvironment 因为是 trusted local template
    try:
        import jinja2

        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(tpl_path.parent)),
            keep_trailing_newline=True,
            autoescape=False,
        )
        template = env.get_template(tpl_path.name)
        return template.render(
            sprint_id=sprint_id,
            sprint_id_normalized=_normalize_sprint_id(sprint_id),
            window=window,
            slug=slug,
            in_scope=in_scope,
            today=_dt.date.today().isoformat(),
        )
    except ImportError:
        raise RuntimeError("jinja2 not installed · `pip install jinja2`")


def cmd_sprint_init(args) -> int:
    """`docs-cockpit sprint init <version>` · scaffold sprint plan MD."""
    cfg_path = pathlib.Path(getattr(args, "config", None) or "docs-cockpit.yaml")
    if not cfg_path.exists():
        print(f"[ERR] config not found: {cfg_path}", file=sys.stderr)
        return 2
    repo_root = _config_repo_root(cfg_path)

    sprint_id_raw = (getattr(args, "version", None) or "").strip()
    if not sprint_id_raw:
        print("[ERR] usage: docs-cockpit sprint init <version>", file=sys.stderr)
        return 2
    sprint_id = _normalize_sprint_id(sprint_id_raw)

    # window 默认 = 今天 + 14 天
    window = getattr(args, "window", None)
    if not window:
        today = _dt.date.today()
        end = today + _dt.timedelta(days=14)
        window = f"{today.isoformat()} → {end.isoformat()}"

    slug = (getattr(args, "slug", None) or "").strip()
    filename_base = sprint_id
    if slug:
        filename_base = f"{sprint_id}-{slug}"
    target = repo_root / SPRINT_PLAN_DIR / f"{filename_base}.md"

    if target.exists() and not getattr(args, "force", False):
        print(
            f"[ERR] {target} 已存在 · 加 --force 覆盖(会先 .bak)",
            file=sys.stderr,
        )
        return 1

    try:
        scaffold = _scaffold_sprint_plan(sprint_id, window, slug, repo_root)
    except RuntimeError as e:
        print(f"[ERR] scaffold failed: {e}", file=sys.stderr)
        return 2

    if target.exists():  # --force
        import shutil

        bak = target.with_suffix(target.suffix + ".bak")
        shutil.copy2(target, bak)
        print(f"[backup] {bak}", file=sys.stderr)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(scaffold, encoding="utf-8")
    print(f"[OK] wrote {target}")
    print("     next steps:")
    print(f"       1. edit goals[] / dor[] / dod[] / prd_refs[]")
    print(f"       2. run `docs-cockpit sprint check {sprint_id_raw}` to verify DoR")
    print(f"       3. start working · subtasks 进度 docs-cockpit build 自动算")
    return 0


# ─── sprint check ─────────────────────────────────────────────────────────


def cmd_sprint_check(args) -> int:
    """`docs-cockpit sprint check <version|--all> [--strict]` · 跑 sprint-readiness lint."""
    cfg_path = pathlib.Path(getattr(args, "config", None) or "docs-cockpit.yaml")
    if not cfg_path.exists():
        print(f"[ERR] config not found: {cfg_path}", file=sys.stderr)
        return 2
    repo_root = _config_repo_root(cfg_path)

    state = _load_state(repo_root)
    if not state:
        print(
            "[ERR] docs/state.json 不存在或解析失败 · 先跑 `docs-cockpit build`",
            file=sys.stderr,
        )
        return 2

    sprint_plans = load_sprint_plans(repo_root)
    if not sprint_plans:
        print(
            "[WARN] 当前 repo 还没有 sprint-plan(docs/plans/V*.md)· "
            "跑 `docs-cockpit sprint init <version>` 起一份",
        )
        return 0 if not getattr(args, "strict", False) else 1

    # filter by version 或 --all
    target_version = (getattr(args, "version", None) or "").strip()
    all_flag = getattr(args, "all_sprints", False)
    if not target_version and not all_flag:
        print(
            "[ERR] usage: docs-cockpit sprint check <version> 或 --all",
            file=sys.stderr,
        )
        return 2

    if target_version:
        norm = _normalize_sprint_id(target_version)
        sprint_plans = [
            sp for sp in sprint_plans
            if _normalize_sprint_id((sp.get("meta") or {}).get("id", "")) == norm
        ]
        if not sprint_plans:
            print(
                f"[ERR] sprint-plan id={norm} 找不到 · "
                f"`docs-cockpit sprint list` 看现有的",
                file=sys.stderr,
            )
            return 2

    modules = state.get("modules") or []

    # 1) sprint-plan schema 校验(每个 plan 各自的 validate_sprint_plan 结果)
    all_issues: list[Issue] = []
    for sp in sprint_plans:
        all_issues.extend(sp.get("_validate_issues") or [])

    # 2) sprint-readiness lint(DoR check · 全部 plan 一起跑)
    proj_cfg = _read_project_cfg(cfg_path)
    enforce = bool((proj_cfg or {}).get("enforce_sprint_plans", False))
    all_issues.extend(lint_sprint_readiness(modules, sprint_plans, enforce=enforce))

    errors = [i for i in all_issues if i.severity == "error"]
    warns = [i for i in all_issues if i.severity == "warn"]
    hints = [i for i in all_issues if i.severity == "hint"]

    # report
    if not all_issues:
        plan_ids = [
            (sp.get("meta") or {}).get("id", "?") for sp in sprint_plans
        ]
        print(
            f"[OK] sprint readiness · {len(sprint_plans)} plan(s) checked: "
            f"{', '.join(plan_ids)} · 0 issue · DoR 全部满足"
        )
        return 0

    severity_rank = {"error": 0, "warn": 1, "hint": 2}
    all_issues.sort(key=lambda i: (severity_rank.get(i.severity, 9), str(i.path)))

    for issue in all_issues:
        print(issue.format_for_terminal())
        print()

    print(
        f"Summary · {len(errors)} error(s) · {len(warns)} warning(s) · "
        f"{len(hints)} hint(s)"
    )
    print(
        "Reference · docs-cockpit-author skill · §17 (agile workflow)"
    )

    if errors:
        return 1
    if warns and getattr(args, "strict", False):
        return 1
    return 0


def _read_project_cfg(config_path: pathlib.Path) -> dict:
    """读 yaml 拿 project 子段 · 用来看 enforce_sprint_plans 配置."""
    if yaml is None:
        return {}
    try:
        cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}
    return cfg.get("project") or {}


# ─── sprint list ─────────────────────────────────────────────────────────


def cmd_sprint_list(args) -> int:
    """`docs-cockpit sprint list [--status ...]` · 列所有 sprint-plan + 状态."""
    cfg_path = pathlib.Path(getattr(args, "config", None) or "docs-cockpit.yaml")
    if not cfg_path.exists():
        print(f"[ERR] config not found: {cfg_path}", file=sys.stderr)
        return 2
    repo_root = _config_repo_root(cfg_path)

    sprint_plans = load_sprint_plans(repo_root)
    if not sprint_plans:
        print("(no sprint plans yet · run `docs-cockpit sprint init <version>` 起一份)")
        return 0

    status_filter = (getattr(args, "status", None) or "").strip()

    # 按 id 自然排序(走 _normalize_sprint_id 后字典序 · semver 单 digit minor 安全)
    sprint_plans.sort(
        key=lambda sp: _normalize_sprint_id((sp.get("meta") or {}).get("id", "")),
        reverse=True,
    )

    # ascii table · 4 列:id / status / progress / window
    header = ("Sprint", "Status", "Progress", "Window")
    rows: list[tuple[str, str, str, str]] = []
    for sp in sprint_plans:
        meta = sp.get("meta") or {}
        status = (meta.get("status") or "?")
        if status_filter and status != status_filter:
            continue
        rows.append((
            str(meta.get("id") or pathlib.Path(sp["path"]).stem),
            status,
            f"{meta.get('progress', 0)}%",
            str(meta.get("window") or ""),
        ))

    if not rows:
        print(f"(no sprint plans match status={status_filter!r})")
        return 0

    widths = [
        max(len(header[i]), *(len(r[i]) for r in rows)) for i in range(4)
    ]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*header))
    print(fmt.format(*("-" * w for w in widths)))
    for r in rows:
        print(fmt.format(*r))
    print()
    print(f"{len(rows)} sprint-plan(s) shown")
    return 0
