"""Shared test configuration."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

# Ensure repo root is on sys.path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def _mock_enqueue_job(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent tests from connecting to a real Redis/BullMQ instance."""
    mock = AsyncMock(return_value="mock-job-id")
    monkeypatch.setattr("services.workers.queue.enqueue_job", mock)
    monkeypatch.setattr("services.api.routers.corrections.enqueue_job", mock)
    monkeypatch.setattr("services.api.routers.checks.enqueue_job", mock)
