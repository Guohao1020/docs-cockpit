# MCP Client Wiring · docs-cockpit v0.12+

`docs-cockpit mcp-serve` exposes three endpoints via the [Model Context Protocol](https://modelcontextprotocol.io/) — Claude / Cursor / Codex / Continue can call them directly instead of going through the v0.11 copy-paste workflow.

## What you get

| Endpoint | Type | Purpose |
|---|---|---|
| `cockpit_prompt(module_id, subtask_id?, template?)` | tool | Render the same prompt as `docs-cockpit prompt <module> <subtask>` |
| `cockpit_apply_patch(yaml_patch, module_id, apply?)` | tool | Apply LLM-output YAML patch to module MD (M08 backend) |
| `cockpit://state` | resource | Live `docs/state.json` payload (modules / subtasks / issues) |

## Prerequisites

```bash
# Install docs-cockpit with the optional `mcp` extra
pip install 'docs-cockpit[mcp]'
# Or via uv tool (recommended)
uv tool install --with mcp docs-cockpit
```

Verify:
```bash
docs-cockpit --version    # 0.12.0+
docs-cockpit mcp-serve --help
```

## Wiring per client

### Claude Code (plugin · automatic)

If you installed docs-cockpit via the [Claude Code plugin](https://github.com/Guohao1020/docs-cockpit), the MCP server is **auto-registered** through `.claude-plugin/plugin.json::mcpServers`. Nothing else to configure — restart Claude Code and the three endpoints appear in the MCP tools list.

Manual registration (if you bootstrap docs-cockpit CLI directly without the plugin):

```bash
# In any project root
claude mcp add docs-cockpit docs-cockpit mcp-serve
```

### Cursor

Edit `~/.cursor/mcp.json` (global) or `<project>/.cursor/mcp.json` (per-project):

```json
{
  "mcpServers": {
    "docs-cockpit": {
      "command": "docs-cockpit",
      "args": ["mcp-serve", "-c", "docs-cockpit.yaml"]
    }
  }
}
```

Restart Cursor · the three endpoints surface under MCP tools.

### Codex CLI

Codex CLI reads `~/.codex/mcp.toml`:

```toml
[mcpServers.docs-cockpit]
command = "docs-cockpit"
args = ["mcp-serve"]
```

Or invoke ad-hoc:

```bash
codex --mcp-server "docs-cockpit:docs-cockpit mcp-serve"
```

### Continue (VS Code extension)

Edit `~/.continue/config.json`:

```json
{
  "experimental": {
    "modelContextProtocolServers": [
      {
        "name": "docs-cockpit",
        "transport": {
          "type": "stdio",
          "command": "docs-cockpit",
          "args": ["mcp-serve"]
        }
      }
    ]
  }
}
```

### Other MCP-aware clients

The server speaks vanilla MCP over stdio. Any client supporting [stdio transport](https://modelcontextprotocol.io/docs/concepts/transports#stdio) just needs:

- **command**: `docs-cockpit`
- **args**: `["mcp-serve"]` (optionally `-c <path>` for non-default config)

## Sanity check

```bash
# Start the server with verbose logging
DOCS_COCKPIT_MCP_LOG=DEBUG docs-cockpit mcp-serve

# From the client side, list tools
# (Claude Code) /mcp list
# Should see: cockpit_prompt, cockpit_apply_patch
# (Resources) cockpit://state
```

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ImportError: docs-cockpit mcp-serve requires the optional 'mcp' SDK` | `[mcp]` extra not installed | `pip install 'docs-cockpit[mcp]'` |
| `state.json not readable at ...` | `docs-cockpit build` not run yet | Run `docs-cockpit build -c docs-cockpit.yaml` first |
| `module M07 not found in state.json` | Module id not declared in `docs-cockpit.yaml` scan paths | Check `modules:` config block + frontmatter `id:` field |
| Tool returns "Error: ..." | Handler-side validation | See server stderr — `DOCS_COCKPIT_MCP_LOG=DEBUG` for verbose trace |
| Cursor / Codex sees no tools | Wrong config path | Use absolute path in `command` if `docs-cockpit` not on PATH |

## Endpoint details

### `cockpit_prompt`

Returns the executable prompt for one subtask. Equivalent to:

```bash
docs-cockpit prompt <module_id> <subtask_id> [-t <template>]
```

If `subtask_id` is omitted, returns the prompt for the first `not-started` / `in-progress` subtask (semantics: "what should I work on next in M07?").

If `template` is omitted, falls through `subtask.prompt → module.prompt_kind → 'generic'` (see `docs-cockpit-author` §10).

### `cockpit_apply_patch`

```yaml
# yaml_patch input (string)
subtasks:
  - id: M07-fbe944
    status: done
    code: ["docs_cockpit/mcp_server.py:200-280"]
```

Returns a JSON summary:

```json
{
  "target": "<absolute MD path>",
  "applied_ids": ["M07-fbe944"],
  "conflicts": [],
  "wrote": false,
  "bak_path": null,
  "diff": "--- a/M07-mcp-server.md\n+++ b/M07-mcp-server.md\n..."
}
```

`apply=false` (default) is dry-run. `apply=true` writes the MD with a `.bak` backup.

### `cockpit://state` resource

Returns the raw contents of `docs/state.json` (computed by the most recent `docs-cockpit build`). The schema is documented in `CLAUDE.md` "State.json schema" + `docs-cockpit-standup/SKILL.md`. Top-level keys: `project / systemDocs / modules / concepts / warnings / issues`.

The resource is **not live** — it reflects the last build. To force-refresh, run `docs-cockpit build` and the MCP server reads on the next `cockpit://state` request (no caching).
