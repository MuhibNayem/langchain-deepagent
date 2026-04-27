from fastapi import FastAPI
from typing import Optional

from .metrics import TaskMetrics, SwarmMetrics

def create_app(task_queue=None, swarm=None, alert_engine=None) -> FastAPI:
    app = FastAPI(title="LuminaMind Monitoring")

    @app.get("/api/v1/metrics/tasks")
    def get_task_metrics():
        if not task_queue:
            return {"error": "No task queue configured"}
        metrics = task_queue.get_metrics()
        return TaskMetrics(
            queued=metrics.pending,
            running=metrics.running,
            completed=metrics.completed,
            failed=metrics.failed,
            dead_letter=metrics.dead_letter,
        )

    @app.get("/api/v1/metrics/swarm")
    def get_swarm_metrics():
        if not swarm:
            return {"error": "No swarm configured"}
        status = swarm.get_status()
        return SwarmMetrics(
            active_agents=status.active_agents,
            idle_agents=status.idle_agents,
            total_agents=status.total_tasks,
            tasks_completed=0,  # Would track over time
        )

    @app.get("/api/v1/alerts")
    def get_alerts():
        if not alert_engine:
            return {"alerts": []}
        return {"alerts": alert_engine.get_active_alerts()}

    @app.get("/health")
    def health():
        return {"status": "healthy"}

    return app