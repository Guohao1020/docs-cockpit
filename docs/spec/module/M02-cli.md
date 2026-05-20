---
id: M02
type: module
title: "CLI"
status: done
sprint: "0.11"
progress: 100
desc: "argparse dispatcher + 7 subcommands · v0.11 加 prompt / migrate-subtasks / lint --prompts"
owner: harvey
prd_ref: "v0.11 driver-seat plan §6.2 + §11 Step 2-3"
docs:
  - { title: "v0.11 driver-seat plan", path: "docs/plans/P-v0.11-driver-seat.md" }
  - { title: "Config reference", path: "references/config_reference.md" }
depends_on: [M01]
blocks: []
---

# M02 · CLI

## §1 · 范围

`docs-cockpit` 命令行接口 · argparse 分发 · 用户主要入口。

```
docs-cockpit <subcommand> [args]
        │
        ├── build       → build.py::cmd_build      · MD → HTML
        ├── lint        → build.py::cmd_lint       · frontmatter 校验
        ├── init        → build.py::cmd_init       · 脚手架 docs-cockpit.yaml
        ├── migrate     → migrate.py::cmd_migrate  · 把现有项目 docs 迁到 docs-cockpit 规范
        ├── browse      → browse.py::cmd_browse    · 生成 docs/browse.html
        ├── portfolio   → portfolio.py             · 多项目 registry + weekly diff
        └── upgrade     → upgrade.py               · CLI + plugin 原子升级
```

## §2 · 关键文件

| 文件 | 角色 |
|---|---|
| `docs_cockpit/build.py::main()` | argparse 顶层 dispatcher · v0.11 拆到 cli.py |
| `docs_cockpit/migrate.py` | migrate 子命令 · 跨项目导入 |
| `docs_cockpit/browse.py` | browse 子命令 · 单文件 tree-sidebar 文档浏览器 |
| `docs_cockpit/portfolio.py` | portfolio 子命令 · projects.yaml + snapshots |
| `docs_cockpit/upgrade.py` | upgrade 子命令 · CLI + plugin marketplace cache 原子化 |
| `docs_cockpit/__main__.py` | `python -m docs_cockpit` 入口 |

## 3 · 待办

- [x] v0.10 build / lint / init / migrate / browse / portfolio / upgrade 全部上线 @code:docs_cockpit/cli.py @code:docs_cockpit/build.py @code:docs_cockpit/migrate.py @code:docs_cockpit/browse.py @code:docs_cockpit/portfolio.py @code:docs_cockpit/upgrade.py
- [x] First-build bootstrap · plugin 检测 CLI 缺失自动走 uv tool / pipx / pip --user 三档兜底装 @code:skills/docs-cockpit/SKILL.md @docs:skills/docs-cockpit/SKILL.md
- [x] 把 CLI 入口从 build 引擎拆出 · 独立 dispatcher @code:docs_cockpit/cli.py @code:docs_cockpit/build.py
- [x] 让用户从命令行直接拿到任意 subtask 的可执行 prompt @code:docs_cockpit/cli.py:88-112 @docs:docs/plans/P-v0.11-driver-seat.md
- [x] prompt 复制到剪贴板免去用户手动选中 · 没装剪贴板库时给清晰兜底提示 @code:docs_cockpit/cli.py:103-106 @code:docs_cockpit/build.py:780-874
- [x] 列出内置 prompt template 名让用户挑 @code:docs_cockpit/cli.py:107-110
- [x] 把老 string 子任务一键升级到新 object schema · dry-run 先看 diff 再 apply @code:docs_cockpit/build.py:712-779
- [x] lint 加入 prompt template 校验 · 让 CI 能挡住 Jinja2 语法错 @code:docs_cockpit/build.py:587-694
- [x] CLI 子命令端到端集成测试 · CliRunner 跑通整条 pipeline @code:tests/integration/test_cli_v011.py
