# README Marketing Brand Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh docs-cockpit's README, landing page, and project-owned brand assets around the approved A+B visual direction: Radar Flight Deck for brand identity and Operational Kanban for product proof.

**Architecture:** Keep the site as a static single HTML file and store all project-owned visuals under `site/assets/**`. README files reference repository-local assets using relative Markdown image paths, while the landing page references `assets/**` paths relative to `site/index.html`.

**Tech Stack:** Markdown, static HTML/CSS/JS, Python `http.server` for local preview, built-in image generation for raster assets, pytest for regression verification.

---

## File Structure

- Modify `.gitignore` to exclude `.superpowers/` brainstorming artifacts.
- Create `site/assets/brand/` for logo, hero background, and Open Graph cover.
- Create `site/assets/screenshots/` for dashboard/product proof images.
- Modify `README.md` as the English primary README.
- Modify `README.zh-CN.md` as the structurally aligned Chinese README.
- Modify `site/index.html` as the static landing page.
- Modify `plugins/docs-cockpit/README.md` and `plugins/docs-cockpit/README.zh-CN.md` only if the marketplace-distributed README must stay in sync.
- Run existing tests; no production Python behavior should change.

---

### Task 1: Local Artifact Hygiene

**Files:**
- Modify: `.gitignore`

- [x] **Step 1: Add `.superpowers/` to ignored local artifacts**

Add this block near the existing local worktree ignores:

```gitignore
# Superpowers brainstorming companion artifacts
.superpowers/
```

- [x] **Step 2: Verify brainstorming files are ignored**

Run:

```powershell
git status --short --ignored .superpowers
```

Expected: `.superpowers/` appears as ignored (`!! .superpowers/`) and is not staged.

- [x] **Step 3: Commit hygiene change**

Run:

```powershell
git add .gitignore
git commit -m "Ignore local brainstorming artifacts" -m "将 Superpowers 视觉讨论产生的 .superpowers/ 本地文件排除在版本控制外，避免预览草稿误提交。"
```

---

### Task 2: Generate and Store Brand Assets

**Files:**
- Create: `site/assets/brand/docs-cockpit-logo.png`
- Create: `site/assets/brand/docs-cockpit-logo-mark.png`
- Create: `site/assets/brand/docs-cockpit-hero-bg.png`
- Create: `site/assets/brand/docs-cockpit-og-cover.png`
- Create: `site/assets/screenshots/dashboard-kanban.png`
- Create: `site/assets/screenshots/workflow-overview.svg`

- [x] **Step 1: Create asset directories**

Run:

```powershell
New-Item -ItemType Directory -Force site\assets\brand, site\assets\screenshots
```

- [x] **Step 2: Generate the Radar Flight Deck logo assets**

Use the built-in image generation tool with this prompt for the main logo:

```text
Use case: logo-brand
Asset type: open-source developer tool logo
Primary request: Create a clean logo for "docs-cockpit", a skill-first project cockpit for AI coding agents.
Subject: a vector-friendly radar/cockpit mark combining a circular radar sweep, markdown document shape, and small project nodes.
Style/medium: modern developer-tool brand mark, crisp geometric shapes, high contrast, minimal detail.
Composition/framing: centered logo mark with optional "docs-cockpit" wordmark, generous padding.
Color palette: deep navy, electric blue, cyan, small green status accent.
Constraints: readable at small sizes, no tiny text except the exact wordmark if included, no mascot, no airplane, no photorealism, no watermark.
Avoid: clutter, gradients that obscure the shape, illegible text, generic rocket imagery.
```

Save the selected output as `site/assets/brand/docs-cockpit-logo.png`. Crop or create a mark-only sibling as `site/assets/brand/docs-cockpit-logo-mark.png`.

- [x] **Step 3: Generate the hero background and OG cover**

Use the built-in image generation tool with this prompt:

```text
Use case: ads-marketing
Asset type: landing page hero background and social cover
Primary request: A polished AI cockpit control room visual for docs-cockpit.
Scene/backdrop: dark developer cockpit interface with a project radar, subtle kanban panels, markdown document nodes, and schema validation indicators.
Subject: abstract product UI panels, radar sweep, project status cards, no people.
Style/medium: high-end SaaS/developer-tool hero artwork, semi-realistic UI composition, crisp readable shapes, not sci-fi fantasy.
Composition/framing: wide landscape, strong visual detail on the right and lower half, clean negative space on the left for headline text.
Lighting/mood: dark navy control surface with electric blue/cyan accents and restrained green/orange status lights.
Color palette: deep navy, slate, blue, cyan, small green and amber accents.
Constraints: no readable fake text, no logos, no watermark, no people, no aircraft, no excessive glow.
```

