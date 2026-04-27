from fastapi import APIRouter, Depends, Query, Security
from fastapi.responses import StreamingResponse
from starlette.requests import Request
from typing import Optional

from luminamind.events import EventStream, EventSubscription
from luminamind.events.schema import AgentEventType
from luminamind.api.auth import verify_api_key

router = APIRouter(prefix="/events", tags=["events"])

# EventStream singleton (initialized in app.py)
event_stream: EventStream | None = None


def get_event_stream() -> EventStream:
    global event_stream
    if event_stream is None:
        event_stream = EventStream()
    return event_stream


@router.get("")
async def get_events(
    session_id: Optional[str] = None,
    task_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    event_types: Optional[str] = None,  # comma-separated
    api_key: str = Security(verify_api_key),
):
    """SSE endpoint for event streaming."""
    # Parse event_types
    types = None
    if event_types:
        type_list = [t.strip() for t in event_types.split(",")]
        types = [AgentEventType(t) for t in type_list]

    subscription = EventSubscription(
        session_id=session_id,
        task_id=task_id,
        agent_id=agent_id,
        event_types=types
    )

    es = get_event_stream()
    subscription_id = await es.subscribe(subscription, transport="sse")

    async def event_generator():
        async for sse_data in es.sse.stream(subscription_id):
            yield sse_data

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Subscriber-ID": subscription_id
        }
    )


@router.get("/replay/{session_id}")
async def replay_events(
    session_id: str,
    from_event_id: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    api_key: str = Security(verify_api_key),
):
    """Get buffered events for replay."""
    es = get_event_stream()
    events = es.replay(session_id, from_event_id)
    return {"events": events[:limit], "total": len(events)}