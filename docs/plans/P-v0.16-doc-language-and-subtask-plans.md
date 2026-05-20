---
id: P-v0.16
type: plan
title: "v0.16 · 项目级 doc_language + 每 subtask 独立 plan MD + skill-first 治理"
status: planned
sprint: "0.16"
progress: 0
desc: "用户 dogfood Sourcery 暴露 3 个根问题:subtask title 中英混用 · title 里塞 §N.M / 文件名等 anchor 信息 · 没有 per-subtask 独立 plan。v0.16 用 skill+yaml 治理(不堆 python)"
prd_ref: "用户 2026-05-20 反馈 + 截图"
docs:
  - { title: "Author skill (待加 §16)",  path: "skills/docs-cockpit-author/SKILL.md" }
  - { title: "v0.15 §15 编排 workflow",  path: "skills/docs-cockpit-author/SKILL.md" }
depends_on: []
---

# v0.16 · doc_language + per-subtask plan + skill-first 治理

Generated: 2026-05-20 · Status: PLANNED · Mode: dogfood-driven

## §0 · 角色定位

docs-cockpit 自我定位的根重述(用户原话):**「我们项目本质上是 skill · python 代码只是辅助 · 不能依赖 python 代码解决任务问题 · 应该尽可能用 skill 解决问题」**。

这是项目的 north star。v0.11-v0.15 偏重 python(build / apply-patch / sync-status / bundle / aliases)· v0.16 校正方向:**skill 主导规则 · python 只做检测**。

## §1 · Problem Statement

用户在 Sourcery 项目截图反馈 3 个 subtask 治理根问题:

**P1 · subtask title 中英混合**

例:`M1.1 · ResourcePool[T] 通用借/还 + COOLDOWN(5 失败 → 300s 冷却 / 25min 超时)+ EWMA 评分`

混用读起来认知负担大 · 翻译团队不友好 · 国际化破。

**P2 · title 里塞 anchor 信息**

例:`M1.2 Lane F · DATA_SCHEMA.md §3.1 / §3.2 行同步 + §4.6 / §4.7 / §4.8 三张 vendor 池新表预留 + §4.1 Fingerprint 表撤销`

这是 anchor 信息(文件名 + 行号 + heading)· 应该走 `code:` / `docs:` 字段 · 不是 title。title 该说**用户得到什么** · 不是「改哪个文件哪行」。

**P3 · 没有 per-subtask 独立 plan MD**

当前 subtask 只是 body checklist 一行 · 或 frontmatter object。复杂 subtask 完全没空间展开 · 用户硬塞进 title 就出 P2 的问题。需要让每条 subtask 有独立 plan 文件 · title 只是 1 行概述。

## §2 · What Makes This Cool

driver-seat 从「subtask 是一行字」→「subtask 是 1 页 plan」· 让 AI 有空间真正展开需求逻辑。dashboard 点 subtask → 右栏渲染那条 plan(不是 module 的 plan)· 信息粒度 1:1 对应。

配合项目级 `doc_language` 锁单语 · 文档质量自动提升 · 国际化友好。

## §3 · Constraints

- **不破老 project** · 老 yaml 无 `doc_language` 字段 / 老 module 无 `docs/plans/M×/S×-*.md` 文件 · 仍 work · 仅 lint warn
- **不堆 python** · 检测放 schema.py(lint)· 创建放 author skill(AI 写)· 不写 auto-fixer
- **dashboard 渲染不变 schema** · subtask plan 通过 `subtask.doc_anchors[]` 自动 wire · 不加新 payload bucket
- **per-module dir 决策** · `docs/plans/M××/S××-<slug>.md`(用户 D2 选)· 路径明确

## §4 · Approaches Considered

### A · 纯 schema 改 · python 强 validator(reject)
全靠 Python · validate_meta 加严 · title 含 § / 文件名直接 reject。
- ❌ Python 不通用 · 不同项目惯例不同 · 强 reject 反 fragile
- ❌ 跟「skill 主导」north star 冲突

### B · 纯 skill 改 · 不动 python(reject)
只改 author skill §3.1 + §11 · AI 学规则 · python 完全不管。
- ❌ 老 doc 没 lint 兜底 · 已经混乱的 doc 没法批量识别
- ❌ 自助 detection 缺失 · 用户跑 build 看不到 doc-lang 问题

### C · skill 主导 · python lint 兜底 ✅ CHOSEN
skill 教 AI 怎么写 · python validate_meta 加 doc_language consistency + title style 2 个新 issue type · severity=warn。AI 自然走对 · 老 doc 有 hint 慢慢迁。
- ✅ skill 主体担纲(satisfies north star)
- ✅ Python 只做 lint detect · 不做 auto-fix
- ✅ 老 project 兼容(warn 不 block)
- ✅ dogfood + 下游可渐进迁移

## §5 · Recommended Approach (C 详细设计)

### §5.1 · yaml schema · project.doc_language

```yaml
project:
  name: docs-cockpit
  doc_language: "zh-CN"   # NEW · zh-CN | en · 不填默认 auto-detect
```

`build.py::_expand_project_str` 把 `{doc_language}` 也支持 placeholder。

不填时 · `schema.py::detect_doc_language(modules)` 启发式判断 · 拿 module title 的 CJK 字符占比 > 30% → zh-CN · else en · 把检测结果 stash 到 `payload.project.doc_language` · 给 lint 用。

### §5.2 · schema.py · 2 个新 Issue type

- **`doc-lang-mix`** severity=warn · subtask title CJK + ASCII 单词混用(启发式 · 排除技术 token 白名单 like `MCP` / `API` / 文件后缀 / 函数标识符)
- **`title-has-anchor`** severity=warn · title 含 `§N` / `path/file.md` / `function()` / `Class.method` 等 · 应该走 anchor 字段不是 title

