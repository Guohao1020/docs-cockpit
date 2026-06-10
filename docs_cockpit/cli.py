"""docs-cockpit · CLI argparse dispatcher.

v1.0 起 CLI 只保留机械渲染核 · 认知子命令(prompt / suggest / verify /
sprint / apply-patch / apply-body-patch / migrate-subtasks / mcp-serve)
已删除 · 认知职责由 plugin skills 承担:

  render(+ deprecated alias build)/ lint / init → build.py
  migrate → migrate.py
  browse → browse.py
  sync-status → sync_status.py
  upgrade → upgrade.py

0.11.0-alpha.1:从 build.py 拆出(plan-eng-review 1A)。
build.py 仍 re-export `main` · 老 entry-point (`docs_cockpit.build:main`)
和老 import (`from docs_cockpit.build import main`)继续 work。
"""

from __future__ import annotations

import argparse
import sys


def _add_render_options(p: argparse.ArgumentParser) -> None:
    """render/build 共用选项 · 集中一处防 alias 漂移 · 无状态纯参数定义 helper."""
    p.add_argument("--config", "-c", default="docs-cockpit.yaml",
                   help="YAML 配置文件路径(默认:当前目录 docs-cockpit.yaml)")
    p.add_argument("--debug", action="store_true",
                   help="打印解析后的路径变量与每条 entry 的绝对路径")
    p.add_argument("--no-version-check", action="store_true",
                   help="跳过新版本检测(也可设 DOCS_COCKPIT_NO_VERSION_CHECK=1)")
    p.add_argument("--strict", action="store_true",
                   help="0.9.0:任何 frontmatter error 非零退出(CI 用 · warn/hint 不算)")


