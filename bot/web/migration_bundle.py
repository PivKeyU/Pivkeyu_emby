from __future__ import annotations

import base64
import io
import json
import shutil
import stat
import tempfile
import zipfile
from datetime import date, datetime, time, timezone
from decimal import Decimal
from pathlib import Path, PurePosixPath
from typing import Any

from sqlalchemy import MetaData, select, text
from sqlalchemy.sql.sqltypes import Boolean, Date, DateTime, Float, Integer, JSON, LargeBinary, Numeric, Time

from bot import LOGGER, config
from bot.plugins import list_plugins
from bot.sql_helper import Session, engine


BUNDLE_SCHEMA_VERSION = 1
TYPE_MARKER = "__pivkeyu_type__"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_DIRNAME = "database"
DATA_DIRNAME = "data"
PLUGIN_DIRNAME = "plugins"
CONFIG_DIRNAME = "config"
MANIFEST_FILENAME = "manifest.json"
PLUGIN_SNAPSHOT_FILENAME = "plugins.json"
CONFIG_SNAPSHOT_FILENAME = "data-config.json"
EXPORT_EXCLUDED_DATA_NAMES = {
    "__pycache__",
    "config.json",
    "migration_exports",
    "migration_imports",
    "runtime_plugin_backups",
    "session",
}


