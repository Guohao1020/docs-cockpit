# Codex Plugin Marketplace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Codex-native plugin manifest and repo marketplace entry while keeping the existing Claude plugin entry working.

**Architecture:** This is a distribution-layer change. The existing shared `skills/`, `commands/`, and `hooks/` directories remain the source of behavior; new Codex metadata points at those shared assets, and existing Claude metadata stays in place with synchronized versions.

**Tech Stack:** JSON plugin manifests, Markdown documentation, Python package version metadata, Codex CLI marketplace commands, pytest.

---

## File Structure

- Create `.codex-plugin/plugin.json`: Codex-native plugin manifest for docs-cockpit.
- Create `.agents/plugins/marketplace.json`: repo-scoped Codex marketplace catalog.
- Modify `.claude-plugin/plugin.json`: bump version only.
- Modify `.claude-plugin/marketplace.json`: bump version only.
- Modify `docs_cockpit/__init__.py`: bump `__version__`.
- Modify `README.md`: add Codex installation commands before Claude Code commands.
- Modify `README.zh-CN.md`: add matching Chinese Codex installation commands before Claude Code commands.
- Modify `references/operations.md`: make install/upgrade wording account for Codex plus Claude where it currently implies Claude-only.
- Modify `CHANGELOG.md`: add a `1.3.0` release entry dated `2026-06-12`.

## Task 1: Add Codex Plugin Metadata

**Files:**
- Create: `.codex-plugin/plugin.json`
- Create: `.agents/plugins/marketplace.json`

- [ ] **Step 1: Create the Codex manifest**

Create `.codex-plugin/plugin.json` with this content. Keep paths relative to the repository root, matching Codex plugin examples from the current Codex manual.

```json
{
  "name": "docs-cockpit",
  "version": "1.3.0",
  "description": "Skill-first project dashboard: 1 entry router (use-docs-cockpit, auto-injected via SessionStart hook) + 2 flow skills (docs-cockpit-build: create the module-to-doc association system in dialogue; docs-cockpit-rebuild: diagnose drift + refresh + status narratives) + a mechanical render CLI (docs-cockpit render: YAML-frontmatter markdown to single-file Kanban dashboard HTML + state.json). Cognition lives in skills; Python only renders.",
  "author": {
    "name": "Guohao1020"
  },
  "homepage": "https://github.com/Guohao1020/docs-cockpit",
  "repository": "https://github.com/Guohao1020/docs-cockpit",
  "license": "MIT",
  "keywords": [
    "documentation",
    "markdown",
    "aggregator",
    "single-file-html",
    "cockpit",
    "dashboard",
    "kanban",
    "frontmatter",
    "status-tracking",
    "skill-first",
    "codex-plugin",
    "docs-preview"
  ],
  "skills": "./skills/",
  "interface": {
    "displayName": "docs-cockpit",
    "shortDescription": "Skill-first project dashboard from YAML-frontmatter markdown",
    "longDescription": "docs-cockpit bundles routing and workflow skills for building and refreshing a markdown-driven project dashboard. The Python CLI only renders validated markdown into a single-file Kanban dashboard and state.json.",
    "developerName": "Guohao1020",
    "category": "Developer Tools",
    "capabilities": [
      "Interactive",
      "Read",
      "Write"
    ],
    "defaultPrompt": [
      "Set up docs-cockpit for this project.",
      "Render the docs-cockpit dashboard.",
      "Refresh the docs-cockpit associations."
    ],
    "websiteURL": "https://github.com/Guohao1020/docs-cockpit",
    "privacyPolicyURL": "https://github.com/Guohao1020/docs-cockpit",
    "termsOfServiceURL": "https://github.com/Guohao1020/docs-cockpit/blob/main/LICENSE",
    "brandColor": "#2563EB",
    "screenshots": []
  }
}
```

- [ ] **Step 2: Create the repo-scoped marketplace catalog**

Create `.agents/plugins/marketplace.json` with this content. `source.path` is relative to the marketplace root, which is the repository root when Codex adds this repo as a marketplace.

```json
{
  "name": "docs-cockpit",
  "interface": {
    "displayName": "docs-cockpit"
  },
  "plugins": [
    {
      "name": "docs-cockpit",
      "source": {
        "source": "local",
        "path": "./"
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
      },
      "category": "Developer Tools",
      "interface": {
        "displayName": "docs-cockpit",
        "shortDescription": "Skill-first project dashboard from markdown",
        "developerName": "Guohao1020"
      },
      "version": "1.3.0"
    }
  ]
}
```

- [ ] **Step 3: Validate JSON syntax**

Run:

