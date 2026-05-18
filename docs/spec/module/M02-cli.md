---
id: M02
type: module
title: "CLI"
status: in-progress
sprint: "0.11"
progress: 80
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

- [x] v0.10 build / lint / init / migrate / browse / portfolio / upgrade 全部上线
- [x] First-build bootstrap(plugin 检测 CLI 缺失 → uv tool / pipx / pip --user)
- [ ] @plan-eng-review 1A · `cli.py` 从 build.py 拆出 @code:docs_cockpit/build.py
- [ ] W3 · `docs-cockpit prompt <module-id> [<subtask-id>]` 子命令 @docs:docs/plans/P-v0.11-driver-seat.md
- [ ] W3 · `--copy` flag + pyperclip optional dep · 未装时输出 stdout + stderr 提示
- [ ] W3 · `--list` 列内置 prompt templates
- [ ] W1 · `docs-cockpit migrate-subtasks <file>` · dry-run / --apply
- [ ] W3 · `docs-cockpit lint --prompts` · Jinja2 语法 + template path 校验
- [ ] tests/integration/test_cli_v011.py · CliRunner 覆盖新子命令