报告时引用 author skill §16(本 sprint 新加)。

### §5.3 · 新约定 · per-subtask plan MD

**文件位置**(用户 D2 决策):

```
docs/plans/
  M01/
    S01-resource-pool-borrow-and-return.md       ← subtask plan
    S02-account-proxy-pydantic-and-fernet.md
    S03-account-proxy-binding-via-borrow-filter.md
    ...
  M02/
    S01-...md
```

**命名规则**:
- module dir · `M<NN>/`(零 pad 2 位 · 跟 module file 同名)
- subtask file · `S<NN>-<slug>.md`
- `<NN>` · 该 module 下 subtask 序号 1-indexed
- `<slug>` · kebab-case · 5-8 词 · 概括 subtask 需求 · 单语(跟 project.doc_language 一致)

**Frontmatter**:

```yaml
---
type: subtask-plan
parent_module: M01
parent_subtask: M01-S1            # 或 sha1 id · 跟 module 内 subtask.id 一致
title: "通用资源池借/还机制 · 含失败冷却 + 超时回收 + EWMA 评分"
status: not-started               # 自动跟 module 内 subtask.status 同步
desc: "一句话说清楚 user 得到什么"
---

# 通用资源池借/还机制

## 用户得到什么
(一段话 · 用户需求语言 · 不讲代码)

## 范围
(从哪到哪 · 边界清晰)

## 实施 approach
(简短 · 写代码逻辑 · 这里才放 §N.M / 文件名 / 函数名)

## 验证
(完成标准 · 测试 · acceptance criteria)
```

**自动 wire 到 dashboard**:

`schema.py::extract_subtasks_from_body` 增强 · 对每个 subtask · 自动查找 `docs/plans/<module-id>/<S-prefix>*.md`(用 sha1 id OR S<NN> 序号匹配)· 如果找到 · 自动注入 `doc_anchors` 列表第一条 · dashboard 点 subtask 默认渲染这条 plan(不再渲染 module 级 docs)。

### §5.4 · author skill · 新加 §16 + 改 §3.1 + 改 §11

**§16(新)· skill-first authoring philosophy**

3 节:

- §16.1 · 为什么 docs-cockpit 是 skill not python(north star 解释)
- §16.2 · subtask title 写法 4 黄金法则 + good/bad 对比表
- §16.3 · per-subtask plan MD 标准结构 + 何时该写(复杂 subtask · 简单的可以不写)

**§3.1 改**(subtask format)· 加「title 风格规则」段落:

- 1 行 · 单语(zh-CN 或 en 由 project.doc_language)
- 一句话讲**用户得到什么** · 不讲代码细节
- 禁:`§N.M` · 文件名 · 函数名 · 行号 · 这些是 anchor 范畴 · 走 `code:` / `docs:` 字段
- 复杂 subtask · 写独立 plan MD 在 `docs/plans/M××/S××-<slug>.md`

**§11 改**(authoring flow)· 加 Step 6:

- Step 6 · 「为每个复杂 subtask 写独立 plan MD」· 落点 `docs/plans/M××/S××-<slug>.md` · frontmatter `parent_subtask` · body 4 节(用户得到什么 / 范围 / 实施 / 验证)

### §5.5 · 新 CLI · `docs-cockpit init-subtask-plan`

可选 · 不强制 · 给「我想写 subtask plan 但不想 boilerplate」用户:

```bash
docs-cockpit init-subtask-plan M01 M01-S1
# 自动创建 docs/plans/M01/S01-<slug>.md · 从 module MD 读 subtask title · slugify · 预填 frontmatter
```

`<slug>` 默认从 subtask title 用 author skill §16.2 规则转 · 用户可 `--slug=custom` override。

### §5.6 · README + CHANGELOG

- README 加 v0.16 banner · 双语共讲
- CHANGELOG `[0.16.0]` · why / added · schema · added · skill · changed · 老 doc fallback / not-changed / verified

## §6 · Distribution Plan

- alpha.1 · project.doc_language + lint 2 个新 issue type + tests
- alpha.2 · per-subtask plan MD scanner + auto-wire 到 doc_anchors + tests
- alpha.3 · author skill §16 + §3.1 改 + §11 改(SKILL.md 改 = minor)
- 0.16.0 · 4 文件 bump + CHANGELOG aggregate + push

## §7 · Success Criteria

- docs-cockpit 自己 dogfood 走完 · subtask title 全 zh-CN · 0 个 title 含 §N.M · 5+ subtask 有独立 plan MD
- 跑 `docs-cockpit lint --doc-lang` 拿到当前项目所有 title-style violation(从 Sourcery 看 · 估 20+ 条 hint/warn)
- 老 project 不破 · 没 `doc_language` 字段的 yaml 仍正常 build · 没 subtask plan 的 module 仍渲染

## §8 · Open Questions(留实施时定)

- Q1 · doc_language 自动 detect 触发器 ratio · 30% CJK 算 zh-CN 是经验值 · 测了再调
- Q2 · subtask plan parent_subtask 字段 · 用 `M01-S1` 序号形式 还是 `M01-f75501` sha1 形式?推荐序号(用户可读)· 但 title 改 id 漂移用 sha1 稳。可能要支持两个
- Q3 · 已经存在的 subtask body checklist · 一键迁移到 per-subtask plan MD 的 CLI 工具要不要做?可能 v0.17 候选

## §9 · Out of scope · 留 v0.17+

- doc_language 加更多语种(日 / 韩 / 西 ...) · 当前 zh-CN + en 二选一够
- subtask plan 用 LLM 自动 draft 从 module body checklist line · 太多 hallucination 风险
- title style auto-fix · 自动改用户写的 title 太干涉 · 仅 lint warn
