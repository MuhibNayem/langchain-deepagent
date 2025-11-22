import subprocess
import asyncio
import json
import sys
import time
from typing import Any, Iterable, Optional

import questionary
import typer
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    HumanMessage,
    ToolMessage,
)
from langchain_core.runnables.config import RunnableConfig
from langgraph.types import Command
from langsmith import uuid7
from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table
from rich.text import Text
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings

from deepagents import create_deep_agent
from .config.checkpointer import create_checkpointer
from .config.env import load_project_env
from .deep_agent import app as default_app, agent_kwargs

console = Console()
cli = typer.Typer(help="Interactive Deep Agent CLI", invoke_without_command=True)

STATUS_PHRASES = [
    "Coding is 90% debugging, 10% writing bugs.",
    "Aligning semicolons with the universe...",
    "Convincing the AI to stick to the plan...",
    "Refactoring reality one function at a time.",
    "Untangling dependency spaghetti...",
]


def _content_to_text(content: Any) -> str:
    """Normalize LangChain content blocks into text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    if isinstance(content, Iterable):
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
            elif hasattr(block, "text"):
                parts.append(getattr(block, "text") or "")
    return "".join(parts)


def _stringify(value: Any, limit: int = 200) -> str:
    """Best effort stringify with truncation."""
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, default=str)
        except Exception:
            text = str(value)
    text = text.strip()
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


IGNORED_NAMESPACE = {}


def _is_uuid(part: str) -> bool:
    """Check if a string looks like a UUID."""
    return len(part) > 20 and "-" in part


def _render_namespace_header(namespace: tuple[str, ...]) -> None:
    """Render a header for the current namespace (sub-agent)."""
    labels = []
    for part in namespace:
        label = part
        if ":" in part:
            label = part.split(":", 1)[1]
        
        if label not in IGNORED_NAMESPACE and not _is_uuid(label):
            labels.append(label)
    
    if not labels:
        return
 
    header_text = " > ".join(labels)
    console.print(f"\n[bold blue]🤖 {header_text}[/]")


def _render_tool_start(name: str, args: Any, call_id: str = None) -> None:
    from rich.tree import Tree
    
    tree = Tree(f"[bold magenta]🔧 {name}[/]", guide_style="dim")
    
    # Add input branch
    input_str = _stringify(args, limit=500)
    if len(input_str) > 100:
        # Pretty print for long inputs
        try:
            formatted = json.dumps(json.loads(input_str) if isinstance(args, str) else args, indent=2, ensure_ascii=False)
            input_branch = tree.add("[cyan]Input:[/]")
            for line in formatted.split('\n'):
                if line.strip():
                    input_branch.add(f"[dim]{line}[/]")
        except:
            tree.add(f"[cyan]Input:[/] [dim]{input_str}[/]")
    else:
        tree.add(f"[cyan]Input:[/] [dim]{input_str}[/]")
    
    # Store tool info for later output rendering
    if call_id:
        _active_tool_trees[call_id] = {"name": name, "args": args}


def _render_tool_end(name: str, result: Any, call_id: str = None) -> None:
    from rich.tree import Tree
    
    result_str = _stringify(result, limit=500)
    
    # Try to get the stored tool info
    tool_info = _active_tool_trees.pop(call_id, None) if call_id else None
    
    if tool_info:
        # Create a complete tree with both input and output
        tree = Tree(f"[bold green]✓ {tool_info['name']}[/]", guide_style="dim")
        
        # Add input (concise version)
        input_str = _stringify(tool_info['args'], limit=100)
        tree.add(f"[cyan]Input:[/] [dim]{input_str}[/]")
        
        # Add output
        if len(result_str) > 100:
            try:
                formatted = json.dumps(json.loads(result_str) if isinstance(result, str) else result, indent=2, ensure_ascii=False)
                output_branch = tree.add("[green]Output:[/]")
                for line in formatted.split('\n')[:20]:
                    if line.strip():
                        output_branch.add(f"[dim]{line}[/]")
                if formatted.count('\n') > 20:
                    output_branch.add("[dim]... (truncated)[/]")
            except:
                tree.add(f"[green]Output:[/] [dim]{result_str}[/]")
        else:
            tree.add(f"[green]Output:[/] [dim]{result_str}[/]")
        console.print(tree)
    else:
        # Fallback: create a simple output-only tree
        tree = Tree(f"[bold green]✓ {name}[/]", guide_style="dim")
        tree.add(f"[green]Output:[/] [dim]{result_str}[/]")
        console.print(tree)


# Global dictionary to track active tool trees
_active_tool_trees = {}


def _render_todos(todos: list[dict]) -> None:
    console.print(f"  [cyan]To-Do Updates[/cyan]")
    for todo in todos:
        status = todo.get("status", "pending")
        if status == "completed":
            badge = "[green]✔[/]"
        elif status == "in_progress":
            badge = "[yellow]~[/]"
        else:
            badge = "[dim]•[/]"
        console.print(f"    {badge} {todo.get('content','')}")




async def _prompt_for_approval(action: dict) -> str:
    description = action.get("description", "Tool action requires approval.")
    args_text = _stringify(action.get("args") or action.get("arguments"), 200)
    console.print(
        Panel(
            f"[bold]{description}[/]\n[dim]{args_text}[/]",
            title="🤖 Approval Needed",
            border_style="red",
        )
    )
    return await questionary.select(
        "Select action:",
        choices=["Approve", "Approve for Session", "Reject"],
        style=questionary.Style([
            ('qmark', 'fg:#673ab7 bold'),
            ('question', 'bold'),
            ('answer', 'fg:#f44336 bold'),
            ('pointer', 'fg:#673ab7 bold'),
            ('highlighted', 'fg:#673ab7 bold'),
            ('selected', 'fg:#cc5454'),
            ('separator', 'fg:#cc5454'),
            ('instruction', ''),
            ('text', ''),
            ('disabled', 'fg:#858585 italic')
        ])
    ).ask_async()


def _render_agent_reply(text: str) -> None:
    console.print()
    console.print(
        Panel(
            Markdown(text),
            border_style="white",
            title="Agent",
            style="white",
        )
    )
    console.print()


def _get_tool_calls(message: AIMessage) -> list[dict]:
    calls = getattr(message, "tool_calls", None)
    if calls:
        return calls
    return message.additional_kwargs.get("tool_calls") or []


def _parse_args(args: Any) -> Any:
    if isinstance(args, str):
        try:
            return json.loads(args)
        except Exception:
            return args
    return args


CONTEXT_WINDOW_LIMIT = 128000


def _render_usage(usage: dict) -> None:
    """Render token usage statistics."""
    if not usage:
        return
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    total_tokens = usage.get("total_tokens", 0)
    remaining_tokens = CONTEXT_WINDOW_LIMIT - total_tokens
    
    usage_text = f"[dim]Tokens: {input_tokens} in / {output_tokens} out / {total_tokens} total / {remaining_tokens} remaining[/dim]"
    console.print(f"  {usage_text}")


async def _stream_agent_response(user_input: str, thread_id: str, session_approved_tools: set, app: Any) -> None:
    """Stream the agent response with tool + HITL visibility."""
    stream_input: Any = {"messages": [{"role": "user", "content": user_input}]}
    config: RunnableConfig = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 600,
    }

    current_namespace = "Agent"
    printed_tool_calls = set()
    streamed_messages = set()

    while True:
        interrupt_requests: list[dict] = []
        last_event = time.time()
        assistant_line_open = False
        status_index = 0
        status_frame = 0
        status_running = True
        status = console.status(
            Text(
                f"{STATUS_PHRASES[status_index]}",
                style="bold magenta",
            ),
            spinner="dots",
        )
        status.start()

        async def status_task() -> None:
            nonlocal status_index, status_frame
            while status_running:
                await asyncio.sleep(0.7)
                if not status_running:
                    break
                idle = time.time() - last_event
                if idle >= 2:
                    status_frame = (status_frame + 1) 
                    style = "bold magenta"
                    status_index = (status_index + 1) % len(STATUS_PHRASES)
                    status.update(Text(f"{STATUS_PHRASES[status_index]}", style=style))
                else:
                    status.update(Text("", style="magenta"))

        monitor_task = asyncio.create_task(status_task())

        try:
            async for event in app.astream_events(
                stream_input,
                version="v2",
                config=config,
            ):
                last_event = time.time()
                
                if event["event"] == "on_tool_start" and event["name"] == "task":
                    subagent_type = event["data"]["input"]["subagent_type"]
                    if current_namespace != subagent_type:
                        current_namespace = subagent_type
                        _render_namespace_header((current_namespace,))
                elif event["event"] == "on_tool_end" and event["name"] == "task":
                    if current_namespace != "Agent":
                        current_namespace = "Agent"
                        _render_namespace_header((current_namespace,))
                
                # Handle tool call start events
                if event["event"] == "on_tool_start":
                    if status_running:
                        status.stop()
                        status_running = False
                    
                    tool_name = event.get("name", "tool")
                    tool_input = event.get("data", {}).get("input", {})
                    run_id = event.get("run_id")
                    
                    _render_tool_start(tool_name, tool_input, run_id)
                    continue
                
                # Handle tool call end events
                if event["event"] == "on_tool_end":
                    tool_name = event.get("name", "tool")
                    tool_output = event.get("data", {}).get("output")
                    run_id = event.get("run_id")
                    
                    _render_tool_end(tool_name, tool_output, run_id)
                    continue
                
                #Handle streaming token events from LLM
                if event["event"] == "on_chat_model_stream":
                    chunk_data = event.get("data", {})
                    chunk = chunk_data.get("chunk")
                    if chunk and hasattr(chunk, "content"):
                        text = _content_to_text(chunk.content)
                        if text:
                            if status_running:
                                status.stop()
                                status_running = False
                            sys.stdout.write(text)
                            sys.stdout.flush()
                            assistant_line_open = True
                    continue
                
                # Handle LLM completion
                if event["event"] == "on_chat_model_end":
                    if assistant_line_open:
                        sys.stdout.write("\n")
                        sys.stdout.flush()
                        assistant_line_open = False
                    
                    # Show usage if available
                    output_data = event.get("data", {}).get("output", {})
                    if hasattr(output_data, "usage_metadata") and output_data.usage_metadata:
                        _render_usage(output_data.usage_metadata)
                    continue
                
                # Handle interrupts
                if event["event"] == "on_chain_end":
                    chain_output = event.get("data", {}).get("output", {})
                    if isinstance(chain_output, dict) and "__interrupt__" in chain_output:
                        interrupt_data = chain_output["__interrupt__"]
                        if isinstance(interrupt_data, tuple):
                            interrupt_data = interrupt_data[0]
                        if hasattr(interrupt_data, "value"):
                            interrupt_data = interrupt_data.value
                        if interrupt_data:
                            interrupt_requests.append(interrupt_data)

        finally:
            if status_running:
                status_running = False
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
                sys.stdout.write("\r" + " " * (console.width - 1) + "\r")
                sys.stdout.flush()
                status.stop()
            console.print()

        # Check for interrupts in the state if none were caught in the stream
        if not interrupt_requests:
            state = await app.aget_state(config)
            if state.tasks:
                for task in state.tasks:
                    if task.interrupts:
                        for interrupt in task.interrupts:
                            val = interrupt.value
                            if val:
                                interrupt_requests.append(val)

        if interrupt_requests:
            decisions = []
            for request in interrupt_requests:
                for action in request.get("action_requests", []):
                    tool_name = action.get("name")
                    
                    if tool_name and tool_name in session_approved_tools:
                        console.print(f"  [dim]Auto-approved {tool_name} (Session)[/dim]")
                        decisions.append({"type": "approve"})
                        continue

                    choice = await _prompt_for_approval(action)
                    
                    if choice == "Approve":
                        decisions.append({"type": "approve"})
                    elif choice == "Approve for Session":
                        if tool_name:
                            session_approved_tools.add(tool_name)
                        decisions.append({"type": "approve"})
                    else:
                        decisions.append({"type": "reject", "message": "Rejected by user"})

            stream_input = Command(resume={"decisions": decisions})
            continue
        
        break

    if assistant_line_open:
        console.print()

@cli.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    LuminaMind: Deep Agent CLI & Dev Server Launcher.
    """
    if ctx.invoked_subcommand is None:
        console.print(Panel.fit("[bold cyan]Welcome to LuminaMind[/bold cyan]", border_style="cyan"))
        
        choice = questionary.select(
            "Select mode:",
            choices=["CLI Chat", "LangGraph Dev"],
            style=questionary.Style([
                ('qmark', 'fg:#673ab7 bold'),       # token in front of the question
                ('question', 'bold'),               # question text
                ('answer', 'fg:#f44336 bold'),      # submitted answer text behind the question
                ('pointer', 'fg:#673ab7 bold'),     # pointer used in select and checkbox prompts
                ('highlighted', 'fg:#673ab7 bold'), # pointed-at choice in select and checkbox prompts
                ('selected', 'fg:#cc5454'),         # style for a selected item of a checkbox
                ('separator', 'fg:#cc5454'),        # separator in lists
                ('instruction', ''),                # user instructions for select, rawselect, checkbox
                ('text', ''),                       # plain text
                ('disabled', 'fg:#858585 italic')   # disabled choices for select and checkbox prompts
            ])
        ).ask()
        
        if choice == "CLI Chat":
            chat(None)
        elif choice == "LangGraph Dev":
            console.print("[green]Starting LangGraph Dev Server...[/green]")
            subprocess.run(["langgraph", "dev"])


