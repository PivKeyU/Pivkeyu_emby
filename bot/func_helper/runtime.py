from __future__ import annotations

import logging
import os


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return max(minimum, int(raw))
    except (TypeError, ValueError):
        logging.getLogger(__name__).warning("环境变量 %s=%r 不是有效整数，回退到默认值 %s", name, raw, default)
        return default


def configure_runtime_limits(desired_nofile: int | None = None) -> None:
    logger = logging.getLogger(__name__)

    if os.name != "posix":
        return

    if desired_nofile is None:
        desired_nofile = _env_int("PIVKEYU_NOFILE_SOFT", 65535)

    try:
        import resource
    except ImportError:
        return

    try:
        soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
        target_hard = hard_limit
        target_soft = desired_nofile

        if hard_limit != resource.RLIM_INFINITY:
            target_soft = min(target_soft, hard_limit)

        if soft_limit >= target_soft:
            return

        resource.setrlimit(resource.RLIMIT_NOFILE, (target_soft, target_hard))
        logger.info("已将 RLIMIT_NOFILE 从 %s 提升到 %s", soft_limit, target_soft)
    except Exception as exc:
        logger.warning("提升 RLIMIT_NOFILE 失败：%s", exc)
