"""Closed-Loop Feedback Integration.

Integrates evaluator feedback into skill improvement loop
for permanent harness enhancement.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from luminamind.learning.skill_acquirer import SkillAcquisition
    from luminamind.learning.lessons import LessonsLearned
    from luminamind.evaluator.pipeline import RefinementResult


@dataclass
class RewardSignal:
    """Signal from evaluator representing task quality.

    Attributes:
        task_id: ID of the evaluated task
        final_score: Final quality score (0-100)
        iteration_count: Number of refinement iterations
        tokens_used: Total tokens consumed
        skill_ids_used: List of skill IDs that were invoked
        improvements: Suggested improvements for next run
        timestamp: When the reward signal was generated
    """

    task_id: str
    final_score: float
    iteration_count: int
    tokens_used: int
    skill_ids_used: list[str]
    improvements: list[str]
    timestamp: datetime = field(default_factory=datetime.now)


class ClosedLoopFeedback:
    """Integrates evaluator feedback into skill improvement loop.

    Processes completed tasks through a closed-loop feedback cycle:
    1. If reward.score > threshold: distill skill from successful execution
    2. If reward.score < threshold: inject failure lesson
    3. Update skill effectiveness metrics
    """

    def __init__(
        self,
        skill_acquisition: "SkillAcquisition",
        lessons_learned: "LessonsLearned",
    ):
        """Initialize ClosedLoopFeedback.

        Args:
            skill_acquisition: SkillAcquisition instance for skill management
            lessons_learned: LessonsLearned instance for lesson management
        """
        self.skill_acquisition = skill_acquisition
        self.lessons_learned = lessons_learned

    def process_result(
        self, task_result: "RefinementResult", reward: RewardSignal
    ) -> None:
        """Process completed task with reward signal.

        Args:
            task_result: The completed task result
            reward: Reward signal from evaluator with quality metrics
        """
        # Quality threshold for skill distillation
        QUALITY_THRESHOLD = 80.0

        if reward.final_score >= QUALITY_THRESHOLD:
            # High quality: distill skill from successful execution
            skill = self.skill_acquisition.distill_from_result(task_result)
            if skill:
                self.skill_acquisition.skill_library.register(skill)
        else:
            # Low quality: inject failure lesson
            self.lessons_learned.inject(task_result)

        # Update skill effectiveness metrics for any skills used
        for skill_id in reward.skill_ids_used:
            self.skill_acquisition.evaluate_skill_effectiveness(
                skill_id, [task_result]
            )

    def get_improvement_suggestions(self, task_id: str) -> list[str]:
        """Get improvement suggestions for a task based on lessons learned.

        Args:
            task_id: ID of the task to get suggestions for

        Returns:
            List of improvement suggestion strings
        """
        # Retrieve relevant lessons for this task
        # TODO: Get task type from task_id
        task_type = ""
        lessons = self.lessons_learned.retrieve(task_type)

        suggestions = []
        for lesson in lessons:
            if lesson.lesson_type == "failure":
                suggestions.append(lesson.description)

        return suggestions