```powershell
@'
import json
from pathlib import Path
for p in [Path(".codex-plugin/plugin.json"), Path(".agents/plugins/marketplace.json")]:
    json.loads(p.read_text(encoding="utf-8"))
    print(f"OK {p}")
'@ | py -3.13 -
```

Expected:

```text
OK .codex-plugin\plugin.json
OK .agents\plugins\marketplace.json
```

- [ ] **Step 4: Commit metadata**

```bash
git add .codex-plugin/plugin.json .agents/plugins/marketplace.json
git commit -m "feat: add codex plugin marketplace metadata"
```

## Task 2: Bump Release Metadata

**Files:**
- Modify: `docs_cockpit/__init__.py`
- Modify: `.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `.codex-plugin/plugin.json`
- Modify: `.agents/plugins/marketplace.json`

- [ ] **Step 1: Update Python package version**

In `docs_cockpit/__init__.py`, change:

```python
__version__ = "1.2.0"
```

to:

```python
__version__ = "1.3.0"
```

- [ ] **Step 2: Update Claude plugin version**

In `.claude-plugin/plugin.json`, change:

```json
"version": "1.2.0"
```

to:

```json
"version": "1.3.0"
```

- [ ] **Step 3: Update Claude marketplace version**

In `.claude-plugin/marketplace.json`, change the plugin entry:

```json
"version": "1.2.0"
```

to:

```json
"version": "1.3.0"
```

- [ ] **Step 4: Confirm Codex versions are already `1.3.0`**

Run:

```powershell
@'
import json
from pathlib import Path
checks = {
    "codex manifest": json.loads(Path(".codex-plugin/plugin.json").read_text(encoding="utf-8"))["version"],
    "codex marketplace": json.loads(Path(".agents/plugins/marketplace.json").read_text(encoding="utf-8"))["plugins"][0]["version"],
}
for name, version in checks.items():
    print(f"{name}: {version}")
'@ | py -3.13 -
```

Expected:

```text
codex manifest: 1.3.0
codex marketplace: 1.3.0
```

- [ ] **Step 5: Commit release metadata**

```bash
git add docs_cockpit/__init__.py .claude-plugin/plugin.json .claude-plugin/marketplace.json .codex-plugin/plugin.json .agents/plugins/marketplace.json
git commit -m "release: bump metadata for codex marketplace"
```

## Task 3: Update Installation Documentation

**Files:**
- Modify: `README.md`
- Modify: `README.zh-CN.md`
- Modify: `references/operations.md`

- [ ] **Step 1: Update the English README installation section**

Replace the current `## Installation` section opening through the Claude Code command block with:

````markdown
## Installation

### Codex

```bash
# in Codex CLI
codex plugin marketplace add Guohao1020/docs-cockpit
```

Then open the Codex plugin directory, choose the `docs-cockpit` marketplace, and install the `docs-cockpit` plugin. In the Codex app, open **Plugins** after adding the marketplace and install it from there.

### Claude Code

```bash
# inside Claude Code
/plugin marketplace add Guohao1020/docs-cockpit
/plugin install docs-cockpit@docs-cockpit
```
````

Keep the paragraph that starts `That's the whole install.` immediately after the Claude Code block.

- [ ] **Step 2: Update the Chinese README installation section**

Replace the current Chinese installation opening through the Claude Code command block with this UTF-8 text:

````markdown
## 安装

### Codex

```bash
# 在 Codex CLI 里
codex plugin marketplace add Guohao1020/docs-cockpit
```

然后打开 Codex 插件目录,选择 `docs-cockpit` marketplace,安装 `docs-cockpit` 插件。在 Codex app 里,添加 marketplace 后从 **Plugins** 页面安装。

### Claude Code

```bash
# 在 Claude Code 里
/plugin marketplace add Guohao1020/docs-cockpit
/plugin install docs-cockpit@docs-cockpit
```
````

Keep the following Chinese paragraph about first-render runtime bootstrap in place.

- [ ] **Step 3: Update operations install wording**

In `references/operations.md`, add this subsection near the bootstrap/config material before `## upgrade`:

````markdown
## Codex plugin marketplace

Codex-native installation uses the repo-scoped marketplace at `.agents/plugins/marketplace.json` plus the manifest at `.codex-plugin/plugin.json`:

```bash
codex plugin marketplace add Guohao1020/docs-cockpit
```

After adding the marketplace, install `docs-cockpit` from the Codex plugin directory. This does not replace the existing `.claude-plugin/` entry; both plugin surfaces point at the same `skills/`, `commands/`, and `hooks/` content and must share the same release version.
````

- [ ] **Step 4: Validate docs mention both install surfaces**

Run:

```powershell
rg -n "codex plugin marketplace add|/plugin marketplace add|\\.codex-plugin|\\.claude-plugin" README.md README.zh-CN.md references/operations.md
```

