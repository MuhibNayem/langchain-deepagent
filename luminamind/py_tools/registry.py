from __future__ import annotations

from langchain_core.tools import BaseTool

from .edit import edit_file
from .grep import grep_search
from .multi_replace import multi_replace_in_file
from .os_info import os_info
from .read_many import read_files_in_directory
from .replace_in_file import replace_in_file
from .shell import shell
from .weather import get_weather
from .web_crawl import web_crawl
from .web_search import web_search

PY_TOOL_REGISTRY = {
    "edit_file": edit_file,
    "get_weather": get_weather,
    "grep_search": grep_search,
    "multi_replace_in_file": multi_replace_in_file,
    "os_info": os_info,
    "read_files_in_directory": read_files_in_directory,
    "replace_in_file": replace_in_file,
    "shell": shell,
    "web_crawl": web_crawl,
    "web_search": web_search,
}

__all__ = ["PY_TOOL_REGISTRY"]
