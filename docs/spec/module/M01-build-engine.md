---
id: M01
type: module
title: "Build Engine"
status: in-progress
sprint: "0.11"
progress: 90
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

- [x] v0.10 build_payload + render_html 稳定
- [x] frontmatter validator + Issue.reference 体系
- [x] docs 三步 fallback path resolver
- [x] @plan-eng-review 1A · 拆 `schema.py` + `paths.py` + `cli.py` @code:docs_cockpit/build.py
- [x] W1 · `normalize_subtasks` + `validate_subtask_schema` @docs:docs/plans/P-v0.11-driver-seat.md
- [x] W1 · `resolve_code_anchor` + defensive IO + `@lru_cache` @docs:docs/plans/P-v0.11-driver-seat.md
- [x] HTML template `<script type="application/json">` 嵌入策略 · `__DOCS_JSON__` collision 消除
- [ ] sidecar 输出 · `docs/prompts.js` + `docs/code_previews.js`
- [x] `</script>` escape 防 script tag 提前关闭
- [x] pytest 测试基础 · `tests/unit/` + `tests/integration/`
