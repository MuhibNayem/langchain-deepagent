import click
import requests
import os
import json

from luminamind.deep_agent import DeepAgent

API_BASE = os.environ.get("LUMINAMIND_API_URL", "http://localhost:8000")


@click.group(name="swarm")
def swarm_cli():
    """Swarm control commands."""
    pass


@swarm_cli.command("status")
def status():
    """Get swarm status."""
    api_key = os.environ.get("LUMINAMIND_API_KEY")
    if not api_key:
        click.echo("Error: LUMINAMIND_API_KEY not set")
        return

    response = requests.get(
        f"{API_BASE}/api/v1/swarm/status",
        headers={"X-API-Key": api_key},
    )
    if response.ok:
        data = response.json()
        click.echo(f"Active agents: {data['active_agents']}")
        click.echo(f"Idle agents: {data['idle_agents']}")
    else:
        click.echo(f"Error: {response.status_code}")


@swarm_cli.command("spawn")
@click.option("--role", required=True, help="Agent role")
@click.option("--config", default="{}", help="JSON config")
def spawn(role: str, config: str):
    """Spawn an agent."""
    api_key = os.environ.get("LUMINAMIND_API_KEY")
    if not api_key:
        click.echo("Error: LUMINAMIND_API_KEY not set")
        return

    try:
        config_dict = json.loads(config) if config != "{}" else {}
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON config: {e}")
        return

    response = requests.post(
        f"{API_BASE}/api/v1/swarm/spawn?role={role}",
        headers={"X-API-Key": api_key},
        json=config_dict,
    )
    if response.ok:
        click.echo(f"Agent spawned: {response.json()['agent_id']}")
    else:
        click.echo(f"Error: {response.status_code} - {response.text}")


@swarm_cli.command("kill")
@click.argument("agent_id")
def kill(agent_id: str):
    """Kill an agent."""
    api_key = os.environ.get("LUMINAMIND_API_KEY")
    if not api_key:
        click.echo("Error: LUMINAMIND_API_KEY not set")
        return

    response = requests.delete(
        f"{API_BASE}/api/v1/swarm/kill/{agent_id}",
        headers={"X-API-Key": api_key},
    )
    if response.ok:
        click.echo(f"Agent {agent_id} killed")
    else:
        click.echo(f"Error: {response.status_code}")


@swarm_cli.command("broadcast")
@click.option("--type", required=True, help="Message type")
@click.option("--payload", default="{}", help="JSON payload")
def broadcast(type: str, payload: str):
    """Broadcast a message to all agents."""
    api_key = os.environ.get("LUMINAMIND_API_KEY")
    if not api_key:
        click.echo("Error: LUMINAMIND_API_KEY not set")
        return

    try:
        payload_dict = json.loads(payload) if payload != "{}" else {}
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON payload: {e}")
        return

    response = requests.post(
        f"{API_BASE}/api/v1/swarm/broadcast?message_type={type}",
        headers={"X-API-Key": api_key},
        json=payload_dict,
    )
    if response.ok:
        click.echo("Broadcast sent")
    else:
        click.echo(f"Error: {response.status_code}")


@click.group(name="queue")
def queue_cli():
    """Queue control commands."""
    pass


@queue_cli.command("enqueue")
@click.option("--type", required=True, help="Task type")
@click.option("--payload", default="{}", help="JSON payload")
@click.option("--priority", default="NORMAL", help="Priority")
def enqueue(type: str, payload: str, priority: str):
    """Enqueue a task."""
    api_key = os.environ.get("LUMINAMIND_API_KEY")
    if not api_key:
        click.echo("Error: LUMINAMIND_API_KEY not set")
        return

    try:
        payload_dict = json.loads(payload) if payload != "{}" else {}
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON payload: {e}")
        return

    response = requests.post(
        f"{API_BASE}/api/v1/queue/enqueue?task_type={type}&priority={priority}",
        headers={"X-API-Key": api_key},
        json=payload_dict,
    )
    if response.ok:
        click.echo(f"Task enqueued: {response.json()['task_id']}")
    else:
        click.echo(f"Error: {response.status_code}")


@queue_cli.command("status")
@click.argument("task_id")
def task_status(task_id: str):
    """Get task status."""
    api_key = os.environ.get("LUMINAMIND_API_KEY")
    if not api_key:
        click.echo("Error: LUMINAMIND_API_KEY not set")
        return

    response = requests.get(
        f"{API_BASE}/api/v1/queue/status/{task_id}",
        headers={"X-API-Key": api_key},
    )
    if response.ok:
        click.echo(f"Task {task_id}: {response.json()['status']}")
    else:
        click.echo(f"Error: {response.status_code}")


@queue_cli.command("cancel")
@click.argument("task_id")
def cancel_task(task_id: str):
    """Cancel a task."""
    api_key = os.environ.get("LUMINAMIND_API_KEY")
    if not api_key:
        click.echo("Error: LUMINAMIND_API_KEY not set")
        return

    response = requests.delete(
        f"{API_BASE}/api/v1/queue/cancel/{task_id}",
        headers={"X-API-Key": api_key},
    )
    if response.ok:
        click.echo(f"Task {task_id} cancelled")
    else:
        click.echo(f"Error: {response.status_code}")


@queue_cli.command("metrics")
def metrics():
    """Get queue metrics."""
    api_key = os.environ.get("LUMINAMIND_API_KEY")
    if not api_key:
        click.echo("Error: LUMINAMIND_API_KEY not set")
        return

    response = requests.get(
        f"{API_BASE}/api/v1/queue/metrics",
        headers={"X-API-Key": api_key},
    )
    if response.ok:
        data = response.json()
        click.echo(f"Pending: {data['pending']}")
        click.echo(f"Running: {data['running']}")
        click.echo(f"Completed: {data['completed']}")
        click.echo(f"Failed: {data['failed']}")
        click.echo(f"Dead letter: {data['dead_letter']}")
    else:
        click.echo(f"Error: {response.status_code}")


@click.group(name="luminamind")
def main():
    """LuminaMind CLI."""
    pass


main.add_command(swarm_cli)
main.add_command(queue_cli)


if __name__ == "__main__":
    main()
