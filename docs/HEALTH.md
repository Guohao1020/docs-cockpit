---
type: health-report
date: 2026-06-11
mode: deep
grade: D+
departments:
  - id: structure
    name: "结构"
    verdict: pass
    summary: "docs-cockpit lint:0 error · 0 warn · 0 hint(17 module · 121 subtask 全过)"
  - id: anchors
    name: "关联"
    verdict: fail
    summary: "覆盖率 121/121=100% · 死锚 0 · 方法3 抽检 41 条(风险优先):✅21 ⚠️3 ❌17 · accurate 51%"
    detail: "抽样刻意偏向高风险面(31 条行号锚全验 + 10 条 doc 锚),51% 不代表全量 192 锚的无偏估计;❌ 集中于 v0.10-0.14 时代写定的行号锚,详见处方 RX-001~006"
  - id: freshness
    name: "新鲜"
    verdict: fail
    summary: "近 14 天 146/192 锚指向变更文件(首检无基线 · 全列嫌疑) · 抽验实锤 17 wrong · status 矛盾 0"
    detail: "v1.0/v1.1 大改期:build.py +32 行(2ec300f)· cli.py -24 行(201798c)· schema.py 增至 1755 行——行号锚位移的直接近因;0 个 in-progress module,无 30 天 commit 矛盾项"
  - id: coverage
    name: "覆盖"
    verdict: fail
    summary: "孤儿 plan 12 篇(>3) · v1.0/v1.1 工作 0 module 0 sprint-plan(看板内容停在 v0.14 时代) · 0-anchor subtask 0"
    detail: "「无 spec module」检查项对本仓不适用:module 卡自身位于 docs/spec/module/ 即 spec(自举仓豁免 · 已回评方法论)"
  - id: consistency
    name: "一致"
    verdict: warn
    summary: "depends_on↔blocks 单边 10 处(schema.md 注明 informational · 按 warn 计) · V0.19 plan status 过时 · subtask×module 矛盾 0"
  - id: code-quality
    name: "代码质量"
    verdict: pass
    summary: "pytest 289 passed(5.45s · 与 CI test.yml 同源) · ruff/mypy 未配置 → N/A 不计分"
  - id: defects
    name: "缺陷"
    verdict: pass
    summary: "TODO/FIXME 命中均为 lint 实现代码假阳性 · 0 skip/xfail · 0 裸 except(2 处 except Exception 均带注释理由)"
  - id: production-readiness
    name: "生产就绪"
    verdict: pass
    summary: "0 secret · 0 绝对路径 · 0 console.log · print 均为 CLI 正当输出(_safe_print/sync-status 报告) · stub 为文档化 MVP 特性"
  - id: architecture
    name: "架构"
    verdict: warn
    summary: "build↔cli 双边环(lazy import + 注释明示缓解) · build.py 960 行逼近 1000 线 · schema.py 1755 行入台账(已接受 · 复审 2026-08)"
