---
name: use-docs-cockpit
description: |
  Entry/router for the docs-cockpit skill ecosystem. Loaded by default in any project that has a docs-cockpit.yaml. Tells the agent: this project uses docs-cockpit; cognition lives in skills, python only renders; route to docs-cockpit-build (create/extend association), docs-cockpit-rebuild (refresh/diagnose/read-status), or CLI docs-cockpit render (just regenerate HTML).
---

# use-docs-cockpit

> **[Session context · docs-cockpit router]** This block is injected at session start in any project with a `docs-cockpit.yaml`. Its only job: route you to the right skill before you act on any docs-cockpit-related intent.

This project manages its documentation association system (module ↔ subtask ↔ spec/plan/RFC anchors) with **docs-cockpit**. North-star: **cognition lives in skills, Python only renders — and anchor precision comes first: a wrong anchor is worse than a missing anchor.**

This file is a router only. Each routed skill carries its own complete workflow — read it before acting; do not improvise doc-association work from here.

## Routing

| You want to | Use | Trigger examples |
|---|---|---|
| Build or extend the association system — plan the whole project's spec/plan, wire modules to docs, fill anchor gaps (0→1 / whole-project) | `docs-cockpit-build` skill | 「把文档体系建起来」「关联模块和文档」「规划 spec」 |
| Refresh an EXISTING association that drifted — anchors stale after refactor, spec evolved and links need re-sync | `docs-cockpit-rebuild` skill | 「关联乱了重新梳理」「anchor 失效了」 |
| Just regenerate the dashboard HTML, no association work | CLI `docs-cockpit build` (will be renamed `docs-cockpit render`) | 「重新生成 dashboard」 |
| Read status / progress / blockers, no file changes | `docs-cockpit-rebuild` Phase 1 (pure status queries end there) | 「项目进度怎么样」「哪些卡了」 |

Discriminator between the two skills: **build = the association does not exist yet (or whole-project planning); rebuild = it already exists and needs diagnosis / refresh (or just reading).**

## When NOT to apply

If the project has no `docs-cockpit.yaml` at the repo root, this router does not apply — the project does not use docs-cockpit. (The SessionStart hook injects this file conditionally, but a marketplace install can also trigger it directly; check for the config first.)
