"""
初始化数据库
"""
import os
import importlib
import time
from pathlib import Path

from bot import db_backend, db_host, db_user, db_pwd, db_name, db_port, db_url
from bot import LOGGER
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return max(minimum, int(raw))
    except (TypeError, ValueError):
        LOGGER.warning(f"环境变量 {name}={raw!r} 不是有效整数，回退到默认值 {default}")
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


# 创建engine对象
def _validate_db_config():
    configured_url = str(db_url or "").strip()
    if configured_url:
        return

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


def _normalize_db_backend(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"postgres", "postgresql", "pgsql"}:
        return "postgresql"
    if normalized in {"mysql", "mariadb"}:
        return "mysql"
    return "postgresql"


def _build_database_url() -> str:
    raw_url = str(db_url or "").strip()
    if raw_url:
        return raw_url

    normalized_backend = _normalize_db_backend(db_backend)

    if normalized_backend == "mysql":
        return str(
            URL.create(
                "mysql+pymysql",
                username=db_user,
                password=db_pwd,
                host=db_host,
                port=int(db_port),
                database=db_name,
                query={"charset": "utf8mb4"},
            )
        )

    if normalized_backend == "postgresql":
        return str(
            URL.create(
                "postgresql+psycopg",
                username=db_user,
                password=db_pwd,
                host=db_host,
                port=int(db_port),
                database=db_name,
            )
        )

    raise RuntimeError(f"暂不支持的数据库后端: {db_backend}")


DATABASE_URL = _build_database_url()
DB_BACKEND = make_url(DATABASE_URL).get_backend_name()
DB_STARTUP_MAX_RETRIES = max(1, int(os.getenv("PIVKEYU_DB_STARTUP_MAX_RETRIES", "20")))
DB_STARTUP_RETRY_DELAY = max(0.5, float(os.getenv("PIVKEYU_DB_STARTUP_RETRY_DELAY", "3")))
DB_CONNECT_TIMEOUT = _env_int("PIVKEYU_DB_CONNECT_TIMEOUT", 5, 1)
DB_POOL_SIZE = _env_int("PIVKEYU_DB_POOL_SIZE", 24, 1)
DB_MAX_OVERFLOW = _env_int("PIVKEYU_DB_MAX_OVERFLOW", 24, 0)
DB_POOL_TIMEOUT = _env_int("PIVKEYU_DB_POOL_TIMEOUT", 30, 1)
DB_POOL_RECYCLE = _env_int("PIVKEYU_DB_POOL_RECYCLE", 60 * 30, 30)
DB_POOL_PRE_PING = _env_bool("PIVKEYU_DB_POOL_PRE_PING", True)
DB_POOL_USE_LIFO = _env_bool("PIVKEYU_DB_POOL_USE_LIFO", True)
DB_POOL_RESET_ON_RETURN = (os.getenv("PIVKEYU_DB_POOL_RESET_ON_RETURN", "rollback") or "rollback").strip()


def _build_connect_args() -> dict:
    if DB_BACKEND == "mysql":
        return {
            "init_command": "SET NAMES utf8mb4",
            "connect_timeout": DB_CONNECT_TIMEOUT,
        }

    if DB_BACKEND == "postgresql":
        return {
            "connect_timeout": DB_CONNECT_TIMEOUT,
        }

    return {}

engine = create_engine(
    DATABASE_URL,
    echo=False,
    echo_pool=False,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=DB_POOL_RECYCLE,
    pool_pre_ping=DB_POOL_PRE_PING,
    pool_use_lifo=DB_POOL_USE_LIFO,
    pool_reset_on_return=DB_POOL_RESET_ON_RETURN,
    connect_args=_build_connect_args(),
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
    from bot.sql_helper import sql_bot_access, sql_code, sql_emby, sql_emby2, sql_favorites, sql_partition, sql_plugin, sql_request_record, sql_shop, sql_xiuxian  # noqa: F401

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


# 调用 sql_start() 返回一个轻量工厂。每次 Session() 都创建独立会话，
# 避免同线程嵌套 with Session() 时复用 scoped_session，导致内层 close()
# 把外层事务对象提前关闭，引发 "Instance ... is not persistent within this Session"。
class _SessionFactory:
    def __init__(self):
        self._maker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def __call__(self):
        return self._maker()

    def remove(self) -> None:
        # 兼容旧调用路径；非 scoped_session 下无需显式移除线程本地会话。
        return None

    def close_all(self) -> None:
        self._maker.close_all()


def sql_start() -> _SessionFactory:
    return _SessionFactory()


Session = sql_start()


run_migrations()
