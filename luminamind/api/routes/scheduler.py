from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

router = APIRouter(prefix="/api/v1/scheduler", tags=["scheduler"])


def get_scheduler():
    """Override in app to inject scheduler."""
    return None


@router.post("/schedule")
def schedule_task(
    task_type: str,
    cron: str = None,
    payload: dict = {},
    name: str = "",
    timezone: str = "UTC",
    run_missed: bool = False,
    scheduler=Depends(get_scheduler),
):
    """Schedule a task."""
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not configured")

    from luminamind.scheduler import ScheduledTask, CronExpression, parse_cron

    cron_expr = None
    if cron:
        cron_expr = parse_cron(cron)

    task = ScheduledTask(
        name=name,
        task_type=task_type,
        payload=payload,
        cron=cron_expr,
        timezone=timezone,
        run_missed=run_missed,
    )
    task_id = scheduler.schedule(task)
    return {"task_id": task_id, "status": "scheduled"}


@router.get("/list")
def list_scheduled_tasks(scheduler=Depends(get_scheduler)):
    """List all scheduled tasks."""
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not configured")

    tasks = list(scheduler._tasks.values())
    return {
        "tasks": [
            {
                "id": t.id,
                "name": t.name,
                "task_type": t.task_type,
                "enabled": t.enabled,
                "next_run": t.next_run.isoformat() if t.next_run else None,
                "last_run": t.last_run.isoformat() if t.last_run else None,
                "total_runs": t.total_runs,
            }
            for t in tasks
        ]
    }


@router.delete("/unschedule/{task_id}")
def unschedule_task(task_id: str, scheduler=Depends(get_scheduler)):
    """Unschedule a task."""
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not configured")

    removed = scheduler.unschedule(task_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task_id, "status": "unscheduled"}


@router.put("/pause/{task_id}")
def pause_task(task_id: str, scheduler=Depends(get_scheduler)):
    """Pause a scheduled task."""
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not configured")

    paused = scheduler.pause(task_id)
    if not paused:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task_id, "status": "paused"}


@router.put("/resume/{task_id}")
def resume_task(task_id: str, scheduler=Depends(get_scheduler)):
    """Resume a paused task."""
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not configured")

    resumed = scheduler.resume(task_id)
    if not resumed:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task_id, "status": "resumed"}
