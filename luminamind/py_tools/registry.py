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

PY_TOOL_REGISTRY = {
    "apply_patch": apply_patch,
    "fetch_as_markdown": fetch_as_markdown,
    "get_weather": get_weather,
    "grep_search": grep_search,
    "multi_replace_in_file": multi_replace_in_file,
    "os_info": os_info,
    "read_files_in_directory": read_files_in_directory,
    "shell": shell,
    "tree_view": tree_view,
    "web_search": web_search,
}

__all__ = ["PY_TOOL_REGISTRY"]
