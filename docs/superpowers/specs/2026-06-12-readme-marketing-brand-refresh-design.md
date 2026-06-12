# README, Marketing Page, and Brand Asset Refresh Design

## Context

docs-cockpit is now positioned as a Codex/Claude Code-native, skill-first project cockpit for AI coding workflows. The current README is technically complete but too dense for first-time readers, has limited visual proof, and duplicates some older product language. The current landing page has a strong long-form marketing draft, but it still contains stale version and support claims from the pre-Codex-native phase.

The target user for this refresh is an AI coding power user or indie developer who keeps project truth in markdown, works across Codex / Claude Code / Cursor-style agents, and wants a local, schema-validated project cockpit instead of another SaaS workspace.

## Approved Direction

Use **A+B mixed visual direction**:

- **A. Radar Flight Deck** for brand identity, hero imagery, Open Graph cover, and the first emotional impression.
- **B. Operational Kanban** for README screenshots, feature proof, install walkthroughs, and product credibility.

This balances memorability with clarity: the cockpit metaphor becomes visible without hiding the actual dashboard product.

## Goals

1. Make the README feel like a professional open-source product page, not only a technical reference.
2. Add visual proof wherever it helps comprehension: hero brand image, dashboard screenshot/mock, workflow diagram, and install/usage snippets.
3. Update the landing page to reflect the current v1.3.1 product reality, especially Codex marketplace support.
4. Generate project-owned visual assets: logo mark and hero/OG background.
5. Keep English and Chinese README siblings structurally aligned.
6. Preserve the repo's skill-first positioning: cognition lives in skills, Python renders deterministically.

## Non-Goals

- Do not redesign the generated dashboard UI in `templates/index.html.tmpl`.
- Do not change plugin behavior, CLI behavior, schema fields, or skills.
- Do not add a JS build pipeline for the landing page.
- Do not add remote runtime assets that break the current static/offline posture.

## Information Architecture

### README.md

The English README remains primary and should be reorganized around scanning:

1. Hero block with logo, tagline, badges, and one concise product paragraph.
2. Visual proof: hero/OG image plus dashboard screenshot or polished mock.
3. "Why docs-cockpit" section for the AI-written markdown problem.
4. Quickstart with Codex first, Claude Code second, CLI fallback third.
5. "How it works" with the router skill, build skill, rebuild skill, and render CLI.
6. Product tour: Kanban, backlog, inline docs drawer, validation, state.json, upgrade.
7. Architecture/philosophy: skill-first, wrong anchor > missing anchor, file:// first.
8. Reference sections: frontmatter example, project anatomy, contributing, community.

### README.zh-CN.md

The Chinese README must mirror the English section order and include equivalent visuals. It should be rewritten in natural Chinese rather than preserving any mojibake or machine-corrupted prose. Technical terms such as `frontmatter`, `state.json`, `render`, `skill-first`, and `file://` should remain in English where that is clearer.

### site/index.html

The landing page stays a single static HTML file. It should be tightened around:

1. Hero: Radar Flight Deck background, direct AI-coding positioning, two CTAs.
2. Product proof band: dashboard/kanban visual and current install commands.
3. Problem/solution: AI writes markdown faster than humans can audit it.
4. Workflow: install plugin -> set up cockpit -> build associations -> render -> rebuild/status.
5. Feature grid: schema validation, skill workflows, single-file dashboard, state.json, upgrade.
6. Audience: AI coding power users and indie developers first.
7. FAQ updated for Codex marketplace support and v1.3.1.

Remove stale claims that Codex native packaging is still on the roadmap.

## Visual Assets

Create project-owned assets under a stable static asset directory, recommended:

```text
site/assets/
  brand/
    docs-cockpit-logo.png
    docs-cockpit-logo-mark.png
    docs-cockpit-hero-bg.png
    docs-cockpit-og-cover.png
  screenshots/
    dashboard-kanban.png
    workflow-overview.png
```

Asset intent:

- **Logo mark**: vector-friendly radar/cockpit mark, readable at small sizes, no tiny text.
- **Hero background**: dark Radar Flight Deck image with subtle project radar, cockpit panels, and enough negative space for headline text.
- **OG cover**: 1200x630 social image combining Radar Flight Deck identity with an operational kanban preview.
- **Dashboard screenshot/mock**: Operational Kanban style. Prefer a real rendered dashboard screenshot if the local demo render is stable; otherwise create a polished static mock clearly representing the product.
- **Workflow overview**: lightweight diagram for README, preferably SVG or Mermaid-derived static image only if it adds clarity.

Generated raster assets must be copied into the repository before being referenced. README and site must not point to Codex's default generated image cache.

## Copy Direction

Primary message:

> A skill-first project cockpit for AI coding agents. Turn AI-written markdown into a schema-validated, single-file dashboard.

Supporting claims:

- Codex and Claude Code plugin support.
- Markdown remains source of truth.
- No SaaS workspace, no runtime network, no server required.
- Skills handle judgment; Python only renders.
- A wrong anchor is worse than a missing anchor.

Avoid over-claiming:

- Do not imply docs-cockpit replaces all of Jira / Linear / Notion for every team.
- Do not claim full native packaging for agents that are still roadmap-only.
- Do not describe the dashboard as cloud-hosted or multi-user SaaS.

## Technical Approach

- Keep `site/index.html` self-contained except local `site/assets/**` images.
- Use responsive image sizing and alt text for all README and site visuals.
- Add or update Open Graph/Twitter metadata to use `site/assets/brand/docs-cockpit-og-cover.png` or the published equivalent path.
- If `.superpowers/` remains local-only, add it to `.gitignore` during implementation so visual brainstorming artifacts are not accidentally committed.
- If assets are duplicated into `plugins/docs-cockpit`, do so only if plugin marketplace surfaces need them. README assets do not need to be duplicated into the plugin bundle unless referenced by the plugin-distributed README.

## Validation

Implementation is complete only after:

1. Markdown renders correctly in GitHub preview style for both README files.
2. Landing page opens locally in a browser at desktop and mobile widths.
3. Image references resolve from the repository and published site paths.
4. No stale `0.14.x`, `v0.14`, or "Codex roadmap" claims remain in README or site.
5. Existing test suite still passes.
6. Git status excludes `.superpowers/` brainstorming artifacts.

