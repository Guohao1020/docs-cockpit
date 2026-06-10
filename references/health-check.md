<!-- 体检方法论 SSOT · build Phase 5 前 / rebuild Phase 2 末引用 · v1.1 -->

# docs-cockpit · 全方位体检方法论

build / rebuild 升格为「项目体检」的方法论 SSOT —— 查什么（九科检查表）+ 怎么判（量化阈值）+ 怎么开方（处方与五桶分诊）。与 `references/association-method.md` 平级：它讲「怎么核 anchor」（②关联科引用其方法 3，不重复），本文讲体检全流程。HEALTH.md 的 frontmatter 字段规范见 `references/schema.md · health-report schema` 节，本文只讲方法与模板，不重复字段表。

## 目录

1. [九科检查表](#九科检查表) — 文档卷①-⑤ · 工程卷⑥-⑨
2. [双模式](#双模式) — 快检 / 深检 · 抽检规则 · 置信度门
3. [三条铁律](#三条铁律)
4. [三段式报告模板](#三段式报告模板)
5. [HEALTH.md 写入规范](#healthmd-写入规范)
6. [五桶分诊判据](#五桶分诊判据)
7. [台账机制](#台账机制)
8. [体检在 build / rebuild 流程里的位置](#体检在-build--rebuild-流程里的位置)

---

## 九科检查表

每科固定三块：**查什么**（检查项清单）· **怎么查**（可直接执行的工具调用）· **判定标准**（✅⚠️❌ 量化阈值）。科 verdict 取该科各检查项里最差的一档。

### 文档卷（docs-cockpit 本职）

#### ① 结构科 · structure

**查什么** — frontmatter 全量合规：必填字段缺失 · status×progress 矛盾 · placeholder id · subtask title 法则 · anchor 语法错误。

**怎么查**

1. 在 cockpit 根目录跑 `docs-cockpit lint`（或 `docs-cockpit lint -c <path>/docs-cockpit.yaml`），解析输出的 ❌ error / ⚠️ warn / 💡 hint 三档行
2. 若刚 render 过，等价读 `docs/state.json::issues[]`——每条带 `severity / field / message / suggestion / reference`，无需重跑

**判定标准** — 0 error 且 0 warn → ✅ · 有 warn 无 error → ⚠️ · 有 error → ❌（error = 该 doc 在看板上渲染不出来）

#### ② 关联科 · anchors

**查什么** — anchor 覆盖率 · anchor verdict 抽检 · 死锚。

**怎么查**

1. **覆盖率** = 有 anchor 的 subtask / 总 subtask：读 `docs/state.json`，数 `modules[*].subtasks[*]` 中 `code_anchors` 或 `doc_anchors` 非空的条数除以总条数（0-anchor 清单不用手数——lint 的 `subtask-missing-anchors` 直接给）。可执行统计：

   ```bash
   python -c "import json; d=json.load(open('docs/state.json',encoding='utf-8')); \
   subs=[s for m in d['modules'] for s in m.get('subtasks') or []]; \
   hit=[s for s in subs if s.get('code_anchors') or s.get('doc_anchors')]; \
   print(f'{len(hit)}/{len(subs)} = {len(hit)/max(len(subs),1):.0%}')"
   ```

2. **verdict 抽检** — 按 `references/association-method.md · 方法 3` 逐条预演给 4 档 verdict（✅ accurate / ⚠️ partial / ❌ wrong / ❓ missing），流程不在本文重复；抽样规则见[双模式](#双模式)
3. **死锚** = state.json 里任一 anchor 条目（`subtasks[*].code_anchors[*]` / `doc_anchors[*]` / `modules[*].docs[*]`）`exists=false` 或 `warning` 非空——机器已判好，grep `"exists": false` 与 `"warning": "[^"]` 即得清单（`warning` 字段恒存在 · 空串 `""` = 健康 · 必须排除空串否则 192 条健康锚全报假阳性）

**判定标准** — 覆盖率 ≥90% → ✅ · 70–90% → ⚠️ · <70% → ❌；抽检 accurate 率 ≥90% → ✅ · 70–90% → ⚠️ · <70% → ❌（任一 wrong 实锤即开 high 处方）；死锚 0 条是 ✅ 的前提，有死锚至少 ⚠️

#### ③ 新鲜科 · freshness

**查什么** — 近期大改文件的 anchor 是否复核过 · module status 与 commit 活跃度矛盾。

**怎么查**

1. 拿近期变更文件清单：

   ```bash
   git log --since="14 days ago" --name-only --pretty=format: | sort -u
   ```

2. 交叉 state.json：在这份清单里的文件，反查哪些 `code_anchors[].path` 指向它们（路径比对前统一 `\` → `/`）
3. 对命中的 anchor 查复核状态：读 `docs/HEALTH.md` frontmatter 的上次体检 `date`，跑 `git log --since=<上次体检 date> -- <file>`——上次体检后该文件又改过、且本次体检前没人重验过这条 anchor = **未复核嫌疑**（首次体检无 HEALTH.md → 全部近期变更锚都算嫌疑，进抽检优先队列）
4. **status 矛盾**：对每个 `status: in-progress` 的 module，取其全部 code anchor 文件跑 `git log --since="30 days ago" -- <files>`——输出为空 = 宣称推进中却 30 天无 commit

**判定标准** — 0 未复核嫌疑且 0 status 矛盾 → ✅ · 有嫌疑或矛盾 → ⚠️ · 嫌疑锚经方法 3 抽验实锤 wrong → ❌

#### ④ 覆盖科 · coverage

**查什么** — 孤儿文档 · 无 spec 的 module · 无 plan 的 sprint · 0-anchor subtask。

**怎么查**（即 `association-method.md · 方法 1` 第 3 步的检索产出，执行细节见彼处）

1. **孤儿文档** = Glob 五类 docs 全集 − 所有 module `docs:` / `@docs:` 引用的并集
2. **无 spec module** = state.json `modules[*].docs[]` 里没有任何 `path` 含 `-spec.md`（或 `type: spec`）条目的 module
3. **无 plan sprint** = 收集 `modules[*].sprint` 值集合，逐个查 `docs/plans/` 有无对应 sprint-plan（frontmatter `sprint:` 匹配；schema 见 `references/schema.md · sprint-plan schema`）
4. **0-anchor subtask** = lint 的 `subtask-missing-anchors` 直接给清单

**判定标准** — 四类缺口全 0 → ✅ · 仅孤儿文档或 0-anchor subtask ≤3 条 → ⚠️ · 任一 in-progress module 无 spec / 当前 sprint 无 plan / 缺口合计 >3 → ❌

#### ⑤ 一致科 · consistency

**查什么** — depends_on↔blocks 配对 · subtask status × module status · sprint 对齐。

**怎么查**

1. **配对**：读 state.json `modules[*].depends_on / blocks`（或 `Grep "depends_on:|blocks:" docs/spec/module/`）——A `depends_on` B 则 B 的 `blocks` 应含 A，反向同理，列出单边缺失对
2. **subtask×module**：数每个 module 的 subtask done 比例，对照 module `status` / `progress`——9 done + 1 not-started 而 module 仍 `not-started` → 该 in-progress；subtask 全 done 而 module 仍 in-progress → 该 done 或缺 subtask
3. **sprint 对齐**：module `sprint` 字段 vs sprint-plan `in_scope` 互查（lint 的 `sprint-schema` 类 issue 已覆盖结构层，本科查语义层：in_scope 列了的 module 其 sprint 字段是否一致）

**判定标准** — 0 矛盾 → ✅ · 1–2 处 → ⚠️ · ≥3 处或硬矛盾（module done 但 subtask 0% done）→ ❌

### 工程卷（内置基线 · 不依赖外部插件）

#### ⑥ 代码质量科 · code quality

**查什么** — 项目自带的 test / lint / type 工具能否全过。**只包装既有工具，不替项目发明标准**。

**怎么查**

1. **探测**：Read `pyproject.toml`（`[tool.pytest.ini_options]` / `[tool.ruff]` / `[tool.mypy]` / dev 依赖）→ `package.json`（`scripts.test / lint / typecheck`）→ Glob `.github/workflows/*.yml` grep `run:` 行，汇出该项目实际配了哪些工具
2. **跑**：探测到什么跑什么——`pytest tests/ -q`（取末尾 summary 行）· `npm test --silent` · `ruff check .` · `mypy <pkg>` / `npx tsc --noEmit` 等
3. 没探测到的维度标 **N/A**，不扣分、不开「该加测试框架」处方（那是用户的工程决策，非体检职权）

**判定标准** — 检出的工具全过 → ✅ · 任一失败 → ❌ · 工具在但跑不起来（依赖未装等环境因素）→ ⚠️ 并开「修运行环境」处方 · 一个工具都没有 → 整科 N/A（报告标注，不算 ❌，不影响总评）

#### ⑦ 缺陷科 · defects

**查什么** — 陈旧 TODO/FIXME/HACK/XXX · 被 skip 的测试 · 裸 except 吞异常 · 大段注释掉的代码。

**怎么查**（`--include` / `--type` 按项目源码语言换）

1. 标记债：

   ```bash
   grep -rn "TODO\|FIXME\|HACK\|XXX" --include="*.py" <src-dirs>
   ```

   逐条 `git blame -L <line>,<line> --date=short -- <file>` 取年龄，>90 天 → 陈旧（命中 >30 条时抽样 blame 10 条 + 报总数，其余按文件 `git log -1 --format=%cs -- <file>` 近似）；命中后必须 Read 上下文排除假阳性（处理 TODO/FIXME 标记的 lint 代码本身不是 TODO 债）
2. 测试逃逸：`grep -rn "skip\|xfail" --include="*.py" tests/`（`pytest.mark.skip` / `it.skip` 等），区分「带 reason 注明」与「裸 skip」
3. 裸 except：`rg -n "except\s*:\s*$" --type py` + `rg -nU "except\s+Exception\s*:\s*\n\s*pass" --type py`（多行模式抓吞异常）
4. 注释代码块：`rg -n "^\s*#.*[=(]" --type py` 先粗筛，连续 ≥5 行命中的段落 Read 确认是不是整块被注释的代码——这步是认知判断，grep 只负责缩小范围

**判定标准** — 0 陈旧标记且 0 裸 except → ✅ · 有陈旧标记 / 无 reason 的 skip / 注释代码块 → ⚠️ · 裸 except 吞异常在生产路径或陈旧 FIXME 指向真 bug → ❌

#### ⑧ 生产就绪科 · production readiness

**查什么** — 硬编码 secret · 绝对路径硬编码 · 调试残留 · mock/stub 混入非 test 路径。

**怎么查**（命中后必须 Read 上下文排除假阳性——示例占位 `<your-key>` / `xxx` / 测试 fixture 不算）

1. **secret 模式**：

   ```bash
   rg -in "(api[_-]?key|password|token)\s*=\s*[\"'][^\"']{8,}" -g '!tests/**' -g '!docs/**'
   ```

2. **绝对路径**：`rg -n "[C-Z]:\\\\|/Users/|/home/" <src-dirs>`（排除注释与文档字符串里的示例）
3. **调试残留**：`rg -n "print\(" --type py -g '!tests/**'` 命中后认知过滤——CLI 的正当输出路径（如本仓 `_safe_print`）不算；JS 侧 `rg -n "console\.log" -g '!**/*.test.*'`
4. **mock/stub**：`rg -in "\b(mock|stub|fake)\w*" -g '!tests/**' -g '!**/conftest.py'` 命中类名 / 函数名 / import 即嫌疑

**判定标准** — 任一真 secret 命中 → ❌ 即刻（severity high · 不等累计）· 其余三项累计：0 → ✅ · 1–4 → ⚠️ · ≥5 → ❌

#### ⑨ 架构科 · architecture（深检专属）

**查什么** — God file · 循环依赖 · 职责漂移。快检不进本科。

**怎么查**

1. **单文件行数**：

   ```bash
   find <src-dirs> -name "*.py" | xargs wc -l | sort -rn | head -15
   ```

   >1000 行 → ⚠️ · >1500 行 → ❌ God file
2. **循环依赖**（python）：对包内每个模块 `rg -n "^(import|from)\s+<pkg>"` 建简单 import 图，先查双边环（A import B 且 B import A——最常见），更长的环靠认知走查
3. **职责漂移**：Read 模块 docstring 宣称的职责 vs 实际函数清单——纯认知判断（如 docstring 说「只做渲染」却长出了状态合并逻辑），命中时引 docstring 行号 + 越界函数行号作证据

**判定标准** — 0 God file 且 0 环 → ✅ · 有 >1000 行文件或一个双边环 → ⚠️ · 有 >1500 行文件 / 多环 / 实锤职责漂移 → ❌

---

## 双模式

| | 快检（build / rebuild 自动附带） | 深检（「全面体检 / 深度体检」明示触发） |
|---|---|---|
| 科室 | ①②④ 全量 + ⑥ 机械跑 + ⑦⑧ 高置信 grep 项 | 全九科（⑨ 深检专属 · ③⑤ 补齐） |
| anchor verdict | >30 锚抽检（规则见下） | 全量逐条 |
| 报告门槛 | 高置信才报 · 台账条目跳过 | 低置信也报（标置信度）· 台账条目列出但标「已接受」 |

**抽检规则**（②关联科 verdict 用）：总锚数 ≤30 → 全量；>30 → 抽 20%，**最少 10 条**；优先抽 ③新鲜科标出的「近期变更文件的锚」（drift 概率最高），余量随机补齐。

**置信度门**：

- **快检**只报「有具体证据 + 精确定位（文件:行 / state.json 字段路径）」的异常——嫌疑、感觉、模式命中但没 Read 过上下文的，一律不进报告
- **深检**嫌疑也报，但每条标置信度 **高**（实锤 · 有证据链）/ **中**（模式命中 + 上下文支持）/ **低**（仅模式命中），低置信项只能进观察桶，不开处方

---

## 三条铁律

1. **Iron Law** —— 处方必须带**根因 + anchor 定位**。查不出根因的不开药：写「进一步检查单」，进观察桶等下次体检。没有根因的「修法」是猜，猜错比不开更伤。检查单三要素：

   ```markdown
   #### 进一步检查 · {现象一句话}
   - 要查什么:{待确认的假设 · 如「M03 的 anchor 漂移是否因 5/20 重构」}
   - 怎么查:{可执行步骤 · 如「git log --since=2026-05-20 -- src/foo.py + 方法 3 重验」}
   - 预期确认:{查完能回答什么 · 答不上说明假设本身要换}
   ```

2. **Zero-noise** —— 体检报告没人看 = 体检失败。快检只报高置信异常；`accepted_debts` 台账条目不重复报（机制见[台账机制](#台账机制)）。宁可漏报一条低置信嫌疑，不可让用户在噪声里漏掉真问题。
3. **诊断治疗分离** —— 体检只产出报告，**不动手改任何文件**（HEALTH.md 本身除外）。治疗走 build / rebuild 的对话决策 phase（Phase 5-6）：用户逐桶确认后才执行。

---

## 三段式报告模板

呈给用户的对话输出按此模板，HEALTH.md body 持久化同款（frontmatter 另见写入规范）：

```markdown
## 体检报告 · {项目名} · {YYYY-MM-DD} · {快检|深检}

### 一 · 诊断

总评:{A|B|C|D}{±}

| 科 | verdict | 摘要 |
|---|---|---|
| ① 结构 | ✅ | 0 error · 0 warn |
| ② 关联 | ⚠️ | 覆盖率 78% · 抽检 10 条 1❌ · 死锚 2 |
| ③ 新鲜 | ✅ | 近 14 天变更 6 文件 · 0 未复核锚 |
| ④ 覆盖 | ⚠️ | 孤儿文档 2 · M03 无 spec |
| ⑤ 一致 | ✅ | depends_on↔blocks 全配对 |
| ⑥ 代码质量 | ✅ | pytest 253 passed · ruff N/A |
| ⑦ 缺陷 | ⚠️ | 陈旧 TODO 3(>90d) · 裸 except 1 |
| ⑧ 生产就绪 | ✅ | 0 secret · 0 调试残留 |
| ⑨ 架构 | ⚠️ | schema.py 1492 行（>1000 行）|（快检:未查 · 深检专属）

### 二 · 处方(按伤害排序:错 anchor/真 bug > 生产就绪 > 规范瑕疵)

#### RX-001 · {title} · severity: high · bucket: sprint
- 根因:{一句话根因 · 不是现象复述}
- anchor:{path:42-89 / path#§N —— 按方法 3 预演过}
- 修法:{具体动作 · 收尾「改后 docs-cockpit render 验证」}
- module:{真实 module id · 看板反链用}

#### RX-002 · …（同构 · severity: medium|low）

（查不出根因的 → 不开 RX · 列「进一步检查单」:要查什么 · 怎么查 · 预期确认什么）

### 三 · 行动规划(逐桶呈用户确认)

| 桶 | 处方 | 落地动作 |
|---|---|---|
| 立即修 | RX-003 | 当场治(Phase 5-6 对话决策 + Edit) |
| 本 sprint | RX-001 | →subtask 带 @code 挂 {module} · 同步 sprint-plan in_scope |
| backlog | RX-002 | 起草 docs/plans/P-{slug}.md |
| 观察 | RX-004 | 记复查清单 · 下次体检重点核 |
| 接受 | — | 入 HEALTH.md 台账 · 带复审日期 |

复查节奏建议:{治疗型(本轮处方治完即复查) | 周期型(30 天深检) | 触发型(下次大重构后) + 一句选择理由}
```

**总评规则**：全 ✅（N/A 科不计）→ **A** · 有 ⚠️ 无 ❌ → **B** · 有任一 ❌ 科 → 从 **C** 起算 · ≥2 个 ❌ 科、或 ⑧生产就绪科 secret 命中（即刻 ❌ 类）、或 ①结构科有 error → 从 **D** 起算；再按处方 severity 微调 ±：有未分诊的 high 处方 → 减一档的 `-`（如 B-）· ❌/D 科的处方全部已分诊入桶 → 加 `+`。等级回答「这个项目的文档/工程状态可信吗」，不是绩效分。

**处方四字段是看板 Copy-prompt 的原料**（前端拼自然语言 prompt：title + 根因 + anchor + 修法 + 「完成后跑 docs-cockpit render 验证」）——所以 `根因` / `修法` 必须写成完整可执行的句子，不写只有体检上下文才懂的缩略语；丢给一个全新 Claude Code session 能直接照做才算合格。

---

## HEALTH.md 写入规范

frontmatter 字段 schema 见 `references/schema.md · health-report schema` 节（type / date / mode / grade / departments / prescriptions / accepted_debts / next_checkup——字段表以彼处为准，本文不重复）。写入注意：

- **处方 id `RX-NNN` 稳定递增**——复查时未解决的处方**保留原 id**（趋势对比、看板反链、用户讨论都靠 id 锚定），新处方接着上次最大号往下编，已解决的号不复用
- **`module` 字段必须是真实 module id**——写入前对照 state.json `modules[*].id` 存在性；处方不归属任何 module 时省略该字段，不准编造
- **`anchors` 写入前必须按 `association-method.md · 方法 3` 预演过**——体检报告里的死锚是最高级别的自我打脸
- **`date` 用体检当天**——③新鲜科靠它界定「上次体检后」的窗口，写错日期 = 下次体检的新鲜科失明
- body = 上节三段式人读报告；frontmatter 是机器读（render 解析进看板），两者同步写、内容一致

---

## 五桶分诊判据

行动规划阶段对每条处方分桶，**逐桶呈用户确认**（铁律 3：分诊建议是诊断产物，执行须用户点头）：

| 桶 | 判定规则 | 落地动作 |
|---|---|---|
| **立即修** `now` | 一行级改动 · 零风险（改错可秒回滚）· 不牵连其它文件 | 当场治：Phase 5-6 对话决策 + Edit · 改后 `docs-cockpit render` 验证 |
| **本 sprint** `sprint` | 中等工作量 · 有明确归属 module · 本 sprint 容量装得下 | 处方转 subtask（title 按 4 法则 · 带 `@code:` anchor 指向问题位置）挂该 module · 同步 sprint-plan `in_scope` |
| **backlog** `backlog` | 大项：跨 module / 需设计决策 / 工作量超一个 sprint | 起草 plan 文档 `docs/plans/P-{slug}.md`（frontmatter 合规 → 自动进看板）· 处方 anchor 进 plan 的「证据」节 |
| **观察** `watch` | 低置信（深检的低/中置信嫌疑）· 或根因未明只有「进一步检查单」 | 记入复查跟踪清单（HEALTH.md prescriptions 里 `bucket: watch`）· 下次体检的②③科优先核这些 |
| **接受** `accepted` | **用户明示**「这个不修 / 已知且接受」——skill 不得自行分入此桶 | 入 HEALTH.md `accepted_debts` 台账 · 带 `review` 复审日期 |

分桶吃不准时问用户，不替用户决定——North star 同款：错分诊（该立即修的进了 backlog）比多问一句伤害大。

---

## 台账机制

`accepted_debts` 是 Zero-noise 铁律的落地载体：

- **写入**：用户明示接受时，每条记 `{ item, reason, review }`——`item` 一句话指明对象（带文件/模块定位）· `reason` 为什么接受（已排期 / 收益不抵成本 / 外部依赖）· `review` 复审日期（YYYY-MM 粒度即可）
- **快检**：台账条目命中的检查项**直接跳过不报**——同一条债每次体检都喊一遍 = 训练用户无视报告
- **深检**：列出但标「已接受 · 复审 {review}」，不计入科 verdict，不开处方
- **到期重审**：体检日 ≥ `review` 日期 → 该条**重新呈给用户**：继续接受（更新 review 日期）还是转处方进桶？不准静默续期——台账是延期决策，不是免死金牌
- 台账只在 HEALTH.md frontmatter 维护一份（SSOT），报告 body 的台账折叠区从它生成

---

## 体检在 build / rebuild 流程里的位置

| 触发面 | 模式 | 报告呈现时机 | 之后 |
|---|---|---|---|
| `docs-cockpit-build`（入院基线） | 快检 | Phase 5 对话决策**前**呈报告 | 行动规划与首次关联决策合并走 Phase 5-6 |
| `docs-cockpit-rebuild`（复查） | 快检 | Phase 2 诊断**末**呈报告 | 用户确认分诊后进 Phase 3-4 治疗 |
| 「体检一下 / health check」 | 快检 | rebuild Phase 1-2 出报告**即止** | 不进治疗 phase · 用户看完自行决定 |
| 「全面体检 / 深度体检」（明示） | 深检 | 同 rebuild 路径 · 全九科 + 全量 verdict | 同上 · 五桶逐桶确认 |

数据流闭环（spec §6）：skill 体检 → 写 / 更新 `docs/HEALTH.md` → `docs-cockpit render` 解析 → `state.json::health` + 看板健康面板 → 用户点处方卡 Copy prompt 丢给 Claude Code 治疗 → 治疗完 rebuild 复查 → HEALTH.md 更新 → 循环。

分工边界提醒：**写入者是 skill**（体检是认知产物），**解析者是 render**（机械）——与 module MD 的职责分界完全同构。体检不新增 CLI 子命令；`docs-cockpit lint` 仍是死规则门禁（CI `--strict` 不变），体检是引用 lint 输出的诊断叙事层。
