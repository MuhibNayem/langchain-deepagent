from __future__ import annotations

from langchain_core.tools import BaseTool

from .grep import grep_search
from .multi_replace import multi_replace_in_file
from .os_info import os_info
from .patch import apply_patch
from .read_many import read_files_in_directory
from .shell import shell
from .tree import tree_view
from .weather import get_weather
from .web_markdown import fetch_as_markdown
from .web_search import web_search
from .edit import edit_file
from .replace_in_file import replace_in_file
from .web_crawl import web_crawl

PY_TOOL_REGISTRY = {
    "apply_patch": apply_patch,
    "edit_file": edit_file,
    "fetch_as_markdown": fetch_as_markdown,
    "get_weather": get_weather,
    "grep_search": grep_search,
    "multi_replace_in_file": multi_replace_in_file,
    "os_info": os_info,
    "read_files_in_directory": read_files_in_directory,
    "replace_in_file": replace_in_file,
    "shell": shell,
    "tree_view": tree_view,
    "web_crawl": web_crawl,
    "web_search": web_search,
}

# Optional: register multimodal tools if available
try:
    from luminamind.multimodal.tools import analyze_image, generate_image
    PY_TOOL_REGISTRY["analyze_image"] = analyze_image
    PY_TOOL_REGISTRY["generate_image"] = generate_image
except Exception:
    pass

# Optional: register memory tools if available
try:
    from luminamind.memory.manager import get_memory_manager
    from langchain.tools import tool

    @tool("search_memory")
    def search_memory(query: str, k: int = 5) -> list[dict]:
        """Search agent memory for past session context."""
        import asyncio
        mgr = get_memory_manager()
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, mgr.search_sessions(query, k=k))
                    return future.result()
            return loop.run_until_complete(mgr.search_sessions(query, k=k))
        except RuntimeError:
            return asyncio.run(mgr.search_sessions(query, k=k))

    @tool("save_memory")
    def save_memory(text: str, memory_type: str = "episodic") -> str:
        """Save a fact or observation to long-term memory."""
        import asyncio
        mgr = get_memory_manager()
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, mgr.add_memory(text, memory_type=memory_type))
                    return future.result()
            return loop.run_until_complete(mgr.add_memory(text, memory_type=memory_type))
        except RuntimeError:
            return asyncio.run(mgr.add_memory(text, memory_type=memory_type))

    PY_TOOL_REGISTRY["search_memory"] = search_memory
    PY_TOOL_REGISTRY["save_memory"] = save_memory
except Exception:
    pass

__all__ = ["PY_TOOL_REGISTRY", "TIERED_TOOL_REGISTRY"]


def _get_tiered_registry():
    """Lazy import to avoid circular dependency."""
    from luminamind.config.tool_tier import create_tiered_registry, DEFAULT_TIER_ASSIGNMENTS
    return create_tiered_registry(PY_TOOL_REGISTRY, DEFAULT_TIER_ASSIGNMENTS)


TIERED_TOOL_REGISTRY = _get_tiered_registry()
