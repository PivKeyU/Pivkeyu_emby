import asyncio
import contextlib
import os
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from bot import LOGGER


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return max(minimum, int(raw))
    except (TypeError, ValueError):
        LOGGER.warning(f"环境变量 {name}={raw!r} 不是有效整数，回退到默认值 {default}")
        return default


REGISTER_QUEUE_WORKERS = _env_int("PIVKEYU_REGISTER_QUEUE_WORKERS", 1, 1)
REGISTER_QUEUE_MAXSIZE = _env_int("PIVKEYU_REGISTER_QUEUE_MAXSIZE", 64, 1)


@dataclass(slots=True)
class RegisterQueueSubmitResult:
    accepted: bool
    duplicate: bool
    ahead: int = 0
    capacity: int = REGISTER_QUEUE_MAXSIZE


@dataclass(slots=True)
class _RegisterQueueJob:
    user_id: int
    runner: Callable[[], Awaitable[None]]
    enqueued_at: float = field(default_factory=time.monotonic)


class RegisterQueue:
    def __init__(self, workers: int = REGISTER_QUEUE_WORKERS, maxsize: int = REGISTER_QUEUE_MAXSIZE):
        self._worker_count = max(1, int(workers))
        self._queue: asyncio.Queue[_RegisterQueueJob] = asyncio.Queue(maxsize=max(1, int(maxsize)))
        self._workers: list[asyncio.Task] = []
        self._worker_lock = asyncio.Lock()
        self._pending_user_ids: list[int] = []
        self._running_user_ids: set[int] = set()
        self._active_user_ids: set[int] = set()

    @property
    def capacity(self) -> int:
        return self._queue.maxsize

    def _ahead_for_new_job(self) -> int:
        return len(self._running_user_ids) + len(self._pending_user_ids)

    def _ahead_for_existing_user(self, user_id: int) -> int:
        if user_id in self._running_user_ids:
            return 0
        try:
            index = self._pending_user_ids.index(int(user_id))
        except ValueError:
            return self._ahead_for_new_job()
        return len(self._running_user_ids) + index

    async def _ensure_workers(self) -> None:
        async with self._worker_lock:
            active_workers = [task for task in self._workers if not task.done()]
            self._workers = active_workers
            missing_workers = self._worker_count - len(self._workers)
            for index in range(max(0, missing_workers)):
                task = asyncio.create_task(self._worker_loop(), name=f"register-queue-{len(self._workers) + index + 1}")
                self._workers.append(task)

    async def submit(self, user_id: int, runner: Callable[[], Awaitable[None]]) -> RegisterQueueSubmitResult:
        normalized_user_id = int(user_id)
        await self._ensure_workers()

        if normalized_user_id in self._active_user_ids:
            return RegisterQueueSubmitResult(
                accepted=False,
                duplicate=True,
                ahead=self._ahead_for_existing_user(normalized_user_id),
                capacity=self.capacity,
            )

        if self._queue.full():
            return RegisterQueueSubmitResult(
                accepted=False,
                duplicate=False,
                ahead=self._ahead_for_new_job(),
                capacity=self.capacity,
            )

        job = _RegisterQueueJob(user_id=normalized_user_id, runner=runner)
        self._active_user_ids.add(normalized_user_id)
        self._pending_user_ids.append(normalized_user_id)
        self._queue.put_nowait(job)
        return RegisterQueueSubmitResult(
            accepted=True,
            duplicate=False,
            ahead=max(0, self._ahead_for_existing_user(normalized_user_id)),
            capacity=self.capacity,
        )

    async def _worker_loop(self) -> None:
        while True:
            job = await self._queue.get()
            user_id = int(job.user_id)
            try:
                with contextlib.suppress(ValueError):
                    self._pending_user_ids.remove(user_id)
                self._running_user_ids.add(user_id)
                await job.runner()
            except Exception as exc:
                LOGGER.exception(f"注册队列任务执行失败 user={user_id}: {exc}")
            finally:
                self._running_user_ids.discard(user_id)
                self._active_user_ids.discard(user_id)
                self._queue.task_done()

register_create_queue = RegisterQueue()