def main(argv: list[str] | None = None) -> int:
    """argparse dispatcher · 走 args.func 跑对应子命令实现."""
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    # Lazy import 避免顶层循环导入 · cmd_* 在各自 module
    from .build import cmd_build, cmd_init, cmd_lint

    parser = argparse.ArgumentParser(
        prog="docs-cockpit",
        description="把项目 MD 文档汇总成单文件 HTML 看板",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    render_p = sub.add_parser("render", help="按 config 渲染 HTML 看板（原 build 命令 · 1.0 改名）")
    _add_render_options(render_p)
    render_p.set_defaults(func=cmd_build)

    # deprecated alias · 保留一个 minor 周期（1.0.x）· 1.1 移除
    build_p = sub.add_parser("build", help="[已废弃] 用 render 替代 · 行为相同")
    _add_render_options(build_p)

    def _cmd_build_deprecated(args):
        print(
            "[docs-cockpit] 警告：`build` 已废弃，请改用 `render`（行为相同）。该别名将在 1.1 移除。",
            file=sys.stderr,
        )
        return cmd_build(args)

    build_p.set_defaults(func=_cmd_build_deprecated)

    # 0.9.0:lint 子命令 · 只校验不 build · 规范见 references/schema.md
    # 0.18.0(gap #3):lint = build 校验子集 · 跑跟 build 同款 issue collection ·
    #                  只是不写 HTML / state.json · 加 --include / --exclude / --legacy-schema-only
    lint_p = sub.add_parser(
        "lint",
        help="校验 frontmatter + body 是否符合 references/schema.md 规范(不 build · CI / pre-commit 用)",
    )
    lint_p.add_argument("--config", "-c", default="docs-cockpit.yaml",
                       help="YAML 配置文件路径")
    lint_p.add_argument("--json", action="store_true",
                       help="JSON 输出 · 给 IDE / CI 消费")
    lint_p.add_argument("--strict-warn", action="store_true",
                       help="把 warning 也升级成 error(默认只 error 非零退出)")
    lint_p.add_argument(
        "--include", dest="include_categories", default=None,
        help="0.18.0 · 只跑指定类别 lint(逗号分隔)· e.g. `frontmatter-schema,subtask-missing-anchors`",
    )
    lint_p.add_argument(
        "--exclude", dest="exclude_categories", default=None,
        help="0.18.0 · 跳过指定类别 lint(逗号分隔)· e.g. `--exclude doc-lang-mix,title-has-anchor`",
    )
    lint_p.add_argument(
        "--legacy-schema-only", action="store_true",
        help="0.18.0 · 回到 0.17 之前的行为 · 只跑 validate_meta(不跑 title / anchor lint)· CI 兼容兜底",
    )
    lint_p.set_defaults(func=cmd_lint)

    init_p = sub.add_parser("init", help="生成最小可用配置模板")
    init_p.add_argument("-o", "--output", default="docs-cockpit.yaml")
    init_p.add_argument("--force", action="store_true")
    init_p.set_defaults(func=cmd_init)

    mig_p = sub.add_parser(
        "migrate",
        help="一键迁移现有项目散落 MD → docs-cockpit canonical 布局",
    )
    mig_p.add_argument("--repo", default=".", help="目标项目根 · 默认当前目录")
    mig_p.add_argument(
        "--apply", action="store_true",
        help="真执行迁移(默认 dry-run · 只 print 计划不动文件)",
    )
    mig_p.add_argument(
        "--keep-originals", action="store_true",
        help="复制而非移动原文件(保留 docs/plans/ 等原 dir)",
    )
    from . import migrate as _migrate_mod
    mig_p.set_defaults(func=_migrate_mod.cmd_migrate)

    browse_p = sub.add_parser(
        "browse",
        help="生成单 HTML markdown 浏览器(树形侧边栏 + marked.js 渲染)",
    )
    browse_p.add_argument("--repo", default=".", help="项目根 · 默认当前目录")
    browse_p.add_argument(
        "--dir", action="append",
        help="指定扫描目录(可多次)· 不指定时默认扫项目+~/.claude",
    )
    browse_p.add_argument(
        "--no-claude", action="store_true",
        help="跳过 ~/.claude/{plans,projects} 扫描",
    )
    browse_p.add_argument(
        "-o", "--output", default=None,
        help="输出 HTML 路径(默认 docs/browse.html)",
    )
    browse_p.add_argument(
        "--project", default=None,
        help="项目名(显示在 topbar · 默认从 repo 目录名推)",
    )
    from . import browse as _browse_mod
    browse_p.set_defaults(func=_browse_mod.cmd_browse)

    # 0.12 M09 · sync-status · dashboard localStorage override → MD 反向同步
    ss_p = sub.add_parser(
        "sync-status",
        help="把 dashboard 勾选的 subtask 状态写回 MD(plan §1 缺口 3 收口)",
    )
    ss_p.add_argument(
        "--import", dest="import_path", default=None,
        help="dashboard 导出的 overrides JSON 路径",
    )
    ss_p.add_argument(
        "--from-browser", dest="from_browser", default=None,
        choices=["chrome", "firefox", "edge"],
        help="直读浏览器 profile localStorage(0.14.3+ · Firefox 完整 · Chrome/Edge MVP stub)",
    )
    ss_p.add_argument(
        "--profile", default=None,
        help="显式 profile dir 名(`Default` / `Profile 1` for Chrome · `<hash>.default-release` for Firefox)· 不传走平台 default",
    )
    ss_p.add_argument(
        "--apply", action="store_true",
        help="真写回 MD(默认 dry-run · 只 print diff)· 写前每个 MD 生成 .bak",
    )
    ss_p.add_argument(
        "--config", "-c", default="docs-cockpit.yaml",
        help="项目 docs-cockpit.yaml 路径 · 默认 CWD",
    )
    from . import sync_status as _sync_mod
    ss_p.set_defaults(func=_sync_mod.cmd_sync_status)

    up_p = sub.add_parser(
        "upgrade",
        help="一条命令升级 CLI + plugin (auto-detect backend · 智能判断要不要重启)",
    )
    up_p.add_argument(
        "--dry-run", action="store_true",
        help="只 print 升级计划 · 不执行 · 不动文件",
    )
    up_p.add_argument(
        "--yes", "-y", action="store_true",
        help="非交互模式 · 跳过 'Proceed? [Y/n]' 确认",
    )
    up_p.add_argument(
        "--no-clear-cache", action="store_true",
        help="不自动清 plugin cache · 让用户手工处理(给老姿势兜底)",
    )
    up_p.add_argument(
        "--skip-changelog", action="store_true",
        help="不 fetch + 显示 CHANGELOG diff(网络差时加速)",
    )
    from . import upgrade as _upgrade_mod
    up_p.set_defaults(func=_upgrade_mod.cmd_upgrade)

    args = parser.parse_args(argv)
    return args.func(args)
