"""GPT-4o vision scoring service for slide quality evaluation."""

from services.vision.rubric import SLIDE_SCORING_RUBRIC
from services.vision.scorer import VisionScore, score_deck, score_slide

__all__ = [
    "SLIDE_SCORING_RUBRIC",
    "VisionScore",
    "score_deck",
    "score_slide",
]
