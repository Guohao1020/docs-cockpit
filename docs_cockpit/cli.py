"""docs-cockpit · CLI argparse dispatcher.

main() 接所有子命令并 dispatch · 子命令实现散在各 module:
  build / lint / init → build.py
  migrate → migrate.py
  browse → browse.py
  portfolio → portfolio.py
  upgrade → upgrade.py

0.11.0-alpha.1:从 build.py 拆出(plan-eng-review 1A)。
build.py 仍 re-export `main` · 老 entry-point (`docs_cockpit.build:main`)
和老 import (`from docs_cockpit.build import main`)继续 work。
"""

from __future__ import annotations

import argparse
import sys


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

    build_p = sub.add_parser("build", help="按 config 生成 HTML 看板")
    build_p.add_argument("--config", "-c", default="docs-cockpit.yaml",
                        help="YAML 配置文件路径(默认:当前目录 docs-cockpit.yaml)")
    build_p.add_argument("--debug", action="store_true",
                        help="打印解析后的路径变量与每条 entry 的绝对路径")
    build_p.add_argument("--no-version-check", action="store_true",
                        help="跳过新版本检测(也可设 DOCS_COCKPIT_NO_VERSION_CHECK=1)")
    build_p.add_argument("--strict", action="store_true",
                        help="0.9.0:任何 frontmatter error 非零退出(CI 用 · warn/hint 不算)")
    build_p.set_defaults(func=cmd_build)

    # 0.9.0:lint 子命令 · 只校验不 build · 配合 docs-cockpit-author skill 使用
    # 0.18.0(gap #3):lint = build 校验子集 · 跑跟 build 同款 issue collection ·
    #                  只是不写 HTML / state.json · 加 --include / --exclude / --legacy-schema-only
    lint_p = sub.add_parser(
        "lint",
        help="校验 frontmatter + body 是否符合 docs-cockpit-author 规范(不 build · CI / pre-commit 用)",
    )
    lint_p.add_argument("--config", "-c", default="docs-cockpit.yaml",
                       help="YAML 配置文件路径")
    lint_p.add_argument("--json", action="store_true",
                       help="JSON 输出 · 给 IDE / CI 消费")
    lint_p.add_argument("--strict-warn", action="store_true",
                       help="把 warning 也升级成 error(默认只 error 非零退出)")
    lint_p.add_argument("--prompts", action="store_true",
                       help="0.11.0-alpha.3 · 额外校验 prompt template syntax(Jinja2)+ user override 文件存在性")
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

    # 0.11.0-alpha.2 · W1:把 v0.10 字符串 subtasks 升级到 v0.11 对象 schema
    ms_p = sub.add_parser(
        "migrate-subtasks",
        help="把 MD frontmatter 里 v0.10 字符串 subtasks 升级到 v0.11 对象 schema",
    )
    ms_p.add_argument("file", help="目标 MD 文件路径")
    ms_p.add_argument(
        "--apply", action="store_true",
        help="真执行写回(默认 dry-run · 输出 diff 不动文件)· 写前生成 .bak 备份",
    )
    from .build import cmd_migrate_subtasks
    ms_p.set_defaults(func=cmd_migrate_subtasks)

    # 0.11.0-alpha.3 · W3:render prompt for a subtask (plan §6.2)
    pr_p = sub.add_parser(
        "prompt",
        help="渲染 subtask 的可执行 prompt · 给 Claude / Cursor / Codex 跑",
    )
    pr_p.add_argument(
        "module_id", nargs="?", default=None,
        help="module id(例如 M01)· 不传则配 --list",
    )
    pr_p.add_argument(
        "subtask_id", nargs="?", default=None,
        help="subtask id · 不传则列 module 下所有 subtask · 选一个看",
    )
    pr_p.add_argument(
        "--config", "-c", default="docs-cockpit.yaml",
        help="YAML 配置文件路径(默认:当前目录 docs-cockpit.yaml)",
    )
    pr_p.add_argument(
        "--template", "-t", default=None,
        help="显式指定 template 名(generic / feature / fix / refactor 或自定义)",
    )
    pr_p.add_argument(
        "--copy", action="store_true",
        help="复制到剪贴板(需要 pyperclip · 未装时输出到 stdout + stderr 提示)",
    )
    pr_p.add_argument(
        "--list", action="store_true",
        help="列内置 prompt template 名 · 不渲染",
    )
    # 0.14 M17 · bundle 路径 · 跟单 subtask 路径同 subcommand 二选一
    pr_p.add_argument(
        "--bundle", default=None,
        help="把多 subtask 聚合渲染一份 prompt(逗号分隔 id · 例 M07-f75501,M07-53a63a)",
    )
    def _cmd_prompt_dispatch(args):
        # --bundle 优先 · 否则走单 subtask
        if getattr(args, "bundle", None):
            from . import bundle as _bundle_mod
            return _bundle_mod.cmd_bundle_prompt(args)
        from .build import cmd_prompt
        return cmd_prompt(args)
    pr_p.set_defaults(func=_cmd_prompt_dispatch)

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

    # 0.10.0:portfolio · 多项目注册表 + 周快照
    from . import portfolio as _portfolio_mod
    _portfolio_mod.add_portfolio_parser(sub)

    # 0.12 M08 · apply-patch CLI · refine 流程模式 B 收口 · YAML patch → MD merge
    ap_p = sub.add_parser(
        "apply-patch",
        help="把 LLM 输出的 YAML patch 落回 module MD(dry-run 默认 + .bak 备份)",
    )
    ap_p.add_argument(
        "md_path",
        help="目标 module MD 文件路径(例如 docs/spec/module/M07-mcp-server.md)",
    )
    ap_p.add_argument(
        "patch_file", nargs="?", default=None,
        help="patch YAML 文件 · 省略则从 stdin 读",
    )
    ap_p.add_argument(
        "--apply", action="store_true",
        help="真写回 MD(默认 dry-run · 只 print diff 不动文件)· 写前生成 .bak 备份",
    )
    from . import apply_patch as _apply_patch_mod
    ap_p.set_defaults(func=_apply_patch_mod.cmd_apply_patch)

    # 0.18.0 gap #2 · apply-body-patch CLI · body checklist inline annotation 行级 edit
    abp_p = sub.add_parser(
        "apply-body-patch",
        help="0.18.0 · 把 body checklist edit patch(add/replace/remove inline @code/@docs)落回 MD",
    )
    abp_p.add_argument(
        "md_path",
        help="目标 module MD 文件路径(例如 docs/spec/module/M07-mcp-server.md)",
    )
    abp_p.add_argument(
        "patch_file", nargs="?", default=None,
        help="body patch YAML 文件 · 省略则从 stdin 读",
    )
    abp_p.add_argument(
        "--apply", action="store_true",
        help="真写回 MD(默认 dry-run · 只 print diff 不动文件)· 写前生成 .bak 备份",
    )
    def _cmd_apply_body_patch_dispatch(args):
        from . import body_patch as _bp
        return _bp.cmd_apply_body_patch(args)
    abp_p.set_defaults(func=_cmd_apply_body_patch_dispatch)

    # 0.12 M10 · suggest · LLM-augmented soft document optimization · plan §5 Approach W2
    sg_p = sub.add_parser(
        "suggest",
        help="跑 LLM suggest prompt 检查 module 文档质量(desc / subtask 拆解 / anchor 完整性 / cross-doc consistency)",
    )
    sg_p.add_argument(
        "module_id", nargs="?", default=None,
        help="目标 module id · 不传 + --all 跑全部",
    )
    sg_p.add_argument(
        "--all", dest="all_modules", action="store_true",
        help="跑所有 module · 通常配 --strict 用 in CI",
    )
    sg_p.add_argument(
        "--template", "-t", default=None,
        help="显式 template 名(desc-rewrite / subtask-recompose / anchor-completeness / cross-doc-consistency)· 不传 = 跑所有 triggered",
    )
    sg_p.add_argument(
        "--strict", action="store_true",
        help="任何 suggest triggered → exit 1 · CI 用",
    )
    sg_p.add_argument(
        "--copy", action="store_true",
        help="复制全部 prompts 到剪贴板(需要 pyperclip)",
    )
    sg_p.add_argument(
        "--list-templates", dest="list_templates", action="store_true",
        help="列内置 suggest template 名 · 不渲染",
    )
    sg_p.add_argument(
        "--config", "-c", default="docs-cockpit.yaml",
        help="项目 docs-cockpit.yaml 路径 · 默认 CWD",
    )
    from . import suggest as _suggest_mod
    sg_p.set_defaults(func=_suggest_mod.cmd_suggest)

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

    # 0.12 M07 · mcp-serve · 起 MCP stdio server · let Claude/Cursor/Codex 直连
    mcp_p = sub.add_parser(
        "mcp-serve",
        help="启 MCP stdio server · let Claude / Cursor / Codex 直连消费 cockpit prompt / state / apply-patch",
    )
    mcp_p.add_argument(
        "--config", "-c", default="docs-cockpit.yaml",
        help="项目 docs-cockpit.yaml 路径 · MCP server 启动时 load 一次 · 默认 CWD",
    )
    def _cmd_mcp_serve(args):
        # lazy import · mcp 是 optional dep · 不让 build/lint 受牵连
        from . import mcp_server as _mcp
        return _mcp.cmd_mcp_serve(args)
    mcp_p.set_defaults(func=_cmd_mcp_serve)

    # 0.17.0 · verify · LLM 二次确认 subtask anchor 准不准 · 跟 lint_subtask_anchors 联动
    vf_p = sub.add_parser(
        "verify",
        help="LLM 二次确认 subtask 的 anchor 是否真指到对的代码 / 文档(渲染 prompt · 给 Claude / Cursor / 浏览器 LLM 跑)",
    )
    vf_p.add_argument(
        "module_id", nargs="?", default=None,
        help="目标 module id(例 M03)· 跟 --all 二选一",
    )
    vf_p.add_argument(
        "--all", dest="all_modules", action="store_true",
        help="跑所有 module · prompt 体量大 · 慎用",
    )
    vf_p.add_argument(
        "--copy", action="store_true",
        help="复制 prompt 到剪贴板(需要 pyperclip)",
    )
    vf_p.add_argument(
        "--config", "-c", default="docs-cockpit.yaml",
        help="项目 docs-cockpit.yaml 路径 · 默认 CWD",
    )
    def _cmd_verify_dispatch(args):
        from . import verify as _verify_mod
        return _verify_mod.cmd_verify(args)
    vf_p.set_defaults(func=_cmd_verify_dispatch)

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
