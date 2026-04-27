import asyncio
import json
import os
import re
import sys
import time
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
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
from .config.session_store import FileBackedSessionStore
from .config.setup_wizard import run_setup_wizard_sync, _is_configured
from .config.providers import (
    read_provider_configs,
    write_provider_config,
    set_active_provider,
    get_active_provider,
    remove_provider,
    PROVIDER_SCHEMA,
)
from .models.presets import ModelPresets
from .models.registry import AgentRole, ModelRegistry, RoleModelMapping
from .observability.logging import setup_logging
from .observability.metrics import start_metrics_server

# Import chaos module
from luminamind.chaos import (
    ChaosEngine,
    ChaosReport,
    ChaosSuiteResult,
    generate_chaos_report,
    list_scenarios,
    run_chaos_test,
    save_json_report,
    SCENARIOS,
)

console = Console()
cli = typer.Typer(help="Interactive Deep Agent CLI", invoke_without_command=True)
chaos_cli = typer.Typer(help="Chaos testing commands for resilience validation")
cli.add_typer(chaos_cli, name="chaos", invoke_without_command=True)
session_cli = typer.Typer(help="Persistent session browser and transcript export")
model_cli = typer.Typer(help="Model registry and runtime model selection")
permission_cli = typer.Typer(help="Tool approval and shell permission profiles")
mcp_cli = typer.Typer(help="MCP server/config inspection")
providers_cli = typer.Typer(help="Manage multiple LLM provider configs in parallel")
cli.add_typer(session_cli, name="sessions")
cli.add_typer(model_cli, name="models")
cli.add_typer(permission_cli, name="permissions")
cli.add_typer(mcp_cli, name="mcp")
cli.add_typer(providers_cli, name="providers")
_observability_initialized = False

STATUS_PHRASES = [
    "Coding is 90% debugging, 10% writing bugs.",
    "Aligning semicolons with the universe...",
    "Convincing the AI to stick to the plan...",
    "Refactoring reality one function at a time.",
    "Untangling dependency spaghetti...",
]

PIPE_LIMIT_BYTES = 10 * 1024 * 1024
DEFAULT_STREAM_MODES = ["messages", "updates", "custom", "tasks"]
JSON_FORMATS = {"json", "stream-json"}
DEFAULT_SESSION_ROOT = Path.home() / ".luminamind"
CLI_CONFIG_DIR = Path.home() / ".luminamind"
PERMISSION_CONFIG = CLI_CONFIG_DIR / "permissions.json"
CLI_CONFIG = CLI_CONFIG_DIR / "cli.json"

PERMISSION_PROFILES: dict[str, dict[str, Any]] = {
    "auto": {
        "approval": "auto",
        "shell_commands": ["cat", "echo", "find", "git", "grep", "ls", "npm", "pwd", "pytest", "python", "which", "yarn"],
    },
    "ask": {
        "approval": "ask",
        "shell_commands": ["cat", "echo", "find", "git", "grep", "ls", "npm", "pwd", "pytest", "python", "which", "yarn"],
    },
    "locked": {
        "approval": "ask",
        "shell_commands": ["ls", "pwd", "which"],
    },
}


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


