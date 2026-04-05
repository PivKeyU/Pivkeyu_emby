from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PLUGIN_ROOT = ROOT / "data" / "runtime_plugins"


def normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)):
        value = [value]

    normalized: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def load_runtime_plugin_dependencies() -> dict[str, list[str]]:
    if not RUNTIME_PLUGIN_ROOT.exists():
        return {}

    dependencies_by_plugin: dict[str, list[str]] = {}
    for plugin_dir in sorted(RUNTIME_PLUGIN_ROOT.iterdir()):
        if not plugin_dir.is_dir():
            continue

        manifest_path = plugin_dir / "plugin.json"
        if not manifest_path.exists():
            continue

        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RuntimeError(f"无法读取运行时插件 manifest: {manifest_path} ({exc})") from exc

        if not isinstance(raw, dict):
            raise RuntimeError(f"插件 manifest 必须是 JSON 对象: {manifest_path}")

        plugin_id = str(raw.get("id") or plugin_dir.name).strip() or plugin_dir.name
        dependencies = normalize_string_list((raw.get("dependencies") or {}).get("python"))
        if dependencies:
            dependencies_by_plugin[plugin_id] = dependencies

    return dependencies_by_plugin


def main() -> int:
    dependencies_by_plugin = load_runtime_plugin_dependencies()
    if not dependencies_by_plugin:
        print("No runtime plugin Python dependencies declared. Skipping.")
        return 0

    unique_requirements: list[str] = []
    owners: dict[str, list[str]] = {}
    for plugin_id, dependencies in dependencies_by_plugin.items():
        for requirement in dependencies:
            owners.setdefault(requirement, []).append(plugin_id)
            if requirement not in unique_requirements:
                unique_requirements.append(requirement)

    print(
        f"Installing {len(unique_requirements)} runtime plugin dependencies "
        f"from {len(dependencies_by_plugin)} plugin(s)."
    )
    for requirement in unique_requirements:
        print(f" - {requirement} <- {', '.join(owners[requirement])}")

    subprocess.run(
        [sys.executable, "-m", "pip", "install", *unique_requirements],
        check=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
