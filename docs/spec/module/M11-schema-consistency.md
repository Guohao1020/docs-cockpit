---
id: M11
type: module
title: "Schema consistency cleanup"
status: not-started
sprint: "0.13"
progress: 0
desc: "code_anchors vs doc_anchors 字段命名统一 · 修 0.11.2 暴露的 :lines:lines 双拼 bug 的根 schema 不一致"
owner: harvey
prd_ref: "v0.13 plan §5.1"
docs:
  - { title: "v0.13 plan · §5.1",          path: "docs/plans/P-v0.13-polish-and-edges.md" }
  - { title: "Author skill §3.1.2/3.1.3",  path: "skills/docs-cockpit-author/SKILL.md" }
  - { title: "Path resolver",              path: "docs_cockpit/paths.py" }
depends_on: []
blocks: []
---

# M11 · Schema consistency cleanup

## §1 · 范围

修 v0.11/v0.12 dogfood 暴露的根 schema 不一致:

| Field                        | 当前语义              | 推荐(0.13+)              |
|------------------------------|-----------------------|---------------------------|
| `code_anchors[].path`        | raw 串(含 :lines)    | 不动(stability contract)|
| `code_anchors[].path_only`   | —                     | **NEW** · clean path · 跟 `doc_anchors[].path` 对齐 |
| `code_anchors[].lines`       | "42-89" / "42" / null | 不动                      |
| `doc_anchors[].raw`          | raw 串(含 anchor)   | 不动                      |
| `doc_anchors[].path`         | clean path            | 不动                      |
| `doc_anchors[].raw_with_anchor` | —                  | **NEW** · alias of `raw` · 命名对称 future-proof |

不删字段 · 只加。Stability contract §10.2 守住。Template 渲染端推荐用新 clean 字段 · 4 个 subtask template + refine.md.j2 都对齐。

## §2 · 关键文件

| 文件 | 角色 |
|---|---|
| `docs_cockpit/paths.py::_resolve_code_anchor` | 加 `path_only` 字段 |
| `docs_cockpit/paths.py::_resolve_subtask_doc_anchor` | 加 `raw_with_anchor` alias |
| `docs_cockpit/templates/prompts/*.md.j2` | 4 主 template 渲染端用新 clean 字段 |
| `skills/docs-cockpit-author/SKILL.md` §3.1.2/§3.1.3 | doc 说明新字段 + dual-name 关系 |
| `tests/unit/test_paths.py` | 加新字段 fixture + 校验 |

## 3 · 待办

- [ ] `_resolve_code_anchor` 输出加 `path_only` 字段(`raw.split(':', 1)[0]`)
- [ ] `_resolve_subtask_doc_anchor` 输出加 `raw_with_anchor` alias(`= raw`)
- [ ] generic/feature/fix/refactor 4 个 template 渲染端走新 clean 字段
- [ ] author skill §3.1.2 加「code anchor 字段表」+ §3.1.3 加「doc anchor 字段表」
- [ ] tests/unit/test_paths.py 覆盖新字段 + 现有字段不变
- [ ] M10 suggest 4 template 也走 clean 字段
- [ ] CHANGELOG 加 schema-additions section · 标 stability contract reaffirm
