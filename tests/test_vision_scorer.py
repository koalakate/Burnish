"""Tests for GPT-4o vision scoring service."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from services.vision.rubric import SLIDE_SCORING_RUBRIC
from services.vision.scorer import (
    VisionScore,
    VisionSettings,
    _build_messages,
    _parse_vision_response,
    _thumbnail_cache_key,
    score_deck,
    score_slide,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # Minimal fake PNG bytes


def _make_openai_response(scores: dict) -> SimpleNamespace:
    """Build a mock OpenAI chat completion response."""
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=json.dumps(scores))
            )
        ]
    )


def _make_mock_client(scores: dict | None = None) -> MagicMock:
    """Create a mock OpenAI client that returns the given scores."""
    if scores is None:
        scores = {
            "visual_quality": 8,
            "layout_balance": 7,
            "readability": 9,
            "overall_impression": 8,
        }
    client = MagicMock()
    client.chat.completions.create.return_value = _make_openai_response(scores)
    return client


# ---------------------------------------------------------------------------
# VisionScore model tests
# ---------------------------------------------------------------------------


class TestVisionScore:
    def test_construction(self):
        score = VisionScore(
            visual_quality=8, layout_balance=7, readability=9, overall_impression=8
        )
        assert score.visual_quality == 8
        assert score.layout_balance == 7
        assert score.readability == 9
        assert score.overall_impression == 8

    def test_average(self):
        score = VisionScore(
            visual_quality=8, layout_balance=6, readability=10, overall_impression=8
        )
        assert score.average == 8.0

    def test_json_roundtrip(self):
        score = VisionScore(
            visual_quality=7, layout_balance=8, readability=6, overall_impression=7
        )
        dumped = score.model_dump_json()
        restored = VisionScore.model_validate_json(dumped)
        assert restored == score

    def test_validation_bounds(self):
        with pytest.raises(Exception):
            VisionScore(
                visual_quality=0, layout_balance=5, readability=5, overall_impression=5
            )
        with pytest.raises(Exception):
            VisionScore(
                visual_quality=11, layout_balance=5, readability=5, overall_impression=5
            )


# ---------------------------------------------------------------------------
# Rubric tests
# ---------------------------------------------------------------------------


class TestRubric:
    def test_rubric_contains_dimensions(self):
        assert "Visual Quality" in SLIDE_SCORING_RUBRIC
        assert "Layout Balance" in SLIDE_SCORING_RUBRIC
        assert "Readability" in SLIDE_SCORING_RUBRIC
        assert "Overall Impression" in SLIDE_SCORING_RUBRIC

    def test_rubric_requests_json(self):
        assert "JSON" in SLIDE_SCORING_RUBRIC
        assert "visual_quality" in SLIDE_SCORING_RUBRIC


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_cache_key_deterministic(self):
        key1 = _thumbnail_cache_key(SAMPLE_PNG)
        key2 = _thumbnail_cache_key(SAMPLE_PNG)
        assert key1 == key2
        assert key1.startswith("burnish:vision:")

    def test_cache_key_differs_for_different_input(self):
        key1 = _thumbnail_cache_key(b"image1")
        key2 = _thumbnail_cache_key(b"image2")
        assert key1 != key2

    def test_build_messages_structure(self):
        msgs = _build_messages(SAMPLE_PNG, "Rate this slide.")
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"
        content = msgs[0]["content"]
        assert len(content) == 2
        assert content[0]["type"] == "text"
        assert content[0]["text"] == "Rate this slide."
        assert content[1]["type"] == "image_url"
        assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")

    def test_parse_vision_response_plain_json(self):
        raw = json.dumps(
            {"visual_quality": 8, "layout_balance": 7,
             "readability": 9, "overall_impression": 8}
        )
        score = _parse_vision_response(raw)
        assert score.visual_quality == 8
        assert score.readability == 9

    def test_parse_vision_response_with_code_fence(self):
        inner = json.dumps(
            {"visual_quality": 6, "layout_balance": 5,
             "readability": 7, "overall_impression": 6}
        )
        raw = f"```json\n{inner}\n```"
        score = _parse_vision_response(raw)
        assert score.visual_quality == 6
        assert score.overall_impression == 6


# ---------------------------------------------------------------------------
# score_slide tests
# ---------------------------------------------------------------------------


class TestScoreSlide:
    @pytest.mark.asyncio
    async def test_score_slide_calls_openai(self):
        client = _make_mock_client()
        score = await score_slide(SAMPLE_PNG, openai_client=client)
        assert isinstance(score, VisionScore)
        assert score.visual_quality == 8
        client.chat.completions.create.assert_called_once()
        call_kwargs = client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "gpt-4o"
        assert call_kwargs.kwargs["temperature"] == 0.0

    @pytest.mark.asyncio
    async def test_score_slide_prompt_construction(self):
        client = _make_mock_client()
        custom_rubric = "Custom rubric text"
        await score_slide(
            SAMPLE_PNG, rubric=custom_rubric, openai_client=client
        )
        call_kwargs = client.chat.completions.create.call_args
        messages = call_kwargs.kwargs["messages"]
        assert messages[0]["content"][0]["text"] == custom_rubric

    @pytest.mark.asyncio
    async def test_score_slide_with_cache_hit(self):
        """When Redis has a cached score, OpenAI should NOT be called."""
        cached_score = VisionScore(
            visual_quality=10,
            layout_balance=10,
            readability=10,
            overall_impression=10,
        )
        redis_mock = MagicMock()
        redis_mock.get.return_value = (
            cached_score.model_dump_json().encode("utf-8")
        )

        client = _make_mock_client()
        score = await score_slide(
            SAMPLE_PNG, openai_client=client, redis_client=redis_mock
        )

        assert score.visual_quality == 10
        client.chat.completions.create.assert_not_called()
        redis_mock.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_score_slide_with_cache_miss(self):
        """When Redis returns None, OpenAI is called and result cached."""
        redis_mock = MagicMock()
        redis_mock.get.return_value = None

        client = _make_mock_client()
        settings = VisionSettings(vision_cache_ttl=3600)
        score = await score_slide(
            SAMPLE_PNG,
            openai_client=client,
            redis_client=redis_mock,
            settings=settings,
        )

        assert score.visual_quality == 8
        client.chat.completions.create.assert_called_once()
        redis_mock.set.assert_called_once()
        set_call = redis_mock.set.call_args
        assert set_call.args[0].startswith("burnish:vision:")
        assert set_call.kwargs["ex"] == 3600

    @pytest.mark.asyncio
    async def test_score_slide_no_redis(self):
        """When redis_client is None, scoring works without caching."""
        client = _make_mock_client()
        score = await score_slide(
            SAMPLE_PNG, openai_client=client, redis_client=None
        )
        assert isinstance(score, VisionScore)
        assert score.visual_quality == 8


# ---------------------------------------------------------------------------
# score_deck tests
# ---------------------------------------------------------------------------


class TestScoreDeck:
    @pytest.mark.asyncio
    async def test_score_deck_parallel(self):
        """Score multiple slides -- all should be scored."""
        thumbnails = [SAMPLE_PNG, SAMPLE_PNG + b"x", SAMPLE_PNG + b"xy"]
        client = _make_mock_client()
        scores = await score_deck(thumbnails, openai_client=client)
        assert len(scores) == 3
        assert all(isinstance(s, VisionScore) for s in scores)
        assert client.chat.completions.create.call_count == 3

    @pytest.mark.asyncio
    async def test_score_deck_empty(self):
        """Empty thumbnail list returns empty scores list."""
        client = _make_mock_client()
        scores = await score_deck([], openai_client=client)
        assert scores == []
        client.chat.completions.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_score_deck_respects_concurrency_limit(self):
        """Verify that semaphore limits concurrent calls."""
        settings = VisionSettings(vision_max_concurrent=2)
        thumbnails = [SAMPLE_PNG] * 5
        client = _make_mock_client()

        scores = await score_deck(
            thumbnails, openai_client=client, settings=settings
        )
        assert len(scores) == 5
        assert client.chat.completions.create.call_count == 5

    @pytest.mark.asyncio
    async def test_score_deck_preserves_order(self):
        """Scores should be returned in same order as thumbnails."""
        call_count = 0

        def fake_create(**kwargs):
            nonlocal call_count
            call_count += 1
            return _make_openai_response(
                {
                    "visual_quality": call_count,
                    "layout_balance": call_count,
                    "readability": call_count,
                    "overall_impression": call_count,
                }
            )

        client = MagicMock()
        client.chat.completions.create.side_effect = fake_create

        thumbnails = [b"slide1", b"slide2", b"slide3"]
        scores = await score_deck(
            thumbnails, openai_client=client
        )
        assert len(scores) == 3
        score_values = sorted(s.visual_quality for s in scores)
        assert score_values == [1, 2, 3]
