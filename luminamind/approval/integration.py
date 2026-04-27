from datetime import datetime


def check_and_escalate_low_quality(task_id: str, evaluator_score: float, iteration_count: int, pipeline) -> bool:
    """Check if task should be escalated for human approval."""
    from luminamind.approval.queue import ApprovalQueue, ApprovalRequest, ApprovalStatus
    from luminamind.approval.policies import ApprovalPolicies

    policies = ApprovalPolicies()
    context = {
        "task_id": task_id,
        "evaluator_score": evaluator_score,
        "iteration_count": iteration_count,
        "operation_type": "low_quality_escalation",
    }

    if policies.should_escalate(context):
        queue = ApprovalQueue()
        request = ApprovalRequest(
            request_id=None,
            created_at=datetime.now(),
            operation_type="low_quality_escalation",
            description=f"Task {task_id} has low quality score {evaluator_score} after {iteration_count} iterations",
            payload={"task_id": task_id, "score": evaluator_score, "iterations": iteration_count},
            priority=policies.get_escalation_priority(context),
        )
        queue.enqueue(request)
        return True
    return False
