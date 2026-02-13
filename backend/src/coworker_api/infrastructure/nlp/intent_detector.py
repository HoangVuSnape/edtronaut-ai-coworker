"""
Intent Detector — Heuristic Intent Classification.

Classifies user messages into intent categories using keyword
matching and patterns. For production, consider an LLM-based classifier.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional


class Intent(str, Enum):
    """Possible user intents."""
    QUESTION = "question"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    GREETING = "greeting"
    FAREWELL = "farewell"
    AGREEMENT = "agreement"
    DISAGREEMENT = "disagreement"
    REQUEST_INFO = "request_info"
    SMALL_TALK = "small_talk"
    UNKNOWN = "unknown"


# ── Pattern Maps ──

_INTENT_PATTERNS: dict[Intent, list[str]] = {
    Intent.QUESTION: [
        r"\b(what|how|why|when|where|who|which|can you|could you|would you)\b",
        r"\?$",
    ],
    Intent.PROPOSAL: [
        r"\b(i (think|propose|suggest|recommend)|let's|we (should|could|might)|my plan)\b",
    ],
    Intent.NEGOTIATION: [
        r"\b(offer|deal|terms|counter|negotiate|compromise|trade-off|agree on)\b",
    ],
    Intent.GREETING: [
        r"\b(hello|hi|hey|good (morning|afternoon|evening)|greetings)\b",
    ],
    Intent.FAREWELL: [
        r"\b(bye|goodbye|see you|farewell|take care|talk later)\b",
    ],
    Intent.AGREEMENT: [
        r"\b(i agree|absolutely|exactly|correct|yes|sure|definitely|sounds good)\b",
    ],
    Intent.DISAGREEMENT: [
        r"\b(i disagree|no|nope|i don't think|that's wrong|incorrect)\b",
    ],
    Intent.REQUEST_INFO: [
        r"\b(tell me|show me|can i see|give me|share|provide)\b",
    ],
}


class IntentDetector:
    """Heuristic intent classifier for user messages."""

    def detect(self, text: str) -> Intent:
        """
        Classify the intent of a given text.

        Args:
            text: The user's message.

        Returns:
            The detected Intent enum value.
        """
        text_lower = text.lower().strip()

        if not text_lower:
            return Intent.UNKNOWN

        # Score each intent based on pattern matches
        scores: dict[Intent, int] = {}
        for intent, patterns in _INTENT_PATTERNS.items():
            score = sum(
                1 for pattern in patterns
                if re.search(pattern, text_lower, re.IGNORECASE)
            )
            if score > 0:
                scores[intent] = score

        if not scores:
            return Intent.UNKNOWN

        # Return the highest-scoring intent
        return max(scores, key=scores.get)  # type: ignore

    def detect_with_confidence(self, text: str) -> tuple[Intent, float]:
        """
        Classify intent and return a confidence score (0.0 - 1.0).
        """
        text_lower = text.lower().strip()

        if not text_lower:
            return Intent.UNKNOWN, 0.0

        scores: dict[Intent, int] = {}
        total_matches = 0
        for intent, patterns in _INTENT_PATTERNS.items():
            score = sum(
                1 for pattern in patterns
                if re.search(pattern, text_lower, re.IGNORECASE)
            )
            if score > 0:
                scores[intent] = score
                total_matches += score

        if not scores:
            return Intent.UNKNOWN, 0.0

        best_intent = max(scores, key=scores.get)  # type: ignore
        confidence = scores[best_intent] / max(total_matches, 1)
        return best_intent, round(confidence, 2)
