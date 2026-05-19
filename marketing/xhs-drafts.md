# docs-cockpit 小红书推广文案（3 版）

> 目标：vibe coding 群体 · 引导评论/私信增加互动 · 不放外链避免限流

---

## 版本 1：痛点共鸣型（最稳，推荐首发）

**标题**（任选）：
- 和 AI 聊了一下午，桌面多了 47 个 md 文件，我崩溃了
- vibe coder 的真实噩梦：docs 目录像被狗刨过
- 跟 Claude 写代码爽是真爽，乱也是真乱

**正文**：

做 vibe coding 的姐妹应该都懂这个痛——

跟 Claude / Cursor / Codex 聊到飞起，一个项目下来：
· PRD.md
· DESIGN.md
· module-01.md ~ module-23.md
· 一堆 plan / spec / adr
· 各种"先写下来回头看"的 memo

然后呢？全散在 docs/ 各个角落，**到底哪个模块在做、哪个卡了、哪个已经写完了，我自己都说不清。**

装 Jira？太重。
开 Notion？复制粘贴麻烦还要钱。
心累。

后来我自己写了个开源小工具，**专门给 vibe coder 用**：

扫一遍你 docs 目录下所有 md → 自动生成一个单文件 dashboard（kanban + sprint timeline + 进度条），浏览器双击打开就能看，零依赖。

跟 Claude Code 说一句"帮我把 docs 做成 dashboard"，它自己装、自己跑、自己出图。

现在每天开工第一件事就是看这个面板，**再也没"我上次写到哪了"的失忆时刻**。

已经开源了，纯 Python，MIT 协议，免费用。

⚠️ 小红书放外链容易限流，**评论区扣"1"或私信我"dashboard"**，我把仓库地址发你～

#vibecoding #claudecode #cursor #程序员 #开源项目 #ai编程 #独立开发者 #效率工具 #github

---

## 版本 2：show off 型（带点小炫耀，更适合个人 IP）

**标题**（任选）：
- 自己用 AI 写了个工具，把 vibe coding 的烂摊子收拾干净了
- 给所有 vibe coder 安利一个我自己开源的小工具
- 让 Claude 自动整理它自己生成的 md，真的爽

**正文**：

最近 vibe coding 上瘾，副作用就是——

**docs 目录像被狗刨过。**

几十个 .md 文件躺在那里，我自己都不记得哪个还在写、哪个早废了。

试过 Notion、试过飞书 wiki，都嫌重；
后来索性自己写了个 CLI + Claude Code plugin：

✓ 一条命令扫完所有 md
✓ 按 frontmatter 自动生成 kanban + sprint timeline
✓ 输出一个单文件 index.html，浏览器直接打开
✓ 改 md → 重跑 → 同步，不用学新平台
✓ 跟 Claude 说一句"帮我做个 dashboard"全自动

写出来意外清爽，做完直接开源了（Python + MIT）。

自用大半个月，**最大收获不是"工具多好用"，而是"我又能看清自己在做啥了"**。

vibe coder 的福音真的，谁用谁知道。

想试的，评论区扣"码"或私我"cockpit"，发你 github 地址（小红书放链接容易吞）。

#aicoding #vibecoding #claudecode #开源 #程序员日常 #cursor #独立开发者 #效率提升 #ai工具

---

## 版本 3：故事钩子型（流量上限最高，但需要好封面）

**标题**（任选）：
- 我的 AI 助手最近罢工了，因为我的 docs 目录太乱
- Claude 看完我的项目沉默了十秒……
- 当 AI 都开始嫌我乱

**正文**：

真实故事。

上周我让 Claude 接着上次的活儿继续做，它读完我 docs 目录沉默了十秒，回我：

> "您的项目有 38 个 md 文件、跨 6 个 sprint，建议先理清楚目前状态。"

我：……

它是对的。一个 vibe coding 项目跑久了，**md 文件膨胀的速度比代码还快**——PRD 改三版、模块 spec 各自为政、plan 写完没人回看、adr 落地全靠记忆。

为了让我和 AI 都活下去，我花了三个周末搓了个小工具：

**docs-cockpit** —— 把散落的 md 自动揉成一个 dashboard，HTML 单文件，离线可用。

· 模块按状态分列（没开始 / 计划中 / 进行中 / 卡住 / 完成）
· sprint 时间线一目了然
· 改 md，重跑一行命令，dashboard 自动同步
· Claude Code 用户一句话搞定，连配置都让 AI 写

开源 + MIT 协议，**纯给 vibe coder 用的**。

不放链接怕限流——
**评论区打"想要"或者私我"cockpit"，我发你仓库地址 + 安装教程。**

#vibecoding #claude #cursor #ai编程 #独立开发 #程序员 #开源工具 #github #aiagent

---

## 封面建议（小红书 70% 看封面决定打不打开）

**首选**：dashboard 的截图（kanban 视图最好看），加大字标题，比如：

> 「47 个 md 文件 → 一张 dashboard」
> 「vibe coder 的 docs 救命工具」
> 「让 AI 自己收拾自己生成的烂摊子」

**次选**：对比图——左边一堆杂乱 md 文件 emoji / 截图，右边干净的 dashboard。

**配色**：白底 + 黑字 + 一个亮色（推荐你 dashboard 的主色），不要花。

---

## 发布节奏建议

1. **首发用版本 1**（最安全，痛点最普适），看数据。
2. 3-5 天后用版本 2 或 3 二次曝光，但**别同号连发**——内容相似容易判搬运降权。
3. 黄金时间：工作日 12:00-13:00 / 20:00-22:00；周末 10:00-11:00。
4. 私信回复模板提前准备好：仓库链接 + 一句安装命令 + 一句使用引导（别甩个链接就完事，转化率差）。

---

## 私信回复模板（可直接复制）

> 嗨～仓库地址给你：
> https://github.com/Guohao1020/docs-cockpit
>
> 如果你用 Claude Code，最简单：
> 1. `/plugin marketplace add Guohao1020/docs-cockpit`
> 2. `pip install git+https://github.com/Guohao1020/docs-cockpit.git`
> 3. 重启 Claude Code，跟它说"帮我把 docs 做成 dashboard"
>
> 用别的工具（Cursor / Codex）也可以，README 里有手动复制 skill 的步骤。
>
> 用得顺手的话可以帮我点个 ⭐️，有问题随时回我～