Save the wide final as `site/assets/brand/docs-cockpit-hero-bg.png`. Create or crop a 1200x630 social cover as `site/assets/brand/docs-cockpit-og-cover.png`.

- [x] **Step 4: Create the Operational Kanban product proof image**

Prefer a deterministic static mock or screenshot over another abstract AI image. Create `site/assets/screenshots/dashboard-kanban.png` as a polished product-style kanban dashboard mock with columns `Planned`, `In progress`, `Blocked`, `Done`, visible progress bars, validation chips, and a right-side linked-doc preview. Use real docs-cockpit concepts, not fake SaaS metrics.

- [x] **Step 5: Create workflow diagram SVG**

Create `site/assets/screenshots/workflow-overview.svg` showing this flow:

```text
Install plugin -> SessionStart router -> build/rebuild skill -> docs-cockpit render -> docs/index.html + state.json
```

Keep it simple, with no external fonts and no script tags.

- [x] **Step 6: Validate assets exist and are reasonably sized**

Run:

```powershell
Get-ChildItem site\assets -Recurse | Select-Object FullName,Length
```

Expected: all six assets exist. Raster images should not be zero bytes. Prefer keeping each raster under roughly 2 MB unless visual quality requires more.

- [x] **Step 7: Commit assets**

Run:

```powershell
git add site/assets
git commit -m "Add docs-cockpit brand assets" -m "新增 Radar Flight Deck 品牌图和 Operational Kanban 产品展示图，供 README 与营销页引用。"
```

---

### Task 3: Rewrite README Pair

**Files:**
- Modify: `README.md`
- Modify: `README.zh-CN.md`
- Modify if syncing plugin bundle: `plugins/docs-cockpit/README.md`
- Modify if syncing plugin bundle: `plugins/docs-cockpit/README.zh-CN.md`

- [x] **Step 1: Rewrite `README.md` around the approved structure**

Use this exact section order:

```markdown
# docs-cockpit

<p align="center">
  <img src="site/assets/brand/docs-cockpit-logo.png" alt="docs-cockpit logo" width="520">
</p>

> A skill-first project cockpit for AI coding agents. Turn AI-written markdown into a schema-validated, single-file dashboard.

[badges...]

![docs-cockpit cockpit hero](site/assets/brand/docs-cockpit-og-cover.png)

## Why docs-cockpit
## Quickstart
### Codex
### Claude Code
### CLI fallback
## See It
## How It Works
## Product Tour
## Skill Layer
## State Sidecar
## Philosophy
## Project Anatomy
## Frontmatter Example
## Updating
## Contributing
## Community
## License
```

Keep copy concise. Mention Codex marketplace support as current:

```bash
codex plugin marketplace add Guohao1020/docs-cockpit
codex plugin add docs-cockpit@docs-cockpit
```

- [x] **Step 2: Rewrite `README.zh-CN.md` with matching structure**

Use natural Chinese and keep the same section order as `README.md`. Preserve English technical terms where clearer: `frontmatter`, `state.json`, `render`, `skill-first`, `file://`, `SessionStart`.

- [x] **Step 3: Sync plugin bundle README files if they exist**

Copy the updated README content into:

```text
plugins/docs-cockpit/README.md
plugins/docs-cockpit/README.zh-CN.md
```

Only adjust image paths if needed. Since these files live two directories deeper, use:

```markdown
![...](../../site/assets/brand/docs-cockpit-og-cover.png)
```

- [x] **Step 4: Scan for stale claims and mojibake**

Run:

```powershell
rg -n "0\\.14|v0\\.14|Codex.*roadmap|roadmap.*Codex|鈥|鐨|涓|鍗|馃|鉂" README.md README.zh-CN.md plugins/docs-cockpit/README.md plugins/docs-cockpit/README.zh-CN.md
```

Expected: no matches except intentional historical references in changelog links are not present in README.

- [x] **Step 5: Commit README refresh**

Run:

