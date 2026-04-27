"""Unit tests for Self-Improving Memory System (learning module)."""
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from luminamind.learning import (
    AtomicSkill,
    SkillAcquisition,
    SkillLibrary,
    SkillSuggestion,
    SkillTrigger,
    ClosedLoopFeedback,
    LessonsLearned,
    RewardSignal,
    StructuredLesson,
    FailureLesson,
)


class TestAtomicSkill:
    """Tests for AtomicSkill dataclass."""

    def test_creation(self):
        """AtomicSkill creates with all required fields."""
        skill = AtomicSkill(
            id="test-skill-001",
            name="Test Skill",
            description="A test skill for unit testing",
            trigger_conditions=["python", "testing"],
            actions=["run_pytest", "assert_results"],
            success_rate=0.85,
            avg_tokens_saved=150.0,
            version=1,
        )
        assert skill.id == "test-skill-001"
        assert skill.name == "Test Skill"
        assert skill.trigger_conditions == ["python", "testing"]
        assert skill.actions == ["run_pytest", "assert_results"]
        assert skill.success_rate == 0.85
        assert skill.version == 1

    def test_default_values(self):
        """AtomicSkill has sensible defaults."""
        skill = AtomicSkill(
            id="test-002",
            name="Minimal Skill",
            description="Minimal skill for testing",
            trigger_conditions=[],
            actions=[],
        )
        assert skill.success_rate == 0.0
        assert skill.avg_tokens_saved == 0.0
        assert skill.version == 1
        assert skill.created_at is not None
        assert skill.last_used is not None


class TestSkillTrigger:
    """Tests for SkillTrigger enum."""

    def test_trigger_types(self):
        """All trigger types exist and have values."""
        assert SkillTrigger.AUTO.value == "auto"
        assert SkillTrigger.MANUAL.value == "manual"
        assert SkillTrigger.ONESHOT.value == "oneshot"


class TestSkillSuggestion:
    """Tests for SkillSuggestion dataclass."""

    def test_creation(self):
        """SkillSuggestion creates correctly."""
        skill = AtomicSkill(
            id="test-003",
            name="Suggested Skill",
            description="A suggested skill",
            trigger_conditions=["api"],
            actions=["call_api"],
        )
        suggestion = SkillSuggestion(
            skill=skill,
            confidence=0.75,
            trigger=SkillTrigger.AUTO,
            reasoning="Matches API call patterns",
        )
        assert suggestion.skill == skill
        assert suggestion.confidence == 0.75
        assert suggestion.trigger == SkillTrigger.AUTO
        assert "API" in suggestion.reasoning


