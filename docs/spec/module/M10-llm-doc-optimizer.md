---
id: M10
type: module
title: "LLM Doc Optimizer · docs-cockpit suggest (W2)"
status: done
sprint: "0.12"
progress: 100
desc: "docs-cockpit suggest · LLM 改写 prompt 生成器 · 检查 module MD 质量 + 提议改进 · plan §5 Approach W2 落地"
owner: harvey
prd_ref: "v0.11 driver-seat plan §5 Approach W2 · v0.11 内未做 · 留 v0.12"
docs:
  - { title: "v0.11 driver-seat plan · §5 Approach W2", path: "docs/plans/P-v0.11-driver-seat.md" }
  - { title: "Author skill §11 / §12 self-check",        path: "skills/docs-cockpit-author/SKILL.md" }
depends_on: []
blocks: []
---

# M10 · LLM Doc Optimizer · docs-cockpit suggest (W2)

## §1 · 范围

v0.11 plan §5 提了三条路 · W1(subtask schema)+ W3(prompt scaffolding)已在 0.11.0 ship · **W2(LLM 文档优化器)留给 v0.12**。

`docs-cockpit suggest` 跟现有 `docs-cockpit lint` 互补:
- `lint` · 死规则校验 · `status × progress` / `id` 缺失 / `docs:` path 找不到 · 输出 Issue(error / warn / hint)
- `suggest` · LLM 软建议 · 「这个 module 的 desc 太短 · subtask 拆得过细可考虑合并 · §2.1 应该补 code anchor」· 不报错 · 输出可执行 prompt

```bash
docs-cockpit suggest M03                  # 给 M03 module 跑 LLM 检查 · 输出 prompt
docs-cockpit suggest M03 --copy           # prompt 进剪贴板
docs-cockpit suggest --all --strict       # 全部 module + 错误超 N 个 exit non-zero(CI 用)
```

跟 Refine 按钮的区别:
- **Refine** · 检查 anchor 精度(`code:` / `docs:` 是否准)· 输出 YAML patch
- **suggest** · 检查 doc 质量(desc / subtasks 拆解 / 行文)· 输出改写建议 prompt · 用户/AI 自己决定要不要执行

## §2 · 关键文件

| 文件 | 角色 |
|---|---|
| `docs_cockpit/suggest.py` | 主模块 · 复用 prompt.py 的 SandboxedEnvironment + ChoiceLoader · 走新 templates/suggest/ 目录 |
| `docs_cockpit/templates/suggest/*.md.j2` | 4-5 个建议 prompt template(desc 改写 / subtask 重组 / anchor 完整性 / cross-doc consistency) |
| `docs_cockpit/cli.py::cmd_suggest` | argparse 入口 |
| `skills/docs-cockpit-author/SKILL.md` §13 | 新增「How to consume suggest output」一节 · 跟 §11 / §12 自检对齐 |

## §3 · 待办

- [x] suggest.py scaffold · 复用 prompt.py SandboxedEnvironment + ChoiceLoader(template 寻找顺序:repo `docs/suggest/` → 内置) @code:docs_cockpit/suggest.py:42-79 @code:docs_cockpit/prompt.py:85-106 @docs:skills/docs-cockpit-author/SKILL.md#§13
- [x] 4 个内置 suggest template @code:docs_cockpit/templates/suggest/desc-rewrite.md.j2 @code:docs_cockpit/templates/suggest/subtask-recompose.md.j2 @code:docs_cockpit/templates/suggest/anchor-completeness.md.j2 @code:docs_cockpit/templates/suggest/cross-doc-consistency.md.j2 @docs:skills/docs-cockpit-author/SKILL.md#§13.2
- [x] `docs-cockpit suggest [module] [--copy] [--all] [--strict]` CLI · `--strict` 把建议视作 issue · CI 用 @code:docs_cockpit/suggest.py:202-282 @code:docs_cockpit/cli.py:165-201 @docs:skills/docs-cockpit-author/SKILL.md#§13.3
- [x] caller-aware mode(沿用 refine 的 A/B 模式)· Claude Code 直接动手 · 浏览器 LLM 输出 prompt @code:docs_cockpit/templates/suggest/anchor-completeness.md.j2 @docs:skills/docs-cockpit-author/SKILL.md#§13.1
- [x] author skill §13 「How to consume suggest output」· 5 步流程跟 §11 对齐 @code:skills/docs-cockpit-author/SKILL.md @docs:skills/docs-cockpit-author/SKILL.md#§13
- [x] 集成测试:对 M03 跑 suggest · 验输出 prompt 含 module 全 frontmatter + linked docs summary + 4 template 都能渲染 @code:tests/unit/test_suggest.py @docs:skills/docs-cockpit-author/SKILL.md#§13
