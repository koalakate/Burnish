"""BullMQ worker entry point — registers and runs all job processors.

Usage:
    python -m services.workers.main
"""

from __future__ import annotations

import asyncio
import logging
import signal
from typing import Any

from bullmq import Worker

from services.workers.check_worker import process_check_job
from services.workers.correction_worker import process_correction_job
from services.workers.ingestion_worker import process_ingestion_job

logger = logging.getLogger(__name__)

REDIS_URL = "redis://localhost:6379"

QUEUE_CONFIG: list[dict[str, Any]] = [
    {"name": "ingestion", "processor": process_ingestion_job},
    {"name": "check", "processor": process_check_job},
    {"name": "correction", "processor": process_correction_job},
]


async def _run_workers() -> None:
    """Start all queue workers and wait until shutdown signal."""
    workers: list[Worker] = []
    for cfg in QUEUE_CONFIG:
        w = Worker(
            cfg["name"],
            cfg["processor"],
            {"connection": REDIS_URL},
        )
        workers.append(w)
        logger.info("Started worker for queue: %s", cfg["name"])

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    await stop_event.wait()

    logger.info("Shutting down workers...")
    for w in workers:
        await w.close()
    logger.info("All workers stopped.")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    asyncio.run(_run_workers())


if __name__ == "__main__":
    main()
