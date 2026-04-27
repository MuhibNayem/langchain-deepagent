"""Unit tests for prompt_composer module."""
import pytest

from luminamind.config.prompt_composer import (
    PromptComposer,
    PersonalityProfile,
    ContextBundle,
    DEFAULT_PERSONALITIES,
    compose_prompt,
)


def test_personality_profile_apply():
    """Test PersonalityProfile.apply_to() modifies base prompt correctly."""
    profile = PersonalityProfile(
        profile_id="test",
        name="Test",
        tone="formal",
        style="detailed",
        focus_areas=["security"],
    )

    base = "You are a helpful assistant."
    result = profile.apply_to(base)

    assert "precision" in result.lower()
    assert "security" in result.lower()
    assert "thorough" in result.lower() or "explanations" in result.lower()


def test_personality_profile_tone_casual():
    """Test casual tone modifier."""
    profile = PersonalityProfile(
        profile_id="casual-test",
        name="Casual Test",
        tone="casual",
        style="balanced",
    )
    base = "You are a helpful assistant."
    result = profile.apply_to(base)
    assert "friendly" in result.lower() or "approachable" in result.lower()


def test_personality_profile_tone_technical():
    """Test technical tone modifier."""
    profile = PersonalityProfile(
        profile_id="tech-test",
        name="Technical Test",
        tone="technical",
        style="balanced",
    )
    base = "You are a helpful assistant."
    result = profile.apply_to(base)
    assert "precise technical language" in result.lower() or "technical language" in result.lower()


def test_personality_profile_style_concise():
    """Test concise style modifier."""
    profile = PersonalityProfile(
        profile_id="concise-test",
        name="Concise Test",
        tone="technical",
        style="concise",
    )
    base = "You are a helpful assistant."
    result = profile.apply_to(base)
    assert "brief" in result.lower() or "point" in result.lower()


def test_personality_profile_focus_areas():
    """Test focus areas are included in modified prompt."""
    profile = PersonalityProfile(
        profile_id="focus-test",
        name="Focus Test",
        tone="technical",
        style="balanced",
        focus_areas=["performance", "caching"],
    )
    base = "You are a helpful assistant."
    result = profile.apply_to(base)
    assert "performance" in result.lower()
    assert "caching" in result.lower()


def test_personality_profile_system_hints():
    """Test system hints are included in modified prompt."""
    profile = PersonalityProfile(
        profile_id="hints-test",
        name="Hints Test",
        tone="technical",
        style="balanced",
        system_hints=["Always validate inputs", "Check for null values"],
    )
    base = "You are a helpful assistant."
    result = profile.apply_to(base)
    assert "validate inputs" in result.lower()
    assert "null values" in result.lower()


def test_context_bundle_format():
    """Test ContextBundle.format_context() produces correct output."""
    ctx = ContextBundle(
        task_type="code-editing",
        current_working_directory="/project",
        recent_files=["a.py", "b.py"],
        active_task="Fix login bug",
        tool_access=["shell", "read_file"],
        evaluator_score=0.85,
    )

    result = ctx.format_context()

    assert "/project" in result
    assert "login bug" in result
    assert "shell" in result
    assert "0.85" in result


def test_context_bundle_empty():
    """Test ContextBundle with minimal data."""
    ctx = ContextBundle(task_type="general")
    result = ctx.format_context()
    assert result == ""


def test_context_bundle_recent_files_limit():
    """Test ContextBundle only shows last 5 recent files."""
    ctx = ContextBundle(
        task_type="general",
        recent_files=["1.py", "2.py", "3.py", "4.py", "5.py", "6.py", "7.py"],
    )
    result = ctx.format_context()
    # Should only include the last 5 files
    assert "6.py" in result
    assert "7.py" in result
    assert "1.py" not in result


def test_context_bundle_no_evaluator_score():
    """Test ContextBundle omits evaluator score when None."""
    ctx = ContextBundle(
        task_type="general",
        current_working_directory="/test",
        evaluator_score=None,
    )
    result = ctx.format_context()
    assert "/test" in result
    assert "quality score" not in result.lower()


def test_prompt_composer_basic():
    """Test PromptComposer.compose() with minimal arguments."""
    composer = PromptComposer()
    result = composer.compose()

    assert len(result) > 0
    assert "helpful" in result.lower() or "assistant" in result.lower()


def test_prompt_composer_with_personality():
    """Test PromptComposer applies personality correctly."""
    composer = PromptComposer()
    result = composer.compose(personality="security-focused")

    assert "security" in result.lower() or "access control" in result.lower()


def test_prompt_composer_with_context():
    """Test PromptComposer includes context in output."""
    composer = PromptComposer()
    ctx = ContextBundle(
        task_type="code-editing",
        current_working_directory="/project/src",
        active_task="Add feature",
    )
    result = composer.compose(context=ctx)

    assert "/project/src" in result
    assert "Add feature" in result