class TestSkillLibrary:
    """Tests for SkillLibrary class."""

    def test_initialization(self, tmp_path):
        """SkillLibrary initializes with correct base path."""
        library = SkillLibrary(base_path=tmp_path / "skills")
        assert library.base_path == tmp_path / "skills"
        assert library.base_path.exists()

    def test_register_and_get_skill(self, tmp_path):
        """SkillLibrary can register and retrieve a skill."""
        library = SkillLibrary(base_path=tmp_path / "skills")
        skill = AtomicSkill(
            id="register-test-001",
            name="Register Test Skill",
            description="Testing registration",
            trigger_conditions=["test"],
            actions=["run_test"],
            version=1,
        )

        result = library.register(skill)
        assert result == "register-test-001"

        retrieved = library.get("register-test-001")
        assert retrieved is not None
        assert retrieved.name == "Register Test Skill"
        assert retrieved.id == "register-test-001"

    def test_versioning(self, tmp_path):
        """SkillLibrary maintains version history."""
        library = SkillLibrary(base_path=tmp_path / "skills")
        skill = AtomicSkill(
            id="version-test-001",
            name="Version Test",
            description="Testing versioning",
            trigger_conditions=["test"],
            actions=["run"],
            version=1,
        )
        library.register(skill)

        versions = library.list_versions("version-test-001")
        assert 1 in versions

    def test_search(self, tmp_path):
        """SkillLibrary search finds matching skills."""
        library = SkillLibrary(base_path=tmp_path / "skills")

        # Register a skill
        skill = AtomicSkill(
            id="search-test-001",
            name="API Handler",
            description="Handles API requests",
            trigger_conditions=["api", "http"],
            actions=["call_api"],
            version=1,
        )
        library.register(skill)

        # Search for it
        results = library.search("api")
        assert len(results) > 0
        assert any(s.id == "search-test-001" for s in results)

    def test_rollback(self, tmp_path):
        """SkillLibrary rollback functionality."""
        library = SkillLibrary(base_path=tmp_path / "skills")
        skill = AtomicSkill(
            id="rollback-test-001",
            name="Rollback Test",
            description="Testing rollback",
            trigger_conditions=["test"],
            actions=["run"],
            version=1,
        )
        library.register(skill)

        # Rollback should work if version exists
        result = library.rollback("rollback-test-001", 1)
        assert result is True

    def test_get_skill_catalog(self, tmp_path):
        """SkillLibrary generates SKILLS.md catalog."""
        library = SkillLibrary(base_path=tmp_path / "skills")
        skill = AtomicSkill(
            id="catalog-test-001",
            name="Catalog Test Skill",
            description="Testing catalog generation",
            trigger_conditions=["test"],
            actions=["run"],
            version=1,
        )
        library.register(skill)

        catalog = library.get_skill_catalog()
        assert "Skill Catalog" in catalog
        assert "Catalog Test Skill" in catalog


class TestLessonsLearned:
    """Tests for LessonsLearned class."""

    def test_initialization(self):
        """LessonsLearned initializes empty."""
        lessons = LessonsLearned()
        assert len(lessons._lessons) == 0
        assert len(lessons._failure_lessons) == 0

    def test_inject_failure_lesson(self):
        """LessonsLearned can inject failure lessons."""
        lessons = LessonsLearned()
        failure = FailureLesson(
            id="failure-001",
            original_failure="API timeout",
            root_cause="Network latency",
            correction_action="Add retry with backoff",
            injection_target="global_reasoning",
        )
        lessons.inject(failure)
        assert "API timeout" in lessons._failure_patterns or failure.correction_action in lessons._failure_patterns


class TestRewardSignal:
    """Tests for RewardSignal dataclass."""

    def test_creation(self):
        """RewardSignal creates with all fields."""
        signal = RewardSignal(
            task_id="task-001",
            final_score=85.0,
            iteration_count=3,
            tokens_used=5000,
            skill_ids_used=["skill-001"],
            improvements=["Add error handling"],
        )
        assert signal.task_id == "task-001"
        assert signal.final_score == 85.0
        assert signal.iteration_count == 3
        assert signal.tokens_used == 5000
        assert "skill-001" in signal.skill_ids_used
        assert "Add error handling" in signal.improvements


class TestClosedLoopFeedback:
    """Tests for ClosedLoopFeedback class."""

    def test_initialization(self):
        """ClosedLoopFeedback initializes with components."""
        library = SkillLibrary(base_path=Path(tempfile.mkdtemp()) / "skills")
        acquisition = SkillAcquisition(library)
        lessons = LessonsLearned()

        feedback = ClosedLoopFeedback(acquisition, lessons)
        assert feedback.skill_acquisition is not None
        assert feedback.lessons_learned is not None

    def test_get_improvement_suggestions(self):
        """ClosedLoopFeedback returns improvement suggestions."""
        library = SkillLibrary(base_path=Path(tempfile.mkdtemp()) / "skills")
        acquisition = SkillAcquisition(library)
        lessons = LessonsLearned()

        feedback = ClosedLoopFeedback(acquisition, lessons)
        suggestions = feedback.get_improvement_suggestions("test-task")
        assert isinstance(suggestions, list)
