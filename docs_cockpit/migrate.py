"""docs-cockpit migrate · 把现有项目的散落 MD 文档迁移到 canonical 布局.

适用场景:已有项目用 `docs/plans/`、`docs/adrs/`、`docs/superpowers/plans/`、
`docs/PRD/` 等散落结构 · 想一键迁到 `docs/spec/module/` + 自动写
`docs-cockpit.yaml` + 跑 build。

设计:
- **dry-run by default** · 只 print 迁移计划 · 不动文件
- **--apply** · 真执行 · git mv 保留 history · 注入 frontmatter
- **--keep-originals** · 复制而非移动 · 保留 docs/plans/ 等原 dir
- **启发式分类** · 见 MODULE_DIRS / CONCEPT_DIRS / SYSDOC_DIRS

迁移后产出:
- `docs/spec/module/M{NN}-{slug}.md` · 含 frontmatter (id/title/status/sprint/progress)
- `docs/spec/concept/C{NN}-{slug}.md` (如有)
- `docs-cockpit.yaml` · 含 project / paths / system_docs / modules / concepts / frontmatter
- 用户跑 `docs-cockpit build` 即出 dashboard
"""

from __future__ import annotations

import argparse
import pathlib
import re
import shutil
import subprocess
from typing import Any

import yaml

from .build import (
    _safe_print,
    slugify,
    split_frontmatter,
    extract_subtasks_from_body,
    extract_docs_from_body,
)

# ── 启发式分类规则 ────────────────────────────────────────────────────
# 这些目录里的 *.md 文件 · 默认视为 module candidate
MODULE_DIRS = [
    "docs/spec/module",
    "docs/plans",
    "docs/tasks",
    "docs/adrs",
    "docs/superpowers/plans",
    "docs/superpowers/specs",
]

# 这些目录里的 *.md 视为 concept
CONCEPT_DIRS = [
    "docs/spec/concept",
    "docs/concepts",
]

# 这些目录整个作为 system_docs 一条 entry(指向目录 · 不是单文件)
SYSDOC_DIRS = [
    "docs/PRD",
    "docs/RFC",
    "docs/architecture",
    "docs/DESIGN",
    "docs/audits",
    "docs/review",
]

# 这些根级文件 · 各自作为 system_docs 一条 entry
ROOT_SYSDOC_FILES = [
    "README.md",
    "CLAUDE.md",
    "AGENTS.md",
    "GEMINI.md",
    "PROGRESS.md",
    "CHANGELOG.md",
    "PRE-LAUNCH-CHECKLIST.md",
    "dogfood-onboarding.md",
    "DESIGN.md",
]


def _icon_for(name: str) -> str:
    """根据 entry 名启发挑 icon · memory / design / plan / doc."""
    n = name.lower()
    if any(k in n for k in ("memory", "claude", "agents", "gemini")):
        return "memory"
    if any(k in n for k in ("design", "architecture", "audit")):
        return "design"
    if any(
        k in n
        for k in ("plan", "roadmap", "progress", "checklist", "dogfood", "rfc", "adr")
    ):
        return "plan"
    return "doc"


def _h1_or_stem(path: pathlib.Path) -> str:
    """读 MD 第一行 H1 作 title · 否则从文件名 stem 推."""
    try:
        body = path.read_text(encoding="utf-8")
    except Exception:
        body = ""
    _, content = split_frontmatter(body)
    m = re.search(r"^#\s+(.+?)$", content, re.MULTILINE)
    if m:
        title = m.group(1).strip()
        # 去掉文章开头的 "M01 · " / "C03 - " / "ADR 0001:" 之类的前缀
        title = re.sub(r"^[MCTPR]\d+\s*[·.\-:]?\s*", "", title, flags=re.IGNORECASE)
        title = re.sub(r"^(ADR|RFC)[-\s]*\d+\s*[·.\-:]?\s*", "", title, flags=re.IGNORECASE)
        return title.strip() or path.stem
    # fallback · 文件名 stem · 横线 / 下划线 → 空格 · 首字母大写
    stem = re.sub(r"^[MCTPR]?\d+[-_]*", "", path.stem)
    stem = re.sub(r"^(ADR|RFC)[-_]*\d+[-_]*", "", stem, flags=re.IGNORECASE)
    return stem.replace("-", " ").replace("_", " ").strip().title() or path.stem