def test_prompt_composer_system_instructions():
    """Test PromptComposer prepends system instructions."""
    composer = PromptComposer()
    result = composer.compose(
        system_instructions=["No shell commands", "Read-only mode"],
    )

    assert "No shell commands" in result
    assert "Read-only" in result


def test_prompt_composer_for_agent():
    """Test compose_for_agent convenience method."""
    composer = PromptComposer()
    result = composer.compose_for_agent("code-executor")

    # Should have substantial content from preset or default
    assert len(result) > 20


def test_prompt_composer_for_agent_with_context():
    """Test compose_for_agent with context parameter."""
    composer = PromptComposer()
    ctx = ContextBundle(
        task_type="code-review",
        current_working_directory="/src",
    )
    result = composer.compose_for_agent(
        "code-review",
        context=ctx,
        personality="security-focused",
    )

    assert "/src" in result
    assert "security" in result.lower()


def test_register_personality():
    """Test registering a custom personality profile."""
    composer = PromptComposer()
    new_profile = PersonalityProfile(
        profile_id="custom",
        name="Custom",
        tone="casual",
    )
    composer.register_personality(new_profile)

    result = composer.list_personalities()
    assert any(p.profile_id == "custom" for p in result)


def test_list_personalities_returns_all():
    """Test list_personalities returns all registered profiles."""
    composer = PromptComposer()
    result = composer.list_personalities()

    # Should include default personalities
    assert len(result) >= 4


def test_default_personalities():
    """Test default personalities are properly defined."""
    assert "default" in DEFAULT_PERSONALITIES
    assert "security-focused" in DEFAULT_PERSONALITIES
    assert "performance-focused" in DEFAULT_PERSONALITIES
    assert "debugging" in DEFAULT_PERSONALITIES


def test_default_personality_has_correct_values():
    """Test default personality profile has expected values."""
    default = DEFAULT_PERSONALITIES["default"]
    assert default.tone == "technical"
    assert default.style == "balanced"
    assert default.focus_areas == []


def test_security_focused_personality():
    """Test security-focused personality has correct values."""
    security = DEFAULT_PERSONALITIES["security-focused"]
    assert security.tone == "formal"
    assert security.style == "detailed"
    assert "security" in security.focus_areas


def test_performance_focused_personality():
    """Test performance-focused personality has correct values."""
    perf = DEFAULT_PERSONALITIES["performance-focused"]
    assert perf.tone == "technical"
    assert perf.style == "concise"
    assert "performance" in perf.focus_areas


def test_debugging_personality():
    """Test debugging personality has correct values."""
    debug = DEFAULT_PERSONALITIES["debugging"]
    assert debug.tone == "casual"
    assert debug.style == "detailed"
    assert "bugs" in debug.focus_areas


def test_compose_prompt_function():
    """Test standalone compose_prompt function."""
    result = compose_prompt(
        context={"task_type": "web-research", "current_working_directory": "/test"},
        personality="default",
    )

    assert len(result) > 0
    assert "/test" in result


def test_compose_prompt_with_unknown_personality():
    """Test compose_prompt falls back to default for unknown personality."""
    composer = PromptComposer()
    result = composer.compose(personality="nonexistent")

    # Should not crash, should use default
    assert len(result) > 0


def test_compose_with_preset_id_no_library():
    """Test compose with preset_id but no library falls back to default."""
    composer = PromptComposer()
    result = composer.compose(preset_id="some-preset")

    # Should get default base prompt since no library
    assert "helpful" in result.lower() or "assistant" in result.lower()


def test_compose_with_task_type_no_library():
    """Test compose with task_type but no library falls back to default."""
    composer = PromptComposer()
    result = composer.compose(task_type="code-editing")

    # Should get default base prompt since no library
    assert "helpful" in result.lower() or "assistant" in result.lower()


def test_personality_apply_preserves_base():
    """Test that apply_to preserves the original base prompt."""
    profile = PersonalityProfile(
        profile_id="test",
        name="Test",
        tone="technical",
        style="balanced",
    )
    base = "You are a helpful AI assistant."
    result = profile.apply_to(base)

    # Base should be at the start
    assert result.startswith(base)


def test_context_bundle_all_fields():
    """Test ContextBundle with all fields populated."""
    ctx = ContextBundle(
        task_type="code-editing",
        session_id="session-123",
        current_working_directory="/workspace",
        recent_files=["main.py", "utils.py"],
        active_task="Refactoring",
        tool_access=["shell", "edit", "search"],
        evaluator_score=0.92,
    )

    result = ctx.format_context()

    assert "/workspace" in result
    assert "Refactoring" in result
    assert "main.py" in result
    assert "utils.py" in result
    assert "shell" in result
    assert "0.92" in result
