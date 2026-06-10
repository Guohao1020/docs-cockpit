---
id: M01
type: module
title: "Build Engine"
status: done
sprint: "0.11"
progress: 100
desc: "MD frontmatter → state.json + index.html 单文件 dashboard · v0.10 稳定 · v0.11 W1 schema 演进"
owner: harvey
prd_ref: "v0.11 driver-seat plan §6.1"
docs:
  - { title: "v0.11 driver-seat plan", path: "docs/plans/P-v0.11-driver-seat.md" }
  - { title: "v0.11 test plan", path: "docs/plans/P-v0.11-test-plan.md" }
  - { title: "Frontmatter conventions", path: "references/frontmatter_conventions.md" }
  - { title: "Design tokens", path: "references/design_tokens.md" }
depends_on: []
blocks: [M02]
---

# M01 · Build Engine

## §1 · 范围

`docs-cockpit build` 的核心 pipeline · 把项目根的 `docs-cockpit.yaml` + `docs/spec/{module,concept}/*.md` + system_docs 卷成单文件 dashboard:

```
docs-cockpit.yaml + MD files
        │
        ▼
  load_config()          ── YAML 解析 + path 变量替换 ({repo} / {home} / {env:X})
        │
        ▼
  _resolve_group_files()  ── modules:/concepts: 的 files / scan / glob 解析
        │
        ▼
  read_md() + split_frontmatter()
        │
        ▼
  _build_card()           ── frontmatter normalize + docs/subtasks 嵌入
        │
        ▼
  validate_meta()         ── Issue 对象 + severity + reference
        │
        ▼
  build_payload()         ── 输出 (payload, issues)
        │
        ▼
  render_html() + state.json
```

## §2 · 关键文件

| 文件 | 角色 |
|---|---|
| `docs_cockpit/build.py` | 主 pipeline + CLI dispatcher · ~1000 行 · v0.11 拆 schema.py + paths.py + cli.py(plan-eng-review 1A) |
| `docs_cockpit/templates/index.html.tmpl` | HTML 模板 · `__DOCS_JSON__` 占位 · v0.11 改 `<script type="application/json">` 嵌入 |
| `docs_cockpit/templates/browse.html.tmpl` | docs browser 模板 · v0.11 不动 |

## 3 · 待办

- [x] v0.10 build_payload + render_html 稳定 @code:docs_cockpit/build.py:380-466 @code:docs_cockpit/build.py:469-540
- [x] frontmatter validator + Issue.reference 体系 @code:docs_cockpit/schema.py:96-141 @docs:CLAUDE.md
- [x] docs 三步 fallback path resolver(绝对 → 相对 source → 相对 repo 根 · 修 0.7.0 双 docs/docs/ 实拍 bug)@code:docs_cockpit/paths.py @docs:CLAUDE.md
- [x] 按职责拆分 build 引擎模块边界 @code:docs_cockpit/schema.py @code:docs_cockpit/paths.py @code:docs_cockpit/cli.py @code:docs_cockpit/build.py @docs:docs/plans/P-v0.11-driver-seat.md#§6.1
- [x] 把 subtask 升为一等公民 schema · 给每条 subtask 独立 id 跟状态校验 @code:docs_cockpit/schema.py:421-475 @docs:docs/plans/P-v0.11-driver-seat.md
- [x] 让每条 subtask 锚定到代码行号 · 文件读出错也不崩 @code:docs_cockpit/paths.py:402-456 @docs:docs/plans/P-v0.11-driver-seat.md
- [x] 把 module 数据安全嵌进 HTML 模板 · 避免脚本提前结束 @code:docs_cockpit/build.py:483-498
- [x] 输出独立 sidecar JS 文件给 dashboard 按需加载 @code:docs_cockpit/build.py:512-535
- [x] 模板特殊串 `</script>` 转义 · 防 script 标签被内容截断 @code:docs_cockpit/build.py:483-490
- [x] 立 pytest 测试地基 · 给所有后续 schema 改动护栏 @code:tests/unit/test_schema.py @code:tests/integration/test_dashboard_render.py
