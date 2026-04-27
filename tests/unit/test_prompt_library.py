import pytest
from luminamind.config.prompt_library import (
    PromptLibrary,
    PromptPreset,
    PromptVariant,
    TaskType,
    create_prompt_library,
    create_default_library,
)


@pytest.fixture
def library():
    return create_prompt_library()


class TestPromptPresetModel:
    """Test PromptPreset serialization and versioning."""

    def test_prompt_preset_serializes_to_dict(self, library):
        """PromptPreset serializes to dict with all fields."""
        preset = library.create_preset(
            preset_id="test-preset",
            name="Test Preset",
            base_prompt="Test prompt content",
            task_types=[TaskType.GENERAL],
        )
        data = preset.model_dump(mode="json")
        assert data["preset_id"] == "test-preset"
        assert data["name"] == "Test Preset"
        assert data["version"] == 1
        assert len(data["variants"]) == 1

    def test_prompt_variant_stores_base_and_variations(self, library):
        """PromptVariant stores base_prompt and variations."""
        preset = library.create_preset(
            preset_id="test-variant",
            name="Test Variant",
            base_prompt="Original prompt",
            task_types=[TaskType.CODE_EDITING],
        )
        variant = PromptVariant(
            variant_id="variant-a",
            base_prompt="Variant A prompt",
            description="A/B test variant",
            weight=1.0,
        )
        preset.add_variant(variant)
        assert len(preset.variants) == 2
        assert preset.variants[1].variant_id == "variant-a"

    def test_version_tracking_increments_correctly(self, library):
        """Version tracking increments correctly on update."""
        library.create_preset("test-ver", "Test", "Original")
        preset = library.update_preset("test-ver", base_prompt="Updated")
        assert preset.version == 2
        preset = library.update_preset("test-ver", base_prompt="Updated Again")
        assert preset.version == 3

    def test_task_type_mapping_stores_multiple_types(self, library):
        """Task type mapping stores multiple task types per preset."""
        preset = library.create_preset(
            preset_id="multi-task",
            name="Multi Task",
            base_prompt="Content",
            task_types=[TaskType.CODE_EDITING, TaskType.CODE_REVIEW],
        )
        assert TaskType.CODE_EDITING in preset.task_types
        assert TaskType.CODE_REVIEW in preset.task_types


class TestPromptLibraryCRUD:
    """Test PromptLibrary CRUD operations with versioning."""

    def test_create_preset_adds_to_library(self, library):
        """Create preset adds to library."""
        preset = library.create_preset(
            preset_id="crud-test",
            name="CRUD Test",
            base_prompt="Test content",
            task_types=[TaskType.GENERAL],
        )
        assert preset is not None
        assert library.get_preset("crud-test") is not None

    def test_get_preset_by_id_returns_correct_preset(self, library):
        """Get preset by ID returns correct preset."""
        library.create_preset("test-get", "Test", "Content")
        preset = library.get_preset("test-get")
        assert preset is not None
        assert preset.preset_id == "test-get"

    def test_update_preset_increments_version_and_updates_timestamp(self, library):
        """Update preset increments version and updates timestamp."""
        library.create_preset("test-update", "Test", "Original")
        preset = library.update_preset("test-update", base_prompt="Updated")
        assert preset.current_variant.base_prompt == "Updated"
        assert preset.version == 2

    def test_delete_preset_marks_as_inactive(self, library):
        """Delete preset marks as inactive (soft delete)."""
        library.create_preset("test-delete", "Test", "Content")
        result = library.delete_preset("test-delete")
        assert result is True
        preset = library.get_preset("test-delete")
        assert preset is not None
        assert preset.is_active is False

    def test_list_presets_by_task_type_filters_correctly(self, library):
        """List presets by task_type filters correctly."""
        library.create_preset("a", "A", "Content", [TaskType.CODE_EDITING])
        library.create_preset("b", "B", "Content", [TaskType.WEB_RESEARCH])
        library.create_preset("c", "C", "Content", [TaskType.CODE_EDITING, TaskType.CODE_REVIEW])

        code_presets = library.list_presets(task_type=TaskType.CODE_EDITING)
        assert len(code_presets) == 2


class TestABTesting:
    """Test A/B testing support and variant selection."""

    def test_add_variant_with_different_weight(self, library):
        """Add variant with different weight."""
        preset = library.create_preset("ab-test", "AB Test", "Control")
        preset.add_variant(PromptVariant(
            variant_id="variant-a",
            base_prompt="Variant A",
            weight=1.0,
        ))
        preset.add_variant(PromptVariant(
            variant_id="variant-b",
            base_prompt="Variant B",
            weight=3.0,  # 3x weight
        ))
        assert len(preset.variants) == 3

    def test_select_variant_by_id(self, library):
        """Select variant by ID."""
        preset = library.create_preset("select-test", "Select", "Control")
        preset.add_variant(PromptVariant(
            variant_id="variant-a",
            base_prompt="Variant A",
            weight=1.0,
        ))

        selected = preset.select_variant("variant-a")
        assert selected.variant_id == "variant-a"

    def test_weight_based_selection_distributes_correctly(self, library):
        """Weight-based selection distributes correctly across all variants."""
        preset = library.create_preset("weight-test", "Weight", "Control")
        preset.add_variant(PromptVariant(
            variant_id="variant-a",
            base_prompt="Variant A",
            weight=1.0,
        ))
        preset.add_variant(PromptVariant(
            variant_id="variant-b",
            base_prompt="Variant B",
            weight=1.0,
        ))

        # Weight-based selection (statistical test)
        # All 3 variants (control + variant-a + variant-b) are in the pool with equal weight
        results = {"weight-test-v1": 0, "variant-a": 0, "variant-b": 0}
        for _ in range(1000):
            selected = preset.select_variant()
            results[selected.variant_id] += 1

        # Should be roughly 333 each (1/3 each for 3 variants with equal weight)
        assert results["weight-test-v1"] > 200
        assert results["variant-a"] > 200
        assert results["variant-b"] > 200

    def test_default_presets_created_for_all_agent_types(self, library):
        """Default presets created for all agent types."""
        library = create_default_library()
        presets = library.list_presets()
        assert len(presets) >= 4  # system, web-research, code-executor, code-review

        system = library.get_preset("system")
        assert system is not None
        assert TaskType.GENERAL in system.task_types

        web_research = library.get_preset("web-research")
        assert web_research is not None
        assert TaskType.WEB_RESEARCH in web_research.task_types

        code_executor = library.get_preset("code-executor")
        assert code_executor is not None
        assert TaskType.CODE_EDITING in code_executor.task_types

        code_review = library.get_preset("code-review")
        assert code_review is not None
        assert TaskType.CODE_REVIEW in code_review.task_types