```powershell
git add README.md README.zh-CN.md plugins/docs-cockpit/README.md plugins/docs-cockpit/README.zh-CN.md
git commit -m "Refresh README product narrative" -m "重写中英文 README，围绕 AI coding 重度用户、Codex/Claude 插件安装、skill-first 工作流和新品牌图进行专业化展示。"
```

---

### Task 4: Refresh Static Marketing Page

**Files:**
- Modify: `site/index.html`

- [x] **Step 1: Update metadata**

Set:

```html
<title>docs-cockpit · A skill-first project cockpit for AI coding agents</title>
<meta name="description" content="Turn AI-written markdown into a schema-validated, single-file project dashboard. docs-cockpit ships Codex and Claude Code plugin workflows, a deterministic Python renderer, and local file:// output.">
<meta property="og:image" content="https://guohao1020.github.io/docs-cockpit/assets/brand/docs-cockpit-og-cover.png">
<meta name="twitter:image" content="https://guohao1020.github.io/docs-cockpit/assets/brand/docs-cockpit-og-cover.png">
```

Update JSON-LD `softwareVersion` to `1.3.1`.

- [x] **Step 2: Redesign hero with Radar Flight Deck background**

Use `assets/brand/docs-cockpit-hero-bg.png` as the hero background. Keep headline and CTAs outside cards:

```text
docs-cockpit
A skill-first project cockpit for AI coding agents.
```

Primary CTA: GitHub. Secondary CTA: Install with Codex.

- [x] **Step 3: Add product proof band**

Add a section immediately after hero with:

```html
<img src="assets/screenshots/dashboard-kanban.png" alt="docs-cockpit dashboard showing kanban cards, validation status, and linked markdown preview">
```

Include concise install tabs or side-by-side command blocks for Codex and Claude Code.

- [x] **Step 4: Update workflow and feature sections**

Remove stale v0.14 language and update features around:

- SessionStart router
- `docs-cockpit-build`
- `docs-cockpit-rebuild`
- `docs-cockpit render`
- schema validation
- `state.json`
- local `file://` dashboard
- `docs-cockpit upgrade`

- [x] **Step 5: Update FAQ and audience text**

Codex must be described as supported now, not roadmap-only. Other agents can remain roadmap/adapter mentions where true.

- [x] **Step 6: Run local preview**

Run:

```powershell
py -3.13 -m http.server 8088 --bind 127.0.0.1 --directory site
```

Open:

```text
http://127.0.0.1:8088/
```

Expected: hero background loads, product image loads, no overlapping text at desktop width.

- [x] **Step 7: Commit site refresh**

Run:

```powershell
git add site/index.html
git commit -m "Refresh marketing landing page" -m "更新营销页定位、视觉层级、Codex 支持状态和 v1.3.1 元数据，使用新的品牌与产品展示资产。"
```

---

### Task 5: Final Verification and Push

**Files:**
- No new source files unless verification reveals a bug.

- [x] **Step 1: Check stale references**

Run:

```powershell
rg -n "0\\.14|v0\\.14|Codex.*roadmap|roadmap.*Codex|softwareVersion\"\\s*:\\s*\"0" README.md README.zh-CN.md site/index.html
```

Expected: no matches.

- [x] **Step 2: Check referenced assets exist**

Run:

```powershell
@(
  'site/assets/brand/docs-cockpit-logo.png',
  'site/assets/brand/docs-cockpit-logo-mark.png',
  'site/assets/brand/docs-cockpit-hero-bg.png',
  'site/assets/brand/docs-cockpit-og-cover.png',
  'site/assets/screenshots/dashboard-kanban.png',
  'site/assets/screenshots/workflow-overview.svg'
) | ForEach-Object {
  if (-not (Test-Path $_)) { throw "Missing asset: $_" }
}
```

Expected: command exits successfully.

- [x] **Step 3: Run tests**

Run:

```powershell
py -3.13 -m pytest tests/ -q
```

Expected: all tests pass.

- [x] **Step 4: Browser verify landing page**

Use the in-app browser at `http://127.0.0.1:8088/` with desktop and mobile widths. Check:

- hero text readable
- images load
- no text overlap
- mobile section flow is readable
- install commands are current

- [x] **Step 5: Review git status**

Run:

```powershell
git status --short --branch
```

Expected: no `.superpowers/` tracked changes. `AGENTS.md` may remain untracked and must not be committed unless explicitly requested.

- [ ] **Step 6: Push main**

Run:

```powershell
git push origin main
```

Expected: `main -> main`.