class MigrationBundleError(ValueError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _bundle_name() -> str:
    return f"pivkeyu-migration-{_utc_now().strftime('%Y%m%d-%H%M%S')}"


def _clean_data_name(name: str) -> bool:
    if not name:
        return False
    if name in EXPORT_EXCLUDED_DATA_NAMES:
        return False
    if name.startswith("migration_"):
        return False
    return True


def _serialize_scalar(value: Any) -> Any:
    if isinstance(value, datetime):
        return {TYPE_MARKER: "datetime", "value": value.isoformat()}
    if isinstance(value, date) and not isinstance(value, datetime):
        return {TYPE_MARKER: "date", "value": value.isoformat()}
    if isinstance(value, time):
        return {TYPE_MARKER: "time", "value": value.isoformat()}
    if isinstance(value, Decimal):
        return {TYPE_MARKER: "decimal", "value": str(value)}
    if isinstance(value, (bytes, bytearray)):
        return {TYPE_MARKER: "bytes", "value": base64.b64encode(bytes(value)).decode("ascii")}
    if isinstance(value, dict):
        return {str(key): _serialize_scalar(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_scalar(item) for item in value]
    return value


def _deserialize_scalar(value: Any) -> Any:
    if isinstance(value, list):
        return [_deserialize_scalar(item) for item in value]
    if not isinstance(value, dict):
        return value

    marker = value.get(TYPE_MARKER)
    if marker == "datetime":
        return datetime.fromisoformat(str(value.get("value") or ""))
    if marker == "date":
        return date.fromisoformat(str(value.get("value") or ""))
    if marker == "time":
        return time.fromisoformat(str(value.get("value") or ""))
    if marker == "decimal":
        return Decimal(str(value.get("value") or "0"))
    if marker == "bytes":
        return base64.b64decode(str(value.get("value") or "").encode("ascii"))
    return {str(key): _deserialize_scalar(item) for key, item in value.items()}


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _json_load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_data_snapshot(target_dir: Path) -> dict[str, Any]:
    target_dir.mkdir(parents=True, exist_ok=True)
    copied_items: list[dict[str, Any]] = []
    if not DATA_DIR.exists():
        return {"count": 0, "items": copied_items}

    # 导出运行时数据时排除会随部署环境变化的目录，避免把会话和历史备份一并带走。
    for child in sorted(DATA_DIR.iterdir(), key=lambda item: item.name.lower()):
        if not _clean_data_name(child.name):
            continue

        destination = target_dir / child.name
        if child.is_dir():
            shutil.copytree(child, destination, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
            item_type = "directory"
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(child, destination)
            item_type = "file"

        copied_items.append(
            {
                "name": child.name,
                "type": item_type,
            }
        )

    return {"count": len(copied_items), "items": copied_items}


def _write_plugin_snapshot(target_dir: Path) -> dict[str, Any]:
    target_dir.mkdir(parents=True, exist_ok=True)
    plugins = list_plugins()
    _json_dump(target_dir / PLUGIN_SNAPSHOT_FILENAME, plugins)
    return {
        "count": len(plugins),
        "items": plugins,
    }


def _write_config_snapshot(target_dir: Path) -> dict[str, Any]:
    target_dir.mkdir(parents=True, exist_ok=True)
    source = DATA_DIR / "config.json"
    target = target_dir / CONFIG_SNAPSHOT_FILENAME
    if not source.exists():
        return {"available": False, "filename": target.name}
    shutil.copy2(source, target)
    return {"available": True, "filename": target.name}


def _write_database_snapshot(target_dir: Path) -> dict[str, Any]:
    target_dir.mkdir(parents=True, exist_ok=True)
    metadata = MetaData()
    metadata.reflect(bind=engine)

    tables_summary: list[dict[str, Any]] = []
    total_rows = 0

    with engine.connect() as connection:
        for table in metadata.sorted_tables:
            # 统一按 JSON 快照导出，迁移时不依赖 mysqldump 或目标机器额外工具链。
            rows = [
                {column: _serialize_scalar(value) for column, value in row.items()}
                for row in connection.execute(select(table)).mappings()
            ]
            _json_dump(target_dir / f"{table.name}.json", rows)
            row_count = len(rows)
            total_rows += row_count
            tables_summary.append({"name": table.name, "rows": row_count})

    return {
        "count": len(tables_summary),
        "rows": total_rows,
        "tables": tables_summary,
    }


def _zip_dir(source_dir: Path, target_file: Path) -> None:
    with zipfile.ZipFile(target_file, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            archive.write(path, arcname=path.relative_to(source_dir.parent).as_posix())


def create_migration_bundle() -> dict[str, Any]:
    temp_root = Path(tempfile.mkdtemp(prefix="pivkeyu-migration-export-"))
    bundle_name = _bundle_name()
    bundle_root = temp_root / bundle_name
    database_root = bundle_root / DATABASE_DIRNAME
    data_root = bundle_root / DATA_DIRNAME
    plugin_root = bundle_root / PLUGIN_DIRNAME
    config_root = bundle_root / CONFIG_DIRNAME

    database = _write_database_snapshot(database_root)
    data = _copy_data_snapshot(data_root)
    plugins = _write_plugin_snapshot(plugin_root)
    config_snapshot = _write_config_snapshot(config_root)

    manifest = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "created_at": _utc_now().isoformat(),
        "bundle_name": bundle_name,
        "bot_name": config.bot_name,
        "database": database,
        "data": data,
        "config": config_snapshot,
        "plugins": {
            "count": plugins["count"],
        },
    }
    _json_dump(bundle_root / MANIFEST_FILENAME, manifest)

    archive_path = temp_root / f"{bundle_name}.zip"
    _zip_dir(bundle_root, archive_path)
    return {
        "archive_path": archive_path,
        "bundle_root": bundle_root,
        "temp_root": temp_root,
        "filename": archive_path.name,
        "manifest": manifest,
    }


def _normalize_archive_path(name: str) -> PurePosixPath | None:
    normalized = (name or "").replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized:
        return None
    if normalized.startswith("/"):
        raise MigrationBundleError("迁移压缩包包含非法绝对路径，已拒绝导入。")

    path = PurePosixPath(normalized)
    clean_parts: list[str] = []
    for part in path.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            raise MigrationBundleError("迁移压缩包包含非法上级目录路径，已拒绝导入。")
        clean_parts.append(part)

    if clean_parts and clean_parts[0].endswith(":"):
        raise MigrationBundleError("迁移压缩包包含非法磁盘路径，已拒绝导入。")
    if not clean_parts:
        return None
    return PurePosixPath(*clean_parts)


def _resolve_bundle_root(paths: set[PurePosixPath]) -> str | None:
    if PurePosixPath(MANIFEST_FILENAME) in paths:
        return None

    top_levels = {path.parts[0] for path in paths if path.parts}
    if len(top_levels) != 1:
        raise MigrationBundleError("迁移压缩包需要在根目录，或唯一一级目录内包含 manifest.json。")

    top_level = next(iter(top_levels))
    if PurePosixPath(top_level, MANIFEST_FILENAME) not in paths:
        raise MigrationBundleError("未在迁移压缩包中找到 manifest.json。")
    return top_level


def _extract_bundle(archive_bytes: bytes) -> tuple[Path, dict[str, Any], Path]:
    if not archive_bytes:
        raise MigrationBundleError("上传的迁移压缩包为空。")

    try:
        zip_file = zipfile.ZipFile(io.BytesIO(archive_bytes))
    except zipfile.BadZipFile as exc:
        raise MigrationBundleError("上传文件不是有效的 ZIP 压缩包。") from exc

    temp_root = Path(tempfile.mkdtemp(prefix="pivkeyu-migration-import-"))
    extract_root = temp_root / "bundle"

    with zip_file as archive:
        normalized_members: list[tuple[zipfile.ZipInfo, PurePosixPath]] = []
        visible_paths: set[PurePosixPath] = set()

        for info in archive.infolist():
            normalized = _normalize_archive_path(info.filename)
            if normalized is None:
                continue
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise MigrationBundleError("迁移压缩包中不能包含符号链接。")
            normalized_members.append((info, normalized))
            visible_paths.add(normalized)

        if not visible_paths:
            raise MigrationBundleError("迁移压缩包中没有可导入的内容。")

        bundle_root_name = _resolve_bundle_root(visible_paths)

        for info, normalized in normalized_members:
            relative = normalized.relative_to(bundle_root_name) if bundle_root_name else normalized
            target = extract_root / relative
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info, "r") as source, target.open("wb") as destination:
                shutil.copyfileobj(source, destination)

    manifest_path = extract_root / MANIFEST_FILENAME
    if not manifest_path.exists():
        raise MigrationBundleError("迁移压缩包缺少 manifest.json。")

    manifest = _json_load(manifest_path)
    schema_version = int(manifest.get("schema_version") or 0)
    if schema_version != BUNDLE_SCHEMA_VERSION:
        raise MigrationBundleError(
            f"迁移压缩包版本不兼容：当前仅支持 schema_version={BUNDLE_SCHEMA_VERSION}，实际为 {schema_version}。"
        )

    return extract_root, manifest, temp_root


def _coerce_column_value(column, value: Any) -> Any:
    value = _deserialize_scalar(value)
    if value is None:
        return None
    if isinstance(column.type, JSON):
        return value
    if isinstance(column.type, DateTime) and isinstance(value, str):
        return datetime.fromisoformat(value)
    if isinstance(column.type, Date) and isinstance(value, str):
        return date.fromisoformat(value)
    if isinstance(column.type, Time) and isinstance(value, str):
        return time.fromisoformat(value)
    if isinstance(column.type, Boolean):
        return bool(value)
    if isinstance(column.type, Integer):
        return int(value)
    if isinstance(column.type, Float):
        return float(value)
    if isinstance(column.type, Numeric) and not isinstance(value, Decimal):
        return Decimal(str(value))
    if isinstance(column.type, LargeBinary) and isinstance(value, str):
        return value.encode("utf-8")
    return value


def _restore_database_snapshot(database_root: Path) -> dict[str, Any]:
    metadata = MetaData()
    metadata.reflect(bind=engine)
    archive_tables = sorted(path.stem for path in database_root.glob("*.json"))
    table_map = {table.name: table for table in metadata.sorted_tables}
    restored_tables: list[dict[str, Any]] = []
    skipped_archive_tables = [name for name in archive_tables if name not in table_map]
    cleared_tables: list[str] = []

    Session.remove()
    engine.dispose()

    with engine.begin() as connection:
        connection.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        try:
            # 先清空再恢复，保证迁移结果与压缩包内容完全一致，不残留旧表数据。
            for table in reversed(metadata.sorted_tables):
                connection.execute(table.delete())
                cleared_tables.append(table.name)

            for table in metadata.sorted_tables:
                table_file = database_root / f"{table.name}.json"
                if not table_file.exists():
                    restored_tables.append({"name": table.name, "rows": 0})
                    continue

                rows = _json_load(table_file)
                converted_rows = []
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    converted_row = {}
                    for column in table.columns:
                        if column.name not in row:
                            continue
                        converted_row[column.name] = _coerce_column_value(column, row[column.name])
                    converted_rows.append(converted_row)

                if converted_rows:
                    # 批量写入避免单次 SQL 过大，兼顾导入速度和稳定性。
                    for index in range(0, len(converted_rows), 500):
                        connection.execute(table.insert(), converted_rows[index:index + 500])
                restored_tables.append({"name": table.name, "rows": len(converted_rows)})
        finally:
            connection.execute(text("SET FOREIGN_KEY_CHECKS=1"))

    engine.dispose()
    return {
        "cleared_tables": cleared_tables,
        "restored_tables": restored_tables,
        "skipped_archive_tables": skipped_archive_tables,
    }


def _restore_data_snapshot(data_root: Path) -> dict[str, Any]:
    restored_items: list[dict[str, Any]] = []
    if not data_root.exists():
        return {"count": 0, "items": restored_items}

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for source in sorted(data_root.iterdir(), key=lambda item: item.name.lower()):
        target = DATA_DIR / source.name
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()

        if source.is_dir():
            shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
            item_type = "directory"
        else:
            shutil.copy2(source, target)
            item_type = "file"
        restored_items.append({"name": source.name, "type": item_type})

    return {"count": len(restored_items), "items": restored_items}


def _restore_config_snapshot(config_root: Path) -> dict[str, Any]:
    snapshot = config_root / CONFIG_SNAPSHOT_FILENAME
    if not snapshot.exists():
        return {"restored": False, "available": False, "filename": CONFIG_SNAPSHOT_FILENAME}
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(snapshot, DATA_DIR / "config.json")
    return {"restored": True, "available": True, "filename": snapshot.name}


def restore_migration_bundle(archive_bytes: bytes, *, restore_config_file: bool = False) -> dict[str, Any]:
    extract_root, manifest, temp_root = _extract_bundle(archive_bytes)
    warnings: list[str] = []
    try:
        # 没有数据库快照时直接拒绝，防止误导入后把现有数据库清空。
        database_root = extract_root / DATABASE_DIRNAME
        if not database_root.exists() or not any(database_root.glob("*.json")):
            raise MigrationBundleError("迁移压缩包中未找到数据库快照，已拒绝导入。")

        data_result = _restore_data_snapshot(extract_root / DATA_DIRNAME)
        database_result = _restore_database_snapshot(database_root)
        config_result = (
            _restore_config_snapshot(extract_root / CONFIG_DIRNAME)
            if restore_config_file
            else {
                "restored": False,
                "available": bool((extract_root / CONFIG_DIRNAME / CONFIG_SNAPSHOT_FILENAME).exists()),
                "filename": CONFIG_SNAPSHOT_FILENAME,
            }
        )
        plugin_snapshot_path = extract_root / PLUGIN_DIRNAME / PLUGIN_SNAPSHOT_FILENAME
        plugin_items = _json_load(plugin_snapshot_path) if plugin_snapshot_path.exists() else []
        if database_result["skipped_archive_tables"]:
            warnings.append(
                "以下归档表未在当前数据库结构中找到，已跳过恢复："
                + "、".join(database_result["skipped_archive_tables"])
            )
        if config_result["available"] and not config_result["restored"]:
            warnings.append("迁移包内包含配置快照，但本次未恢复 data/config.json。")
        return {
            "manifest": manifest,
            "data": data_result,
            "database": database_result,
            "config": config_result,
            "plugins": {
                "count": len(plugin_items),
                "items": plugin_items,
            },
            "warnings": warnings,
            "restart_required": True,
        }
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
