from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import queue as queue_router
from .routes import scheduler as scheduler_router
from .routes import swarm as swarm_router
from .auth import create_api_key_auth, verify_api_key
from .middleware import RateLimitMiddleware


def create_app(task_queue=None, scheduler=None, swarm=None, auth=None) -> FastAPI:
    """Create and configure FastAPI application.

    Args:
        task_queue: Optional TaskQueue instance for queue operations
        scheduler: Optional Scheduler instance for scheduler operations
        swarm: Optional Swarm instance for swarm operations
        auth: Optional auth handler (defaults to APIKeyAuth from env)

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(title="LuminaMind API", version="1.0.0")

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting
    app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)

    # Auth
    auth_handler = auth or create_api_key_auth()

    # Store dependencies in app state
    app.state.task_queue = task_queue
    app.state.scheduler = scheduler
    app.state.swarm = swarm
    app.state.auth = auth_handler

    # Override dependency functions using FastAPI's dependency_overrides
    if task_queue is not None:
        app.dependency_overrides[queue_router.get_task_queue] = lambda: task_queue

    if scheduler is not None:
        app.dependency_overrides[scheduler_router.get_scheduler] = lambda: scheduler

    if swarm is not None:
        app.dependency_overrides[swarm_router.get_swarm] = lambda: swarm

    # Include routers
    app.include_router(queue_router.router)
    app.include_router(scheduler_router.router)
    app.include_router(swarm_router.router)
    app.include_router(events_router.router)

    @app.get("/health")
    def health():
        return {"status": "healthy", "version": "1.0.0"}

    return app
