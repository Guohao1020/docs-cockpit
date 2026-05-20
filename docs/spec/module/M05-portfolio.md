---
id: M05
type: module
title: "Portfolio · Multi-project Registry"
status: done
sprint: "0.10"
progress: 100
desc: "用户级跨项目 registry · ~/.docs-cockpit/projects.yaml + snapshots/<name>/<date>.json · 支持 weekly diff"
owner: harvey
prd_ref: "docs-cockpit-portfolio SKILL"
docs:
  - { title: "Portfolio SKILL", path: "skills/docs-cockpit-portfolio/SKILL.md" }
  - { title: "Config reference", path: "references/config_reference.md" }
depends_on: [M01]
blocks: []
---

# M05 · Portfolio · Multi-project Registry

## §1 · 范围

跨项目层 · 用户级 `~/.docs-cockpit/projects.yaml` registry + `snapshots/<project-name>/<YYYY-MM-DD>.json` 跨周快照 · 支撑 weekly diff narrative。

```
~/.docs-cockpit/
  ├── projects.yaml                    ── CLI 管 · add/list/remove/tag
  └── snapshots/
      └── <project-name>/
          └── <YYYY-MM-DD>.json        ── state.json 每周快照 · 周对比
```

## §2 · 关键文件

| 文件 | 角色 |
|---|---|
| `docs_cockpit/portfolio.py` | CLI subcommands · add/list/remove/tag/snapshot + weekly reporter |
| `skills/docs-cockpit-portfolio/SKILL.md` | 跨项目 weekly narrative skill · 读 projects.yaml + snapshots |
| `commands/weekly.md` | `/docs-cockpit:weekly` slash command |

## 3 · 待办

- [x] portfolio add/list/remove/tag CLI 全部上线 @code:docs_cockpit/portfolio.py @code:docs_cockpit/cli.py
- [x] 跨平台规整用户级注册表里的路径 · Windows 跟 POSIX 都能读写 @code:docs_cockpit/portfolio.py
- [x] snapshot CLI + weekly diff · 用户每周 export 项目状态留快照 · 下次跑 diff 看 WoW 变化 @code:docs_cockpit/portfolio.py
- [x] docs-cockpit-portfolio skill 输出多项目周报 · 跨项目叙事 + WoW 对比 @code:skills/docs-cockpit-portfolio/SKILL.md @docs:skills/docs-cockpit-portfolio/SKILL.md
