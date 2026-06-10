---
id: M10
type: module
title: "LLM Doc Optimizer · 原 docs-cockpit suggest (W2 · v1.0 已删)"
status: done
sprint: "0.12"
progress: 100
desc: "（v1.0 已移除 · 历史模块）docs-cockpit suggest · LLM 改写 prompt 生成器 · 检查 module MD 质量 + 提议改进 · 功能并入 build / rebuild skill 流程"
owner: harvey
prd_ref: "v0.11 driver-seat plan §5 Approach W2 · v0.11 内未做 · 留 v0.12"
docs:
  - { title: "v0.11 driver-seat plan · §5 Approach W2", path: "docs/plans/P-v0.11-driver-seat.md" }
  - { title: "关联方法论(原 author §11/§12)",        path: "references/association-method.md" }
depends_on: []
blocks: []
---

# M10 · LLM Doc Optimizer · 原 docs-cockpit suggest (W2)

> **v1.0 已移除 · 历史模块** — suggest CLI 已在 v1.0 随认知 CLI 层删除 · 「LLM 检查文档质量 + 提议改进」这层认知职能并入 build / rebuild skill 流程。本模块保留为 0.12 sprint 的历史记录（特性曾完整 ship · 故 `status: done` 不变）· 发布详情见 CHANGELOG 的 0.12.0 节。

## §1 · 范围

v0.11 plan §5 提了三条路 · W1(subtask schema)+ W3(prompt scaffolding)已在 0.11.0 ship · **W2(LLM 文档优化器)留给 v0.12**。

`docs-cockpit suggest`(v1.0 已删)曾跟 `docs-cockpit lint` 互补:
- `lint` · 死规则校验 · `status × progress` / `id` 缺失 / `docs:` path 找不到 · 输出 Issue(error / warn / hint)
- `suggest` · LLM 软建议 · 「这个 module 的 desc 太短 · subtask 拆得过细可考虑合并 · §2.1 应该补 code anchor」· 不报错 · 输出可执行 prompt

(该 CLI v1.0 已删 · 功能并入 build / rebuild skill 流程 · 历史见 CHANGELOG 0.12.0 节)

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
| ~~`docs_cockpit/suggest.py`~~ | 主模块 · 复用 prompt.py 的 SandboxedEnvironment + ChoiceLoader · 走 templates/suggest/ 目录（v1.0 已删） |
| ~~`docs_cockpit/templates/suggest/*.md.j2`~~ | 4-5 个建议 prompt template(desc 改写 / subtask 重组 / anchor 完整性 / cross-doc consistency)（v1.0 已删） |
| ~~`docs_cockpit/cli.py::cmd_suggest`~~ | argparse 入口（v1.0 已删） |
| 原 author SKILL §13(v1.0 已随 suggest 删除) | 「How to consume suggest output」一节 · 跟 §11 / §12 自检对齐 |

## §3 · 待办

- [x] 起 LLM 软建议模块的引擎骨架 · 复用 prompt 渲染层 @docs:CHANGELOG.md#0.12.0 @code:docs_cockpit/prompt.py:80-106
- [x] 内置四种建议视角的 template · 描述改写 / 子任务重组 / 锚点完整性 / 跨文档一致性 @docs:CHANGELOG.md#0.12.0
- [x] 用户命令行触发建议 · 严格模式下当 issue 卡 CI @docs:CHANGELOG.md#0.12.0
- [x] 沿用 refine 的两套执行模式 · 有 fs 工具直接改 · 浏览器只能输出 prompt @docs:CHANGELOG.md#0.12.0
- [x] 给 author skill 加章节讲清如何消费 suggest 输出 · 跟原有自检流程对齐(该章节随 v1.0 suggest 删除) @docs:CHANGELOG.md#0.12.0 <!-- 该 author 章节已随 v1.0 删除 · 历史锚指向 0.12.0 release 节 -->
- [x] 集成测试 · 选一个 module 跑 suggest · 验 prompt 含完整 module 上下文跟所有 template 都能渲染 @docs:CHANGELOG.md#0.12.0
