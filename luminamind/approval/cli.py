from __future__ import annotations
import click
from datetime import datetime


@click.group()
def approval_commands():
    """Manage approval workflow."""
    pass


@approval_commands.command()
@click.option("--limit", default=10, help="Number of requests to show")
def list(limit):
    """List pending approval requests."""
    from luminamind.approval.queue import ApprovalQueue, ApprovalStatus
    queue = ApprovalQueue()
    pending = queue.list_pending(limit)

    if not pending:
        click.echo("No pending approval requests.")
        return

    click.echo(f"{'ID':<40} {'Priority':<10} {'Type':<20} {'Description'}")
    click.echo("-" * 100)
    for req in pending:
        click.echo(f"{req.request_id:<40} {req.priority:<10} {req.operation_type:<20} {req.description[:30]}")


@approval_commands.command()
@click.argument("request_id")
@click.option("--reviewer", default="cli", help="Reviewer name")
@click.option("--notes", help="Review notes")
def approve(request_id, reviewer, notes):
    """Approve a request."""
    from luminamind.approval.queue import ApprovalQueue
    queue = ApprovalQueue()
    if queue.approve(request_id, reviewer, notes):
        click.echo(f"Request {request_id} approved.")
    else:
        click.echo(f"Request {request_id} not found or already reviewed.")


@approval_commands.command()
@click.argument("request_id")
@click.option("--reviewer", default="cli", help="Reviewer name")
@click.option("--notes", help="Review notes")
def reject(request_id, reviewer, notes):
    """Reject a request."""
    from luminamind.approval.queue import ApprovalQueue
    queue = ApprovalQueue()
    if queue.reject(request_id, reviewer, notes):
        click.echo(f"Request {request_id} rejected.")
    else:
        click.echo(f"Request {request_id} not found or already reviewed.")


@approval_commands.command()
@click.argument("request_id")
def status(request_id):
    """Get status of a request."""
    from luminamind.approval.queue import ApprovalQueue, ApprovalStatus
    queue = ApprovalQueue()
    status = queue.get_status(request_id)
    if status:
        click.echo(f"Request {request_id}: {status.value}")
    else:
        click.echo(f"Request {request_id} not found.")
