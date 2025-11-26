import asyncio
import json
import os
import sys
import time
import subprocess
from contextlib import contextmanager
from importlib import resources
from pathlib import Path
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
from .config.env import load_project_env, ensure_global_env, configure_global_env
from .observability.logging import setup_logging
from .observability.metrics import start_metrics_server

console = Console()
cli = typer.Typer(help="Interactive Deep Agent CLI", invoke_without_command=True)
_observability_initialized = False

STATUS_PHRASES = [
    "Coding is 90% debugging, 10% writing bugs.",
    "Aligning semicolons with the universe...",
    "Convincing the AI to stick to the plan...",
    "Refactoring reality one function at a time.",
    "Untangling dependency spaghetti...",
]


def _initialize_observability() -> None:
    """Configure logging and metrics once per process."""
    global _observability_initialized
    if _observability_initialized:
        return

    log_format_json = os.getenv("LOG_FORMAT", "json").lower() == "json"
    setup_logging(level=os.getenv("LOG_LEVEL", "INFO"), json_format=log_format_json)
    start_metrics_server()
    _observability_initialized = True


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


@contextmanager
def _langgraph_config_file() -> Iterable[Path]:
    """Locate langgraph.json from CWD or package."""
    # 1. Check CWD (user override)
    cwd_config = Path.cwd() / "langgraph.json"
    if cwd_config.exists():
        yield cwd_config
        return

    # 2. Check package resources
    ctx = None
    try:
        pkg_resource = resources.files("luminamind").joinpath("langgraph.json")
        ctx = resources.as_file(pkg_resource)
    except (FileNotFoundError, ModuleNotFoundError, ImportError):
        pass

    if ctx:
        with ctx as pkg_path:
            if pkg_path.exists():
                yield pkg_path
                return

    # 3. Fallback to local file (for source execution)
    local_config = Path(__file__).parent / "langgraph.json"
    if local_config.exists():
        yield local_config
        return

    raise FileNotFoundError(f"langgraph.json not found in CWD, package resources, or at {local_config}")


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
    
    usage_text = f"\n[dim]Tokens: {input_tokens} in / {output_tokens} out / {total_tokens} total / {remaining_tokens} remaining[/dim]"
    console.print(f"\n{usage_text}")


