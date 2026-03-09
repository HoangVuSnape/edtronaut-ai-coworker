"""
Director Service — Supervisor & Analysis.

Use-case: A meta-agent that oversees the conversation,
analyzes quality, and provides feedback or interventions.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from coworker_api.domain.models import Conversation, Speaker
from coworker_api.domain.ports import LLMPort

logger = logging.getLogger(__name__)


DIRECTOR_SYSTEM_PROMPT = """You are the Director — a hidden supervisor overseeing a workplace \
simulation between a user and an AI NPC. Your job is to analyze the conversation quality.

Your responsibilities:
1. Assess the user's communication effectiveness (clarity, confidence, professionalism).
2. Evaluate whether the NPC is staying in character.
3. Identify if the user needs guidance (hints).
4. Flag any conversation that is going off-track or becoming unproductive.

Output your analysis as structured JSON:
{
    "user_assessment": {
        "confidence_level": 0.0-1.0,
        "professionalism": 0.0-1.0,
        "clarity": 0.0-1.0,
        "communication_style": "assertive|passive|aggressive|passive-aggressive"
    },
    "npc_assessment": {
        "in_character": true/false,
        "response_quality": 0.0-1.0
    },
    "intervention": {
        "needed": true/false,
        "type": "hint|redirect|none",
        "message": "optional message for the user or NPC"
    },
    "overall_score": 0.0-1.0
}
"""


class DirectorService:
    """
    Supervisor that analyzes the ongoing conversation and provides
    meta-feedback or instructions.
    """

    def __init__(self, llm_port: LLMPort):
        self._llm = llm_port

    async def analyze_conversation(
        self,
        conversation: Conversation,
        *,
        last_n_turns: int = 6,
    ) -> dict[str, Any]:
        """
        Analyze the recent conversation turns and return a structured assessment.

        Args:
            conversation: The full conversation object.
            last_n_turns: Number of recent turns to analyze.

        Returns:
            Dict with user_assessment, npc_assessment, intervention, overall_score.
        """
        recent_turns = conversation.turns[-last_n_turns:]
        if not recent_turns:
            return self._empty_assessment()

        # Build analysis prompt
        history_text = "\n".join(
            f"{t.speaker.value.capitalize()}: {t.content}"
            for t in recent_turns
        )

        prompt = f"""Analyze the following conversation excerpt between a User and an NPC \
named "{conversation.npc.name}" ({conversation.npc.role_title}).

Conversation:
{history_text}

Provide your analysis."""

        logger.info(
            "Director analyzing conversation",
            extra={"session_id": conversation.id, "turns_analyzed": len(recent_turns)},
        )

        response = await self._llm.generate(
            prompt=prompt,
            system_prompt=DIRECTOR_SYSTEM_PROMPT,
            temperature=0.3,  # Low temperature for consistent analysis
        )

        # Parse the response (in production, use structured output / JSON mode)
        return {
            "raw_analysis": response,
            "session_id": conversation.id,
            "turns_analyzed": len(recent_turns),
        }

    async def should_intervene(self, conversation: Conversation) -> Optional[str]:
        """
        Quick check if an intervention is needed.

        Returns an intervention hint message, or None if not needed.
        """
        if conversation.turn_count < 2:
            return None  # Too early to intervene

        analysis = await self.analyze_conversation(conversation, last_n_turns=4)
        # In a production system, parse the JSON and check intervention.needed
        return None  # Placeholder — will be enhanced with structured output parsing

    def _empty_assessment(self) -> dict[str, Any]:
        """Return a default empty assessment."""
        return {
            "user_assessment": {
                "confidence_level": 0.0,
                "professionalism": 0.0,
                "clarity": 0.0,
                "communication_style": "unknown",
            },
            "npc_assessment": {
                "in_character": True,
                "response_quality": 0.0,
            },
            "intervention": {
                "needed": False,
                "type": "none",
                "message": "",
            },
            "overall_score": 0.0,
        }