Expected: output includes Codex CLI install commands, Claude Code install commands, `.codex-plugin`, and `.claude-plugin`.

- [ ] **Step 5: Commit documentation**

```bash
git add README.md README.zh-CN.md references/operations.md
git commit -m "docs: document codex plugin marketplace install"
```

## Task 4: Add Changelog Entry

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Add the 1.3.0 section above 1.2.0**

Insert this section immediately above `## [1.2.0] · 2026-06-11`:

```markdown
## [1.3.0] · 2026-06-12

### Added

- **Codex 原生插件入口** —— 新增 `.codex-plugin/plugin.json` 和 `.agents/plugins/marketplace.json`,让用户可以通过 `codex plugin marketplace add Guohao1020/docs-cockpit` 把 docs-cockpit 加入 Codex 插件市场来源并安装。
- **双插件清单兼容** —— 保留既有 `.claude-plugin/` 入口,同时让 Codex 和 Claude 两侧共享同一套 `skills/` / `commands/` / `hooks/` 内容与 release 版本。

### Changed

- **安装文档** —— README / README.zh-CN / operations runbook 区分 Codex 与 Claude Code 安装路径,避免把 repo marketplace 安装误写成单一 Claude 流程。

升级:这次新增插件分发入口,版本按 minor 发布;Codex 用户添加 marketplace 后从 Codex 插件目录安装,Claude Code 用户继续使用既有 `/plugin marketplace add` 流程。
```

- [ ] **Step 2: Commit changelog**

```bash
git add CHANGELOG.md
git commit -m "docs: add changelog for codex marketplace"
```

## Task 5: Verify Codex Marketplace and Test Suite

**Files:**
- No source edits expected.

- [ ] **Step 1: Check all JSON manifests parse and versions match**

Run:

```powershell
@'
import json
from pathlib import Path

versions = {}
versions["python"] = None
for line in Path("docs_cockpit/__init__.py").read_text(encoding="utf-8").splitlines():
    if line.startswith("__version__"):
        versions["python"] = line.split("=")[1].strip().strip('"')

versions["claude plugin"] = json.loads(Path(".claude-plugin/plugin.json").read_text(encoding="utf-8"))["version"]
versions["claude marketplace"] = json.loads(Path(".claude-plugin/marketplace.json").read_text(encoding="utf-8"))["plugins"][0]["version"]
versions["codex plugin"] = json.loads(Path(".codex-plugin/plugin.json").read_text(encoding="utf-8"))["version"]
versions["codex marketplace"] = json.loads(Path(".agents/plugins/marketplace.json").read_text(encoding="utf-8"))["plugins"][0]["version"]

for name, version in versions.items():
    print(f"{name}: {version}")

if set(versions.values()) != {"1.3.0"}:
    raise SystemExit(f"version mismatch: {versions}")
'@ | py -3.13 -
```

Expected:

```text
python: 1.3.0
claude plugin: 1.3.0
claude marketplace: 1.3.0
codex plugin: 1.3.0
codex marketplace: 1.3.0
```

- [ ] **Step 2: Ask Codex CLI to add this branch as a marketplace**

Run this from a disposable branch or local test environment because it mutates the user's Codex marketplace config:

```powershell
codex plugin marketplace add Guohao1020/docs-cockpit --ref main
codex plugin marketplace list
```

Expected: the list includes a marketplace source for `Guohao1020/docs-cockpit`. If testing before merge, replace `main` with the current branch name after pushing the branch.

- [ ] **Step 3: Run the repository test suite**

Run:

```powershell
py -3.13 -m pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 4: Commit any validation fixes**

If validation required edits, commit only those edits:

```bash
git add <fixed-files>
git commit -m "fix: validate codex marketplace metadata"
```

If validation required no edits, do not create an empty commit.

## Task 6: Final Review

**Files:**
- No source edits expected.

- [ ] **Step 1: Review the diff**

Run:

```powershell
git log --oneline -n 6
git diff HEAD~4..HEAD --stat
git diff HEAD~4..HEAD -- .codex-plugin/plugin.json .agents/plugins/marketplace.json README.md README.zh-CN.md references/operations.md CHANGELOG.md docs_cockpit/__init__.py .claude-plugin/plugin.json .claude-plugin/marketplace.json
```

Expected:

- New Codex manifest exists.
- New repo marketplace exists.
- Claude metadata remains present.
- All version fields read `1.3.0`.
- Documentation shows Codex and Claude install paths separately.
- Changelog has a `1.3.0` entry dated `2026-06-12`.

- [ ] **Step 2: Report completion**

Final response should include:

- Files changed.
- Verification commands and outcomes.
- Any Codex CLI marketplace validation that could not be run and why.
- Note that existing untracked `AGENTS.md` was not touched.
