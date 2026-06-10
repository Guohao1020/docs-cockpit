---
id: M09
type: module
title: "Sync Status CLI"
status: done
sprint: "0.12"
progress: 100
manualProgress: true   # M09-1be62a (`--from-browser`) 是 v0.13 候选 · 不计入 0.12 sprint 分母
desc: "docs-cockpit sync-status · localStorage 用户勾选状态合并回 MD frontmatter · 闭环 v0.11 plan §1 缺口 3"
owner: harvey
prd_ref: "v0.11 driver-seat plan §1 缺口 3(状态控制不闭环)· §11 v0.12 候选"
docs:
  - { title: "v0.11 driver-seat plan · §1 缺口 3", path: "docs/plans/P-v0.11-driver-seat.md" }
depends_on: []
blocks: []
---

# M09 · Sync Status CLI

## §1 · 范围

v0.11 plan §1 列的 5 个缺口里第 3 个:**任务清单状态控制不闭环**。localStorage 已经能勾选 subtask 完成 · 但 override 留在浏览器 · 长期跟 source-of-truth(MD frontmatter)漂移。

`docs-cockpit sync-status` 收口:

```bash
# 路径 1 · 浏览器 export
# 用户在 dashboard 点新按钮「Export status overrides」· 下载 JSON
docs-cockpit sync-status --import overrides.json --apply

# 路径 2 · localStorage 文件直读(Chrome / Firefox profile dir)
docs-cockpit sync-status --from-browser chrome --apply
```

输出 · 把所有 `M03-e6adea: done` 这类 override 写回对应 module MD 的 frontmatter / body checklist · 让 MD 重新成为单一真相源。

## §2 · 关键文件

| 文件 | 角色 |
|---|---|
| `docs_cockpit/sync_status.py` | 主模块 · localStorage 解析 + override 合并 + MD 写回 |
| `docs_cockpit/cli.py::cmd_sync_status` | argparse 入口 |
| `templates/index.html.tmpl` (drawer) | 加「Export status overrides」按钮 · 下载 JSON |
| `references/sync_status_workflow.md` | 跨机器场景 · 优先级规则 · 推荐 daily / weekly 频率 |

## §3 · 优先级规则(必须定清楚 · 否则两台机器互相覆盖)

| 情况 | 谁赢 |
|---|---|
| localStorage `M03-x = done` + MD `status: not-started` | localStorage(用户主动勾过 · 是最新意图) |
| localStorage `M03-x = not-started` + MD `status: done` | MD(用户手动改过 MD 比浏览器 false 更权威) |
| localStorage 没记录 + MD 有 | MD |
| localStorage `M03-x = done` + MD `M03-x` 不存在 | warn + skip(可能是 subtask 被删了) |

`manualProgress: true` 锁住的 module 不被 override 撼动 progress 字段(只动 subtask.status)。

## §4 · 待办

- [x] 立同步层骨架 · 三个核心函数解析 / 合并 / 冲突检测 @code:docs_cockpit/sync_status.py:60-110 @code:docs_cockpit/sync_status.py:113-167 @code:docs_cockpit/sync_status.py:170-204 @docs:docs/spec/module/M09-sync-status.md#§2
- [x] 让用户从 dashboard 一键下载本地勾选状态 · 给同步流程供给输入 @code:docs_cockpit/templates/index.html.tmpl:1697-1706 @code:docs_cockpit/templates/index.html.tmpl:3803-3829 @docs:references/sync_status_workflow.md
- [x] 命令行接受导出 JSON · 默认 dry-run 看 diff 再 apply @code:docs_cockpit/cli.py:181-205 @docs:references/sync_status_workflow.md
- [x] 直读浏览器 profile 读出本地勾选 · 用户跳过导出步骤直接同步 @code:docs_cockpit/browser_storage.py @code:tests/unit/test_browser_storage.py @docs:references/sync_status_workflow.md
- [x] 四种优先级冲突场景全部覆盖 · 集成测试守护 @code:tests/unit/test_sync_status.py:1-220 @docs:docs/spec/module/M09-sync-status.md#§3
- [x] 写跨机器日 / 周同步流程推荐文档 · 给用户标准操作 @code:references/sync_status_workflow.md
- [x] 写回 MD 时生成 bak 备份 · 跟 patch 工具共用安全写工具函数 @code:docs_cockpit/sync_status.py:243-268 @docs:CHANGELOG.md#0.12.0