def _slug_from_stem(stem: str) -> str:
    """文件名 stem 去序号前缀后 slugify."""
    # 去 M01- / C03- / P01- / 0001- / ADR-0008- 等前缀
    s = re.sub(
        r"^(?:[MCTPR]\d+|ADR[-_]?\d+|RFC[-_]?\d+|\d+)[-_·.\s]*",
        "",
        stem,
        flags=re.IGNORECASE,
    )
    s = re.sub(r"[^a-z0-9一-鿿]+", "-", s.lower()).strip("-")
    return s or stem.lower()


def _collect_files(repo: pathlib.Path, dirs: list[str]) -> list[pathlib.Path]:
    """扫多个 dir · 收集 *.md · 去重 · 排序."""
    out: list[pathlib.Path] = []
    seen: set[pathlib.Path] = set()
    for d in dirs:
        dir_path = repo / d
        if not dir_path.is_dir():
            continue
        for p in sorted(dir_path.glob("**/*.md")):
            if not p.is_file():
                continue
            if p.name.startswith("_") or p.stem.upper() == "README":
                continue
            if p in seen:
                continue
            seen.add(p)
            out.append(p)
    return out


def _build_plan(repo_root: pathlib.Path) -> dict:
    """扫描 repo · 输出迁移 plan."""
    plan: dict[str, Any] = {
        "repo": repo_root,
        "project_name": repo_root.name,
        "modules": [],
        "concepts": [],
        "system_docs": [],
        "module_dir": repo_root / "docs" / "spec" / "module",
        "concept_dir": repo_root / "docs" / "spec" / "concept",
    }

    # 1) modules
    mod_files = _collect_files(repo_root, MODULE_DIRS)
    for i, src in enumerate(mod_files, start=1):
        mid = f"M{i:02d}"
        slug = _slug_from_stem(src.stem)
        target = plan["module_dir"] / f"{mid}-{slug}.md"
        try:
            existing_meta, _ = split_frontmatter(src.read_text(encoding="utf-8"))
        except Exception:
            existing_meta = {}
        plan["modules"].append({
            "source": src,
            "target": target,
            "id": mid,
            "title": _h1_or_stem(src),
            "existing_meta": existing_meta or {},
        })

    # 2) concepts
    con_files = _collect_files(repo_root, CONCEPT_DIRS)
    for i, src in enumerate(con_files, start=1):
        cid = f"C{i:02d}"
        slug = _slug_from_stem(src.stem)
        target = plan["concept_dir"] / f"{cid}-{slug}.md"
        try:
            existing_meta, _ = split_frontmatter(src.read_text(encoding="utf-8"))
        except Exception:
            existing_meta = {}
        plan["concepts"].append({
            "source": src,
            "target": target,
            "id": cid,
            "title": _h1_or_stem(src),
            "existing_meta": existing_meta or {},
        })

    # 3) system_docs · root files
    for fn in ROOT_SYSDOC_FILES:
        p = repo_root / fn
        if p.is_file():
            plan["system_docs"].append({
                "id": slugify(p.stem) or p.stem.lower(),
                "title": fn,
                "path": "{repo}/" + fn,
                "desc": "",
                "icon": _icon_for(fn),
            })

    # 4) system_docs · whole dirs
    for d in SYSDOC_DIRS:
        p = repo_root / d
        if p.is_dir():
            n_files = len(list(p.glob("*.md")))
            name = d.rsplit("/", 1)[-1]
            plan["system_docs"].append({
                "id": slugify(name) or name.lower(),
                "title": name + "/",
                "path": "{repo}/" + d + "/",
                "desc": f"{n_files} 份" if n_files else "",
                "icon": _icon_for(d),
            })

    return plan


