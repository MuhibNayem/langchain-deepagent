from fastapi import APIRouter, Depends, HTTPException, Security
from typing import Optional

from luminamind.api.auth import verify_api_key

router = APIRouter(prefix="/api/v1/queue", tags=["queue"])

# Dependency for task_queue - will be injected via app state
def get_task_queue():
    """Override in app to inject task_queue."""
    return None


@router.post("/enqueue")
async def enqueue_task(
    task_type: str,
    payload: dict = {},
    priority: str = "NORMAL",
    task_queue=Depends(get_task_queue),
    api_key: str = Security(verify_api_key),
):
    """Enqueue a task into the queue."""
    if task_queue is None:
        raise HTTPException(status_code=503, detail="Task queue not configured")

    from luminamind.queue import Task, Priority as QPriority

    priority_map = {
        "LOW": QPriority.LOW,
        "NORMAL": QPriority.NORMAL,
        "HIGH": QPriority.HIGH,
        "CRITICAL": QPriority.CRITICAL,
    }
    task_priority = priority_map.get(priority.upper(), QPriority.NORMAL)

    task = Task(type=task_type, payload=payload, priority=task_priority)
    task_id = task_queue.enqueue(task)
    return {"task_id": task_id, "status": "enqueued"}


@router.get("/status/{task_id}")
async def get_task_status(task_id: str, task_queue=Depends(get_task_queue), api_key: str = Security(verify_api_key)):
    """Get status of a task."""
    if task_queue is None:
        raise HTTPException(status_code=503, detail="Task queue not configured")

    status = task_queue.get_status(task_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task_id, "status": status.value}


@router.delete("/cancel/{task_id}")
async def cancel_task(task_id: str, task_queue=Depends(get_task_queue), api_key: str = Security(verify_api_key)):
    """Cancel a task."""
    if task_queue is None:
        raise HTTPException(status_code=503, detail="Task queue not configured")

    cancelled = task_queue.cancel(task_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Task not found or already processed")
    return {"task_id": task_id, "status": "cancelled"}


@router.get("/metrics")
async def get_queue_metrics(task_queue=Depends(get_task_queue), api_key: str = Security(verify_api_key)):
    """Get queue metrics."""
    if task_queue is None:
        raise HTTPException(status_code=503, detail="Task queue not configured")

    metrics = task_queue.get_metrics()
    return {
        "pending": metrics.pending,
        "running": metrics.running,
        "completed": metrics.completed,
        "failed": metrics.failed,
        "dead_letter": metrics.dead_letter,
    }
