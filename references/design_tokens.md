# Design tokens · 颜色与排版

> 读这份文档的时机:用户想改 cockpit 的视觉风格(品牌色、字体、版心、看板色调),或者要 vendor marked.js / highlight.js 做离线部署。

## 默认设计基调

cockpit 的默认 token 来自 HP-style 设计语言:

- **canvas 纯白**(`#ffffff`)+ **ink 黑**(`#1a1a1a`)的两极对比
- **单 primary 蓝**(`#024ad8`)做强调色 · 不混用多色
- **8px / 16px rounded** · 大圆角留给 hero 与 KPI bar
- **Inter** 显示字体 + **JetBrains Mono** 等宽

侧边栏永远是 ink 暗色,主区永远是 canvas 白。看板四色 KPI 卡顶部的 accent 用克制的语义色(绿 / 蓝 / 灰)。

## 全部 CSS 变量

模板里 `:root` 暴露的全部 token。前缀 `--colors-` / `--spacing-` / `--rounded-` / `--elev-` / `--font-`:

### Colors

```
--colors-primary           #024ad8   HP blue · 主强调
--colors-primary-bright    #296ef9   hover / focus 亮态
--colors-primary-deep      #0e3191   pressed / 标题深态
--colors-primary-soft      #c9e0fc   info banner / sidebar pill 浅底
--colors-on-primary        #ffffff   primary 上的文字 / icon

--colors-canvas            #ffffff   main pane 底色
--colors-paper             #ffffff   卡片底色(可改 #fafafa 做层次)
--colors-cloud             #f7f7f7   subtle 灰底(代码块 inline / kpi-bar gap)
--colors-fog               #e8e8e8   弱 border · progress track
--colors-steel             #c2c2c2   placeholder / disabled
--colors-hairline          #e8e8e8   表格 / 卡片 border

--colors-bloom-coral       #ff5050   warn 强调(未用)
--colors-bloom-rose        #f9d4d2   danger banner 底
--colors-bloom-deep        #b3262b   missing chip · CDN failure
--colors-bloom-wine        #5a1313   danger 文字

--colors-storm-mist        #8ebdce   未启用
--colors-storm-sea         #7fadbe   未启用
--colors-storm-deep        #356373   RFC 类 group icon

--colors-ink               #1a1a1a   sidebar / footer 底 + 大字
--colors-ink-deep          #000000   wordmark
--colors-ink-soft          #292929   未启用
--colors-on-ink            #ffffff   ink 上的文字
--colors-charcoal          #3d3d3d   次要正文(em / blockquote)
--colors-graphite          #636363   meta / breadcrumb / 三级文字
```

### Spacing

```
--spacing-xxs   4px
--spacing-xs    8px
--spacing-sm    12px
--spacing-md    16px
--spacing-lg    20px
--spacing-xl    24px
--spacing-xxl   32px
--spacing-section  80px
```

### Rounded

```
--rounded-none  0
--rounded-xs    2px
--rounded-sm    3px
--rounded-md    4px
--rounded-lg    8px
--rounded-xl    16px
--rounded-pill  9999px
```

### Elevation

```
--elev-1   0 0 0 1px var(--colors-hairline)
--elev-2   0 2px 8px rgba(26, 26, 26, 0.08)
--elev-3   0 8px 24px rgba(26, 26, 26, 0.12)
```

### Fonts

```
--font-display   'Inter', Arial, system-ui, sans-serif
--font-mono      'JetBrains Mono', ui-monospace, Menlo, monospace
```

## 在 YAML 配置里覆盖

```yaml
design:
  colors:
    primary: "#3b82f6"
    primary_deep: "#1d4ed8"
    primary_bright: "#60a5fa"
    primary_soft: "#dbeafe"
    bloom_deep: "#b91c1c"
```

注意 key 用 underscore(`primary_deep`),build 时转成 `--colors-primary-deep`。任何 `--colors-<name>` token 都可覆盖。

实现细节:覆盖被追加在 `:root` 末尾,CSS 后定义同名变量优先,所以**不会破坏前端 JS 逻辑**。

## 整套换皮 · 例子

### 暗色品牌(Linear / Vercel 风)

```yaml
design:
  colors:
    canvas: "#0a0a0a"
    paper: "#111111"
    cloud: "#1a1a1a"
    fog: "#262626"
    hairline: "#262626"
    ink: "#fafafa"
    ink_deep: "#ffffff"
    on_ink: "#0a0a0a"
    charcoal: "#a3a3a3"
    graphite: "#737373"
    primary: "#5b8def"
    primary_deep: "#3f6fd1"
    primary_bright: "#7daaff"
```

> 注:暗色模式需要同时翻 canvas + ink + on-ink 三组 token。光改 primary 不够。本 skill 默认只测过浅色 · 暗色没经过严格测试 · 用户接受 "差不多对了" 的程度即可。

### 暖色(Stripe-orange 风)

```yaml
design:
  colors:
    primary: "#ff6b35"
    primary_deep: "#c0392b"
    primary_bright: "#ff8c66"
    primary_soft: "#ffe5d9"
```

只换 primary 三件套就有明显效果,其他可不动。

## 改 typography

字体不在 YAML 暴露范围内 · 要换字体直接编辑 `docs_cockpit/templates/index.html.tmpl`:

1. 顶部的 Google Fonts `<link>` 改成你要的 family
2. `:root` 里 `--font-display` / `--font-mono` 改成新 family 名

类似的硬要改 spacing 节奏或 rounded 半径,直接改 template。

## Offline / vendored mode · 无网部署

默认 build artifact 在打开时从 jsdelivr CDN 拉:

- marked.js v12
- highlight.js v11 core + 9 种语言
- highlight.js github theme CSS
- Google Fonts Inter + JetBrains Mono

如果用户的部署环境无法访问外网(企业内网 / 隔离环境 / 离线笔记本),build artifact 顶部会显示 `⚠️ marked.js / highlight.js CDN 加载失败` 红 banner,文档视图 fallback 到 `<pre>` 纯文本。

要做 offline mode,得在 build 阶段 vendor 这些资源:

1. **下载 marked.min.js + highlight.min.js + github.min.css + 字体 woff2**
2. **放到 `docs/_assets/` 之类的子目录**
3. **改 template 的 `<script src>` / `<link href>` 指向本地相对路径**(`./_assets/marked.min.js`)

当前 build 不自动 vendor — 这是未来 sprint 的事(在 M1.2 之前不阻塞主流程)。如果用户现在就要,临时方案:

```bash
mkdir -p docs/_assets
curl https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js -o docs/_assets/marked.min.js
curl https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/core.min.js -o docs/_assets/hljs-core.min.js
# ... 同样下载其他语言 + CSS + 字体
```

然后手工 sed 改 `docs/index.html` 的 src · 但要记得这会被下次 build 覆盖。正确做法是改 template,然后 build 出来就自带本地 src。

## 看板状态色 · 5 种 status

dashboard 的 Kanban 列、status chevron 等用了一组与 token 平行的状态色:

```
not-started   #9ca3af  灰
planned       #6366f1  紫
in-progress   #2563eb  蓝(对齐 primary 但偏深)
blocked       #dc2626  红
done          #059669  绿
deferred      #d97706  琥珀
```

这些颜色硬编码在 template 的 JS 常量 `STATUS_COLOR` 里 + CSS 里 `.s-<status>` 类。当前**不在 YAML 暴露范围**。如果用户的状态色与品牌冲突,要在 template 里改。

未来扩展点(还没做):把 STATUS_COLOR 也作为占位符注入,可在 YAML 里写。