def _print_plan(plan: dict, apply: bool) -> None:
    repo = plan["repo"]
    mode = "APPLY" if apply else "DRY-RUN"
    _safe_print(f"docs-cockpit migrate · {mode}")
    _safe_print(f"Repo: {repo}")
    _safe_print("")

    if plan["modules"]:
        _safe_print(f"MODULES ({len(plan['modules'])} → docs/spec/module/):")
        for m in plan["modules"][:30]:
            src_rel = m["source"].relative_to(repo)
            tgt_rel = m["target"].relative_to(repo)
            has_fm = bool(m["existing_meta"].get("id"))
            mark = "✓" if has_fm else " "
            _safe_print(f"  {mark} {m['id']}  {src_rel}")
            _safe_print(f"     → {tgt_rel}")
            _safe_print(f"     title: \"{m['title']}\"")
        if len(plan["modules"]) > 30:
            _safe_print(f"  ... ({len(plan['modules']) - 30} more not shown)")
        _safe_print("")
    else:
        _safe_print("MODULES: (none detected)")
        _safe_print(f"  Known dirs: {', '.join(MODULE_DIRS)}")
        _safe_print("")

    if plan["concepts"]:
        _safe_print(f"CONCEPTS ({len(plan['concepts'])} → docs/spec/concept/):")
        for c in plan["concepts"][:20]:
            src_rel = c["source"].relative_to(repo)
            tgt_rel = c["target"].relative_to(repo)
            _safe_print(f"   {c['id']}  {src_rel} → {tgt_rel}")
        _safe_print("")

    if plan["system_docs"]:
        _safe_print(f"SYSTEM_DOCS ({len(plan['system_docs'])} entries):")
        for sd in plan["system_docs"]:
            _safe_print(
                f"   - {sd['title']:<32}  icon={sd['icon']:<8}  {sd['path']}"
            )
        _safe_print("")

    yaml_path = repo / "docs-cockpit.yaml"
    if yaml_path.exists():
        _safe_print(f"⚠ docs-cockpit.yaml 已存在 · 将被覆盖: {yaml_path}")
    else:
        _safe_print(f"docs-cockpit.yaml will be written to: {yaml_path}")

    _safe_print("")
    if not apply:
        _safe_print("─── DRY RUN · 没有任何文件被修改 ───")
        _safe_print("确认无误后跑:  docs-cockpit migrate --apply")
        _safe_print("不想动原文件:  docs-cockpit migrate --apply --keep-originals")


def _git_mv(src: pathlib.Path, dst: pathlib.Path, repo: pathlib.Path) -> bool:
    """Try `git mv src dst` · 保留 git history. Return True on success."""
    try:
        subprocess.run(
            ["git", "mv", str(src), str(dst)],
            cwd=str(repo),
            check=True,
            capture_output=True,
        )
        return True
    except Exception:
        return False


