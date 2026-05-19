---
id: M09
type: module
title: "Sync Status CLI"
status: not-started
sprint: "0.12"
progress: 0
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

## 4 · 待办

- [ ] sync_status.py scaffold · `parse_overrides(json)` / `merge_to_md(overrides, md_path)` / `compute_conflicts()`
- [ ] dashboard 加「Export status overrides」按钮 · 下载 JSON
- [ ] `docs-cockpit sync-status --import <json> [--apply]` CLI · dry-run-first
- [ ] `--from-browser <chrome|firefox|edge>` · 直读浏览器 profile dir 的 localStorage(Chrome `Local Storage/leveldb` · Firefox `webappsstore.sqlite`)
- [ ] 优先级规则 4 个 case 全 cover + 集成测试
- [ ] `references/sync_status_workflow.md` · 跨机器 daily / weekly 工作流推荐
- [ ] `.bak` 备份 + 跟 apply-patch 复用 `safe_write_md()` 工具函数