prescriptions:
  - id: RX-001
    severity: high
    bucket: sprint
    title: "M01 行号锚 6 条漂移重锚定(build.py/schema.py/paths.py)"
    root_cause: "M01 的行号锚写定于 v0.10-0.11,此后 build.py 经 v1.1 health 解析块插入(commit 2ec300f 在 490 行处 +32 行)、schema.py 经 v0.16/v0.19/v1.0 多轮增长,行号整体位移;渲染器只验文件存在,行内漂移机器不可见"
    fix: "改 docs/spec/module/M01-build-engine.md 的 @code 锚:M01-2599ce 与 M01-012713 改指 docs_cockpit/build.py:534-555(render_html 的 </script> 转义 + count=1 替换);M01-52d6f1 改指 build.py:698-714(prompts.js sidecar 写出);M01-547e32 改指 docs_cockpit/schema.py:1392-1450(normalize_subtasks id 算法 + status coerce 本体)并附 1369-1381(_subtask_id_for 稳定 id 算法);M01-f19e47 改指 docs_cockpit/paths.py:586-644(_resolve_code_anchor)+ paths.py:343-400(_read_code_lines 容错);M01-f0bd29 第二条 build.py:469-540 收窄为 392-527(build_payload 全体)。每条改前按 association-method.md 方法 3 重读确认,改后跑 docs-cockpit render 验证"
    anchors:
      - "docs/spec/module/M01-build-engine.md"
      - "docs_cockpit/build.py:534-555"
      - "docs_cockpit/build.py:698-714"
      - "docs_cockpit/schema.py:1392-1450"
      - "docs_cockpit/paths.py:586-644"
    module: M01
  - id: RX-002
    severity: high
    bucket: sprint
    title: "M04 行号锚 5 条漂移重锚定(schema.py/prompt.py)"
    root_cause: "schema.py 在锚写定后插入 v0.16 lint 段、v0.19 sprint-plan 校验段、v1.1 health 校验段,原 152-541 区间内容整体易主;prompt.py 在 v1.0 裁剪后只剩 206 行,锚 130-237 行尾越界"
    fix: "改 docs/spec/module/M04-author-skill.md 的 @code 锚:M04-fe43ce 改指 docs_cockpit/schema.py:106-163(Issue 类 + format_for_terminal 三段式输出);M04-5c19d5 改指 schema.py:1392-1450(normalize_subtasks id 算法 + status coerce 本体)并附 1369-1381(_subtask_id_for 稳定 id 算法);M04-4d1c66 改指 schema.py:1369-1381(_subtask_id_for 稳定 id 算法);M04-1c2814 改指 schema.py:1137-1196(@code:/@docs: 内联正则 + 提取逻辑);M04-438a91 改指 docs_cockpit/prompt.py:39(BUILTIN_TEMPLATES)并补 @docs 指向 docs_cockpit/templates/prompts/ 内对应 j2 模板。改后跑 docs-cockpit render 验证"
    anchors:
      - "docs/spec/module/M04-author-skill.md"
      - "docs_cockpit/schema.py:106-163"
      - "docs_cockpit/schema.py:1369-1381"
      - "docs_cockpit/schema.py:1137-1196"
      - "docs_cockpit/prompt.py:39"
    module: M04
  - id: RX-003
    severity: high
    bucket: sprint
    title: "M07 锚 build.py:486-498 改指 state.json sidecar 现位置"
    root_cause: "与 RX-001 同根因——v1.1 health 块插入把 486-498 顶成 sprint-lint 收尾区;M07(MCP server)本体 v1.0 已删,该锚指向的幸存实现是 state.json sidecar 写出"
    fix: "把 docs/spec/module/M07-mcp-server.md 中 M07-e457c0 的 @code 锚改指 docs_cockpit/build.py:684-697(state.json sidecar 写出块),改后跑 docs-cockpit render 验证"
    anchors:
      - "docs/spec/module/M07-mcp-server.md"
      - "docs_cockpit/build.py:684-697"
    module: M07
  - id: RX-004
    severity: high
    bucket: sprint
    title: "M09 锚 3 条漂移(cli.py 行尾越界 + tmpl 指向 CSS 区)"
    root_cause: "cli.py 在 1.1 移除 build 别名后缩至 182 行,锚 181-205 行尾越界且现指 parse_args 收尾;index.html.tmpl 多版本增长至 5226 行,锚 1697-1706 现为 .doc-preview-body CSS、3803-3829 为相邻的 progress override 写入区"
    fix: "改 docs/spec/module/M09-sync-status.md 的 @code 锚:M09-7addb7 改指 docs_cockpit/cli.py:129-156(sync-status 子命令 argparse 接线:130-133 add_parser + 134-137 --import 参数是命令行接受导出 JSON 的语义核心);M09-3879c3 两条改指 docs_cockpit/templates/index.html.tmpl:2066-2070(export-overrides 按钮)与 index.html.tmpl:5163-5187(下载 localStorage JSON 逻辑)。改后跑 docs-cockpit render 验证"
    anchors:
      - "docs/spec/module/M09-sync-status.md"
      - "docs_cockpit/cli.py:129-156"
      - "docs_cockpit/templates/index.html.tmpl:5163-5187"
    module: M09
  - id: RX-005
    severity: high
    bucket: sprint
    title: "M11 锚 2 条漂移(paths.py 目标函数下移约 160 行)"
    root_cause: "paths.py 在锚写定(v0.14.3)后追加 subtask doc-ref resolver 段,_resolve_subtask_doc_anchor 与 _resolve_code_anchor 整体下移约 160-190 行"
    fix: "改 docs/spec/module/M11-schema-consistency.md 的 @code 锚:M11-ccceb7 改指 docs_cockpit/paths.py:606-624(path_only 字段写出 · 函数头 586);M11-ced9f4 改指 paths.py:484-520(_resolve_subtask_doc_anchor 的 raw_with_anchor)。改后跑 docs-cockpit render 验证"
    anchors:
      - "docs/spec/module/M11-schema-consistency.md"
      - "docs_cockpit/paths.py:606-624"
      - "docs_cockpit/paths.py:484-520"
    module: M11
  - id: RX-006
    severity: high
    bucket: sprint
    title: "M12 锚 2 条漂移(heading regex 现位 1117-1132)"
    root_cause: "与 RX-002 同根因——schema.py 多轮插入使 heading regex 区块从 152-168 下移至 1117-1132,原位置现为 Issue.format_for_terminal"
    fix: "改 docs/spec/module/M12-parser-robustness.md 的 @code 锚:M12-64c000 改指 docs_cockpit/schema.py:1117-1126(_SUBTASK_SECTION_RE 放宽说明 + 定义);M12-7039f3 改指 schema.py:1127-1132(_DOCS_SECTION_RE)。改后跑 docs-cockpit render 验证"
    anchors:
      - "docs/spec/module/M12-parser-robustness.md"
      - "docs_cockpit/schema.py:1117-1132"
    module: M12
  - id: RX-007
    severity: medium
    bucket: sprint
    title: "_read_code_lines 行尾越界静默截断 · 漂移锚逃过死锚检测"
    root_cause: "docs_cockpit/paths.py::_read_code_lines 只在 start > total 时返回 warning,end > total 被 min(total, end+CTX) 静默 clamp——cli.py:181-205(文件 182 行)与 prompt.py:130-237(文件 206 行)两条漂移锚因此 exists=true 且 warning 为空,机器死锚清单全绿"
    fix: "在 docs_cockpit/paths.py 的窗口计算分支(约 383-400 行)加判断:end 存在且 end > total 时把 warning 置为 'end line {end} > file total {total} · anchor may be stale',preview 照常按 clamp 后窗口生成(容差行为不变);补对应单测后跑 py -3.13 -m pytest tests/ -q 与 docs-cockpit render,确认 state.json 对越界锚出现该 warning"
    anchors:
      - "docs_cockpit/paths.py:383-400"
    module: M01
  - id: RX-008
    severity: medium
    bucket: backlog
    title: "看板内容停在 v0.14 时代 · v1.0/v1.1 工作未入板"
    root_cause: "v1.0 skill-first pivot 与 v1.1 health-check 的工作以会话任务清单推进,未回写 cockpit 的 module/sprint 体系——17 个 module 全部 done 且 sprint 最大 0.14,12 篇 plan(P-skill-first-pivot、P-v1.0-stage-a/b/c、P-v1.1-health-check/impl、V0.18/V0.19 等)无任何 module 反链成为孤儿"
    fix: "走 docs-cockpit-build skill 的对话决策流程:与用户共定 v1.0/v1.1 的 module 卡(候选如 M18-skill-first-pivot、M19-health-check)并起草对应 sprint-plan;把孤儿 plan 按方法 1/2 挂回 module 的 docs: 或 @docs 锚——高价值优先(P-skill-first-pivot.md、P-v1.1-health-check.md、P-v1.1-health-impl.md),纯历史向(P-v0.11-remaining-backlog 等)可挂 CHANGELOG 历史锚或经用户明示接受后不挂。完成后 docs-cockpit render 验证孤儿清零"
    anchors:
      - "docs/plans/P-skill-first-pivot.md"
      - "docs/plans/P-v1.1-health-check.md"
  - id: RX-009
    severity: low
    bucket: now
    title: "V0.19 sprint-plan status 过时(in-progress 改 done)"
    root_cause: "v0.19 发版收尾只更新了 CHANGELOG,没回写 sprint-plan frontmatter——现已发布至 1.1.0 前夕,V0.19 仍标 in-progress"
    fix: "把 docs/plans/V0.19-agile-version-planning.md 第 5 行 status: in-progress 改为 done(out_of_scope 已明示遗留项,无需迁移),改后跑 docs-cockpit render 验证"
    anchors:
      - "docs/plans/V0.19-agile-version-planning.md:5"
  - id: RX-010
    severity: low
    bucket: backlog
    title: "depends_on↔blocks 10 处单边 · 镜像策略待定"
    root_cause: "module frontmatter 的依赖边按单向语义手写,references/schema.md(142 行)注明该字段 currently informational(不参与渲染),从未要求镜像——累计 10 处单边(涉及 M01-M08/M13/M15/M17)"
    fix: "设计决策二选一:(a) 在 references/schema.md 升级规范要求双向镜像并加 lint 校验,然后补齐 8 个 module MD 的 10 条反向边;(b) render 端从 depends_on 单向推导反向边,MD 保持单写。建议等 dependency graph 渲染特性立项时一并定;落地后跑 docs-cockpit render 验证"
    anchors:
      - "references/schema.md:142"
