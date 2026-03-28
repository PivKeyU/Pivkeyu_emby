from __future__ import annotations

import logging
import os


def configure_runtime_limits(desired_nofile: int = 65535) -> None:
    logger = logging.getLogger(__name__)

    if os.name != "posix":
        return

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
        logger.info("Raised RLIMIT_NOFILE from %s to %s", soft_limit, target_soft)
    except Exception as exc:
        logger.warning("Failed to raise RLIMIT_NOFILE: %s", exc)
