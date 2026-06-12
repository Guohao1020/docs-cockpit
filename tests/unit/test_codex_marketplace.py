import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_codex_marketplace_source_points_to_plugin_bundle():
    marketplace_path = ROOT / ".agents" / "plugins" / "marketplace.json"
    marketplace = json.loads(marketplace_path.read_text(encoding="utf-8-sig"))
    plugin = next(item for item in marketplace["plugins"] if item["name"] == "docs-cockpit")
    root_manifest = json.loads(
        (ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8-sig")
    )

    source = plugin["source"]
    source_path = source["path"] if isinstance(source, dict) else source

    assert source_path != "./"
    assert source_path.startswith("./")

    plugin_root = ROOT / source_path[2:]
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"

    assert manifest_path.is_file()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    assert manifest["name"] == "docs-cockpit"
    assert manifest["name"] == root_manifest["name"]
    assert manifest["version"] == root_manifest["version"]