def _inject_frontmatter(path: pathlib.Path, item: dict) -> None:
    """Merge frontmatter into target file · existing 字段优先 · 缺的填默认.

    0.4.0 起 · frontmatter 没有 subtasks / docs 时 · 自动从 MD body 的
    `## 待办` / `## 关联` 段提取并写入 frontmatter(让用户跑 build 后
    dashboard drawer 直接看到 · 不用再编辑 MD)。
    """
    raw = path.read_text(encoding="utf-8")
    existing_meta, content = split_frontmatter(raw)
    existing_meta = existing_meta or {}

    progress = existing_meta.get("progress")
    if not isinstance(progress, (int, float)):
        progress = 0

    new_meta: dict[str, Any] = {
        "id": item["id"],
        "title": existing_meta.get("title") or item["title"],
        "status": existing_meta.get("status") or "not-started",
        "sprint": existing_meta.get("sprint") or "M0",
        "progress": progress,
    }

    # 0.4.0:body 提取 subtasks / docs 补进 frontmatter
    if not existing_meta.get("subtasks"):
        body_subtasks = extract_subtasks_from_body(content)
        if body_subtasks:
            new_meta["subtasks"] = body_subtasks
    if not existing_meta.get("docs"):
        body_docs = extract_docs_from_body(content)
        if body_docs:
            new_meta["docs"] = body_docs

    # 保留 user 已有的其他字段(desc / docs / subtasks / owner / etc.)
    for k, v in existing_meta.items():
        if k not in new_meta:
            new_meta[k] = v

    fm_yaml = yaml.dump(
        new_meta,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    new_body = f"---\n{fm_yaml}---\n\n{content.lstrip()}"
    path.write_text(new_body, encoding="utf-8")


def _execute_plan(plan: dict, keep_originals: bool = False) -> int:
    """Apply migration · return n_files_processed."""
    repo = plan["repo"]
    plan["module_dir"].mkdir(parents=True, exist_ok=True)
    if plan["concepts"]:
        plan["concept_dir"].mkdir(parents=True, exist_ok=True)

    n_done = 0
    n_skip = 0
    for item in plan["modules"] + plan["concepts"]:
        src = item["source"]
        dst = item["target"]
        if dst.exists():
            _safe_print(f"  [SKIP] target exists: {dst.relative_to(repo)}")
            n_skip += 1
            continue
        try:
            if keep_originals:
                shutil.copy2(src, dst)
            else:
                if not _git_mv(src, dst, repo):
                    src.rename(dst)
            _inject_frontmatter(dst, item)
            n_done += 1
        except Exception as exc:
            _safe_print(f"  [ERR] {src.relative_to(repo)}: {exc}")

    action = "Copied" if keep_originals else "Moved"
    _safe_print(f"\n  ✓ {action} + frontmatter-injected: {n_done} files")
    if n_skip:
        _safe_print(f"  ⚠ Skipped (target exists): {n_skip} files")
    return n_done


def _write_yaml(plan: dict) -> pathlib.Path:
    """Write docs-cockpit.yaml based on migration plan."""
    repo = plan["repo"]
    name = plan["project_name"]
    mark = name[0].upper() if name else "P"

    config: dict[str, Any] = {
        "project": {
            "name": name,
            "mark": mark,
            "tagline": "项目进度概览 · Dashboard",
            "output": "docs/index.html",
        },
        "paths": {"repo": "."},
    }
    if plan["system_docs"]:
        config["system_docs"] = plan["system_docs"]
    if plan["modules"]:
        config["modules"] = {
            "scan": {
                "dir": "{repo}/docs/spec/module",
                "title_transform": "prefix-dot-titlecase",
            }
        }
    if plan["concepts"]:
        config["concepts"] = {
            "scan": {
                "dir": "{repo}/docs/spec/concept",
                "title_transform": "prefix-dot-titlecase",
            }
        }
    config["frontmatter"] = {"enabled": True}

    yaml_path = repo / "docs-cockpit.yaml"
    yaml_text = yaml.dump(
        config,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    yaml_path.write_text(yaml_text, encoding="utf-8")
    return yaml_path


def cmd_migrate(args: argparse.Namespace) -> int:
    repo_root = pathlib.Path(args.repo or ".").resolve()
    if not repo_root.is_dir():
        _safe_print(f"[ERR] not a directory: {repo_root}")
        return 1

    plan = _build_plan(repo_root)

    n_mods = len(plan["modules"])
    n_concepts = len(plan["concepts"])
    n_sysdocs = len(plan["system_docs"])
    if n_mods == 0 and n_concepts == 0 and n_sysdocs == 0:
        _safe_print("[WARN] no MD files found in known directories.")
        _safe_print(f"       Known module dirs: {', '.join(MODULE_DIRS)}")
        _safe_print(f"       Known concept dirs: {', '.join(CONCEPT_DIRS)}")
        _safe_print(f"       Known sysdoc dirs: {', '.join(SYSDOC_DIRS)}")
        _safe_print("Migration not applicable. Use `docs-cockpit init` for a blank yaml.")
        return 1

    _print_plan(plan, args.apply)

    if not args.apply:
        return 0

    _execute_plan(plan, keep_originals=args.keep_originals)
    yaml_path = _write_yaml(plan)
    _safe_print(f"\n  ✓ Wrote {yaml_path.relative_to(repo_root)}")
    _safe_print("")
    _safe_print("Next:")
    _safe_print("  docs-cockpit build")
    return 0
