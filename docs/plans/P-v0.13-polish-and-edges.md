---
id: P-v0.13
type: plan
title: "v0.13 · DX polish + schema consistency + edge cases"
status: planned
sprint: "0.13"
progress: 0
desc: "把 v0.11/v0.12 dogfood 累积的 maintenance debt 一次清完 · 4 个 module · 不引大功能 · 让基本盘更稳"
prd_ref: "v0.12 release notes · v0.13 候选 backlog"
docs:
  - { title: "v0.11 driver-seat plan",      path: "docs/plans/P-v0.11-driver-seat.md" }
  - { title: "AI-augmented precision plan", path: "docs/plans/P-v0.11-ai-augmented-precision-alpha7-2026-05-18.md" }
depends_on: []
---

# Plan · docs-cockpit v0.13 · DX polish + schema consistency + edge cases

Generated 2026-05-19 · Repo: docs-cockpit (MIT) · Status: **PLANNED**

## §0 · 角色定位

v0.11 / v0.12 一气呵成把 driver-seat 4 件大事(W1 schema + split-view UI + W3 prompts + AI 模式 1+2+3)全部 ship。dogfood 自身从「项目状态展示器」升级到「AI 协作驾驶舱」。

代价:跨 12 个 alpha + 7 个 patch · 累积了 4 类 maintenance debt:
1. **Schema 不一致** · `code_anchors[].path` 是 raw 串(含 :lines)· `doc_anchors[].raw` 也是 raw 串 · 但叫法不同 · apply-patch 重序列化时踩坑(0.11.2 修了渲染 · 没修字段命名)
2. **Parser brittleness** · `## §4 · 待办` 不被识别(只接受 `## 4 · 待办` / `## 待办`)· M08/M09/M10 dogfood 实拍过 0 subtask 的 bug
3. **Stub DX** · M09 `--from-browser` 留 stub 报错 · 用户得手动导出 JSON · v0.12 ship 时承诺 v0.13 兑现
4. **CSS time bomb** · v0.12.1 修过 `.split-page[hidden]` specificity 失效 bug · 类似 author CSS vs UA `[hidden]` 的撞 specificity 问题可能还有

v0.13 **不引大功能** · 把这 4 类 debt 清完 · 让 v0.11/v0.12 的承诺真正稳定。

## §1 · Problem Statement

具体表现 · 都来自实际 dogfood 反馈:

**P1 · Schema 字段命名不一致**(apply-patch 暴露)
- `code_anchors[i].path` = "docs_cockpit/prompt.py:130-191"(含 lines)
- `code_anchors[i].lines` = "130-191"
- `doc_anchors[i].raw` = "CLAUDE.md:88-100"(含 lines)
- `doc_anchors[i].path` = "CLAUDE.md"(clean)

template 渲染 `{{ ca.path }}:{{ ca.lines }}` → `:lines:lines` 重复 · 0.11.2 patch 改 `{{ ca.path }}` 兜底 · 但根本问题是 `code` shape 没 clean separation。下游 standup / portfolio / mcp_server 自己消费这些字段时也会踩同样坑。

**P2 · Subtask section heading regex 限死**(parser 暴露)
当前 `_SUBTASK_SECTION_RE`:`^##\s+(?:\d+\s*[·.\-]?\s*)?(?:待办|TODO|...)\b`。
- ✅ `## 待办` / `## 3 · 待办` / `## TODO` / `## Subtasks`
- ❌ `## §4 · 待办` / `## §3.2 · 待办`(section 号带 § 前缀)
- ❌ `### 待办`(三级 heading)
- ❌ 复数空格 / tab(`##\t待办`)

M08/M09/M10 实拍过这个 bug · 我手工把 `## §4 · 待办` 改成 `## 4 · 待办` 来 work around · v0.13 应该让 parser 更宽容。

**P3 · `--from-browser` stub 报错**(M09 留的 v0.13 ticket)
当前 `docs-cockpit sync-status --from-browser chrome` 直接报错让用户改用 `--import`。Chrome LevelDB + Firefox SQLite parsers 是真活 · v0.13 兑现。