def _json_ready(value: Any) -> Any:
    """Convert LangChain/LangGraph objects to JSON-safe structures."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_ready(v) for v in value]
    if hasattr(value, "model_dump"):
        try:
            return _json_ready(value.model_dump())
        except Exception:
            pass
    if hasattr(value, "dict"):
        try:
            return _json_ready(value.dict())
        except Exception:
            pass
    return str(value)


def _emit_json(value: dict, output_format: str = "stream-json") -> None:
    payload = json.dumps(_json_ready(value), ensure_ascii=False)
    if output_format == "json":
        console.print_json(payload)
    else:
        sys.stdout.write(payload + "\n")
        sys.stdout.flush()


def _parse_stream_modes(value: str | None) -> list[str]:
    if not value:
        return list(DEFAULT_STREAM_MODES)
    modes = [item.strip() for item in value.split(",") if item.strip()]
    valid = {"values", "updates", "messages", "custom", "checkpoints", "tasks", "debug"}
    unknown = [mode for mode in modes if mode not in valid]
    if unknown:
        raise typer.BadParameter(f"Unknown stream mode(s): {', '.join(unknown)}")
    return modes or list(DEFAULT_STREAM_MODES)


def _read_piped_stdin() -> str:
    if sys.stdin.isatty():
        return ""
    data = sys.stdin.buffer.read(PIPE_LIMIT_BYTES + 1)
    if len(data) > PIPE_LIMIT_BYTES:
        raise typer.BadParameter("Piped input exceeds 10 MiB limit")
    return data.decode("utf-8", errors="replace").strip()


def _apply_runtime_overrides(
    provider: str | None = None,
    model: str | None = None,
    approval: str | None = None,
    role_models: list[str] | None = None,
) -> None:
    if provider is None and model is None:
        defaults = _load_json_config(CLI_CONFIG, {})
        provider = defaults.get("provider")
        model = defaults.get("model")
    if provider:
        os.environ["LLM_PROVIDER"] = provider
        os.environ["LUMINAMIND_ACTIVE_PROVIDER"] = provider
    if model:
        os.environ["LUMINAMIND_MODEL"] = model
    if approval:
        if approval not in {"ask", "auto"}:
            raise typer.BadParameter("--approval must be 'ask' or 'auto'")
        os.environ["LUMINAMIND_REQUIRE_TOOL_APPROVAL"] = "1" if approval == "ask" else "0"
    if role_models and isinstance(role_models, list):
        for item in role_models:
            if "=" not in item:
                raise typer.BadParameter(f"--role-model must be role=model, got: {item}")
            role, mdl = item.split("=", 1)
            os.environ[f"LUMINAMIND_ROLE_MODEL_{role.upper().strip()}"] = mdl.strip()
            console.print(f"[dim]Override: {role.strip()} → {mdl.strip()}[/dim]")


def _session_store() -> FileBackedSessionStore:
    root = Path(os.environ.get("LUMINAMIND_SESSION_ROOT", str(DEFAULT_SESSION_ROOT))).expanduser()
    return FileBackedSessionStore(root)


def _append_session_message(thread_id: str, role: str, content: str, **extra: Any) -> None:
    if not content:
        return
    store = _session_store()
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat(),
        **extra,
    }
    store.append_message(thread_id, message)
    store.save(thread_id)


def _load_transcript(thread_id: str) -> list[dict[str, Any]]:
    session = _session_store().resume(thread_id)
    count = session.transcript.get_message_count()
    return [msg for idx in range(count) if (msg := session.transcript.get_message_at(idx)) is not None]


def _write_transcript_markdown(thread_id: str, messages: list[dict[str, Any]], export_path: Path) -> None:
    lines = [f"# LuminaMind Session {thread_id}", ""]
    for item in messages:
        role = item.get("role", "message")
        timestamp = item.get("timestamp") or item.get("created_at")
        heading = f"## {role}" + (f" · {timestamp}" if timestamp else "")
        lines.extend([heading, "", str(item.get("content", "")), ""])
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text("\n".join(lines), encoding="utf-8")


def _load_json_config(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return dict(default)
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(default)
    return loaded if isinstance(loaded, dict) else dict(default)


def _save_json_config(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _current_permission_profile() -> str:
    return str(_load_json_config(PERMISSION_CONFIG, {"profile": "auto"}).get("profile", "auto"))


def _apply_permission_profile(profile: str) -> None:
    if profile not in PERMISSION_PROFILES:
        raise typer.BadParameter(f"profile must be one of: {', '.join(PERMISSION_PROFILES)}")
    data = PERMISSION_PROFILES[profile]
    _apply_runtime_overrides(None, None, data["approval"])
    os.environ["LUMINAMIND_ALLOWED_SHELL_COMMANDS"] = ",".join(data["shell_commands"])


def _set_permission_profile(profile: str) -> None:
    _apply_permission_profile(profile)
    _save_json_config(PERMISSION_CONFIG, {"profile": profile})


def _set_cli_theme(theme: str) -> None:
    if theme not in {"cyan", "amber", "green", "mono"}:
        raise typer.BadParameter("theme must be one of: cyan, amber, green, mono")
    config = _load_json_config(CLI_CONFIG, {"theme": "cyan"})
    config["theme"] = theme
    _save_json_config(CLI_CONFIG, config)


def _prompt_style() -> Style:
    theme = _load_json_config(CLI_CONFIG, {"theme": "cyan"}).get("theme", "cyan")
    colors = {"cyan": "bold cyan", "amber": "bold #ffb000", "green": "bold green", "mono": "bold white"}
    return Style.from_dict({"prompt": colors.get(str(theme), "bold cyan")})


def _git_diff() -> str | None:
    completed = subprocess.run(["git", "diff", "--binary"], text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        return None
    return completed.stdout


def _git_apply(diff: str, *, reverse: bool = False) -> tuple[bool, str]:
    if not diff.strip():
        return True, ""
    args = ["git", "apply", "--binary"]
    if reverse:
        args.append("-R")
    completed = subprocess.run(args, input=diff, text=True, capture_output=True, check=False)
    return completed.returncode == 0, completed.stderr or completed.stdout


@dataclass
class UndoRecord:
    before: str
    after: str
    summary: str


def _restore_diff_state(expected: str, target: str) -> tuple[bool, str]:
    current = _git_diff()
    if current is None:
        return False, "Not inside a git worktree or git diff failed."
    if current != expected:
        return False, "Working tree changed since this undo record was created; refusing to overwrite unrelated edits."
    ok, message = _git_apply(expected, reverse=True)
    if not ok:
        return False, message
    ok, message = _git_apply(target, reverse=False)
    return ok, message


def _detect_mcp_configs() -> list[dict[str, Any]]:
    candidates = [
        Path.cwd() / ".mcp.json",
        Path.cwd() / "mcp.json",
        Path.cwd() / ".cursor" / "mcp.json",
        Path.cwd() / ".vscode" / "mcp.json",
        Path.home() / ".config" / "luminamind" / "mcp.json",
    ]
    configs: list[dict[str, Any]] = []
    for path in candidates:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            configs.append({"path": str(path), "error": str(exc), "servers": []})
            continue
        servers = data.get("mcpServers") or data.get("servers") or {}
        if isinstance(servers, dict):
            server_names = sorted(servers)
        elif isinstance(servers, list):
            server_names = [str(item.get("name", "unnamed")) for item in servers if isinstance(item, dict)]
        else:
            server_names = []
        configs.append({"path": str(path), "servers": server_names})
    return configs


def _render_mcp_status() -> None:
    configs = _detect_mcp_configs()
    table = Table(title="MCP Configs", box=box.SIMPLE)
    table.add_column("Path", style="cyan")
    table.add_column("Servers")
    table.add_column("Status")
    if not configs:
        table.add_row("none detected", "", "No MCP config files found in common project/user locations")
    for item in configs:
        table.add_row(
            item.get("path", ""),
            ", ".join(item.get("servers") or []) or "none",
            item.get("error", "ok"),
        )
    console.print(table)


def _load_cli_app(*, interactive: bool = True):
    """Load the lazy app after environment/model overrides are applied."""
    if interactive:
        ensure_global_env()
    load_project_env()
    if interactive or os.environ.get("LUMINAMIND_RUN_OBSERVABILITY") == "1":
        _initialize_observability()

    from .deep_agent import app as default_app, agent_kwargs

    app = default_app
    if app.checkpointer is None:
        cp = create_checkpointer()
        app = create_deep_agent(**agent_kwargs, checkpointer=cp)
    return app


def _expand_file_references(text: str) -> str:
    """Expand simple @path references into bounded inline file context."""
    pattern = re.compile(r"(?<!\S)@([A-Za-z0-9_./~\\:-]+)")

    def replace(match: re.Match[str]) -> str:
        raw_path = match.group(1).rstrip(".,;:)")
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        try:
            resolved = path.resolve()
            if not resolved.exists() or not resolved.is_file():
                return match.group(0)
            content = resolved.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return match.group(0)
        if len(content) > 20_000:
            content = content[:20_000] + "\n... [truncated]"
        return f"\n\n[Referenced file: {resolved}]\n```text\n{content}\n```\n"

    return pattern.sub(replace, text)


def _render_cli_help() -> None:
    table = Table(title="LuminaMind Chat Commands", box=box.SIMPLE)
    table.add_column("Command", style="cyan")
    table.add_column("Description")
    rows = [
        ("/help", "Show this command list"),
        ("/status", "Show thread, model, approval, session, MCP, token, and role state"),
        ("/thread", "Print the current thread id"),
        ("/sessions", "List saved sessions"),
        ("/resume <thread>", "Resume a saved session"),
        ("/search <text>", "Search current session transcript"),
        ("/fork [thread]", "Fork current conversation into a new thread id"),
        ("/reset, /new, /clear", "Start a new thread and clear approvals"),
        ("/model", "Show current model and available models"),
        ("/model <provider/model>", "Switch model (e.g., /model kimi/kimi-k2.6)"),
        ("/provider", "Show current active provider and configured providers"),
        ("/provider <name>", "Switch active provider (e.g., /provider z.ai)"),
        ("/models", "Show per-role model assignments"),
        ("/role-model", "Show current role→model mappings"),
        ("/role-model <role=model>", "Set a role's model (e.g., /role-model planner=kimi-k2.6)"),
        ("/preset", "List available model presets"),
        ("/preset <name>", "Apply a model preset (e.g., /preset fast)"),
        ("/permissions [auto|ask|locked]", "Show or change permission profile"),
        ("/mcp", "Show detected MCP config files and servers"),
        ("/tokens", "Show latest token usage and context estimate"),
        ("/undo, /redo", "Undo or redo the last tracked git diff created after a prompt"),
        ("/theme [cyan|amber|green|mono]", "Show or change prompt theme"),
        ("/export [path]", "Export this session transcript to Markdown"),
        ("/config", "Edit global environment/configuration"),
        ("/exit, /quit", "Exit the CLI"),
        ("!<command>", "Run a local shell command through the safe shell tool"),
        ("@path", "Inline a referenced file into the next prompt"),
    ]
    for command, description in rows:
        table.add_row(command, description)
    console.print(table)


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




async def _prompt_for_approval(action: dict) -> dict:
    """Prompt user for tool approval. Returns a decision dict.

    Supports approve, edit, reject, and session-level approval.
    """
    description = action.get("description", "Tool action requires approval.")
    args_text = _stringify(action.get("args") or action.get("arguments"), 200)
    tool_name = action.get("name", "tool")
    console.print(
        Panel(
            f"[bold]{description}[/]\n[dim]{args_text}[/]",
            title="🤖 Approval Needed",
            border_style="red",
        )
    )
    choice = await questionary.select(
        "Select action:",
        choices=[
            "Approve",
            "Approve for Session",
            "Edit Arguments",
            "Reject",
        ],
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

    if choice == "Edit Arguments":
        # Allow user to edit arguments as JSON
        current_args = action.get("args") or action.get("arguments") or {}
        try:
            current_json = json.dumps(current_args, indent=2, ensure_ascii=False)
        except Exception:
            current_json = str(current_args)

        edited = await questionary.text(
            "Edit tool arguments (JSON):",
            default=current_json,
            multiline=True,
        ).ask_async()

        try:
            new_args = json.loads(edited)
            return {
                "type": "edit",
                "editedAction": {
                    "name": tool_name,
                    "args": new_args,
                },
            }
        except json.JSONDecodeError as exc:
            console.print(f"[red]Invalid JSON: {exc}. Rejecting tool call.[/red]")
            return {"type": "reject", "message": "Invalid JSON in edit"}

    if choice == "Approve":
        return {"type": "approve"}
    if choice == "Approve for Session":
        return {"type": "approve", "session": True}
    return {"type": "reject", "message": "Rejected by user"}


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


def _extract_messages_from_update(data: Any) -> list[Any]:
    messages: list[Any] = []
    if not isinstance(data, dict):
        return messages
    for node_data in data.values():
        if not isinstance(node_data, dict):
            continue
        node_messages = node_data.get("messages", [])
        if isinstance(node_messages, (list, tuple)):
            messages.extend(node_messages)
    return messages


def _render_task_event(data: Any) -> None:
    event = _json_ready(data)
    if isinstance(event, dict):
        name = event.get("name") or event.get("node") or event.get("id") or "task"
        status = event.get("event") or event.get("status") or "event"
        console.print(f"[dim]task {status}: {name}[/dim]")
    else:
        console.print(f"[dim]task: {_stringify(event, 300)}[/dim]")


def _render_custom_event(data: Any) -> None:
    console.print(f"[cyan]progress[/cyan] {_stringify(data, 500)}")


def _render_message_token(token: Any) -> bool:
    """Render a streamed token. Returns True if text was written inline."""
    wrote_text = False
    tool_chunks = getattr(token, "tool_call_chunks", None) or []
    for chunk in tool_chunks:
        name = chunk.get("name") if isinstance(chunk, dict) else None
        args = chunk.get("args") if isinstance(chunk, dict) else None
        if name:
            console.print(f"\n[magenta]tool call[/magenta] {name}")
        if args:
            sys.stdout.write(str(args))
            sys.stdout.flush()
            wrote_text = True

    token_type = getattr(token, "type", None)
    if token_type == "tool":
        name = getattr(token, "name", "tool")
        console.print(f"\n[green]tool result[/green] {name}: {_stringify(getattr(token, 'content', ''), 300)}")
        return wrote_text

    text = _content_to_text(getattr(token, "content", None))
    if text and not tool_chunks:
        sys.stdout.write(text)
        sys.stdout.flush()
        wrote_text = True
    return wrote_text


def _render_update_part(data: Any, processed_message_ids: set[str], current_namespace: str) -> str:
    for message in _extract_messages_from_update(data):
        message_id = getattr(message, "id", None)
        if message_id and message_id in processed_message_ids:
            continue
        if message_id:
            processed_message_ids.add(message_id)

        if isinstance(message, AIMessage) or isinstance(message, AIMessageChunk):
            tool_calls = _get_tool_calls(message)
            if tool_calls:
                for tool_call in tool_calls:
                    tool_name = tool_call.get("name", "tool")
                    tool_args = _parse_args(tool_call.get("args", {}))
                    call_id = tool_call.get("id")

                    if tool_name == "task" and isinstance(tool_args, dict):
                        subagent_type = tool_args.get("subagent_type", "")
                        if subagent_type and current_namespace != subagent_type:
                            current_namespace = subagent_type
                            _render_namespace_header((current_namespace,))

                    if tool_name == "write_todos" and isinstance(tool_args, dict):
                        todos = tool_args.get("todos", [])
                        if todos:
                            _render_todos(todos)
                    else:
                        _render_tool_start(tool_name, tool_args, call_id)

            if hasattr(message, "usage_metadata") and message.usage_metadata:
                _render_usage(message.usage_metadata)

        elif isinstance(message, ToolMessage):
            tool_call_id = getattr(message, "tool_call_id", None)
            content = _content_to_text(message.content)
            tool_name = "tool"
            if tool_call_id and tool_call_id in _active_tool_trees:
                tool_name = _active_tool_trees[tool_call_id].get("name", "tool")
            if tool_name != "write_todos":
                _render_tool_end(tool_name, content, tool_call_id)
            if tool_name == "task" and current_namespace != "Agent":
                current_namespace = "Agent"
                _render_namespace_header((current_namespace,))
    return current_namespace


def _usage_from_update(data: Any) -> dict[str, Any]:
    for message in _extract_messages_from_update(data):
        usage = getattr(message, "usage_metadata", None)
        if usage:
            return dict(usage)
    return {}


async def _stream_agent_response(
    user_input: str,
    thread_id: str,
    session_approved_tools: set,
    app: Any,
    *,
    stream_modes: list[str] | None = None,
    subgraphs: bool = True,
    max_turns: int | None = None,
) -> dict[str, Any]:
    """Stream an interactive agent response with v2 multi-mode events."""
    stream_input: Any = {"messages": [{"role": "user", "content": _expand_file_references(user_input)}]}
    config: RunnableConfig = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": max_turns or 1000,
    }

    current_namespace = "Agent"
    processed_message_ids = set()
    stream_modes = stream_modes or list(DEFAULT_STREAM_MODES)
    final_text_parts: list[str] = []
    last_usage: dict[str, Any] = {}

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
            async for chunk in app.astream(
                stream_input,
                config,
                stream_mode=stream_modes,
                subgraphs=subgraphs,
                version="v2",
            ):
                last_event = time.time()
                chunk_type = chunk.get("type") if isinstance(chunk, dict) else None
                namespace = tuple(chunk.get("ns") or ()) if isinstance(chunk, dict) else ()
                data = chunk.get("data") if isinstance(chunk, dict) else chunk

                if namespace:
                    if status_running:
                        status.stop()
                        status_running = False
                    _render_namespace_header(namespace)

                if chunk_type in {"messages", "updates", "custom", "tasks", "debug", "checkpoints"}:
                    if status_running:
                        status.stop()
                        status_running = False

                if chunk_type == "messages":
                    token, _metadata = data
                    if not getattr(token, "tool_call_chunks", None):
                        text = _content_to_text(getattr(token, "content", None))
                        if text:
                            final_text_parts.append(text)
                    usage = getattr(token, "usage_metadata", None)
                    if usage:
                        last_usage = dict(usage)
                    if _render_message_token(token):
                        assistant_line_open = True
                elif chunk_type == "updates":
                    usage = _usage_from_update(data)
                    if usage:
                        last_usage = usage
                    current_namespace = _render_update_part(data, processed_message_ids, current_namespace)
                elif chunk_type == "custom":
                    if assistant_line_open:
                        sys.stdout.write("\n")
                        sys.stdout.flush()
                        assistant_line_open = False
                    _render_custom_event(data)
                elif chunk_type == "tasks":
                    if assistant_line_open:
                        sys.stdout.write("\n")
                        sys.stdout.flush()
                        assistant_line_open = False
                    _render_task_event(data)
                elif chunk_type == "debug":
                    if os.environ.get("LUMINAMIND_DEBUG_STREAM") == "1":
                        console.print(f"[dim]debug[/dim] {_stringify(data, 500)}")

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

                    decision = await _prompt_for_approval(action)

                    if decision.get("type") == "approve":
                        if decision.get("session") and tool_name:
                            session_approved_tools.add(tool_name)
                        decisions.append({"type": "approve"})
                    elif decision.get("type") == "edit":
                        decisions.append(decision)
                    else:
                        decisions.append({"type": "reject", "message": decision.get("message", "Rejected by user")})

            stream_input = Command(resume={"decisions": decisions})
            continue
        
        break

    if assistant_line_open:
        console.print()

    # Record cost tracking
    try:
        from luminamind.cost import get_cost_tracker, get_budget_enforcer
        tracker = get_cost_tracker()
        model_name = os.environ.get("LUMINAMIND_MODEL") or os.environ.get("GLM_MODEL") or os.environ.get("KIMI_MODEL") or os.environ.get("MINIMAX_MODEL") or "unknown"
        provider_name = os.environ.get("LLM_PROVIDER", "openai")
        if last_usage:
            tracker.record(
                session_id=thread_id,
                thread_id=thread_id,
                model=model_name,
                provider=provider_name,
                input_tokens=last_usage.get("input_tokens", 0),
                output_tokens=last_usage.get("output_tokens", 0),
            )
        # Budget enforcement check
        enforcer = get_budget_enforcer()
        warnings = enforcer.check(session_id=thread_id, thread_id=thread_id)[1]
        for w in warnings:
            console.print(f"[yellow]{w.message}[/yellow]")
    except Exception:
        pass

    return {"text": "".join(final_text_parts).strip(), "usage": last_usage}


def _final_text_from_state(state: Any) -> str:
    value = getattr(state, "value", state)
    if isinstance(value, dict):
        messages = value.get("messages")
        if isinstance(messages, (list, tuple)) and messages:
            for message in reversed(messages):
                if isinstance(message, AIMessage):
                    text = _content_to_text(message.content)
                    if text:
                        return text
        result = value.get("result")
        if result is not None:
            return _stringify(result, 10_000)
    return _stringify(value, 10_000)


async def _run_noninteractive(
    prompt: str,
    app: Any,
    *,
    thread_id: str,
    output_format: str,
    stream_modes: list[str],
    subgraphs: bool,
    no_stream: bool,
    max_turns: int | None,
    quiet: bool,
) -> None:
    stream_input = {"messages": [{"role": "user", "content": _expand_file_references(prompt)}]}
    _append_session_message(thread_id, "user", prompt, mode="run")
    config: RunnableConfig = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": max_turns or 1000,
    }

    if no_stream:
        result = await app.ainvoke(stream_input, config, version="v2")
        text = _final_text_from_state(result)
        if output_format in JSON_FORMATS:
            _emit_json({"type": "result", "thread": thread_id, "data": _json_ready(result)}, "json")
        else:
            if text:
                sys.stdout.write(text + "\n")
        if text:
            _append_session_message(thread_id, "agent", text, mode="run")
        return

    final_text_parts: list[str] = []
    async for chunk in app.astream(
        stream_input,
        config,
        stream_mode=stream_modes,
        subgraphs=subgraphs,
        version="v2",
    ):
        if output_format == "stream-json":
            _emit_json(chunk, "stream-json")
            continue

        chunk_type = chunk.get("type") if isinstance(chunk, dict) else None
        data = chunk.get("data") if isinstance(chunk, dict) else chunk
        if output_format == "json":
            continue

        if chunk_type == "messages":
            token, _metadata = data
            text = _content_to_text(getattr(token, "content", None))
            if text:
                final_text_parts.append(text)
                if not quiet:
                    sys.stdout.write(text)
                    sys.stdout.flush()
        elif not quiet and chunk_type == "custom":
            console.print(f"\n[cyan]progress[/cyan] {_stringify(data, 500)}")
        elif not quiet and chunk_type == "tasks":
            console.print()
            _render_task_event(data)

    if output_format == "json":
        _emit_json({"type": "result", "thread": thread_id, "text": "".join(final_text_parts)}, "json")
    elif final_text_parts:
        sys.stdout.write("\n")
        sys.stdout.flush()
    final_text = "".join(final_text_parts).strip()
    if final_text:
        _append_session_message(thread_id, "agent", final_text, mode="run")

def _find_langgraph_executable() -> str:
    """Find the langgraph executable."""
    # 1. Check in the same directory as the python interpreter (venv bin)
    venv_bin = Path(sys.executable).parent
    langgraph_path = venv_bin / "langgraph"
    if langgraph_path.exists():
        return str(langgraph_path)
    
    # 2. Fallback to PATH
    return "langgraph"


@session_cli.command("list")
def sessions_list(limit: int = typer.Option(30, "--limit", "-n", help="Maximum sessions to show.")) -> None:
    """List saved sessions."""
    sessions = _session_store().list()
    table = Table(title="Saved Sessions", box=box.SIMPLE)
    table.add_column("Thread", style="cyan")
    table.add_column("Messages", justify="right")
    table.add_column("Last Accessed")
    table.add_column("Summary")
    for item in sessions[:limit]:
        table.add_row(
            item.get("thread_id", ""),
            str(item.get("message_count", 0)),
            item.get("last_accessed", ""),
            _stringify(item.get("summary", ""), 120),
        )
    console.print(table)


@session_cli.command("show")
def sessions_show(thread_id: str = typer.Argument(..., help="Thread/session ID.")) -> None:
    """Show a saved session transcript."""
    messages = _load_transcript(thread_id)
    if not messages:
        console.print(f"[yellow]No transcript messages found for {thread_id}.[/yellow]")
        return
    for item in messages:
        role = item.get("role", "message")
        console.print(f"[bold cyan]{role}>[/] {_stringify(item.get('content', ''), 2000)}")


@session_cli.command("export")
def sessions_export(
    thread_id: str = typer.Argument(..., help="Thread/session ID."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Markdown output path."),
) -> None:
    """Export a saved session transcript to Markdown."""
    messages = _load_transcript(thread_id)
    if not messages:
        console.print(f"[yellow]No transcript messages found for {thread_id}.[/yellow]")
        raise typer.Exit(code=1)
    export_path = output or Path(f"luminamind-{thread_id}.md")
    _write_transcript_markdown(thread_id, messages, export_path.expanduser())
    console.print(f"[green]Exported transcript to {export_path}[/green]")


@session_cli.command("cleanup")
def sessions_cleanup(days: int = typer.Option(30, "--days", help="Remove sessions not accessed for this many days.")) -> None:
    """Remove old saved sessions."""
    removed = _session_store().cleanup(days)
    console.print(f"Removed {len(removed)} session(s).")


@model_cli.command("list")
def models_list() -> None:
    """List configured per-role model mappings."""
    registry = ModelRegistry()
    table = Table(title="Model Registry", box=box.SIMPLE)
    table.add_column("Role", style="cyan")
    table.add_column("Provider")
    table.add_column("Model")
    table.add_column("Temp", justify="right")
    table.add_column("Max Tokens", justify="right")
    table.add_column("Enabled")
    for mapping in registry.list_all():
        table.add_row(
            mapping.role.value,
            mapping.provider,
            mapping.model,
            str(mapping.temperature),
            (str(mapping.max_tokens) if mapping.max_tokens is not None else "∞"),
            str(mapping.enabled),
        )
    console.print(table)


@model_cli.command("set")
def models_set(
    role: str = typer.Option(..., "--role", help="planner, executor, evaluator, critic, or orchestrator."),
    provider: str = typer.Option(..., "--provider", help="Provider name."),
    model: str = typer.Option(..., "--model", help="Model name."),
    temperature: float = typer.Option(0.7, "--temperature", help="Sampling temperature."),
    max_tokens: Optional[int] = typer.Option(None, "--max-tokens", help="Max output tokens. Leave unset for unlimited."),
) -> None:
    """Set model mapping for an agent role."""
    agent_role = AgentRole(role)
    registry = ModelRegistry()
    registry.set(agent_role, RoleModelMapping(agent_role, provider, model, temperature, max_tokens, True))
    console.print(f"[green]Set {role} to {provider}/{model}.[/green]")


@model_cli.command("presets")
def models_presets() -> None:
    """List built-in and custom model presets."""
    table = Table(title="Model Presets", box=box.SIMPLE)
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Mappings")
    for preset in ModelPresets().list_presets():
        mappings = ", ".join(f"{role}={model}" for role, model in preset.mappings.items())
        table.add_row(preset.name, preset.description, mappings)
    console.print(table)


@model_cli.command("preset")
def models_preset(name: str = typer.Argument(..., help="Preset name to apply.")) -> None:
    """Apply a model preset to the registry."""
    registry = ModelRegistry()
    ModelPresets().apply_preset(name, registry)
    console.print(f"[green]Applied model preset {name}.[/green]")


@model_cli.command("use")
def models_use(
    provider: str = typer.Argument(..., help="Runtime provider for chat/run."),
    model: str = typer.Argument(..., help="Runtime model for chat/run."),
) -> None:
    """Persist default runtime model used by new CLI shells."""
    config = _load_json_config(CLI_CONFIG, {})
    config["provider"] = provider
    config["model"] = model
    _save_json_config(CLI_CONFIG, config)
    console.print(f"[green]Saved runtime default {provider}/{model}.[/green]")


@permission_cli.command("show")
def permissions_show() -> None:
    """Show active permission profile."""
    profile = _current_permission_profile()
    data = PERMISSION_PROFILES.get(profile, PERMISSION_PROFILES["auto"])
    console.print_json(json.dumps({"profile": profile, **data}, indent=2))


@permission_cli.command("set")
def permissions_set(profile: str = typer.Argument(..., help="auto, ask, or locked.")) -> None:
    """Persist active permission profile."""
    _set_permission_profile(profile)
    console.print(f"[green]Permission profile set to {profile}.[/green]")


@permission_cli.command("profiles")
def permissions_profiles() -> None:
    """List available permission profiles."""
    table = Table(title="Permission Profiles", box=box.SIMPLE)
    table.add_column("Profile", style="cyan")
    table.add_column("Approval")
    table.add_column("Shell Commands")
    for name, data in PERMISSION_PROFILES.items():
        table.add_row(name, data["approval"], ", ".join(data["shell_commands"]))
    console.print(table)


@mcp_cli.command("list")
def mcp_list() -> None:
    """List detected MCP configs and server names."""
    _render_mcp_status()


# Cost tracking CLI subcommand
cost_cli = typer.Typer(help="Cost tracking and budget management")
cli.add_typer(cost_cli, name="cost")


@cost_cli.command("status")
def cost_status(
    session: str = typer.Option(None, "--session", help="Session ID to query."),
    thread: str = typer.Option(None, "--thread", help="Thread ID to query."),
) -> None:
    """Show cost and token usage status."""
    from luminamind.cost import get_cost_tracker

    tracker = get_cost_tracker()
    if session:
        summary = tracker.session_summary(session)
        console.print(Panel.fit(f"[bold cyan]Session {session}[/bold cyan]", border_style="cyan"))
    elif thread:
        summary = tracker.thread_summary(thread)
        console.print(Panel.fit(f"[bold cyan]Thread {thread}[/bold cyan]", border_style="cyan"))
    else:
        summary = tracker.global_summary()
        console.print(Panel.fit("[bold cyan]Global Cost Summary[/bold cyan]", border_style="cyan"))

    table = Table(box=box.SIMPLE)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    table.add_row("Input Tokens", str(summary.get("input_tokens", 0)))
    table.add_row("Output Tokens", str(summary.get("output_tokens", 0)))
    table.add_row("Total Tokens", str(summary.get("total_tokens", 0)))
    table.add_row("Cost USD", f"${summary.get('cost_usd', 0.0):.4f}")
    table.add_row("API Calls", str(summary.get("calls", 0)))
    console.print(table)


@cost_cli.command("top-models")
def cost_top_models(limit: int = typer.Option(10, "--limit")) -> None:
    """Show top models by cost."""
    from luminamind.cost import get_cost_tracker

    tracker = get_cost_tracker()
    results = tracker.top_models(limit)
    table = Table(title="Top Models by Cost", box=box.SIMPLE)
    table.add_column("Model", style="cyan")
    table.add_column("Cost USD", justify="right")
    table.add_column("Tokens", justify="right")
    table.add_column("Calls", justify="right")
    for row in results:
        table.add_row(
            row.get("model", "?"),
            f"${row.get('total_cost', 0):.4f}",
            str(row.get("total_tokens", 0)),
            str(row.get("calls", 0)),
        )
    console.print(table)


@cost_cli.command("budget")
def cost_budget(
    add: str = typer.Option(None, "--add", help="Add a budget policy (JSON)."),
    remove: str = typer.Option(None, "--remove", help="Remove a budget policy by name."),
) -> None:
    """Manage budget policies."""
    from luminamind.cost import get_budget_enforcer, BudgetPolicy, BudgetPolicyType

    enforcer = get_budget_enforcer()
    if add:
        import json

        data = json.loads(add)
        policy = BudgetPolicy(
            name=data["name"],
            policy_type=BudgetPolicyType(data["policy_type"]),
            limit_usd=data["limit_usd"],
            window_hours=data.get("window_hours"),
            scope=data.get("scope", "global"),
            scope_id=data.get("scope_id"),
            warning_threshold=data.get("warning_threshold", 0.8),
        )
        enforcer.add_policy(policy)
        console.print(f"[green]Added budget policy: {policy.name}[/green]")
        return
    if remove:
        if enforcer.remove_policy(remove):
            console.print(f"[green]Removed budget policy: {remove}[/green]")
        else:
            console.print(f"[red]Policy not found: {remove}[/red]")
        return

    policies = enforcer.list_policies()
    if not policies:
        console.print("[dim]No budget policies configured.[/dim]")
        return
    table = Table(title="Budget Policies", box=box.SIMPLE)
    table.add_column("Name", style="cyan")
    table.add_column("Type")
    table.add_column("Limit USD", justify="right")
    table.add_column("Scope")
    console.print(table)
    for p in policies:
        table.add_row(p.name, p.policy_type.value, f"${p.limit_usd:.2f}", f"{p.scope}:{p.scope_id or '-'}")
    console.print(table)


# Memory CLI subcommand
memory_cli = typer.Typer(help="Vector memory and semantic search")
cli.add_typer(memory_cli, name="memory")


@memory_cli.command("search")
def memory_search(
    query: str = typer.Argument(..., help="Search query."),
    k: int = typer.Option(5, "--k", help="Number of results."),
) -> None:
    """Search agent memory for past sessions."""
    import asyncio
    from luminamind.memory import get_memory_manager

    mgr = get_memory_manager()
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                results = pool.submit(asyncio.run, mgr.search_sessions(query, k=k)).result()
        else:
            results = loop.run_until_complete(mgr.search_sessions(query, k=k))
    except RuntimeError:
        results = asyncio.run(mgr.search_sessions(query, k=k))

    if not results:
        console.print("[dim]No memories found.[/dim]")
        return
    table = Table(title=f"Memory Search: {query}", box=box.SIMPLE)
    table.add_column("Score", justify="right")
    table.add_column("Type")
    table.add_column("Text", style="cyan")
    table.add_column("Thread")
    for r in results:
        table.add_row(
            f"{r.get('score', 0):.3f}",
            r.get("memory_type", "?"),
            str(r.get("text", ""))[:80],
            r.get("thread_id", "?") or "-",
        )
    console.print(table)


@memory_cli.command("stats")
def memory_stats() -> None:
    """Show memory store statistics."""
    from luminamind.memory import get_memory_manager

    mgr = get_memory_manager()
    stats = mgr.stats()
    table = Table(title="Memory Statistics", box=box.SIMPLE)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    table.add_row("Total Memories", str(stats.get("total_memories", 0)))
    table.add_row("Dimension", str(stats.get("dim", 0)))
    for mt, count in stats.get("by_type", {}).items():
        table.add_row(f"  {mt}", str(count))
    console.print(table)


# A2A CLI subcommand
a2a_cli = typer.Typer(help="Agent-to-Agent protocol commands")
cli.add_typer(a2a_cli, name="a2a")


@a2a_cli.command("discover")
def a2a_discover(url: str = typer.Argument(..., help="Base URL of the remote agent.")) -> None:
    """Discover an A2A agent at a given URL."""
    import asyncio
    from luminamind.a2a import AgentDiscovery

    async def _discover() -> None:
        discovery = AgentDiscovery()
        card = await discovery.discover(url)
        if card is None:
            console.print(f"[red]No agent found at {url}[/red]")
            return
        console.print(Panel.fit(f"[bold cyan]{card.name}[/bold cyan]", border_style="cyan"))
        console.print(f"Description: {card.description}")
        console.print(f"Version: {card.version}")
        console.print(f"URL: {card.url}")
        console.print(f"Capabilities: {card.capabilities}")
        if card.skills:
            table = Table(title="Skills", box=box.SIMPLE)
            table.add_column("ID", style="cyan")
            table.add_column("Name")
            table.add_column("Description")
            for s in card.skills:
                table.add_row(s.id, s.name, s.description)
            console.print(table)

    asyncio.run(_discover())


@cli.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    LuminaMind: Deep Agent CLI & Dev Server Launcher.
    """
    # Always load global + project env early
    load_project_env()

    if ctx.invoked_subcommand is None:
        # First-launch setup wizard
        if not _is_configured():
            run_setup_wizard_sync()
            # Re-load after wizard writes config
            load_project_env()

        piped = _read_piped_stdin()
        if piped:
            _apply_permission_profile(_current_permission_profile())
            _apply_runtime_overrides(None, None)
            app = _load_cli_app(interactive=False)
            asyncio.run(
                _run_noninteractive(
                    piped,
                    app,
                    thread_id=str(uuid7()),
                    output_format="text",
                    stream_modes=DEFAULT_STREAM_MODES,
                    subgraphs=True,
                    no_stream=False,
                    max_turns=None,
                    quiet=False,
                )
            )
            return
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
            chat(
                thread=None,
                provider=None,
                model=None,
                approval="auto",
                stream_modes=",".join(DEFAULT_STREAM_MODES),
                subgraphs=True,
                max_turns=None,
            )
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


