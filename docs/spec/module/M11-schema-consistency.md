---
id: M11
type: module
title: "Schema consistency cleanup"
status: done
sprint: "0.13"
progress: 100
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

- [x] `_resolve_code_anchor` 输出加 `path_only` 字段 @code:docs_cockpit/paths.py:422-456
- [x] `_resolve_subtask_doc_anchor` 输出加 `raw_with_anchor` alias @code:docs_cockpit/paths.py:296-360
- [x] generic/feature/fix/refactor 4 template 渲染端走 `path_only` @code:docs_cockpit/templates/prompts/generic.md.j2 @code:docs_cockpit/templates/prompts/feature.md.j2 @code:docs_cockpit/templates/prompts/fix.md.j2 @code:docs_cockpit/templates/prompts/refactor.md.j2
- [x] author skill 加 code 跟 doc anchor 字段表 · 让用户跟 AI 都明白新老字段关系 @code:skills/docs-cockpit-author/SKILL.md
- [x] 单元测试覆盖新字段加跟老字段不变 · 守住稳定契约 @code:tests/unit/test_paths.py
- [x] M10 suggest 4 template 也走 clean 字段(bundle-recommendation 用 path_only · 其它 3 template 不渲染 ca/da 字段) @code:docs_cockpit/templates/suggest/bundle-recommendation.md.j2
- [x] CHANGELOG 加 schema-additions section(走 v0.14.3 patch · stability contract reaffirm)