**P4 · CSS specificity 隐 bug**(可能不止 split-page 一处)
0.12.1 修过 `.split-page { display: grid }` vs UA `[hidden]` 同 specificity 的 author CSS winning 问题。模板里类似的 `display: block/grid/flex` + 同 element 用 `hidden` 属性的组合可能还有。需要 audit + 加 `[hidden] { display: none !important; }` 兜底规则。

## §2 · What Makes This Cool

v0.13 是 docs-cockpit 第一个**无新功能** release。表面看「就是 maintenance」· 实际是产品成熟度的转折点:

- 下游 Sourcery / bastion 跑 v0.11/v0.12 时已经 dogfood 这些 bug · v0.13 帮他们彻底 unblock
- 让 0.11/0.12 的「driver-seat 模式 1/2/3」承诺**真的稳** · 不是「能用但有边角问题」
- 给 schema / parser / CSS 加 audit pattern · v0.14+ 加新功能时不再踩同类坑

## §3 · Constraints

- **完全向后兼容** · 不能破 v0.12 用户的 yaml / MD / state.json / CLI 接口
- **Schema 加字段 OK · 改/删现有字段不 OK** · `ca.path` 字段语义不能动(stability contract §10.2)· P1 的修法只能是**加** `ca.path_only` 之类新字段 · old code 继续 work
- **Parser 放宽 OK · 不能收紧** · `## 4 · 待办` 不能停止识别 · 只能加新接受
- **测试覆盖必须先于实施** · 每个 module 至少一个 unit test cover 现有行为 · 改完跑回归

## §4 · Approaches Considered

### Approach A · 全部 patch level(0.12.2 / 0.12.3 / ...)
单点小修 · 每个 bug 一个 patch tag。
- ✅ release 频繁 · 下游能立刻拿
- ❌ CHANGELOG 噪音 · 12 个 alpha 后再加 6 个 patch 像「永远在改」

### Approach B · 一个 minor(0.13.0 一次性)✅ CHOSEN
按 sprint 整体规划 + 一次性 release · 跟 v0.11/v0.12 节奏一致。
- ✅ release notes 写清楚「v0.13 = polish」叙事
- ✅ schema 加字段 / SKILL.md 改一起走 minor cache invalidation · 不分散
- ❌ 下游要等 ~1-2 周(可接受)

### Approach C · 拆成两个 minor(0.13 = schema/parser · 0.14 = DX/CSS)
- ✅ 每个 release 主题更聚焦
- ❌ 工程量重复(两轮 dogfood / CI / release 仪式)· v0.13 4 个 module 工作量本来就只够一个 minor

## §5 · Recommended Approach (B · 4 module 一个 minor)

### §5.1 · M11 · Schema consistency cleanup

**问题**:`code_anchors[].path`(raw 含 lines)vs `doc_anchors[].raw`(raw)+ `doc_anchors[].path`(clean)双重命名。

**修法**(plan-eng-review 2A stability contract 守住):
- 加 `code_anchors[].path_only`(clean 路径 · 无 lines)· 跟 `doc_anchors[].path` 语义对齐
- 保留 `code_anchors[].path`(raw · 不动 · 老 template / 下游不破)
- 给 `doc_anchors[]` 加 `raw_with_anchor` alias = `raw`(让命名对称 · 未来 v0.14 可以 deprecate `raw` 然后 v0.15 remove)
- author skill §3.1.2 / §3.1.3 把这个 dual-name 关系写清

**测试**:
- `tests/unit/test_paths.py` 加 `code_anchors[].path_only` field 校验
- 渲染 4 个 subtask template + refine.md.j2 · 验证不再有 `:lines:lines` 重复

**工程量**:~半天

### §5.2 · M12 · Parser robustness

**问题**:`_SUBTASK_SECTION_RE` 只接受窄子集 · `## §4 · 待办` / `### 待办` / 复数空格都不识别。

