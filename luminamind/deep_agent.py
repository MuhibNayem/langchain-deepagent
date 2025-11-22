import os
import requests
from bs4 import BeautifulSoup
from deepagents import create_deep_agent
from pathlib import Path
from langchain.tools import tool
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_community.tools.file_management.copy import CopyFileTool
from langchain_community.tools.file_management.delete import DeleteFileTool
from langchain_community.tools.file_management.file_search import FileSearchTool
from langchain_community.tools.file_management.list_dir import ListDirectoryTool
from langchain_community.tools.file_management.move import MoveFileTool
from langchain_community.tools.file_management.read import ReadFileTool
from langchain_community.tools.file_management.write import WriteFileTool

from .config.checkpointer import create_checkpointer
from .config.env import load_project_env
from .py_tools.registry import PY_TOOL_REGISTRY

ROOT_DIR = Path(__file__).resolve().parent
load_project_env()


copy_file_tool = CopyFileTool()
delete_file_tool = DeleteFileTool()
file_search_tool = FileSearchTool()
list_directory_tool = ListDirectoryTool()
move_file_tool = MoveFileTool()
read_file_tool = ReadFileTool()
write_file_tool = WriteFileTool()


def registry_tool(name: str):
    tool_obj = PY_TOOL_REGISTRY.get(name)
    if tool_obj is None:
        raise ValueError(f"Tool '{name}' is not registered in PY_TOOL_REGISTRY.")
    return tool_obj


python_native_tools = list(PY_TOOL_REGISTRY.values())

ALL_BASE_TOOLS = [
    copy_file_tool,
    delete_file_tool,
    file_search_tool,
    list_directory_tool,
    move_file_tool,
    read_file_tool,
    write_file_tool,
] + python_native_tools


SYSTEM_PROMPT = """You are a deep autonomy agent that plans, researches, and edits codebases.

- Create a todo list before diving into execution.
- Use the filesystem tools to inspect, edit, and organize the repository.
- Prefer the shell tool for commands that combine multiple steps.
- Keep track of what each subagent is tackling so you can coordinate work.
- Always summarize changes before finishing.
- CRITICAL: Before stopping, verify that ALL items in your todo list are completed. Do not stop if there are pending tasks.
"""

WEB_RESEARCH_SUBAGENT_PROMPT = """You are a focused research specialist.
- Break the assigned question into crisp sub questions.
- Use the web_search and crawling tools to gather facts and cite the strongest sources.
- Return a structured, citation-rich answer that the main agent can use directly.
"""

CODE_EXECUTOR_SUBAGENT_PROMPT = """You are a senior software engineer with commit access.
- Inspect project files and understand the existing implementation.
- Use shell and replace_in_file to make precise, minimal updates.
- Run commands cautiously; read error output and retry with fixes.
- Summarize every change you make so the main agent can keep context.
- CRITICAL: If you have a list of files to create or modify, DO NOT STOP until you have processed ALL of them.
- CRITICAL: Do not ask for confirmation for every single file if you have a batch of work. Execute the entire batch.
"""


def build_subagents():
    research_agent = {
        "name": "web-researcher",
        "description": "Use for deep research, fact gathering, and synthesizing external knowledge.",
        "system_prompt": WEB_RESEARCH_SUBAGENT_PROMPT,
        "tools": [
            registry_tool("web_search"),
            registry_tool("fetch_as_markdown"),
            registry_tool("get_weather"),
        ],
    }
    code_executor_agent = {
        "name": "code-executor",
        "description": "Use for editing repository files, running shell commands, and applying patches.",
        "system_prompt": CODE_EXECUTOR_SUBAGENT_PROMPT,
        "tools": [
            list_directory_tool,
            registry_tool("tree_view"),
            read_file_tool,
            write_file_tool,
            copy_file_tool,
            move_file_tool,
            delete_file_tool,
            file_search_tool,
            registry_tool("multi_replace_in_file"),
            registry_tool("apply_patch"),
            registry_tool("grep_search"),
            registry_tool("read_files_in_directory"),
            registry_tool("shell"),
            registry_tool("os_info"),
        ],
    }
    general_purpose_agent = {
        "name": "general-purpose",
        "description": "Use for multi-step reasoning, planning, and dispatching work.",
        "system_prompt": SYSTEM_PROMPT,
        "tools": ALL_BASE_TOOLS,
    }
    greeting_agent = {
        "name": "greeting-responder",
        "description": "Use for crafting friendly greetings, jokes, and casual replies.",
        "system_prompt": "You are a witty greeter. Respond with short, friendly greetings, optionally including light jokes.",
        "tools": [],
    }
    return [
        greeting_agent,
        general_purpose_agent,
        research_agent,
        {
            **research_agent,
            "name": "research-analyst",
        },
        code_executor_agent,
        {
            **code_executor_agent,
            "name": "executor",
        },
    ]


    
    
def get_llm():
    provider = os.environ.get("LLM_PROVIDER", "openai").lower()
    
    if provider == "ollama":
        return ChatOllama(
            model=os.environ.get("OLLAMA_MODEL", "qwen3:latest"),
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0.7,
            streaming=True,
        )
    
    return ChatOpenAI(
        temperature=0.7,
        model="glm-4.5-flash",
        openai_api_key=os.environ.get("GLM_API_KEY"),
        openai_api_base="https://api.z.ai/api/paas/v4/",
        streaming=True,
    )

llm = get_llm()

LANGGRAPH_PLATFORM_ENV_KEYS = {
    "LANGGRAPH_API_BASE",
    "LANGGRAPH_API_KEY",
    "LANGGRAPH_PROJECT_ID",
    "LANGGRAPH_CLOUD",
    "LANGGRAPH_DEPLOYMENT",
    "LANGGRAPH_GATEWAY_URL",
    "LANGGRAPH_PLATFORM",
}


def should_use_custom_checkpointer() -> bool:
    """Determine if a custom checkpointer should be attached.

    LangGraph Cloud / `langgraph dev` handle persistence automatically, so we skip
    the custom checkpointer whenever platform-related environment variables are present.
    Users can also override via DISABLE_CUSTOM_CHECKPOINTER=1.
    """
    flag = os.environ.get("DISABLE_CUSTOM_CHECKPOINTER")
    if flag and flag.lower() in {"1", "true", "yes"}:
        return False
    return not any(os.environ.get(key) for key in LANGGRAPH_PLATFORM_ENV_KEYS)


agent_kwargs = {
    "model": llm,
    "tools": ALL_BASE_TOOLS,
    "system_prompt": SYSTEM_PROMPT,
    "subagents": build_subagents(),
    "interrupt_on": {
        "file_delete": {"allowed_decisions": ["approve", "edit", "reject"]},
        "shell": {"allowed_decisions": ["approve", "edit", "reject"]},
        "write_file": {"allowed_decisions": ["approve", "edit", "reject"]},
        "copy_file": {"allowed_decisions": ["approve", "edit", "reject"]},
        "move_file": {"allowed_decisions": ["approve", "edit", "reject"]},
        "apply_patch": {"allowed_decisions": ["approve", "edit", "reject"]},
        "multi_replace_in_file": {"allowed_decisions": ["approve", "edit", "reject"]},
        "critical_operation": {"allowed_decisions": ["approve"]},
    },
}

if should_use_custom_checkpointer():
    agent_kwargs["checkpointer"] = create_checkpointer()

app = create_deep_agent(**agent_kwargs)
