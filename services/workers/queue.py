"""Queue helper — enqueue jobs to BullMQ queues from API routes."""

from __future__ import annotations

import os
from typing import Any

from bullmq import Queue

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

_queues: dict[str, Queue] = {}


def _get_queue(name: str) -> Queue:
    """Return a singleton Queue instance for the given queue name."""
    if name not in _queues:
        _queues[name] = Queue(name, {"connection": REDIS_URL})
    return _queues[name]


async def enqueue_job(queue_name: str, data: dict[str, Any]) -> str:
    """Add a job to the named BullMQ queue and return the job ID."""
    queue = _get_queue(queue_name)
    job = await queue.add(queue_name, data)
    return str(job.id)