**修法**:
- regex 放宽:`^#{2,6}[\s\t]+(?:[§\d]+[\s\t]*[·.\-]?[\s\t]*)?(?:待办|TODO|...)\b`
  - `^##` → `^#{2,6}`(接受 ### / #### 等)
  - `\s+` → `[\s\t]+`(显式 tab)
  - `\d+` → `[§\d]+`(接受 § 前缀)
- 同样的放宽 also for `_DOCS_SECTION_RE`(对称)
- 加 12 个 fixture string 跑 `extract_subtasks_from_body` · 全 cover

**测试**:
- `tests/unit/test_schema.py` 加 12+ heading 形式 fixture
- dogfood M08/M09/M10 不用再手工去 § 前缀

**工程量**:~1-2 小时

### §5.3 · M13 · `--from-browser` browser profile reader

**问题**:M09 留的 stub · 用户得手动 Export → import。

**修法**:
- Chrome / Edge:LevelDB 读 `~/Library/Application Support/Google Chrome/Default/Local Storage/leveldb/`(macOS)/ `%LOCALAPPDATA%\Google\Chrome\User Data\Default\Local Storage\leveldb`(Windows)
  - 用 `plyvel` 或 `lmdb` 之类轻量 Python LevelDB 库 · optional dep `[browser]` extra
- Firefox:SQLite 读 `~/Library/Application Support/Firefox/Profiles/*.default-release/webappsstore.sqlite`
  - 用 stdlib `sqlite3` · 不加新 dep
- `--from-browser <name>` 找对应 profile · 解析 localStorage[STORAGE_KEY] · 喂给现有 `parse_overrides` · 走同样 merge_to_md 路径

**测试**:
- mock 个 fixture LevelDB / SQLite · 单测覆盖
- 集成测试可选(平台依赖)

**工程量**:~1 天(LevelDB 解析是主要工作)

### §5.4 · M14 · CSS time-bomb audit + UX polish

**问题**:
- 0.12.1 修过的 `.split-page[hidden]` specificity bug 可能不止一处
- subtask doc anchor 点击后右栏渲染 sliced content · 但用户在原文里找上下文时不知道这段是哪个 section(没显 path:lines 位置标识)

**修法**:
- audit pass · grep 所有 `display: (grid|flex|block)` 加上对应元素 ID/class 是否在 HTML 用 `hidden` 属性
- 加全局兜底:`*[hidden]:not(.split-page) { display: none !important; }` 之类 safety net
- subtask doc anchor preview 加 header「`<path>:<lines>` from anchor #N」让定位清晰
- placeholder 文案 audit(还有几个 alpha 期遗留?)

**测试**:
- `tests/integration/test_dashboard_render.py` · pytest-playwright 跑一次 dashboard root + #/module/X · 验关键元素 visible / hidden 正确

**工程量**:~半天

## §6 · Distribution Plan

- alpha.1 · M11 schema cleanup + tests · 内部 release · dogfood Sourcery 一遍
- alpha.2 · M12 parser robustness + tests · 同上
- alpha.3 · M13 `--from-browser` + Chrome reader · macOS / Windows dual
- alpha.4 · M14 CSS audit + UX polish
- 0.13.0 · 4 文件 version bump + CHANGELOG aggregate + push tag

## §7 · Success Criteria

- 4 module 全部 done · 100%
- 198 tests + 新增 ~30 tests = ~230 测试全过
- Sourcery / bastion `docs-cockpit upgrade` 拿 0.13.0 → 老 build 不破 · 新 feature 可用
- `## §N · 待办` 风格的 module body 不用 work around 也能被 parser 识别
- `--from-browser chrome` 在 macOS + Windows 实测能拉出 localStorage

## §8 · Open Questions (deferred · not blocking)

- 是否做 MCP SSE transport(stdio fine for now · SSE 是远程场景)· 暂不
- doc anchor 行号高亮(`path:88-100` 切完后高亮那 13 行)· 暂不 · plan §6.4 sub-plan §3.5 都标 unreliable
- `subtasks.thresholds` 走 frontmatter 配置 override(M10 suggest 三个数字)· 加进 M11 schema cleanup 一起做

## §9 · Next Steps

implementation 按 §5.1-§5.4 顺序推 · 每个 module 一个 alpha · alpha.4 之后 0.13.0 finalize。可以一次性都做 · 也可以分多次。