accepted_debts:
  - item: "schema.py God file(体检时点 1755 行 · 含 v1.1 健康校验后仍在涨,已越过方法论 1500 行 ❌ 线)"
    reason: "post-1.0 已排期拆 md_merge.py(CLAUDE.md 架构节明示),拆分前不重复报"
    review: "2026-08"
next_checkup: "治疗型:RX-001~006 与 RX-009 治完即 rebuild 快检复查;v1.1 发布后 30 天内做一次深检,优先覆盖本轮未抽的约 150 条锚(主要是 CHANGELOG 历史锚 · 低风险)"
---

## 体检报告 · docs-cockpit · 2026-06-11 · 深检

首次自体检(dogfood)· 无上次 HEALTH.md 基线 · 九科全量。

### 一 · 诊断

总评:**D+**(②③④ 三科 ❌ 从 D 起算 · 全部处方已带分诊建议 → +)

| 科 | verdict | 摘要 |
|---|---|---|
| ① 结构 | ✅ | `docs-cockpit lint`:0 error · 0 warn · 0 hint(17 module · 121 subtask) |
| ② 关联 | ❌ | 覆盖率 121/121=100% · 死锚 0 · 方法3 抽检 41 条(风险优先):✅21 ⚠️3 ❌17 → accurate 51% |
| ③ 新鲜 | ❌ | 近 14 天 146/192 锚指向变更文件(首检全列嫌疑)· 抽验实锤 17 wrong · 0 status 矛盾 |
| ④ 覆盖 | ❌ | 孤儿 plan 12 篇 · v1.0/v1.1 工作 0 module 0 sprint-plan · 0-anchor subtask 0 |
| ⑤ 一致 | ⚠️ | depends_on↔blocks 单边 10 处(schema.md 注明 informational · 按 warn 计)· V0.19 plan status 过时 |
| ⑥ 代码质量 | ✅ | pytest 289 passed(5.45s · 与 CI 同源)· ruff/mypy 未配置 → N/A |
| ⑦ 缺陷 | ✅ | TODO/FIXME 命中均为 lint 实现假阳性 · 0 skip/xfail · 0 裸 except |
| ⑧ 生产就绪 | ✅ | 0 secret · 0 绝对路径 · 0 调试残留(print 均为 CLI 正当输出)· stub 为文档化 MVP 特性 |
| ⑨ 架构 | ⚠️ | build↔cli 双边环(lazy + 注释缓解)· build.py 960 行逼近线 · schema.py 1755 行入台账 |