@cli.command("run", context_settings={"allow_extra_args": True, "ignore_unknown_options": False})
def run_command(
    ctx: typer.Context,
    message: list[str] = typer.Argument(None, help="Prompt/message to run non-interactively."),
    thread: Optional[str] = typer.Option(None, "--thread", "-t", help="Thread ID to resume."),
    output_format: str = typer.Option("text", "--format", "-f", help="Output format: text, json, stream-json."),
    stream_modes: str = typer.Option(
        ",".join(DEFAULT_STREAM_MODES),
        "--stream-modes",
        help="Comma-separated LangGraph stream modes.",
    ),
    no_stream: bool = typer.Option(False, "--no-stream", help="Buffer the final result instead of streaming."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress progress events in text mode."),
    max_turns: Optional[int] = typer.Option(None, "--max-turns", help="Maximum graph recursion/turn budget."),
    subgraphs: bool = typer.Option(True, "--subgraphs/--no-subgraphs", help="Include subagent/subgraph stream events."),
    provider: Optional[str] = typer.Option(None, "--provider", help="Model provider override, e.g. ollama or openai."),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model override for this run."),
    approval: str = typer.Option("auto", "--approval", help="Tool approval mode: auto or ask."),
    role_model: Optional[list[str]] = typer.Option(None, "--role-model", help="Override model for a role. Format: role=model (e.g., executor=glm-4.7-flash). Can be used multiple times."),
) -> None:
    """Run a single task without launching the interactive UI."""
    if output_format not in {"text", "json", "stream-json"}:
        raise typer.BadParameter("format must be one of: text, json, stream-json")
    if max_turns is not None and max_turns <= 0:
        raise typer.BadParameter("--max-turns must be positive")

    piped = _read_piped_stdin()
    prompt_parts = []
    if piped:
        prompt_parts.append(piped)
    if message:
        prompt_parts.append(" ".join(message))
    if ctx.args:
        prompt_parts.append(" ".join(ctx.args))
    prompt = "\n\n".join(part for part in prompt_parts if part.strip()).strip()
    if not prompt:
        raise typer.BadParameter("message or piped stdin is required")

    _apply_permission_profile(_current_permission_profile())
    _apply_runtime_overrides(provider, model, approval, role_model)
    modes = _parse_stream_modes(stream_modes)
    app = _load_cli_app(interactive=False)
    asyncio.run(
        _run_noninteractive(
            prompt,
            app,
            thread_id=thread or str(uuid7()),
            output_format=output_format,
            stream_modes=modes,
            subgraphs=subgraphs,
            no_stream=no_stream,
            max_turns=max_turns,
            quiet=quiet,
        )
    )


@cli.command()
def config(
    wizard: bool = typer.Option(True, "--wizard/--manual", help="Use interactive provider wizard (default) or legacy manual env config."),
) -> None:
    """
    Configure global environment variables. Defaults to interactive provider wizard.
    """
    if wizard:
        run_setup_wizard_sync(force=True)
        # Re-load after wizard writes config
        load_project_env()
    else:
        configure_global_env(force=True)


# ── Provider Management Commands ──

@providers_cli.command("list")
def providers_list() -> None:
    """List all configured providers and show which is active."""
    from rich.table import Table

    configs = read_provider_configs()
    active = get_active_provider()

    table = Table(title="Configured LLM Providers", box=box.ROUNDED)
    table.add_column("Status", style="bold", width=8)
    table.add_column("Provider", style="cyan")
    table.add_column("Model", style="green")
    table.add_column("API Base", style="dim")
    table.add_column("Key", style="dim")

    for pid, schema in PROVIDER_SCHEMA.items():
        cfg = configs.get(pid)
        is_active = pid == active
        status = "[bold green]●[/bold green] active" if is_active else ("[dim]○[/dim] ready" if cfg else "[dim]—[/dim]")
        model = cfg.get("model", "—") if cfg else "—"
        base = cfg.get("api_base", "—") if cfg else "—"
        key_hint = cfg.get("api_key", "")[:4] + "***" if cfg and cfg.get("api_key") else "—"
        table.add_row(status, schema["display_name"], model, base, key_hint)

    console.print(table)
    console.print(f"\n[dim]Active provider: [bold]{PROVIDER_SCHEMA.get(active, {}).get('display_name', active or 'none')}[/bold][/dim]")
    console.print("[dim]Use [bold]luminamind providers add[/bold] to configure a new provider.[/dim]")
    console.print("[dim]Use [bold]luminamind providers set <name>[/bold] to switch active provider.[/dim]")


@providers_cli.command("add")
def providers_add(
    provider: str = typer.Argument(..., help="Provider to add: z.ai, kimi, minimax, openai, ollama"),
    api_key: str = typer.Option(None, "--api-key", "-k", help="API key (will prompt if not given)"),
    api_base: str = typer.Option(None, "--api-base", "-b", help="API base URL (optional)"),
    model: str = typer.Option(None, "--model", "-m", help="Model name (optional)"),
    set_active: bool = typer.Option(True, "--active/--no-active", help="Set as active provider after adding"),
) -> None:
    """Add or update a provider configuration."""
    import questionary

    pid = provider.lower().strip()
    if pid not in PROVIDER_SCHEMA:
        console.print(f"[red]Unknown provider: {pid}[/red]")
        console.print(f"Known providers: {', '.join(PROVIDER_SCHEMA.keys())}")
        raise typer.Exit(1)

    schema = PROVIDER_SCHEMA[pid]
    display = schema["display_name"]

    console.print(Panel(f"Adding provider: [bold cyan]{display}[/bold cyan]", border_style="cyan"))

    # Prompt for API key if not provided
    if api_key is None:
        if pid == "ollama":
            api_key = ""
        else:
            api_key = questionary.password(
                f"Enter your {display} API key:"
            ).ask()
            if not api_key:
                console.print("[yellow]No API key provided. Skipping.[/yellow]")
                raise typer.Exit(0)

    # Prompt for model if not provided
    if model is None:
        default_model = schema["default_model"]
        model = questionary.text(
            f"Model name:", default=default_model
        ).ask() or default_model

    # Write config
    write_provider_config(
        provider_id=pid,
        api_key=api_key,
        api_base=api_base or schema["default_base"],
        model=model,
        set_active=set_active,
    )

    action = "activated" if set_active else "added"
    console.print(f"[green]✓ {display} {action}.[/green]")
    if set_active:
        console.print(f"[dim]It is now the active provider for new sessions.[/dim]")
    console.print(f"[dim]Model: {model}[/dim]")


@providers_cli.command("set")
def providers_set(
    provider: str = typer.Argument(..., help="Provider to activate: z.ai, kimi, minimax, openai, ollama"),
) -> None:
    """Switch the active provider without changing any config."""
    pid = provider.lower().strip()
    if set_active_provider(pid):
        schema = PROVIDER_SCHEMA.get(pid, {})
        console.print(f"[green]✓ Active provider set to: {schema.get('display_name', pid)}[/green]")
        # Show the model that will be used
        configs = read_provider_configs()
        if pid in configs:
            console.print(f"[dim]Model: {configs[pid].get('model', schema.get('default_model', 'unknown'))}[/dim]")
    else:
        console.print(f"[red]✗ Provider '{provider}' is not configured.[/red]")
        console.print("[dim]Run [bold]luminamind providers add {provider}[/bold] to configure it first.[/dim]")
        raise typer.Exit(1)


@providers_cli.command("remove")
def providers_remove(
    provider: str = typer.Argument(..., help="Provider to remove: z.ai, kimi, minimax, openai, ollama"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Remove a provider's configuration from the global config."""
    pid = provider.lower().strip()
    configs = read_provider_configs()

    if pid not in configs:
        console.print(f"[yellow]Provider '{provider}' is not configured.[/yellow]")
        raise typer.Exit(0)

    if not confirm:
        if not questionary.confirm(
            f"Remove {PROVIDER_SCHEMA[pid]['display_name']} configuration?"
        ).ask():
            console.print("[dim]Cancelled.[/dim]")
            return

    if remove_provider(pid):
        console.print(f"[green]✓ Removed {PROVIDER_SCHEMA[pid]['display_name']} configuration.[/green]")
        # Show new active provider if any
        active = get_active_provider()
        if active:
            console.print(f"[dim]Active provider is now: {PROVIDER_SCHEMA[active]['display_name']}[/dim]")
        else:
            console.print("[yellow]No providers remain configured. Run [bold]luminamind config[/bold] to set one up.[/yellow]")
    else:
        console.print(f"[red]Failed to remove {provider}.[/red]")


@cli.command()
def chat(
    thread: Optional[str] = typer.Option(None, help="Existing thread ID to resume."),
    provider: Optional[str] = typer.Option(None, "--provider", help="Model provider override."),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model override for this session."),
    approval: str = typer.Option("auto", "--approval", help="Tool approval mode: auto or ask."),
    role_model: Optional[list[str]] = typer.Option(None, "--role-model", help="Override model for a role. Format: role=model (e.g., planner=kimi-k2.6). Can be used multiple times."),
    stream_modes: str = typer.Option(
        ",".join(DEFAULT_STREAM_MODES),
        "--stream-modes",
        help="Comma-separated LangGraph stream modes.",
    ),
    subgraphs: bool = typer.Option(True, "--subgraphs/--no-subgraphs", help="Show subagent/subgraph stream events."),
    max_turns: Optional[int] = typer.Option(None, "--max-turns", help="Maximum graph recursion/turn budget per prompt."),
) -> None:
    """
    Start a conversational CLI with the deep agent.
    """
    _apply_permission_profile(_current_permission_profile())
    _apply_runtime_overrides(provider, model, approval, role_model)
    modes = _parse_stream_modes(stream_modes)

    current_thread = thread or str(uuid7())
    if thread:
        _session_store().resume(current_thread)
    typer.echo("Deep Agent CLI")
    typer.echo("Type your question. Press Enter to submit, Esc+Enter for newline. Commands: /help, /exit")

    app = _load_cli_app(interactive=True)

    session = PromptSession(history=InMemoryHistory())
    style = _prompt_style()

    kb = KeyBindings()
    last_interrupt_time = 0.0
    session_approved_tools = set()
    transcript: list[dict[str, Any]] = _load_transcript(current_thread) if thread else []
    last_usage: dict[str, Any] = {}
    undo_stack: list[UndoRecord] = []
    redo_stack: list[UndoRecord] = []

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

        stripped = user_input.strip()
        lowered = stripped.lower()
        if lowered in {"/exit", "/quit"}:
            typer.echo("Goodbye!")
            break
        if lowered in {"/reset", "/new", "/clear"}:
            current_thread = str(uuid7())
            session_approved_tools.clear()
            transcript.clear()
            last_usage = {}
            typer.echo("Started a new conversation.")
            continue
        if lowered == "/config":
            configure_global_env(force=True)
            continue
        if lowered == "/help":
            _render_cli_help()
            continue
        if lowered == "/thread":
            typer.echo(current_thread)
            continue
        if lowered == "/sessions":
            sessions = _session_store().list()
            table = Table(title="Saved Sessions", box=box.SIMPLE)
            table.add_column("Thread", style="cyan")
            table.add_column("Messages", justify="right")
            table.add_column("Last Accessed")
            table.add_column("Summary")
            for item in sessions[:30]:
                table.add_row(
                    item.get("thread_id", ""),
                    str(item.get("message_count", 0)),
                    item.get("last_accessed", ""),
                    _stringify(item.get("summary", ""), 80),
                )
            console.print(table)
            continue
        if lowered.startswith("/resume "):
            target = stripped.split(maxsplit=1)[1].strip()
            if not target:
                console.print("[red]Usage: /resume <thread-id>[/red]")
                continue
            current_thread = target
            _session_store().resume(current_thread)
            transcript = _load_transcript(current_thread)
            session_approved_tools.clear()
            typer.echo(f"Resumed session {current_thread} ({len(transcript)} messages).")
            continue
        if lowered.startswith("/search "):
            query = stripped.split(maxsplit=1)[1].strip().lower()
            matches = [item for item in _load_transcript(current_thread) if query in str(item.get("content", "")).lower()]
            table = Table(title=f"Search: {query}", box=box.SIMPLE)
            table.add_column("Role", style="cyan")
            table.add_column("Content")
            for item in matches[:20]:
                table.add_row(str(item.get("role", "")), _stringify(item.get("content", ""), 220))
            console.print(table)
            continue
        if lowered.startswith("/fork"):
            parts = stripped.split(maxsplit=1)
            new_thread = parts[1].strip() if len(parts) > 1 else str(uuid7())
            for item in _load_transcript(current_thread):
                _append_session_message(new_thread, str(item.get("role", "message")), str(item.get("content", "")), forked_from=current_thread)
            current_thread = new_thread
            transcript = _load_transcript(current_thread)
            session_approved_tools.clear()
            typer.echo(f"Forked into session {current_thread}.")
            continue
        # ── Model & Provider Slash Commands ──
        if lowered == "/model" or lowered.startswith("/model "):
            parts = stripped.split(maxsplit=1)
            if len(parts) == 1:
                # Show current model + available models table
                active = get_active_provider()
                current_model = os.environ.get("LUMINAMIND_MODEL") or os.environ.get("GLM_MODEL") or os.environ.get("OLLAMA_MODEL") or "default"
                configs = read_provider_configs()
                table = Table(title=f"Current: {PROVIDER_SCHEMA.get(active, {}).get('display_name', active)} / {current_model}", box=box.SIMPLE)
                table.add_column("Provider", style="cyan")
                table.add_column("Model", style="green")
                table.add_column("API Base", style="dim")
                table.add_column("Status")
                for pid, schema in PROVIDER_SCHEMA.items():
                    cfg = configs.get(pid)
                    is_active = pid == active
                    status = "[bold green]● active[/bold green]" if is_active else ("[dim]○ ready[/dim]" if cfg else "[dim]—[/dim]")
                    model = cfg.get("model", schema["default_model"]) if cfg else schema["default_model"]
                    table.add_row(schema["display_name"], model, schema["default_base"], status)
                console.print(table)
                console.print("[dim]Usage: /model provider/model  (e.g., /model kimi/kimi-k2.6)[/dim]")
                continue
            value = parts[1].strip()
            if "/" in value:
                provider_value, model_value = value.split("/", 1)
            else:
                provider_value, model_value = os.environ.get("LLM_PROVIDER", "openai"), value
            _apply_runtime_overrides(provider_value, model_value, None)
            app = _load_cli_app(interactive=True)
            console.print(f"[green]✓[/green] Model set to [bold]{provider_value}/{model_value}[/bold]")
            continue

        if lowered == "/provider" or lowered.startswith("/provider "):
            parts = stripped.split(maxsplit=1)
            active = get_active_provider()
            if len(parts) == 1:
                # Show current + configured providers
                configs = read_provider_configs()
                table = Table(title="Configured Providers", box=box.SIMPLE)
                table.add_column("Status", style="bold", width=8)
                table.add_column("Provider", style="cyan")
                table.add_column("Model", style="green")
                for pid, schema in PROVIDER_SCHEMA.items():
                    cfg = configs.get(pid)
                    is_active = pid == active
                    status = "[bold green]●[/bold green] active" if is_active else ("[dim]○[/dim] ready" if cfg else "[dim]—[/dim]")
                    model = cfg.get("model", "—") if cfg else "—"
                    table.add_row(status, schema["display_name"], model)
                console.print(table)
                console.print(f"[dim]Active: {PROVIDER_SCHEMA.get(active, {}).get('display_name', active or 'none')}[/dim]")
                console.print("[dim]Usage: /provider <name>  (e.g., /provider z.ai)[/dim]")
                continue
            target = parts[1].strip().lower()
            if set_active_provider(target):
                schema = PROVIDER_SCHEMA.get(target, {})
                console.print(f"[green]✓[/green] Active provider set to [bold]{schema.get('display_name', target)}[/bold]")
                app = _load_cli_app(interactive=True)
            else:
                console.print(f"[red]✗ Provider '{target}' is not configured.[/red]")
                console.print("[dim]Run /providers or `luminamind providers add {target}` to configure it.[/dim]")
            continue

        if lowered == "/models":
            # Show per-role model assignments from registry
            registry = ModelRegistry()
            table = Table(title="Per-Role Model Assignments", box=box.SIMPLE)
            table.add_column("Role", style="cyan")
            table.add_column("Provider")
            table.add_column("Model", style="green")
            table.add_column("Temp")
            table.add_column("Max Tokens")
            for role in AgentRole:
                mapping = registry.get(role)
                if mapping and mapping.enabled:
                    table.add_row(
                        role.value,
                        mapping.provider,
                        mapping.model,
                        str(mapping.temperature),
                        (str(mapping.max_tokens) if mapping.max_tokens is not None else "∞"),
                    )
                else:
                    default = registry.get_default_for_role(role)
                    table.add_row(
                        role.value,
                        f"[dim]{default.provider}[/dim]",
                        f"[dim]{default.model}[/dim]",
                        str(default.temperature),
                        (str(default.max_tokens) if default.max_tokens is not None else "∞"),
                    )
            console.print(table)
            console.print("[dim]Use /role-model <role=model> to change a role's model.[/dim]")
            continue

        if lowered == "/role-model" or lowered.startswith("/role-model "):
            parts = stripped.split(maxsplit=1)
            if len(parts) == 1:
                # Show current role→model mappings (same as /models)
                registry = ModelRegistry()
                table = Table(title="Role → Model Mappings", box=box.SIMPLE)
                table.add_column("Role", style="cyan")
                table.add_column("Provider")
                table.add_column("Model", style="green")
                table.add_column("Temp")
                table.add_column("Max Tokens")
                for role in AgentRole:
                    mapping = registry.get(role)
                    if mapping and mapping.enabled:
                        table.add_row(role.value, mapping.provider, mapping.model, str(mapping.temperature), (str(mapping.max_tokens) if mapping.max_tokens is not None else "∞"))
                    else:
                        default = registry.get_default_for_role(role)
                        table.add_row(role.value, f"[dim]{default.provider}[/dim]", f"[dim]{default.model}[/dim]", str(default.temperature), (str(default.max_tokens) if default.max_tokens is not None else "∞"))
                console.print(table)
                console.print("[dim]Usage: /role-model planner=kimi-k2.6[/dim]")
                console.print("[dim]Usage: /role-model planner=kimi-k2.6 executor=glm-4.7-flash[/dim]")
                continue
            # Parse role=model pairs
            registry = ModelRegistry()
            changed = []
            for pair in parts[1].strip().split():
                if "=" not in pair:
                    console.print(f"[red]Invalid format: {pair} (expected role=model)[/red]")
                    continue
                role_str, model_val = pair.split("=", 1)
                role_str = role_str.strip().lower()
                model_val = model_val.strip()
                try:
                    role = AgentRole(role_str)
                except ValueError:
                    console.print(f"[red]Unknown role: {role_str}. Known: {[r.value for r in AgentRole]}[/red]")
                    continue
                # Detect provider from model name or use active provider
                provider_guess = os.environ.get("LUMINAMIND_ACTIVE_PROVIDER", "openai")
                # Simple heuristic: if model name contains known prefixes
                if "kimi" in model_val.lower():
                    provider_guess = "moonshot"
                elif "glm" in model_val.lower():
                    provider_guess = "zhipu"
                elif "minimax" in model_val.lower():
                    provider_guess = "minimax"
                elif "gpt" in model_val.lower() or "o1" in model_val.lower() or "o3" in model_val.lower():
                    provider_guess = "openai"
                elif "claude" in model_val.lower():
                    provider_guess = "anthropic"
                registry.set(role, RoleModelMapping(role, provider_guess, model_val))
                changed.append(f"{role.value}={model_val}")
            if changed:
                console.print(f"[green]✓[/green] Updated: {', '.join(changed)}")
                app = _load_cli_app(interactive=True)
            continue

        if lowered == "/preset" or lowered.startswith("/preset "):
            parts = stripped.split(maxsplit=1)
            presets = ModelPresets()
            if len(parts) == 1:
                # List available presets
                table = Table(title="Model Presets", box=box.SIMPLE)
                table.add_column("Name", style="cyan")
                table.add_column("Description")
                table.add_column("Mappings")
                for preset in presets.list_presets():
                    mappings = ", ".join(f"{role}={model}" for role, model in preset.mappings.items())
                    table.add_row(preset.name, preset.description, mappings)
                console.print(table)
                console.print("[dim]Usage: /preset <name>  (e.g., /preset fast)[/dim]")
                continue
            name = parts[1].strip()
            try:
                registry = ModelRegistry()
                presets.apply_preset(name, registry)
                console.print(f"[green]✓[/green] Applied preset: [bold]{name}[/bold]")
                # Show what changed
                table = Table(title=f"Preset '{name}' Role Mappings", box=box.SIMPLE)
                table.add_column("Role", style="cyan")
                table.add_column("Model")
                for role in AgentRole:
                    mapping = registry.get(role)
                    if mapping and mapping.enabled:
                        table.add_row(role.value, f"{mapping.provider}/{mapping.model}")
                console.print(table)
                app = _load_cli_app(interactive=True)
            except ValueError as exc:
                console.print(f"[red]✗ {exc}[/red]")
            continue

        if lowered.startswith("/permissions"):
            parts = stripped.split(maxsplit=1)
            if len(parts) == 1:
                typer.echo(_current_permission_profile())
                continue
            profile = parts[1].strip()
            _set_permission_profile(profile)
            app = _load_cli_app(interactive=True)
            typer.echo(f"Permission profile set to {profile}.")
            continue
        if lowered == "/mcp":
            _render_mcp_status()
            continue
        if lowered == "/tokens":
            if last_usage:
                _render_usage(last_usage)
            else:
                console.print("[dim]No token usage metadata has been received in this session.[/dim]")
            continue
        if lowered == "/undo":
            if not undo_stack:
                console.print("[dim]Nothing to undo.[/dim]")
                continue
            record = undo_stack[-1]
            ok, message = _restore_diff_state(record.after, record.before)
            if ok:
                redo_stack.append(undo_stack.pop())
                console.print(f"[green]Undid:[/] {record.summary}")
            else:
                console.print(f"[red]Undo refused:[/] {message}")
            continue
        if lowered == "/redo":
            if not redo_stack:
                console.print("[dim]Nothing to redo.[/dim]")
                continue
            record = redo_stack[-1]
            ok, message = _restore_diff_state(record.before, record.after)
            if ok:
                undo_stack.append(redo_stack.pop())
                console.print(f"[green]Redid:[/] {record.summary}")
            else:
                console.print(f"[red]Redo refused:[/] {message}")
            continue
        if lowered.startswith("/theme"):
            parts = stripped.split(maxsplit=1)
            if len(parts) == 1:
                typer.echo(_load_json_config(CLI_CONFIG, {"theme": "cyan"}).get("theme", "cyan"))
                continue
            _set_cli_theme(parts[1].strip())
            style = _prompt_style()
            typer.echo(f"Theme set to {parts[1].strip()}.")
            continue
        if lowered == "/status":
            table = Table(title="Session Status", box=box.SIMPLE)
            table.add_column("Key", style="cyan")
            table.add_column("Value")
            table.add_row("thread", current_thread)
            active_prov = get_active_provider()
            table.add_row("active provider", PROVIDER_SCHEMA.get(active_prov, {}).get("display_name", active_prov or "unknown"))
            table.add_row("model", os.environ.get("LUMINAMIND_MODEL") or os.environ.get("GLM_MODEL") or os.environ.get("OLLAMA_MODEL") or "default")
            # Per-role models
            registry = ModelRegistry()
            for role in AgentRole:
                mapping = registry.get(role)
                if mapping and mapping.enabled:
                    max_tok = mapping.max_tokens
                    max_tok_str = f", max={max_tok}" if max_tok is not None else ", max=∞"
                    table.add_row(f"  role:{role.value}", f"{mapping.provider}/{mapping.model} (temp={mapping.temperature}{max_tok_str})")
                else:
                    default = registry.get_default_for_role(role)
                    max_tok = default.max_tokens
                    max_tok_str = f", max={max_tok}" if max_tok is not None else ", max=∞"
                    table.add_row(f"  role:{role.value}", f"[dim]{default.provider}/{default.model} (default, temp={default.temperature}{max_tok_str})[/dim]")
            table.add_row("approved tools", ", ".join(sorted(session_approved_tools)) or "none")
            table.add_row("stream modes", ", ".join(modes))
            table.add_row("subgraphs", str(subgraphs))
            table.add_row("permission profile", _current_permission_profile())
            table.add_row("messages", str(len(transcript)))
            table.add_row("token total", str(last_usage.get("total_tokens", "unknown")))
            table.add_row("mcp configs", str(len(_detect_mcp_configs())))
            console.print(table)
            continue
        if lowered.startswith("/export"):
            parts = stripped.split(maxsplit=1)
            export_path = Path(parts[1]).expanduser() if len(parts) > 1 else Path(f"luminamind-{current_thread}.md")
            _write_transcript_markdown(current_thread, transcript, export_path)
            console.print(f"[green]Exported transcript to {export_path}[/green]")
            continue
        if stripped.startswith("!"):
            from luminamind.py_tools.shell import shell
            result = shell.invoke({"command": stripped[1:].strip()})
            if result.get("error"):
                console.print(f"[red]shell error:[/] {_stringify(result, 1000)}")
            else:
                stdout = result.get("stdout", "")
                stderr = result.get("stderr", "")
                if stdout:
                    console.print(stdout.rstrip())
                if stderr:
                    console.print(f"[yellow]{stderr.rstrip()}[/yellow]")
            shell_text = _stringify(result, 4000)
            transcript.append({"role": "shell", "content": shell_text})
            _append_session_message(current_thread, "shell", shell_text)
            continue

        console.print("[bold magenta]Agent>[/] ", end="")
        try:
            before_diff = _git_diff()
            transcript.append({"role": "user", "content": user_input})
            _append_session_message(current_thread, "user", user_input)
            result = asyncio.run(
                _stream_agent_response(
                    user_input,
                    current_thread,
                    session_approved_tools,
                    app,
                    stream_modes=modes,
                    subgraphs=subgraphs,
                    max_turns=max_turns,
                )
            )
            assistant_text = result.get("text") or ""
            last_usage = result.get("usage") or {}
            if assistant_text:
                transcript.append({"role": "agent", "content": assistant_text})
                _append_session_message(current_thread, "agent", assistant_text, usage=last_usage)
            after_diff = _git_diff()
            if before_diff is not None and after_diff is not None and before_diff != after_diff:
                undo_stack.append(UndoRecord(before=before_diff, after=after_diff, summary=_stringify(user_input, 80)))
                redo_stack.clear()
        except KeyboardInterrupt:
            console.print("\n[red]🛑 Agent interrupted by user.[/]")
        except Exception as exc:
            console.print(f"\n[red]Agent error:[/] {exc}")


demo_cli = typer.Typer(help="Run LuminaMind demo applications showcasing harness capabilities.")
cli.add_typer(demo_cli, name="demo", help="Demo commands")


@chaos_cli.callback(invoke_without_command=True)
def chaos_main(ctx: typer.Context) -> None:
    """Chaos testing for resilience validation."""
    pass


@chaos_cli.command("list")
def chaos_list() -> None:
    """List all available chaos scenarios."""
    scenarios = list_scenarios()
    console.print(Panel.fit("[bold cyan]Available Chaos Scenarios[/bold cyan]", border_style="cyan"))
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Severity")

    for scenario in scenarios:
        table.add_row(
            scenario.id,
            scenario.name,
            scenario.scenario_type.name,
            str(scenario.severity),
        )
    console.print(table)
    console.print(f"\n[dim]Total: {len(scenarios)} scenarios[/dim]")


@chaos_cli.command("run")
def chaos_run(
    scenario_id: str = typer.Option(None, help="Specific scenario ID to run (default: all)"),
    task: str = typer.Option("test resilience", help="Task description for chaos test"),
    output: Path = typer.Option(None, help="Output file for JSON results"),
) -> None:
    """Run chaos scenarios to test system resilience."""
    console.print("[bold yellow]Starting chaos testing...[/bold yellow]")

    engine = ChaosEngine()

    if scenario_id:
        # Run single scenario
        if scenario_id not in SCENARIOS:
            console.print(f"[red]Unknown scenario: {scenario_id}[/red]")
            console.print("[dim]Run 'luminamind chaos list' to see available scenarios[/dim]")
            raise typer.Exit(code=1)

        console.print(f"[cyan]Running scenario: {scenario_id}[/cyan]")
        result = engine.run_scenario(scenario_id, task)

        console.print(f"[green]Scenario complete:[/green]")
        console.print(f"  Outcome: {result.outcome}")
        console.print(f"  Graceful: {result.graceful_degradation}")
        console.print(f"  Execution time: {result.execution_time:.2f}s")

        suite_result = ChaosSuiteResult(results=[result], total_scenarios=1, passed=1 if result.outcome != "failed" else 0, failed=1 if result.outcome == "failed" else 0)

    else:
        # Run all scenarios
        console.print("[cyan]Running all chaos scenarios...[/cyan]")
        suite_result = engine.run_all_scenarios(task)

        console.print(f"\n[green]Chaos suite complete:[/green]")
        console.print(f"  Total: {suite_result.total_scenarios}")
        console.print(f"  Passed: {suite_result.passed}")
        console.print(f"  Failed: {suite_result.failed}")

    # Generate and display report
    report = generate_chaos_report(suite_result)
    console.print(Panel.fit(Markdown(report), title="Chaos Test Report", border_style="green"))

    # Save JSON if output path specified
    if output:
        save_json_report(suite_result, output)
        console.print(f"[dim]JSON report saved to: {output}[/dim]")


@chaos_cli.command("report")
def chaos_report(
    input_path: Path = typer.Argument(..., help="Path to JSON results file"),
) -> None:
    """Display a chaos test report from JSON results."""
    import json

    if not input_path.exists():
        console.print(f"[red]File not found: {input_path}[/red]")
        raise typer.Exit(code=1)

    data = json.loads(input_path.read_text())
    report = ChaosReport(
        timestamp=data.get("timestamp", ""),
        total_scenarios=data.get("total_scenarios", 0),
        passed=data.get("passed", 0),
        failed=data.get("failed", 0),
        results=[],
        summary_by_type=data.get("summary_by_type", {}),
    )

    console.print(Panel.fit(Markdown(generate_chaos_report(
        ChaosSuiteResult(results=[], total_scenarios=report.total_scenarios, passed=report.passed, failed=report.failed)
    )), title="Chaos Report", border_style="green"))


@demo_cli.command("list")
def demo_list() -> None:
    """List available demo applications."""
    table = Table(title="Available Demos")
    table.add_column("Demo", style="cyan")
    table.add_column("Description", style="dim")
    table.add_row("frontend", "Frontend design demo using evaluator")
    table.add_row("fullstack", "Full-stack application demo")
    table.add_row("codereview", "Code review demo using evaluator")
    table.add_row("all", "Run all demos sequentially")
    console.print(table)


@demo_cli.command("frontend")
def demo_frontend() -> None:
    """Run the frontend design demo."""
    from luminamind.demos.frontend_demo import run_frontend_demo

    console.print(Panel.fit(
        "[bold cyan]Frontend Design Demo[/]\n[dim]Generating and evaluating a responsive landing page[/]",
        border_style="cyan"
    ))
    result = run_frontend_demo()
    if result.get("passed"):
        console.print("[green]✓ Demo completed successfully![/green]")
    else:
        console.print("[red]✗ Demo did not pass evaluation.[/red]")


@demo_cli.command("fullstack")
def demo_fullstack() -> None:
    """Run the full-stack application demo."""
    from luminamind.demos.fullstack_demo import run_fullstack_demo

    console.print(Panel.fit(
        "[bold cyan]Full-Stack App Demo[/]\n[dim]Generating a FastAPI backend with React frontend[/]",
        border_style="cyan"
    ))
    result = run_fullstack_demo()
    if result.get("passed"):
        console.print("[green]✓ Demo completed successfully![/green]")
    else:
        console.print("[red]✗ Demo did not pass evaluation.[/red]")


@demo_cli.command("codereview")
def demo_codereview() -> None:
    """Run the code review demo."""
    from luminamind.demos.codereview_demo import run_codereview_demo

    console.print(Panel.fit(
        "[bold cyan]Code Review Demo[/]\n[dim]Detecting security vulnerabilities in sample code[/]",
        border_style="cyan"
    ))
    result = run_codereview_demo()
    if result.get("passed"):
        console.print("[green]✓ Demo completed successfully![/green]")
    else:
        console.print("[red]✗ Demo detected critical security issues.[/red]")


@demo_cli.command("all")
def demo_all() -> None:
    """Run all demo applications sequentially."""
    from luminamind.demos import run_all_demos

    console.print(Panel.fit(
        "[bold cyan]LuminaMind Harness Demo Suite[/]\n[dim]Running all demonstrations[/]",
        border_style="cyan"
    ))
    result = run_all_demos()
    if result.get("success"):
        console.print("\n[green]✓ All demos completed successfully![/green]")
    else:
        console.print("\n[red]✗ Some demos failed. Check output for details.[/red]")


# Benchmark CLI subcommand
benchmark_cli = typer.Typer(help="Benchmark harness for LuminaMind agent evaluation")
cli.add_typer(benchmark_cli, name="benchmark", invoke_without_command=True)


@benchmark_cli.command("run")
def benchmark_run(
    cases: int = typer.Option(10, help="Number of random cases to run"),
    category: str = typer.Option(None, help="Category to run (e.g., CODE_GEN)"),
    output_dir: str = typer.Option(None, help="Output directory for results"),
) -> None:
    """Run benchmark test cases."""
    from luminamind.benchmark import TestSuite, BenchmarkRunner, run_benchmark
    from luminamind.benchmark.test_suite import TaskCategory

    console.print(Panel.fit(
        f"[bold cyan]Running Benchmark[/]\n[dim]{cases} test cases[/]",
        border_style="cyan"
    ))

    try:
        suite = TestSuite()
        runner = BenchmarkRunner(max_parallel=4)

        if category:
            cat = TaskCategory[category.upper()]
            results = runner.run_category(cat)
        else:
            results = runner.run_sample(cases)

        console.print(f"\n[green]✓ Completed {results.total_cases} test cases[/green]")
        console.print(f"  Passed: {results.passed} ({results.passed / results.total_cases * 100:.1f}%)" if results.total_cases > 0 else "  Passed: 0")
        console.print(f"  Average score: {sum(r.score for r in results.scores) / len(results.scores):.2%}" if results.scores else "  Average score: N/A")

        if output_dir:
            from pathlib import Path
            runner._save_results(results, Path(output_dir))
            console.print(f"  Results saved to: {output_dir}")

    except Exception as e:
        console.print(f"[red]Benchmark failed: {e}[/red]")
        raise typer.Exit(code=1)


@benchmark_cli.command("list")
def benchmark_list() -> None:
    """List all available benchmark test cases."""
    from luminamind.benchmark import TestSuite

    suite = TestSuite()
    console.print(Panel.fit(
        f"[bold cyan]Benchmark Test Suite[/]\n[dim]{len(suite.cases)} test cases[/]",
        border_style="cyan"
    ))

    from luminamind.benchmark.test_suite import TaskCategory
    cats: dict[str, int] = {}
    for c in suite.cases:
        cat = c.category.value if isinstance(c.category, TaskCategory) else str(c.category)
        cats[cat] = cats.get(cat, 0) + 1

    table = Table(title="Test Cases by Category")
    table.add_column("Category", style="cyan")
    table.add_column("Count", style="magenta", justify="right")

    for cat, count in sorted(cats.items()):
        table.add_row(cat, str(count))

    console.print(table)


@benchmark_cli.command("baseline")
def benchmark_baseline(
    update: bool = typer.Option(False, help="Update baseline with current scores"),
) -> None:
    """Manage benchmark baseline for regression detection."""
    from luminamind.benchmark import TestSuite, BenchmarkRunner
    from luminamind.benchmark.regression import RegressionDetector

    if update:
        console.print("[yellow]Running benchmark to update baseline...[/yellow]")
        suite = TestSuite()
        runner = BenchmarkRunner(max_parallel=4)
        results = runner.run_sample(20)

        from luminamind.benchmark.scoring import Scorer
        scorer = Scorer()
        scores = scorer.score_results(results)

        detector = RegressionDetector()
        detector.update_baseline(scores)

        console.print("[green]✓ Baseline updated successfully![/green]")
    else:
        detector = RegressionDetector()
        baseline_path = detector.baseline_path
        if baseline_path.exists():
            console.print(f"[cyan]Baseline location:[/cyan] {baseline_path}")
            import json
            with open(baseline_path) as f:
                data = json.load(f)
            console.print(f"  Overall average: {data.get('overall_average', 0):.2%}")
            console.print(f"  Total tests: {data.get('total_tests', 0)}")
        else:
            console.print("[yellow]No baseline found. Run with --update to create one.[/yellow]")


@benchmark_cli.command("regress")
def benchmark_regress() -> None:
    """Check for regressions against baseline."""
    from luminamind.benchmark import TestSuite, BenchmarkRunner
    from luminamind.benchmark.regression import RegressionDetector
    from luminamind.benchmark.scoring import Scorer

    console.print("[yellow]Running benchmark for regression check...[/yellow]")

    suite = TestSuite()
    runner = BenchmarkRunner(max_parallel=4)
    results = runner.run_sample(20)

    scorer = Scorer()
    scores = scorer.score_results(results)

    detector = RegressionDetector()
    report = detector.check_regression(scores)

    if report.has_regression:
        console.print(Panel.fit(
            f"[bold red]REGRESSION DETECTED[/]\n[dim]{report.summary}[/dim]",
            border_style="red"
        ))
        for r in report.regressions:
            console.print(f"  [red]{r.severity}:[/red] {r.category} ({r.delta:+.2%})")
    else:
        console.print(Panel.fit(
            f"[bold green]NO REGRESSION[/]\n[dim]{report.summary}[/dim]",
            border_style="green"
        ))


@benchmark_cli.command("report")
def benchmark_report(
    format: str = typer.Option("markdown", help="Report format (markdown or text)"),
) -> None:
    """Generate benchmark report from last results."""
    from luminamind.benchmark import TestSuite
    from luminamind.benchmark.scoring import Scorer

    suite = TestSuite()
    runner = BenchmarkRunner(max_parallel=4)
    results = runner.run_sample(5)

    scorer = Scorer()
    scores = scorer.score_results(results)
    report = scorer.generate_report(results, scores, format=format)

    console.print(report)


if __name__ == "__main__":
    cli()
