---
id: M08
type: module
title: "Apply Patch CLI"
status: not-started
sprint: "0.12"
progress: 0
desc: "docs-cockpit apply-patch · 把 LLM 输出的 frontmatter YAML patch 自动落回 MD · refine 流程模式 B 收口"
owner: harvey
prd_ref: "v0.11 driver-seat plan §11 v0.12 候选 · refine.md.j2 模式 B 后端"
docs:
  - { title: "v0.11 driver-seat plan · v0.12 候选",      path: "docs/plans/P-v0.11-driver-seat.md" }
  - { title: "AI-augmented precision sub-plan",         path: "docs/plans/P-v0.11-ai-augmented-precision-alpha7-2026-05-18.md" }
  - { title: "refine prompt template",                  path: "docs_cockpit/templates/prompts/refine.md.j2" }
depends_on: []
blocks: [M07]
---

# M08 · Apply Patch CLI

## §1 · 范围

v0.11 alpha.7 的 Refine with AI prompt 输出 YAML patch · 模式 A(Claude Code · 有 Edit 工具)直接落地 · 模式 B(浏览器 LLM)输出 patch 让用户复制。模式 B 的最后一步「用户复制 → 自己改 MD」是手工活 · v0.12 收口为一条 CLI:

```bash
docs-cockpit apply-patch < patch.yaml                  # dry-run · 打印 diff
docs-cockpit apply-patch --apply < patch.yaml          # 真写回 + .bak 备份
docs-cockpit apply-patch --apply patch.yaml            # 从文件读也行
```

被 M07 MCP server 的 `cockpit_apply_patch` tool 复用 · 模式 1 也走这条 backend。

## §2 · 关键文件

| 文件 | 角色 |
|---|---|
| `docs_cockpit/apply_patch.py` | 主模块 · `parse_patch` / `apply_to_md` / `compute_diff` 三个核心函数 |
| `docs_cockpit/cli.py::cmd_apply_patch` | argparse 入口 · 支持 stdin / 文件输入 · dry-run-first |
| `tests/unit/test_apply_patch.py` | patch 格式 / 冲突检测 / .bak 备份 单测 |
| `tests/integration/test_apply_patch_e2e.py` | 端到端:`refine.md.j2` 输出 patch → apply → 跑 build 验证 anchor 落地 |

## §3 · patch 格式

跟 `refine.md.j2` 输出格式对齐(只动 frontmatter / 不动 body):

```yaml
# patch for M03
subtasks:
  - id: M03-e6adea            # 必须用 id 定位 · 不靠 index
    code: ["new/path.py:42-89"]
    docs: ["docs/plans/p.md#§6.2"]
  - id: M03-f26708
    status: done
```

跟「整个 module 覆盖」不同 · patch 只列要改的 subtask · 不列的保留原状。

## 4 · 待办

- [ ] patch 格式 spec(subtask id-based · frontmatter-only · 不动 body checklist) @code:docs_cockpit/apply_patch.py @code:docs_cockpit/templates/prompts/refine.md.j2 @docs:docs/spec/module/M08-apply-patch.md#§3 @docs:docs/plans/P-v0.11-ai-augmented-precision-alpha7-2026-05-18.md:133-148
- [ ] `parse_patch(text) -> dict` · 走 PyYAML safe_load · 校验 schema(必须有 id / 字段在白名单 status/code/docs/desc) @code:docs_cockpit/apply_patch.py @code:docs_cockpit/schema.py:421-475 @docs:docs/plans/P-v0.11-ai-augmented-precision-alpha7-2026-05-18.md:133-148
- [ ] `apply_to_md(patch, md_path) -> (diff, conflicts)` · 读 frontmatter · 按 subtask.id 找 · merge · 写回 @code:docs_cockpit/apply_patch.py @code:docs_cockpit/build.py:712-779 @docs:docs/plans/P-v0.11-ai-augmented-precision-alpha7-2026-05-18.md:133-148
- [ ] 冲突检测:patch 想改 M03-e6adea 但用户手改过 · 走「user wins · skip with warning」语义 · 或 `--force` 覆盖 @code:docs_cockpit/apply_patch.py
  <!-- TODO docs anchor: 冲突检测语义 (user-wins / --force) sub-plan / 主 plan 都没专门讲 · 实施时在 §3.3 或 M08 §4 落地后回填 -->
- [ ] `.bak` 备份 · 与 migrate-subtasks 一致 @code:docs_cockpit/apply_patch.py @code:docs_cockpit/build.py:712-779
  <!-- TODO docs anchor: .bak 写法是 migrate-subtasks 隐式约定 · 没专门 doc section · 实施时把约定写进 author skill 后回填 -->
- [ ] dry-run / --apply · diff 输出走 unified diff 格式 · 跟 git diff 一致 @code:docs_cockpit/apply_patch.py @code:docs_cockpit/cli.py
  <!-- TODO docs anchor: dry-run-first 约定散落在 migrate / migrate-subtasks 实现里 · 没专门 doc · 实施时补回填 -->
- [ ] 集成测试:跑完 refine prompt 把 YAML 喂进 apply-patch · 验 anchor 落到 state.json @code:tests/integration/test_apply_patch_e2e.py @code:docs_cockpit/templates/prompts/refine.md.j2 @docs:docs/plans/P-v0.11-ai-augmented-precision-alpha7-2026-05-18.md:156-161 @docs:docs/plans/P-v0.11-ai-augmented-precision-alpha7-2026-05-18.md:133-148
