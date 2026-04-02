"""Queue helper — enqueue jobs to BullMQ queues from API routes."""

from __future__ import annotations

from typing import Any

from bullmq import Queue

REDIS_URL = "redis://localhost:6379"


async def enqueue_job(queue_name: str, data: dict[str, Any]) -> str:
    """Add a job to the named BullMQ queue and return the job ID."""
    queue = Queue(queue_name, {"connection": REDIS_URL})
    job = await queue.add(queue_name, data)
    await queue.close()
    return str(job.id)
