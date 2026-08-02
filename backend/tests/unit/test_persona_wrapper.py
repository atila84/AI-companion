"""Unit tests for the persona placeholder module."""

from src.personas.base import BASE_SYSTEM_INSTRUCTIONS, PersonaConfig, compose_system_prompt


def test_compose_system_prompt_default_persona_returns_base_instructions() -> None:
    prompt = compose_system_prompt(PersonaConfig())

    assert prompt == BASE_SYSTEM_INSTRUCTIONS


def test_compose_system_prompt_appends_persona_instructions() -> None:
    persona = PersonaConfig(persona_instructions="Be playful and curious.")

    prompt = compose_system_prompt(persona)

    assert prompt == f"{BASE_SYSTEM_INSTRUCTIONS}\n\nBe playful and curious."
