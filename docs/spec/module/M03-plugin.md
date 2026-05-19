---
id: M03
type: module
title: "Claude Code Plugin"
status: done
sprint: "0.11"
progress: 100
desc: "Claude Code plugin · 4 skills + 8 commands · marketplace 分发 · bootstrap CLI"
owner: harvey
prd_ref: "v0.11 driver-seat plan §11 Step 3"
docs:
  - { title: "CLAUDE.md · plugin section", path: "CLAUDE.md" }
  - { title: "v0.11 driver-seat plan", path: "docs/plans/P-v0.11-driver-seat.md" }
depends_on: [M02, M04]
blocks: []
manualProgress: true   # 0.11 sprint 工作全 done · v0.12 候选项不计入分母
---

# M03 · Claude Code Plugin

## §1 · 范围

`.claude-plugin/` + `skills/` + `commands/` · Claude Code marketplace 可装。这是 docs-cockpit 第二个 ship target(同 repo 与 PyPI CLI 并行)。

```
.claude-plugin/
  ├── plugin.json        ── 版本 / 元数据
  └── marketplace.json   ── 用户 /plugin install 入口

skills/
  ├── docs-cockpit/                  ── 主 skill · 触发条件 / bootstrap CLI
  ├── docs-cockpit-author/           ── §2 frontmatter schema 的 SSOT
  ├── docs-cockpit-standup/          ── 读 state.json · 单项目 narrative
  └── docs-cockpit-portfolio/        ── 跨项目 weekly + diff

commands/
  ├── build.md / lint.md / status.md
  ├── migrate.md / browse.md / update.md
  └── weekly.md
```

## §2 · 关键文件

| 文件 | 角色 |
|---|---|
| `.claude-plugin/plugin.json` | 版本 + skill / command 注册 · 4 文件 release 同步 bump |
| `.claude-plugin/marketplace.json` | 用户安装入口 · 同上 |
| `skills/docs-cockpit/SKILL.md` | 主 skill · bootstrap CLI 检测 + 触发条件 |
| `commands/*.md` | 8 个 slash command 入口 |

## 3 · 待办

- [x] v0.10 · 4 skills 全部在线 @code:skills/docs-cockpit/SKILL.md @code:skills/docs-cockpit-author/SKILL.md @code:skills/docs-cockpit-standup/SKILL.md @code:skills/docs-cockpit-portfolio/SKILL.md @docs:CLAUDE.md:88-100 @docs:skills/docs-cockpit/SKILL.md:15-35
- [x] v0.10 · 8 commands 全部在线 @code:commands/build.md @code:commands/lint.md @code:commands/status.md @code:commands/migrate.md @code:commands/browse.md @code:commands/update.md @code:commands/weekly.md @docs:CLAUDE.md:158
- [x] First-build bootstrap(uv tool / pipx / pip --user 优先级) @code:skills/docs-cockpit/SKILL.md:149-179 @docs:CLAUDE.md:109-114
- [x] docs-cockpit upgrade 原子升级(plugin cache 失效 + 重启提示) @code:docs_cockpit/upgrade.py:211-350 @code:docs_cockpit/upgrade.py:193-209 @code:docs_cockpit/upgrade.py:120-133 @docs:skills/docs-cockpit/SKILL.md:124-147 @docs:CLAUDE.md:148
- [x] v0.11 skill section · prompt scaffolding 触发条件 + CLI 用法 @code:skills/docs-cockpit/SKILL.md:37-122 @docs:docs/plans/P-v0.11-driver-seat.md#§6.2 @docs:docs/plans/P-v0.11-driver-seat.md:566-577 @docs:docs/plans/P-v0.11-driver-seat.md:367
- [x] v0.11 plugin.json + marketplace.json + __init__.py + CHANGELOG 4 文件 version bump @code:.claude-plugin/plugin.json @code:.claude-plugin/marketplace.json @code:docs_cockpit/__init__.py:7 @code:CHANGELOG.md @docs:CLAUDE.md:42-54 @docs:docs/plans/P-v0.11-driver-seat.md:579-584
- [ ] v0.12 候选 · MCP server · 让 Claude 直连消费 cockpit prompt(替代 copy-paste · **moved to M07-mcp-server.md** · sprint 0.12) @docs:docs/spec/module/M07-mcp-server.md @docs:docs/plans/P-v0.11-driver-seat.md:586-590 @docs:docs/plans/P-v0.11-driver-seat.md:40
