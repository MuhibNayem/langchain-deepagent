"""Structured Lessons from Task Execution.

Distills lessons from task results and injects them into
global reasoning for permanent improvement.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from luminamind.evaluator.pipeline import RefinementResult


@dataclass
class StructuredLesson:
    """A lesson distilled from task execution.

    Attributes:
        id: Unique lesson identifier
        lesson_type: Type of lesson ("success", "failure", "optimization")
        title: Short title for the lesson
        description: Detailed description of what was learned
        trigger_conditions: When this lesson applies
        injected_into: Which component receives this lesson
        created_at: When lesson was created
        task_id: Source task that generated this lesson
        metadata: Additional lesson data
    """

    id: str
    lesson_type: str  # "success", "failure", "optimization"
    title: str
    description: str
    trigger_conditions: list[str]
    injected_into: str  # "global_reasoning", "skill", "workflow_template"
    created_at: datetime = field(default_factory=datetime.now)
    task_id: str | None = None
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class FailureLesson:
    """A failure that has been analyzed and turned into a lesson.

    Attributes:
        id: Unique lesson identifier
        original_failure: The original failure message or error
        root_cause: Analyzed root cause of the failure
        correction_action: What action prevents this failure
        injection_target: Which component receives this lesson
        verified: Whether this lesson has been verified to prevent recurrence
        created_at: When lesson was created
    """

    id: str
    original_failure: str
    root_cause: str
    correction_action: str
    injection_target: str  # Which component receives this lesson
    verified: bool = False
    created_at: datetime = field(default_factory=datetime.now)


class LessonsLearned:
    """Distills lessons from task results and injects them into reasoning.

    Analyzes both successful and failed tasks to extract reusable
    patterns and failure corrections that can be injected into
    the global reasoning system.
    """

    def __init__(self):
        self._lessons: dict[str, StructuredLesson] = {}
        self._failure_lessons: dict[str, FailureLesson] = {}
        self._failure_patterns: list[str] = []

    def distill(self, task_result: "RefinementResult") -> StructuredLesson:
        """Extract a structured lesson from task result.

        For successful tasks: extracts reusable patterns
        For failed tasks: extracts root cause and correction

        Args:
            task_result: The task result to analyze

        Returns:
            StructuredLesson distilled from the result
        """
        import uuid

        # Determine lesson type based on result
        if task_result.converged and task_result.final_result and task_result.final_result.score >= 80.0:
            lesson_type = "success"
            title = f"Success pattern from {task_result.session_id[:8]}"
            description = self._extract_success_pattern(task_result)
        else:
            lesson_type = "failure"
            title = f"Failure pattern from {task_result.session_id[:8]}"
            description = self._extract_failure_pattern(task_result)

        lesson = StructuredLesson(
            id=str(uuid.uuid4()),
            lesson_type=lesson_type,
            title=title,
            description=description,
            trigger_conditions=self._extract_trigger_conditions(task_result),
            injected_into="global_reasoning",
            created_at=datetime.now(),
            task_id=task_result.session_id,
            metadata={},
        )

        self._lessons[lesson.id] = lesson
        return lesson

    def inject(self, failure: "Failure | FailureLesson") -> None:
        """Permanently inject lesson into global reasoning.

        For failures: adds to failure_patterns registry
        For successes: triggers skill_acquisition

        Args:
            failure: Failure or FailureLesson to inject
        """
        import uuid

        if isinstance(failure, FailureLesson):
            self._failure_lessons[failure.id] = failure
            self._failure_patterns.append(failure.correction_action)
        else:
            # Create FailureLesson from raw failure
            lesson = FailureLesson(
                id=str(uuid.uuid4()),
                original_failure=str(failure),
                root_cause="Unknown - needs analysis",
                correction_action="Unknown - needs investigation",
                injection_target="global_reasoning",
                verified=False,
                created_at=datetime.now(),
            )
            self._failure_lessons[lesson.id] = lesson
            self._failure_patterns.append(lesson.correction_action)

    def retrieve(self, task_type: str) -> list[StructuredLesson]:
        """Retrieve relevant lessons for a task type.

        Args:
            task_type: Type of task to get lessons for

        Returns:
            List of relevant StructuredLesson instances
        """
        relevant = []
        for lesson in self._lessons.values():
            # Check if any trigger condition matches
            for trigger in lesson.trigger_conditions:
                if trigger.lower() in task_type.lower():
                    relevant.append(lesson)
                    break
        return relevant

    def verify(self, lesson_id: str, task_result: "RefinementResult") -> bool:
        """Verify a lesson prevented the original failure.

        Args:
            lesson_id: ID of the lesson to verify
            task_result: Task result to verify against

        Returns:
            True if the lesson was effective, False otherwise
        """
        if lesson_id not in self._lessons:
            return False

        lesson = self._lessons[lesson_id]

        # If it's a success lesson, check if task succeeded
        if lesson.lesson_type == "success":
            return task_result.converged and task_result.final_result and task_result.final_result.score >= 80.0

        # For failure lessons, mark as verified
        if lesson_id in self._failure_lessons:
            self._failure_lessons[lesson_id].verified = True
            return True

        return False

    def _extract_success_pattern(self, task_result: "RefinementResult") -> str:
        """Extract the success pattern from a successful task."""
        # TODO: Implement pattern extraction
        return f"Task {task_result.session_id} converged successfully with score {task_result.final_result.score if task_result.final_result else 'N/A'}"

    def _extract_failure_pattern(self, task_result: "RefinementResult") -> str:
        """Extract failure pattern from a failed task."""
        # TODO: Implement failure pattern extraction
        return f"Task {task_result.session_id} failed to converge: {task_result.reason}"

    def _extract_trigger_conditions(self, task_result: "RefinementResult") -> list[str]:
        """Extract trigger conditions from task result."""
        # TODO: Implement trigger condition extraction
        return []


# Stub for type hints
class Failure:
    """Stub for Failure type."""
    pass
