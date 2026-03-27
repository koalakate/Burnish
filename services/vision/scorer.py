"""GPT-4o vision scoring: send slide thumbnails for quality evaluation."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from services.vision.rubric import SLIDE_SCORING_RUBRIC

logger = logging.getLogger(__name__)


class VisionSettings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    vision_max_concurrent: int = 5
    redis_url: str = "redis://localhost:6379/0"
    vision_cache_ttl: int = 86400  # 24 hours


class VisionScore(BaseModel):
    """Scores returned by GPT-4o for a single slide thumbnail."""

    visual_quality: int = Field(ge=1, le=10)
    layout_balance: int = Field(ge=1, le=10)
    readability: int = Field(ge=1, le=10)
    overall_impression: int = Field(ge=1, le=10)

    @property
    def average(self) -> float:
        return (
            self.visual_quality
            + self.layout_balance
            + self.readability
            + self.overall_impression
        ) / 4.0


def _thumbnail_cache_key(thumbnail_png: bytes) -> str:
    """Hash thumbnail bytes for use as a cache key."""
    digest = hashlib.sha256(thumbnail_png).hexdigest()
    return f"burnish:vision:{digest}"


def _build_messages(thumbnail_png: bytes, rubric: str) -> list[dict[str, Any]]:
    """Build the OpenAI chat messages for vision scoring."""
    b64_image = base64.b64encode(thumbnail_png).decode("utf-8")
    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": rubric},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{b64_image}",
                        "detail": "high",
                    },
                },
            ],
        }
    ]


def _parse_vision_response(content: str) -> VisionScore:
    """Parse the JSON response from GPT-4o into a VisionScore."""
    text = content.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [ln for ln in lines if not ln.startswith("```")]
        text = "\n".join(lines).strip()
    data = json.loads(text)
    return VisionScore(**data)


async def _get_cached_score(
    redis_client: Any, cache_key: str
) -> VisionScore | None:
    """Try to fetch a cached VisionScore from Redis."""
    if redis_client is None:
        return None
    try:
        cached = await asyncio.to_thread(redis_client.get, cache_key)
        if cached is not None:
            raw = cached if isinstance(cached, str) else cached.decode("utf-8")
            return VisionScore.model_validate_json(raw)
    except Exception:
        logger.warning("Redis cache read failed for %s", cache_key, exc_info=True)
    return None


async def _set_cached_score(
    redis_client: Any, cache_key: str, score: VisionScore, ttl: int
) -> None:
    """Store a VisionScore in Redis cache."""
    if redis_client is None:
        return
    try:
        await asyncio.to_thread(
            redis_client.set, cache_key, score.model_dump_json(), ex=ttl
        )
    except Exception:
        logger.warning("Redis cache write failed for %s", cache_key, exc_info=True)


async def score_slide(
    thumbnail_png: bytes,
    rubric: str = SLIDE_SCORING_RUBRIC,
    *,
    openai_client: Any = None,
    redis_client: Any = None,
    settings: VisionSettings | None = None,
) -> VisionScore:
    """Score a single slide thumbnail using GPT-4o vision.

    Args:
        thumbnail_png: Raw PNG bytes of the slide thumbnail.
        rubric: Prompt template for the scoring rubric.
        openai_client: An OpenAI client instance (injected for testability).
        redis_client: A Redis client instance for caching (optional).
        settings: Vision service settings.

    Returns:
        VisionScore with ratings on four dimensions.
    """
    cfg = settings or VisionSettings()

    # Check cache first
    cache_key = _thumbnail_cache_key(thumbnail_png)
    cached = await _get_cached_score(redis_client, cache_key)
    if cached is not None:
        return cached

    # Build and send request
    if openai_client is None:
        from openai import OpenAI

        openai_client = OpenAI(api_key=cfg.openai_api_key)

    messages = _build_messages(thumbnail_png, rubric)

    response = await asyncio.to_thread(
        openai_client.chat.completions.create,
        model=cfg.openai_model,
        messages=messages,
        max_tokens=200,
        temperature=0.0,
    )

    content = response.choices[0].message.content or ""
    score = _parse_vision_response(content)

    # Cache the result
    await _set_cached_score(redis_client, cache_key, score, cfg.vision_cache_ttl)

    return score


async def score_deck(
    thumbnails: list[bytes],
    rubric: str = SLIDE_SCORING_RUBRIC,
    *,
    openai_client: Any = None,
    redis_client: Any = None,
    settings: VisionSettings | None = None,
) -> list[VisionScore]:
    """Score all slides in a deck, with rate-limited parallelism.

    Args:
        thumbnails: List of PNG thumbnail bytes, one per slide.
        rubric: Prompt template for the scoring rubric.
        openai_client: An OpenAI client instance (injected for testability).
        redis_client: A Redis client instance for caching (optional).
        settings: Vision service settings.

    Returns:
        List of VisionScore, one per slide, in order.
    """
    cfg = settings or VisionSettings()
    semaphore = asyncio.Semaphore(cfg.vision_max_concurrent)

    async def _score_with_limit(thumb: bytes) -> VisionScore:
        async with semaphore:
            return await score_slide(
                thumb,
                rubric,
                openai_client=openai_client,
                redis_client=redis_client,
                settings=cfg,
            )

    tasks = [_score_with_limit(thumb) for thumb in thumbnails]
    return list(await asyncio.gather(*tasks))
