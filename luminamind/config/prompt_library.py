"""Prompt library with versioning, task-type mapping, and A/B testing support."""
from __future__ import annotations

import json
import random
from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Task types for prompt preset mapping."""
    CODE_EDITING = "code-editing"
    WEB_RESEARCH = "web-research"
    CODE_REVIEW = "code-review"
    EXPLORATION = "exploration"
    GENERAL = "general"


class PromptVariant(BaseModel):
    """A variant of a prompt (for A/B testing)."""
    variant_id: str
    base_prompt: str
    description: str = ""
    weight: float = 1.0  # Probability weight for A/B selection


class PromptPreset(BaseModel):
    """A versioned prompt preset mapped to task types."""
    preset_id: str
    name: str
    task_types: list[TaskType] = Field(default_factory=list)
    current_variant: PromptVariant
    variants: list[PromptVariant] = Field(default_factory=list)
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

    def add_variant(self, variant: PromptVariant) -> None:
        """Add a new variant to the preset."""
        self.variants.append(variant)
        self.updated_at = datetime.utcnow()

    def select_variant(self, variant_id: str | None = None) -> PromptVariant:
        """Select a variant, randomly by weight if variant_id is None."""
        if variant_id:
            for v in self.variants:
                if v.variant_id == variant_id:
                    return v
            raise ValueError(f"Variant {variant_id} not found")
        # Weight-based selection
        total = sum(v.weight for v in self.variants)
        r = random.uniform(0, total)
        cumsum = 0
        for v in self.variants:
            cumsum += v.weight
            if r <= cumsum:
                return v
        return self.current_variant  # fallback


class PromptLibrary:
    """Prompt library with CRUD operations, versioning, and A/B testing."""

    def __init__(self, storage_path: str | None = None):
        self._presets: dict[str, PromptPreset] = {}
        self._storage_path = storage_path
        if storage_path:
            self._load()

    def create_preset(
        self,
        preset_id: str,
        name: str,
        base_prompt: str,
        task_types: list[TaskType] | None = None,
        description: str = "",
    ) -> PromptPreset:
        """Create a new prompt preset."""
        if preset_id in self._presets:
            raise ValueError(f"Preset {preset_id} already exists")

        variant = PromptVariant(
            variant_id=f"{preset_id}-v1",
            base_prompt=base_prompt,
            description=description,
        )
        preset = PromptPreset(
            preset_id=preset_id,
            name=name,
            task_types=task_types or [],
            current_variant=variant,
            variants=[variant],
        )
        self._presets[preset_id] = preset
        self._save()
        return preset

    def get_preset(self, preset_id: str) -> PromptPreset | None:
        """Get a preset by ID."""
        return self._presets.get(preset_id)

    def update_preset(
        self,
        preset_id: str,
        base_prompt: str | None = None,
        task_types: list[TaskType] | None = None,
    ) -> PromptPreset:
        """Update an existing preset (creates new version)."""
        preset = self._presets.get(preset_id)
        if not preset:
            raise ValueError(f"Preset {preset_id} not found")

        if base_prompt:
            preset.version += 1
            variant = PromptVariant(
                variant_id=f"{preset_id}-v{preset.version}",
                base_prompt=base_prompt,
            )
            preset.current_variant = variant
            preset.variants.append(variant)

        if task_types is not None:
            preset.task_types = task_types

        preset.updated_at = datetime.utcnow()
        self._save()
        return preset

    def delete_preset(self, preset_id: str) -> bool:
        """Soft delete a preset."""
        preset = self._presets.get(preset_id)
        if preset:
            preset.is_active = False
            preset.updated_at = datetime.utcnow()
            self._save()
            return True
        return False

    def list_presets(
        self,
        task_type: TaskType | None = None,
        include_inactive: bool = False,
    ) -> list[PromptPreset]:
        """List presets, optionally filtered by task type."""
        results = []
        for preset in self._presets.values():
            if not include_inactive and not preset.is_active:
                continue
            if task_type and task_type not in preset.task_types:
                continue
            results.append(preset)
        return results

    def get_for_task(
        self,
        task_type: TaskType,
        variant_id: str | None = None,
    ) -> PromptPreset | None:
        """Get the best preset for a task type."""
        presets = self.list_presets(task_type=task_type)
        if not presets:
            return None
        # Return first match; could be enhanced with scoring
        preset = presets[0]
        return preset

    def _save(self) -> None:
        """Persist to storage."""
        if not self._storage_path:
            return
        data = {
            preset_id: preset.model_dump(mode="json")
            for preset_id, preset in self._presets.items()
        }
        with open(self._storage_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _load(self) -> None:
        """Load from storage."""
        if not self._storage_path:
            return
        try:
            with open(self._storage_path, "r") as f:
                data = json.load(f)
            for preset_id, preset_data in data.items():
                self._presets[preset_id] = PromptPreset.model_validate(preset_data)
        except FileNotFoundError:
            pass


# Default presets for LuminaMind agents
DEFAULT_PRESETS: dict[str, dict] = {
    "system": {
        "name": "System Agent",
        "task_types": [TaskType.GENERAL],
        "base_prompt": """You are a deep autonomy agent that plans, researches, and edits codebases.

- Create a todo list before diving into execution.
- Use the filesystem tools to inspect, edit, and organize the repository.
- When exploring unfamiliar directory structures, use the tree_view tool first to get a hierarchical overview.
- Prefer the shell tool for commands that combine multiple steps.
- Keep track of what each subagent is tackling so you can coordinate work.
- Always summarize changes before finishing.
- CRITICAL: 
    - Before stopping, verify that ALL items in your todo list are completed. Do not stop if there are pending tasks.
    - Always use the designated subagent to perform the task. Never do the task yourself.
""",
    },
    "web-research": {
        "name": "Web Research Agent",
        "task_types": [TaskType.WEB_RESEARCH],
        "base_prompt": """You are a focused research specialist.
- Break the assigned question into crisp sub questions.
- Use the web_search and crawling tools to gather facts and cite the strongest sources.
- Return a structured, citation-rich answer that the main agent can use directly.
""",
    },
    "code-executor": {
        "name": "Code Executor Agent",
        "task_types": [TaskType.CODE_EDITING],
        "base_prompt": """You are a senior software engineer with commit access.
- Inspect project files and understand the existing implementation.
- Use shell and replace_in_file to make precise, minimal updates.
- Run commands cautiously; read error output and retry with fixes.
- Summarize every change you make so the main agent can keep context.
- CRITICAL: If you have a list of files to create or modify, DO NOT STOP until you have processed ALL of them.
- CRITICAL: Do not ask for confirmation for every single file if you have a batch of work. Execute the entire batch.
""",
    },
    "code-review": {
        "name": "Code Review Agent",
        "task_types": [TaskType.CODE_REVIEW],
        "base_prompt": """You are a code review specialist.
- Review code for correctness, maintainability, performance, and security.
- Provide specific, actionable feedback with examples.
- Focus on logic errors, edge cases, and potential bugs.
""",
    },
}


def create_prompt_library(storage_path: str | None = None) -> PromptLibrary:
    """Factory to create prompt library."""
    return PromptLibrary(storage_path=storage_path)


def create_default_library(storage_path: str | None = None) -> PromptLibrary:
    """Create prompt library with default presets."""
    library = PromptLibrary(storage_path=storage_path)

    for preset_id, preset_data in DEFAULT_PRESETS.items():
        library.create_preset(
            preset_id=preset_id,
            name=preset_data["name"],
            base_prompt=preset_data["base_prompt"],
            task_types=preset_data["task_types"],
        )

    return library