**核心诊断一句话**:机器可验的死规则面全绿(lint/测试/死锚/secret),但**认知面失修**——两个根因撑起三科 ❌:

1. **行号锚没有跟着代码长大**(②③ ❌ 的共同根因):17 条 ❌ 锚全部是 v0.10-0.14 时代写定的行号,schema.py(166→1755 行)、build.py(v1.1 +32 行 @490)、cli.py(1.1 -24 行)、paths.py、index.html.tmpl 多轮增删后从未重锚定。渲染器只验文件存在,行内漂移不可见——其中两条(cli.py:181-205、prompt.py:130-237)甚至行尾越界 EOF 仍报健康,暴露机器检测缺口(RX-007)。
2. **看板内容停在 v0.14 时代**(④ ❌ 的根因):v1.0 pivot 与 v1.1 health 的工作没有回写 module/sprint 体系,12 篇 plan 成为孤儿。

抽检说明:样本 41 条 = 31 条行号锚(全量 · drift 风险最高的子集)+ 10 条 doc 锚(CHANGELOG 版本段 + references/schema.md 整文件,机器 resolve 通过 + 语义对版本号吻合,全 ✅)。51% accurate 是**风险优先样本**的命中率,不是全量 192 锚的无偏估计——未抽的约 150 条以 CHANGELOG 历史锚为主,预期健康。

