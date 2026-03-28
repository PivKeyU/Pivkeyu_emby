from __future__ import annotations

import importlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any


PLUGIN_ROOT = Path(__file__).resolve().parent
_DISCOVERED: dict[str, "PluginRecord"] = {}
_LOADED = False


@dataclass
class PluginRecord:
    plugin_id: str
    name: str
    version: str
    description: str
    entry: str
    enabled: bool
    path: Path
    module: ModuleType | None = None
    loaded: bool = False
    web_registered: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.plugin_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "entry": self.entry,
            "enabled": self.enabled,
            "loaded": self.loaded,
            "web_registered": self.web_registered,
            "error": self.error,
            "path": str(self.path),
        }


def _discover_plugins() -> dict[str, PluginRecord]:
    if _DISCOVERED:
        return _DISCOVERED

    for directory in PLUGIN_ROOT.iterdir():
        if not directory.is_dir():
            continue

        manifest_path = directory / "plugin.json"
        if not manifest_path.exists():
            continue

        with manifest_path.open("r", encoding="utf-8") as manifest_file:
            raw = json.load(manifest_file)

        record = PluginRecord(
            plugin_id=raw["id"],
            name=raw.get("name", raw["id"]),
            version=raw.get("version", "0.0.0"),
            description=raw.get("description", ""),
            entry=raw.get("entry", "plugin"),
            enabled=bool(raw.get("enabled", True)),
            path=directory,
        )
        _DISCOVERED[record.plugin_id] = record

    return _DISCOVERED


def load_plugins() -> list[dict[str, Any]]:
    global _LOADED

    records = _discover_plugins()
    if _LOADED:
        return [record.to_dict() for record in records.values()]

    from bot import LOGGER, bot

    for record in records.values():
        if not record.enabled:
            continue

        try:
            module_name = f"bot.plugins.{record.path.name}.{record.entry.removesuffix('.py')}"
            module = importlib.import_module(module_name)
            record.module = module
            record.loaded = True

            register_bot = getattr(module, "register_bot", None)
            if callable(register_bot):
                register_bot(bot)

            LOGGER.info(f"Loaded plugin: {record.plugin_id}")
        except Exception as exc:
            record.error = str(exc)
            LOGGER.error(f"Failed to load plugin {record.plugin_id}: {exc}")

    _LOADED = True
    return [record.to_dict() for record in records.values()]


def register_web_plugins(app: Any) -> None:
    from bot import LOGGER

    for record in _discover_plugins().values():
        if not record.loaded or record.web_registered or record.module is None:
            continue

        register_web = getattr(record.module, "register_web", None)
        if not callable(register_web):
            continue

        try:
            register_web(app)
            record.web_registered = True
            LOGGER.info(f"Registered web routes for plugin: {record.plugin_id}")
        except Exception as exc:
            record.error = str(exc)
            LOGGER.error(f"Failed to register web routes for plugin {record.plugin_id}: {exc}")


def list_plugins() -> list[dict[str, Any]]:
    return [record.to_dict() for record in _discover_plugins().values()]
