---
id: M13
type: module
title: "sync-status --from-browser · profile localStorage reader"
status: done
sprint: "0.13"
progress: 100
manualProgress: true   # 实施落在 M09-b23cac · M13 是计划早期 placeholder · scope 重复 · 走 manual done
desc: "兑现 M09 留的 stub · 直读 Chrome LevelDB / Firefox SQLite · 用户不用先 Export JSON"
owner: harvey
prd_ref: "v0.13 plan §5.3 · M09-1be62a follow-up"
docs:
  - { title: "v0.13 plan · §5.3",            path: "docs/plans/P-v0.13-polish-and-edges.md" }
  - { title: "M09 sync-status",              path: "docs/spec/module/M09-sync-status.md" }
  - { title: "sync-status workflow doc",     path: "references/sync_status_workflow.md" }
  - { title: "M09 sync_status.py · current stub", path: "docs_cockpit/sync_status.py" }
depends_on: [M09]
blocks: []
---

# M13 · sync-status --from-browser · profile localStorage reader

## §1 · 范围

M09 ship 时 `--from-browser` stub 报错 · 让用户走 Export JSON 路径。v0.13 兑现 v0.13 plan §5.3 承诺:

```bash
docs-cockpit sync-status --from-browser chrome              # macOS / Windows / Linux 自动找 default profile
docs-cockpit sync-status --from-browser chrome --apply
docs-cockpit sync-status --from-browser firefox --profile <name>
```

backend 把 localStorage[`project-kanban-state-v1`] 拉出来 · 走现有 `parse_overrides` + `merge_to_md` 流程。

## §2 · 关键文件

| 文件 | 角色 |
|---|---|
| `docs_cockpit/browser_storage.py` | **NEW** · Chrome LevelDB + Firefox SQLite parsers |
| `docs_cockpit/sync_status.py::cmd_sync_status` | 接 `--from-browser` 路径 · 调 browser_storage |
| `pyproject.toml` | `[project.optional-dependencies] browser = ["plyvel>=1.5"]` |
| `tests/unit/test_browser_storage.py` | fixture leveldb / sqlite |

## §3 · 平台 profile dir

| Browser | macOS | Windows | Linux |
|---|---|---|---|
| Chrome | `~/Library/Application Support/Google Chrome/Default/Local Storage/leveldb` | `%LOCALAPPDATA%\Google\Chrome\User Data\Default\Local Storage\leveldb` | `~/.config/google-chrome/Default/Local Storage/leveldb` |
| Edge   | `~/Library/Application Support/Microsoft Edge/Default/Local Storage/leveldb` | `%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Local Storage\leveldb` | `~/.config/microsoft-edge/Default/Local Storage/leveldb` |
| Firefox | `~/Library/Application Support/Firefox/Profiles/*.default-release/webappsstore.sqlite` | `%APPDATA%\Mozilla\Firefox\Profiles\*.default-release\webappsstore.sqlite` | `~/.mozilla/firefox/*.default-release/webappsstore.sqlite` |

## §4 · 待办

- [x] 起浏览器存储读取层骨架 · 跨平台找 profile 目录 · 给 Chrome 跟 Firefox 两套读法 @code:docs_cockpit/browser_storage.py
- [x] Chrome / Edge 读 LevelDB · 走 plyvel 可选依赖 · 按 key 前缀过滤本项目记录 @code:docs_cockpit/browser_storage.py
- [x] Firefox 读 SQLite · 走 stdlib · 不加新依赖 @code:docs_cockpit/browser_storage.py
- [x] 在打包配置加可选依赖组 · 用户按需安装浏览器读取能力 @code:pyproject.toml
- [x] sync-status 命令接通直读浏览器路径 · 替换原 stub 报错 @code:docs_cockpit/sync_status.py
- [x] 用户能显式指定 profile 名 · 不指定就用各平台默认 release profile @code:docs_cockpit/browser_storage.py
- [x] 单元测试覆盖两种 backend · fixture 构造 LevelDB 跟 SQLite @code:tests/unit/test_browser_storage.py
- [x] 同步工作流文档加直读浏览器路径章节 · 标 v0.13+ 起可用 @docs:references/sync_status_workflow.md