@cli.command()
def chat(thread: Optional[str] = typer.Option(None, help="Existing thread ID to resume.")) -> None:
    """
    Start a conversational CLI with the deep agent.
    """
    load_project_env()
    current_thread = thread or str(uuid7())
    typer.echo("Deep Agent CLI")
    typer.echo("Type your question. Press Meta+Enter (or Esc then Enter) to submit. Commands: /exit, /reset")

    app = default_app
    if app.checkpointer is None:
        console.print("[dim]Initializing local checkpointer for CLI mode...[/dim]")
        cp = create_checkpointer()
        app = create_deep_agent(**agent_kwargs, checkpointer=cp)

    session = PromptSession(history=InMemoryHistory())
    style = Style.from_dict({
        'prompt': 'bold cyan',
    })

    kb = KeyBindings()
    last_interrupt_time = 0.0
    session_approved_tools = set()

    @kb.add('enter')
    def _(event):
        event.current_buffer.validate_and_handle()

    @kb.add('escape', 'enter')
    def _(event):
        event.current_buffer.insert_text('\n')

    while True:
        try:
            user_input = session.prompt([('class:prompt', 'You: ')], style=style, multiline=True, key_bindings=kb)
        except KeyboardInterrupt:
            now = time.time()
            if now - last_interrupt_time < 1.0:
                typer.echo("\nExiting. Goodbye!")
                break
            last_interrupt_time = now
            typer.echo("\n(Press Ctrl+C again to exit)")
            continue
        except EOFError:
            typer.echo("\nExiting. Goodbye!")
            break

        if not user_input.strip():
            continue

        lowered = user_input.strip().lower()
        if lowered in {"/exit", "/quit"}:
            typer.echo("Goodbye!")
            break
        if lowered == "/reset":
            current_thread = str(uuid7())
            session_approved_tools.clear()
            typer.echo("🔄 Started a new conversation.")
            continue

        console.print("[bold magenta]Agent>[/] ", end="")
        try:
            asyncio.run(_stream_agent_response(user_input, current_thread, session_approved_tools, app))
        except KeyboardInterrupt:
            console.print("\n[red]🛑 Agent interrupted by user.[/]")
        except Exception as exc:
            console.print(f"\n[red]Agent error:[/] {exc}")


if __name__ == "__main__":
    cli()