### 二 · 处方(按伤害排序:错 anchor > 机器盲区 > 覆盖缺口 > 规范瑕疵)

#### RX-001 · M01 行号锚 6 条漂移重锚定 · severity: high · bucket: sprint
- 根因:M01 行号锚写定于 v0.10-0.11,build.py 经 v1.1 health 块插入(2ec300f · 490 行处 +32 行)、schema.py 多轮增长后行号整体位移;渲染器只验文件存在抓不到行漂移
- anchor:docs/spec/module/M01-build-engine.md → 新位置 build.py:534-555 / 698-714 · schema.py:1156-1196 · paths.py:586-644(均已按方法 3 预演)
- 修法:见 frontmatter fix 字段的逐条对照表;每条改前重读确认,改后 `docs-cockpit render` 验证
- module:M01

#### RX-002 · M04 行号锚 5 条漂移重锚定 · severity: high · bucket: sprint
- 根因:schema.py 在锚写定后插入 v0.16 lint 段 / v0.19 sprint-plan 段 / v1.1 health 校验段,原 152-541 区间内容易主;prompt.py v1.0 裁剪后 206 行,锚 130-237 行尾越界
- anchor:docs/spec/module/M04-author-skill.md → schema.py:106-163 · 1369-1381 · 1137-1196 · prompt.py:39
- 修法:见 frontmatter fix 字段;改后 render 验证
- module:M04

#### RX-003 · M07 锚改指 state.json sidecar 现位置 · severity: high · bucket: sprint
- 根因:同 RX-001(health 块顶偏);M07 本体 v1.0 已删,锚的幸存指向物是 state.json sidecar
- anchor:docs/spec/module/M07-mcp-server.md → build.py:684-697
- 修法:单条改锚;改后 render 验证
- module:M07

#### RX-004 · M09 锚 3 条漂移 · severity: high · bucket: sprint
- 根因:cli.py 1.1 删 build 别名后缩至 182 行(锚 181-205 越界);tmpl 增长至 5226 行(锚 1697-1706 现为 CSS)
- anchor:docs/spec/module/M09-sync-status.md → cli.py:129-156 · tmpl:2066-2070 + 5163-5187
- 修法:见 frontmatter fix 字段;改后 render 验证
- module:M09

#### RX-005 · M11 锚 2 条漂移 · severity: high · bucket: sprint
- 根因:paths.py 追加 doc-ref resolver 段后目标函数下移约 160-190 行
- anchor:docs/spec/module/M11-schema-consistency.md → paths.py:606-624 · 484-520
- 修法:两条改锚;改后 render 验证
- module:M11