async def _stream_agent_response(user_input: str, thread_id: str, session_approved_tools: set, app: Any) -> None:
    """Stream the agent response with tool + HITL visibility (using astream for guaranteed step completion)."""
    stream_input: Any = {"messages": [{"role": "user", "content": user_input}]}
    config: RunnableConfig = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 1000,
    }

    current_namespace = "Agent"
    processed_message_ids = set()

    while True:
        interrupt_requests: list[dict] = []
        last_event = time.time()
        assistant_line_open = False
        status_index = 0
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
            nonlocal status_index
            while status_running:
                await asyncio.sleep(0.7)
                if not status_running:
                    break
                idle = time.time() - last_event
                if idle >= 2:
                    status_index = (status_index + 1) % len(STATUS_PHRASES)
                    status.update(Text(f"{STATUS_PHRASES[status_index]}", style="bold magenta"))
                else:
                    status.update(Text("", style="magenta"))

        monitor_task = asyncio.create_task(status_task())

        try:
            # Use astream instead of astream_events to ensure step completion
            async for chunk in app.astream(stream_input, config, stream_mode="updates"):
                last_event = time.time()
                
                # Extract messages from the chunk
                for node_name, node_data in chunk.items():
                    # node_data might be a dict or other state update types (Overwrite, etc.)
                    # Only process if it's a dict with messages
                    if not isinstance(node_data, dict):
                        continue
                    
                    messages = node_data.get("messages", [])
                    # messages itself might be an Overwrite object or other non-list type
                    if not isinstance(messages, (list, tuple)):
                        continue
                    if not messages:
                        continue
                    
                    for message in messages:
                        message_id = getattr(message, "id", None)
                        if message_id and message_id in processed_message_ids:
                            continue
                        if message_id:
                            processed_message_ids.add(message_id)
                        
                        # Handle AI messages (includes tool calls and text responses)
                        if isinstance(message, AIMessage) or isinstance(message, AIMessageChunk):
                            # Handle tool calls
                            tool_calls = _get_tool_calls(message)
                            if tool_calls:
                                if status_running:
                                    status.stop()
                                    status_running = False
                                
                                for tool_call in tool_calls:
                                    tool_name = tool_call.get("name", "tool")
                                    tool_args = _parse_args(tool_call.get("args", {}))
                                    call_id = tool_call.get("id")

                                    if tool_name == "task" and isinstance(tool_args, dict):
                                        subagent_type = tool_args.get("subagent_type", "")
                                        if subagent_type and current_namespace != subagent_type:
                                            current_namespace = subagent_type
                                            _render_namespace_header((current_namespace,))
                                    
                                    # Handle write_todos specially
                                    if tool_name == "write_todos" and isinstance(tool_args, dict):
                                        todos = tool_args.get("todos", [])
                                        if todos:
                                            _render_todos(todos)
                                    else:
                                        _render_tool_start(tool_name, tool_args, call_id)
                            
                            # Handle streaming text content
                            content = _content_to_text(message.content)
                            if content and not tool_calls:
                                if status_running:
                                    status.stop()
                                    status_running = False
                                sys.stdout.write(content)
                                sys.stdout.flush()
                                assistant_line_open = True
                            
                            # Show usage metadata if available
                            if hasattr(message, "usage_metadata") and message.usage_metadata:
                                _render_usage(message.usage_metadata)
                        
                        # Handle tool messages (tool results)
                        elif isinstance(message, ToolMessage):
                            if status_running:
                                status.stop()
                                status_running = False
                            
                            tool_call_id = getattr(message, "tool_call_id", None)
                            content = _content_to_text(message.content)
                            
                            # Try to get the tool name from active tracking
                            tool_name = "tool"
                            if tool_call_id and tool_call_id in _active_tool_trees:
                                tool_name = _active_tool_trees[tool_call_id].get("name", "tool")
                            
                            # Don't render write_todos results
                            if tool_name != "write_todos":
                                _render_tool_end(tool_name, content, tool_call_id)

                            if tool_name == "task" and current_namespace != "Agent":
                                current_namespace = "Agent"
                                _render_namespace_header((current_namespace,))

            if assistant_line_open:
                sys.stdout.write("\n")
                sys.stdout.flush()
                assistant_line_open = False

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

        # Check for interrupts in the state
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

def _find_langgraph_executable() -> str:
    """Find the langgraph executable."""
    # 1. Check in the same directory as the python interpreter (venv bin)
    venv_bin = Path(sys.executable).parent
    langgraph_path = venv_bin / "langgraph"
    if langgraph_path.exists():
        return str(langgraph_path)
    
    # 2. Fallback to PATH
    return "langgraph"


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
            langgraph_cmd = _find_langgraph_executable()
            try:
                with _langgraph_config_file() as config_path:
                    subprocess.run([langgraph_cmd, "dev", "--config", str(config_path)])
            except FileNotFoundError as exc:
                console.print(f"[red]Error: {exc}[/red]")
                console.print(f"[dim]Could not find '{langgraph_cmd}'. Ensure langgraph-cli is installed.[/dim]")
                raise typer.Exit(code=1)


@cli.command()
def config() -> None:
    """
    Configure global environment variables.
    """
    configure_global_env(force=True)


@cli.command()
def chat(thread: Optional[str] = typer.Option(None, help="Existing thread ID to resume.")) -> None:
    """
    Start a conversational CLI with the deep agent.
    """
    ensure_global_env()
    load_project_env()
    _initialize_observability()
    
    # Lazy import to avoid early initialization before config is loaded
    from .deep_agent import app as default_app, agent_kwargs
    
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
        if lowered == "/config":
            configure_global_env(force=True)
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
