<!-- build / rebuild 共享 · 4 原子方法 -->

# docs-cockpit · 关联 4 原子方法

把 module / subtask 关联到 spec / plan / RFC 的方法论 SSOT —— `docs-cockpit-build` 的 Phase 1-4、`docs-cockpit-rebuild` 的 Phase 2-3 都引用本文。anchor 的**格式**定义（code anchor / doc anchor 各 4 shape、`@code:` / `@docs:` 行内标注）见 `references/schema.md`，本文只讲**方法**，不重复格式。

---

## 方法 1 · 检索 discovery

**何时用** — 面对一个 module / subtask，不知道该关联哪个文档时。

**怎么做**

1. `Glob` 建全景，一次扫五类 kind：

   ```
   Glob docs/spec/module/*.md
   Glob docs/spec/concept/*.md
   Glob docs/plans/**/*.md
   Glob docs/RFC/*.md
   Glob docs/spec/*-spec.md
   ```

2. 抽关键词反查：从 module 的 `title` / `desc` / `sprint` / `prd_ref` 抽 2-4 个关键词（中英同义词都抽，如「资源池 / ResourcePool」算两个），逐个 `Grep` 上面五类目录。**判据：≥2 个关键词命中同一文档 → 进候选池；只命中 1 个的存疑。** 关键词必须是不同语义维度（如「功能名」+「依赖/上游词」）——同义词不算两个（`ResourcePool` + `资源池` 算 1 个维度命中 2 次，仍是 1）。（sprint 字段慎用——纯版本号如 "0.10" 的 grep 噪声远大于信号，仅当 sprint 值含语义词时才算一个维度）留给方法 2 用 Read 裁决。

   **语境复核（必做）**：grep 命中计数只是粗筛——进池前用 `Grep -C 2` 看每个命中词的上下文，确认它讲的是本 module 的事而非词面巧合（实战教训：搜 browse 命中 22 次的 plan 其实全在讲 BrowserVendor）。多个维度同时词面巧合是常态，不复核语境的候选池可能 100% 假阳性。

   **候选池为空时**（五类 Glob 检索面内无真候选——工具自举型 module 的常态）：扩展检索面到 (a) module frontmatter 已链的 `docs:` 文件 (b) `commands/*.md` (c) `skills/*/SKILL.md` (d) CHANGELOG.md 相关版本段。仍为空 → 按方法 3 的 ❓ missing 处理（TODO 标注），不硬凑。

3. 标两类缺口：
   - **孤儿文档** = Glob 全集 − 所有 module `docs:` / `@docs:` 引用的并集 → 没被任何 module 引用的文档，提示「该有 module 没建」或「文档过时该归档」
   - **无支撑 subtask** = 0 anchor 的 subtask（`docs-cockpit lint` 的 `subtask-missing-anchors` 直接给清单，不用手数）

**反模式**

- 只 grep 一个关键词就下结论 —— 单词命中可能是巧合，换 2-3 个关键词交叉验证
- 把整个 plan 当 anchor —— 检索产出的只是**文档级**候选，必须经方法 2 收窄到 section

---

## 方法 2 · 推理 reasoning

**何时用** — 有候选文档后，判断哪一段真正相关。

**怎么做**

建「证据链」三步：

1. 提取 subtask 的需求点 X（title 讲的那件事）
2. `Read` 候选 plan / RFC 的 body —— **actually Read，不靠关键词碰运气**（grep snippet 看不出一个 section 的真实意图），定位也在讲 X 的 §N
3. 该 §N 即 anchor。**判据：该 § 的内容能回答「这个 subtask 为什么要做」或「怎么做」二者之一**；两者都答不上 → 不是它

术语对齐：用候选 plan/RFC 自己的术语写 subtask title（保持语义对齐——plan 叫「Lane A」就别自创「阶段一」），让 title 与 anchor 内容互相印证。

**反模式**

