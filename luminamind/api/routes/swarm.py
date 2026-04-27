from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

router = APIRouter(prefix="/api/v1/swarm", tags=["swarm"])


def get_swarm():
    """Override in app to inject swarm."""
    return None


@router.post("/spawn")
def spawn_agent(
    role: str,
    config: dict = {},
    swarm=Depends(get_swarm),
):
    """Spawn an agent in the swarm."""
    if swarm is None:
        raise HTTPException(status_code=503, detail="Swarm not configured")

    from luminamind.swarm import AgentRole

    # Convert role string to AgentRole enum
    try:
        agent_role = AgentRole(role.lower())
    except ValueError:
        valid_roles = [r.value for r in AgentRole]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role '{role}'. Valid roles: {valid_roles}",
        )

    agent_id = swarm.spawn(role=agent_role, config=config)
    return {"agent_id": agent_id, "status": "spawned"}


@router.delete("/kill/{agent_id}")
def kill_agent(agent_id: str, swarm=Depends(get_swarm)):
    """Kill an agent in the swarm."""
    if swarm is None:
        raise HTTPException(status_code=503, detail="Swarm not configured")

    killed = swarm.kill(agent_id)
    if not killed:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"agent_id": agent_id, "status": "killed"}


@router.get("/status")
def get_swarm_status(swarm=Depends(get_swarm)):
    """Get swarm status."""
    if swarm is None:
        raise HTTPException(status_code=503, detail="Swarm not configured")

    status = swarm.get_status()
    return {
        "active_agents": status.active_agents,
        "idle_agents": status.idle_agents,
        "total_tasks": status.total_tasks,
        "pending_tasks": status.pending_tasks,
    }


@router.post("/broadcast")
def broadcast_message(
    message_type: str,
    payload: dict = {},
    sender_id: str = "api",
    swarm=Depends(get_swarm),
):
    """Broadcast a message to all agents in the swarm."""
    if swarm is None:
        raise HTTPException(status_code=503, detail="Swarm not configured")

    from luminamind.swarm import SwarmMessage

    message = SwarmMessage(sender_id=sender_id, message_type=message_type, payload=payload)
    swarm.broadcast(message)
    return {"status": "broadcast", "message_type": message_type}


@router.get("/agents")
def list_agents(swarm=Depends(get_swarm)):
    """List all agents in the swarm."""
    if swarm is None:
        raise HTTPException(status_code=503, detail="Swarm not configured")

    status = swarm.get_status()
    return {
        "active_agents": status.active_agents,
        "idle_agents": status.idle_agents,
        "total": status.total_tasks,
    }
