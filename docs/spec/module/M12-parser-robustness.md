---
id: M12
type: module
title: "Parser robustness · subtask section heading"
status: done
sprint: "0.13"
progress: 100
desc: "subtask section heading regex 放宽 · 接受 § 前缀 / 三级 heading / tab 空格 · 修 M08/M09/M10 dogfood 实拍 bug"
owner: harvey
prd_ref: "v0.13 plan §5.2"
docs:
  - { title: "v0.13 plan · §5.2",     path: "docs/plans/P-v0.13-polish-and-edges.md" }
  - { title: "schema._SUBTASK_SECTION_RE", path: "docs_cockpit/schema.py" }
  - { title: "Author skill §3.1",     path: "skills/docs-cockpit-author/SKILL.md" }
depends_on: []
blocks: []
---

# M12 · Parser robustness · subtask section heading

## §1 · 范围

`_SUBTASK_SECTION_RE` 当前只识别窄子集 · v0.12 dogfood 实拍 M08/M09/M10 用 `## §4 · 待办` 风格 heading · parser 不识别 · 0 subtask 解析。当时 work around 是手工去 § 前缀。v0.13 让 parser 宽容。

放宽规则:

| 当前接受 | 新增接受 |
|---|---|
| `## 待办` | ✅ 不变 |
| `## 3 · 待办` | ✅ 不变 |
| `## TODO` | ✅ 不变 |
| ❌ `## §4 · 待办` | ✅ 接受(§ 前缀) |
| ❌ `### 待办` | ✅ 接受(三级 heading) |
| ❌ `##\t待办` | ✅ 接受(tab 空格) |
| ❌ `## §3.2 · 待办` | ✅ 接受(§ + 多级编号) |

同样的放宽 also for `_DOCS_SECTION_RE`(对称 · `## §N · 关联文档` 也常见)。

## §2 · 关键文件

| 文件 | 角色 |
|---|---|
| `docs_cockpit/schema.py::_SUBTASK_SECTION_RE` | regex 放宽 |
| `docs_cockpit/schema.py::_DOCS_SECTION_RE`    | 对称放宽 |
| `tests/unit/test_schema.py` | 12+ heading fixture 全覆盖 |
| `docs/spec/module/M08-apply-patch.md` `M09-sync-status.md` | 把 `## 4 · 待办` 改回 `## §4 · 待办`(验证 parser 接受) |

## 3 · 待办

- [x] 放宽子任务段落的 heading regex · 接受 § 前缀 / 三级 heading / tab 空格 @code:docs_cockpit/schema.py:152-160
- [x] 关联文档段落的 heading regex 同步放宽 · 命名对称 @code:docs_cockpit/schema.py:161-168
- [x] 单元测试覆盖 22+ heading fixture · positive 跟 negative 都验 @code:tests/unit/test_schema.py
- [x] dogfood 验证 · 三个老 module 改回带 § 的 heading · parser 仍能完整解析所有子任务 @code:docs/spec/module/M08-apply-patch.md @code:docs/spec/module/M09-sync-status.md @code:docs/spec/module/M10-llm-doc-optimizer.md
- [x] author skill 加「接受的 heading 形式」表 · 让用户知道哪些写法 parser 认 @code:skills/docs-cockpit-author/SKILL.md
