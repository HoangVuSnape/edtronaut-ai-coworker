"""
Evaluation Service — Assessment Engine.

(Optional) Evaluates the user's performance based on rubrics or
competencies after a simulation session.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from coworker_api.domain.models import Conversation
from coworker_api.domain.ports import LLMPort

logger = logging.getLogger(__name__)


EVALUATION_SYSTEM_PROMPT = """You are an evaluation expert assessing a user's performance \
in a workplace simulation. Analyze the full conversation and score the user on the \
following competencies:

1. **Communication** (0-10): Clarity, professionalism, active listening.
2. **Negotiation** (0-10): Assertiveness, compromise ability, value creation.
3. **Decision Making** (0-10): Analytical thinking, risk assessment, timeliness.
4. **Emotional Intelligence** (0-10): Empathy, self-awareness, conflict management.
5. **Strategic Thinking** (0-10): Big-picture awareness, long-term planning.

Output your evaluation as JSON:
{
    "scores": {
        "communication": 0,
        "negotiation": 0,
        "decision_making": 0,
        "emotional_intelligence": 0,
        "strategic_thinking": 0
    },
    "overall_score": 0.0,
    "strengths": ["..."],
    "areas_for_improvement": ["..."],
    "summary": "..."
}
"""


class EvaluationService:
    """Evaluates user performance on rubrics/competencies after a session."""

    def __init__(self, llm_port: LLMPort):
        self._llm = llm_port

    async def evaluate_session(
        self,
        conversation: Conversation,
    ) -> dict[str, Any]:
        """
        Evaluate a completed conversation session.

        Args:
            conversation: The full conversation to evaluate.

        Returns:
            Dict with scores, strengths, areas_for_improvement, and summary.
        """
        if conversation.turn_count == 0:
            return self._empty_evaluation()

        # Build the conversation transcript
        transcript = "\n".join(
            f"{t.speaker.value.capitalize()}: {t.content}"
            for t in conversation.turns
        )

        prompt = f"""Evaluate the user's performance in this workplace simulation.

NPC: {conversation.npc.name} ({conversation.npc.role_title})
Total Turns: {conversation.turn_count}

Full Transcript:
{transcript}

Provide your detailed evaluation."""

        logger.info(
            "Evaluating session",
            extra={"session_id": conversation.id, "turns": conversation.turn_count},
        )

        response = await self._llm.generate(
            prompt=prompt,
            system_prompt=EVALUATION_SYSTEM_PROMPT,
            temperature=0.2,  # Very low for consistent evaluations
        )

        return {
            "raw_evaluation": response,
            "session_id": conversation.id,
            "npc_name": conversation.npc.name,
            "total_turns": conversation.turn_count,
        }

    def _empty_evaluation(self) -> dict[str, Any]:
        """Return a default empty evaluation."""
        return {
            "scores": {
                "communication": 0,
                "negotiation": 0,
                "decision_making": 0,
                "emotional_intelligence": 0,
                "strategic_thinking": 0,
            },
            "overall_score": 0.0,
            "strengths": [],
            "areas_for_improvement": [],
            "summary": "No turns to evaluate.",
        }
