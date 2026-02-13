"""
Prompt Registry — Factory for retrieving persona prompts.

Provides a unified interface to load any persona's system prompt
and few-shot examples by name.
"""

from __future__ import annotations

from typing import Any

from coworker_api.domain.prompts import gucci_ceo, gucci_chro, gucci_eb_ic
from coworker_api.domain.exceptions import NPCNotFoundError


# ── Registry ──

_PERSONA_REGISTRY: dict[str, Any] = {
    gucci_ceo.PERSONA_NAME: gucci_ceo,
    gucci_chro.PERSONA_NAME: gucci_chro,
    gucci_eb_ic.PERSONA_NAME: gucci_eb_ic,
}


def get_persona_prompt(persona_name: str) -> str:
    """
    Retrieve the system prompt for a given persona.

    Args:
        persona_name: The identifier of the persona (e.g., "gucci_ceo").

    Returns:
        The system prompt string.

    Raises:
        NPCNotFoundError: If the persona is not registered.
    """
    module = _PERSONA_REGISTRY.get(persona_name)
    if module is None:
        raise NPCNotFoundError(f"Persona '{persona_name}' is not registered.")
    return module.get_system_prompt()


def get_persona_few_shots(persona_name: str) -> list[dict[str, str]]:
    """Retrieve the few-shot examples for a persona."""
    module = _PERSONA_REGISTRY.get(persona_name)
    if module is None:
        raise NPCNotFoundError(f"Persona '{persona_name}' is not registered.")
    return module.get_few_shot_examples()


def get_persona_display_name(persona_name: str) -> str:
    """Retrieve the human-readable display name for a persona."""
    module = _PERSONA_REGISTRY.get(persona_name)
    if module is None:
        raise NPCNotFoundError(f"Persona '{persona_name}' is not registered.")
    return module.PERSONA_DISPLAY_NAME


def list_personas() -> list[dict[str, str]]:
    """List all registered personas with their names and roles."""
    result = []
    for key, module in _PERSONA_REGISTRY.items():
        result.append({
            "name": key,
            "display_name": module.PERSONA_DISPLAY_NAME,
            "role": module.PERSONA_ROLE,
        })
    return result
