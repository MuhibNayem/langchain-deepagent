"""Dynamic prompt composition from base, context, and personality modules.

Per D-05: Dynamic composition assembles prompts from base + context + personality modules.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class PersonalityProfile(BaseModel):
    """Personality variation for prompt composition."""
    profile_id: str
    name: str
    tone: Literal["formal", "casual", "technical", "colloquial"] = "technical"
    style: Literal["concise", "detailed", "balanced"] = "balanced"
    focus_areas: list[str] = Field(default_factory=list)  # e.g., ["security", "performance"]
    system_hints: list[str] = Field(default_factory=list)  # Additional instructions

    def apply_to(self, base_prompt: str) -> str:
        """Apply personality to base prompt."""
        lines = [base_prompt, ""]

        # Tone modifier
        if self.tone == "formal":
            lines.append("- Communicate with precision and professional terminology")
        elif self.tone == "casual":
            lines.append("- Be friendly and approachable in responses")
        elif self.tone == "technical":
            lines.append("- Use precise technical language and cite specific patterns")
        elif self.tone == "colloquial":
            lines.append("- Use clear, accessible language avoiding jargon where possible")

        # Style modifier
        if self.style == "concise":
            lines.append("- Keep responses brief and to the point")
        elif self.style == "detailed":
            lines.append("- Provide thorough explanations with examples")

        # Focus areas
        if self.focus_areas:
            lines.append(f"- Pay special attention to: {', '.join(self.focus_areas)}")

        # System hints
        for hint in self.system_hints:
            lines.append(f"- {hint}")

        return "\n".join(lines)


class ContextBundle(BaseModel):
    """Context information for prompt composition."""
    task_type: str
    session_id: str | None = None
    current_working_directory: str | None = None
    recent_files: list[str] = Field(default_factory=list)
    active_task: str | None = None
    tool_access: list[str] = Field(default_factory=list)  # Available tool names
    evaluator_score: float | None = None  # From previous iteration if any

    def format_context(self) -> str:
        """Format context as instruction string."""
        lines = []

        if self.current_working_directory:
            lines.append(f"Working directory: {self.current_working_directory}")

        if self.active_task:
            lines.append(f"Current task: {self.active_task}")

        if self.recent_files:
            lines.append(f"Recently modified: {', '.join(self.recent_files[-5:])}")

        if self.tool_access:
            lines.append(f"Available tools: {', '.join(self.tool_access)}")

        if self.evaluator_score is not None:
            lines.append(f"Previous quality score: {self.evaluator_score:.2f}")

        return "\n".join(lines) if lines else ""


# Default personality profiles
DEFAULT_PERSONALITIES: dict[str, PersonalityProfile] = {
    "default": PersonalityProfile(
        profile_id="default",
        name="Default",
        tone="technical",
        style="balanced",
        focus_areas=[],
    ),
    "security-focused": PersonalityProfile(
        profile_id="security-focused",
        name="Security Focused",
        tone="formal",
        style="detailed",
        focus_areas=["security", "access control", "validation"],
    ),
    "performance-focused": PersonalityProfile(
        profile_id="performance-focused",
        name="Performance Focused",
        tone="technical",
        style="concise",
        focus_areas=["performance", "efficiency", "caching"],
    ),
    "debugging": PersonalityProfile(
        profile_id="debugging",
        name="Debugging Mode",
        tone="casual",
        style="detailed",
        focus_areas=["bugs", "errors", "edge cases"],
    ),
}


class PromptComposer:
    """Composes dynamic prompts from base, context, and personality modules.

    Per D-05: Context-aware assembly considers task type, session state, and workspace.
    """

    def __init__(
        self,
        prompt_library: "PromptLibrary | None" = None,
        personality_profiles: dict[str, PersonalityProfile] | None = None,
    ):
        self._library = prompt_library
        self._personalities = personality_profiles or DEFAULT_PERSONALITIES

    def compose(
        self,
        preset_id: str | None = None,
        task_type: str | None = None,
        context: ContextBundle | None = None,
        personality: str | None = None,
        system_instructions: list[str] | None = None,
    ) -> str:
        """Compose a prompt from components.

        Args:
            preset_id: ID of preset from library (or infer from task_type)
            task_type: Task type to look up preset
            context: Context bundle for dynamic assembly
            personality: Personality profile ID
            system_instructions: Additional system-level instructions
        """
        # Get base prompt from library
        if preset_id and self._library:
            preset = self._library.get_preset(preset_id)
        elif task_type and self._library:
            from luminamind.config.prompt_library import TaskType
            preset = self._library.get_for_task(TaskType(task_type))
        else:
            preset = None

        if preset:
            base = preset.current_variant.base_prompt
        else:
            base = "You are a helpful AI assistant."

        # Apply personality
        personality_profile = self._personalities.get(personality or "default")
        if personality_profile:
            prompt = personality_profile.apply_to(base)
        else:
            prompt = base

        # Prepend system instructions
        if system_instructions:
            system_block = "\n".join(f"- {s}" for s in system_instructions)
            prompt = f"System instructions:\n{system_block}\n\n{prompt}"

        # Append context
        if context:
            context_str = context.format_context()
            if context_str:
                prompt = f"{prompt}\n\nContext:\n{context_str}"

        return prompt

    def compose_for_agent(
        self,
        agent_type: str,
        context: ContextBundle | None = None,
        personality: str | None = None,
    ) -> str:
        """Convenience method: compose prompt for known agent types."""
        preset_map = {
            "system": "system",
            "web-research": "web-research",
            "code-executor": "code-executor",
            "code-review": "code-review",
        }
        preset_id = preset_map.get(agent_type)
        return self.compose(
            preset_id=preset_id,
            task_type=context.task_type if context else None,
            context=context,
            personality=personality,
        )

    def register_personality(self, profile: PersonalityProfile) -> None:
        """Register a new personality profile."""
        self._personalities[profile.profile_id] = profile

    def list_personalities(self) -> list[PersonalityProfile]:
        """List available personality profiles."""
        return list(self._personalities.values())


def compose_prompt(
    preset_id: str | None = None,
    task_type: str | None = None,
    context: dict | None = None,
    personality: str | None = None,
) -> str:
    """Standalone function for simple prompt composition."""
    composer = PromptComposer()
    ctx = ContextBundle(**context) if context else None
    return composer.compose(
        preset_id=preset_id,
        task_type=task_type,
        context=ctx,
        personality=personality,
    )


__all__ = [
    "PromptComposer",
    "PersonalityProfile",
    "ContextBundle",
    "DEFAULT_PERSONALITIES",
    "compose_prompt",
]