#### RX-006 · M12 锚 2 条漂移 · severity: high · bucket: sprint
- 根因:同 RX-002(schema.py 增长);heading regex 区从 152-168 下移至 1117-1132
- anchor:docs/spec/module/M12-parser-robustness.md → schema.py:1117-1126 · 1127-1132
- 修法:两条改锚;改后 render 验证
- module:M12

#### RX-007 · 行尾越界静默截断(机器盲区) · severity: medium · bucket: sprint
- 根因:`_read_code_lines` 只警 `start > total`,`end > total` 被静默 clamp——本轮两条越界漂移锚 exists=true、warning 空,死锚清单全绿
- anchor:docs_cockpit/paths.py:383-400
- 修法:end > total 时 warning 置 "end line {end} > file total {total} · anchor may be stale",preview 行为不变;补单测 + pytest + render 验证
- module:M01

#### RX-008 · v1.0/v1.1 工作入板 · severity: medium · bucket: backlog
- 根因:v1.0/v1.1 工作以会话任务清单推进未回写看板;12 篇 plan 孤儿、sprint 停在 0.14
- anchor:docs/plans/P-skill-first-pivot.md · docs/plans/P-v1.1-health-check.md(整文件)
- 修法:走 docs-cockpit-build 对话决策:立 v1.0/v1.1 module 卡 + sprint-plan,孤儿 plan 分级挂回;完成后 render 验证孤儿清零

#### RX-009 · V0.19 sprint-plan status 过时 · severity: low · bucket: now
- 根因:v0.19 发版只更新 CHANGELOG 未回写 plan frontmatter
- anchor:docs/plans/V0.19-agile-version-planning.md:5
- 修法:status: in-progress → done;改后 render 验证

#### RX-010 · depends_on↔blocks 镜像策略 · severity: low · bucket: backlog
- 根因:依赖边单向手写 · schema.md:142 注明 currently informational,从未要求镜像 · 累计 10 处单边
- anchor:references/schema.md:142
- 修法:设计决策(规范要求镜像 + lint vs render 端推导),建议并入 dependency graph 特性立项

### 三 · 行动规划(逐桶呈用户确认)

| 桶 | 处方 | 落地动作 |
|---|---|---|
| 立即修 | RX-009 | 一行级零风险 · 下次 rebuild 对话决策 phase 当场改 |
| 本 sprint | RX-001~006 · RX-007 | 锚修复:逐 module 改 @code 锚(对照表在各 RX fix 字段);RX-007 转 subtask 带 @code:docs_cockpit/paths.py:383-400 挂 M01 |
| backlog | RX-008 · RX-010 | RX-008 起草入板计划(走 build skill 对话);RX-010 并入 dependency graph 立项 |
| 观察 | — | ① M10-fa6a5e 锚 prompt.py:80-106(⚠️ partial · 模块已历史化 · 中置信)下次体检复点;② build.py 960 行趋势(逼近 1000 ⚠️ 线);③ 未抽的约 150 条 CHANGELOG 历史锚滚动覆盖 |
| 接受 | — | schema.py God file 入台账(见 accepted_debts · 复审 2026-08 · **注意:已从任务预估的 ~1490 行涨至 1755 行,越过 1500 ❌ 线,复审时若 md_merge.py 拆分仍未排上建议转处方**) |

复查节奏建议:**治疗型** —— RX-001~006 + RX-009 全部是低风险机械修复,治完即 rebuild 快检复查;v1.1 发布后 30 天内做一次深检,滚动覆盖本轮未抽的历史锚。选择理由:本轮 ❌ 全部根因明确且修法机械,不需要周期等待;真正的周期项(台账复审)已挂 2026-08。

<details>
<summary>台账(accepted_debts · 1 条)</summary>

| item | reason | review |
|---|---|---|
| schema.py God file(体检时点 1755 行) | post-1.0 已排期拆 md_merge.py(CLAUDE.md 架构节明示) | 2026-08 |

</details>
