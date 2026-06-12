# Codex Plugin Marketplace Design

## Context

docs-cockpit currently ships as a skill-first plugin through the existing `.claude-plugin/` metadata. Codex now uses a separate native plugin shape: `.codex-plugin/plugin.json` for the plugin manifest and `.agents/plugins/marketplace.json` for a repo-scoped marketplace catalog. The goal is to add the Codex-native marketplace entry while keeping the existing Claude plugin entry working.

## Goals

- Add a Codex-native plugin manifest so Codex can recognize docs-cockpit as a plugin.
- Add a repo-scoped marketplace catalog so users can run `codex plugin marketplace add Guohao1020/docs-cockpit` and install docs-cockpit from the Codex plugin directory.
- Preserve `.claude-plugin/` for existing Claude Code users.
- Keep both plugin layers versioned together with the Python package release metadata.
- Update install documentation so Codex and Claude users have separate, clear commands.

## Non-Goals

- Do not remove or rename `.claude-plugin/`.
- Do not change skill workflows, command behavior, hooks, or the render CLI.
- Do not add a metadata generation script in this release.
- Do not publish to an OpenAI-curated marketplace; this is repo marketplace distribution.

## Proposed Approach

Use dual manifests that point at the same repository content:

- Keep `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` unchanged except for the normal release version bump.
- Add `.codex-plugin/plugin.json` with the same plugin name, version, description, author, repository, license, and keywords, plus Codex manifest fields pointing to the shared `skills/`, `commands/`, and `hooks/` directories if supported by the current manifest format.
- Add `.agents/plugins/marketplace.json` with one `plugins[]` entry named `docs-cockpit`. The source should be GitHub-backed for installation via `codex plugin marketplace add Guohao1020/docs-cockpit`, and the entry should include policy/category/interface metadata expected by Codex.
- Update README and README.zh-CN install sections to show Codex first, then Claude-compatible install commands.
- Update `references/operations.md` upgrade/troubleshooting language only where it currently implies Claude-only plugin cache behavior.

## Versioning

This is a plugin distribution feature, so it should be released as a minor version under this repo's SemVer convention. The implementation should bump all release files together:

- `docs_cockpit/__init__.py`
- `.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`
- `.codex-plugin/plugin.json`
- `.agents/plugins/marketplace.json`
- `CHANGELOG.md`

## Validation

Implementation should verify:

- `codex plugin marketplace add Guohao1020/docs-cockpit --ref <branch>` can resolve the marketplace source from this branch.
- `codex plugin marketplace list` shows the added marketplace.
- The plugin appears in the Codex plugin directory with the expected name/version.
- Existing tests still pass with `py -3.13 -m pytest tests/ -q`.
- Existing Claude metadata remains valid JSON and unchanged in behavior.

## Risks

- Manifest drift: dual plugin metadata can diverge. Mitigate by documenting the release checklist and keeping both manifests in the version bump list.
- Codex manifest schema drift: Codex plugin support is still evolving. Mitigate by using the current official manual as the source and validating through the local Codex CLI.
- Upgrade wording: existing `docs-cockpit upgrade` is Claude-cache-oriented. Mitigate by keeping this release focused on installation and only updating docs where wording is clearly misleading.
