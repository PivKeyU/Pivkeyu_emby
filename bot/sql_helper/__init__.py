"""
初始化数据库
"""
import os
import importlib
import time
from pathlib import Path

from bot import db_host, db_user, db_pwd, db_name, db_port
from bot import LOGGER
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

# 创建engine对象
def _validate_db_config():
    missing = []
    for key, value in {
        "db_host": db_host,
        "db_user": db_user,
        "db_name": db_name,
    }.items():
        if value is None or not str(value).strip():
            missing.append(key)

    if missing:
        raise RuntimeError(
            "数据库配置缺失: "
            + ", ".join(missing)
            + "。请在 config.json 中设置 db_host/db_user/db_pwd/db_name，例如 "
            + "db_host=127.0.0.1, db_user=pivkeyu, db_pwd=pivkeyu, db_name=pivkeyu"
        )


_validate_db_config()

DATABASE_URL = f"mysql+pymysql://{db_user}:{db_pwd}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"
DB_STARTUP_MAX_RETRIES = max(1, int(os.getenv("PIVKEYU_DB_STARTUP_MAX_RETRIES", "20")))
DB_STARTUP_RETRY_DELAY = max(0.5, float(os.getenv("PIVKEYU_DB_STARTUP_RETRY_DELAY", "3")))
DB_CONNECT_TIMEOUT = max(1, int(os.getenv("PIVKEYU_DB_CONNECT_TIMEOUT", "5")))

engine = create_engine(
    DATABASE_URL,
    echo=False,
    echo_pool=False,
    pool_size=24,
    max_overflow=24,
    pool_timeout=30,
    pool_recycle=60 * 30,
    pool_pre_ping=True,
    pool_use_lifo=True,
    pool_reset_on_return="rollback",
    connect_args={
        "init_command": "SET NAMES utf8mb4",
        "connect_timeout": DB_CONNECT_TIMEOUT,
    },
)

# 创建Base对象
Base = declarative_base()
Base.metadata.bind = engine

_MIGRATION_GUARD_ENV = "PIVKEYU_RUNNING_MIGRATIONS"


def _run_with_db_retry(action, description: str):
    last_error = None

    for attempt in range(1, DB_STARTUP_MAX_RETRIES + 1):
        try:
            return action()
        except OperationalError as exc:
            last_error = exc
            if attempt >= DB_STARTUP_MAX_RETRIES:
                break
            LOGGER.warning(
                f"{description}失败，数据库暂未就绪，"
                f"将在 {DB_STARTUP_RETRY_DELAY:g} 秒后重试 "
                f"({attempt}/{DB_STARTUP_MAX_RETRIES})：{exc}"
            )
            time.sleep(DB_STARTUP_RETRY_DELAY)

    raise last_error


def _legacy_create_all_tables():
    """
    在未安装 Alembic 或配置缺失时兜底建表，保证服务可启动。
    """
    from bot.sql_helper import sql_code, sql_emby, sql_emby2, sql_favorites, sql_partition, sql_plugin, sql_request_record, sql_xiuxian  # noqa: F401

    _run_with_db_retry(
        lambda: Base.metadata.create_all(bind=engine, checkfirst=True),
        "数据库建表",
    )


def run_migrations():
    """
    启动时自动执行数据库迁移到最新版本。
    """
    if os.getenv(_MIGRATION_GUARD_ENV) == "1":
        return

    alembic_ini = Path(__file__).resolve().parents[2] / "alembic.ini"
    if not alembic_ini.exists():
        LOGGER.warning(f"未找到 Alembic 配置文件，跳过自动迁移: {alembic_ini}")
        _legacy_create_all_tables()
        return

    os.environ[_MIGRATION_GUARD_ENV] = "1"
    try:
        try:
            alembic_command = importlib.import_module("alembic.command")
            alembic_config = importlib.import_module("alembic.config")
        except ImportError:
            LOGGER.warning("未安装 alembic，跳过自动迁移")
            _legacy_create_all_tables()
            return

        Config = getattr(alembic_config, "Config")
        config = Config(str(alembic_ini))
        config.set_main_option("sqlalchemy.url", DATABASE_URL)
        _run_with_db_retry(
            lambda: alembic_command.upgrade(config, "head"),
            "数据库自动迁移",
        )
        LOGGER.info("数据库迁移完成，当前已升级到最新版本")
    except Exception as e:
        LOGGER.error(f"数据库自动迁移失败: {e}")
        raise
    finally:
        os.environ.pop(_MIGRATION_GUARD_ENV, None)


# 调用sql_start()函数，返回一个Session对象
def sql_start() -> scoped_session:
    return scoped_session(sessionmaker(bind=engine, autoflush=False))


Session = sql_start()


run_migrations()