- 语义不匹配硬凑 —— 找不到讲 X 的 section 就承认缺口（走方法 3 的 `missing` 处理），不挑一个「最接近的」充数
- 一个 subtask 关联整篇文档 —— 600 行 plan 丢给用户自己找 = 等于没关联

---

## 方法 3 · 预演 dry-run

**何时用** — 落地 anchor 前，验证它真指对。

**怎么做**

1. 确认 anchor 的精确行范围（写进 MD 的格式形如 `path:42-89` / `path#§6.1`，完整语法见 `references/schema.md`）；读取时用 Read 工具的 offset/limit 参数取那一段（如 `:42-89` → offset=42, limit=48）实际过目内容
2. 对照 subtask title 给 4 档 verdict：

   | Verdict | 含义 | 处理 |
   |---|---|---|
   | ✅ `accurate` | anchor 文件存在 · 行号 / 章节真指到跟 title 相关内容 | 不动 |
   | ⚠️ `partial` | 文件在 · 但 line range 略偏 | 调整范围 |
   | ❌ `wrong` | 文件不存在 / 内容跟 title 完全无关 | 必须改 anchor 或 mark TODO |
   | ❓ `missing` | subtask 0 anchor | 补 anchor（回到方法 1+2 重找） |

边界注：⚠️ partial 也包括「行号正确但内容只覆盖 title 一半语义」（处理：收窄行范围 + 在理由句标注覆盖缺口）；❌ wrong 里「文件不存在」可由 lint 机查、「内容无关」必须人读——成本不同但处理相同（改 anchor 或 TODO）。

3. **错 anchor 比缺 anchor 伤害大**（用户点过去看到无关内容 · 对 dashboard 的信任崩塌）。找不到对应 section 必须给 ❌ + `# TODO: anchor this subtask once plan §X clarifies` —— **不准瞎猜行号**

**反模式**

- 写 `:42-89` 却没 Read 过那 42-89 行
- verify 不过仍落地 —— `partial` / `wrong` 必须先调整 / 改写，再写进 MD

---

## 方法 4 · 高亮 highlight（skill-only）

**何时用** — 把关联呈现给用户 / 写进 anchor 时。

**怎么做**

给每条 anchor 配两件东西：

1. 精确行范围或 heading（格式见 `references/schema.md`）—— 不是裸文件路径
2. 一句关联理由 —— 用文字标出「片段第 X–Y 行 / 这句话」为什么支撑这条 subtask

示例输出（呈现给用户时的形态）：

```
M07-S1 「BrowserVendor 抽象」
  @docs:docs/plans/driver-seat.md#§6.1
  ↳ §6.1 第 142-156 行定义了 vendor 的 launch / dispose 接口契约 —— 正是这个 subtask 要实现的抽象边界
```

**判据：理由必须含两要素 —— (a) 被引片段的具体内容（第 N–M 行说了什么）·(b) 它与 subtask title 的语义关联。缺任一 → 理由不合格，重写；写不出 (b) → 说明关联本身存疑，回方法 2 重找。** 这是**推理层的证据呈现** —— 不是改 template 渲染高亮，不动 `index.html.tmpl`，纯文字输出。

**反模式**

- 只给文件路径不给行范围 —— 用户还得自己找
- 不解释为什么相关 —— 行范围对了但没理由，等于让用户重做一遍方法 2

---

## 四方法在 build / rebuild 流程里的位置

| 方法 | docs-cockpit-build | docs-cockpit-rebuild |
|---|---|---|
| 1 检索 | Phase 1 · 建全景 + 候选池 + 缺口清单 | Phase 3 · 为漂移 anchor 重找候选 |
| 2 推理 | Phase 2 · 收窄到 section | Phase 3 · 重新推理正确 anchor |
| 3 预演 | Phase 3 · 落地前逐条 verdict | Phase 2 · 诊断漂移（重验所有现存 anchor） |
| 4 高亮 | Phase 4 · 每条关联标行 + 理由 | —（落地格式走 `references/schema.md`） |
