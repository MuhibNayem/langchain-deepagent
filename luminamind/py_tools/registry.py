from __future__ import annotations

from langchain_core.tools import BaseTool

from .edit import edit_file
from .os_info import os_info
from .replace_in_file import replace_in_file
from .shell import shell
from .weather import get_weather
from .web_crawl import web_crawl
from .web_search import web_search

PY_TOOL_REGISTRY: dict[str, BaseTool] = {
    tool.name: tool
    for tool in [
        os_info,
        edit_file,
        shell,
        replace_in_file,
        get_weather,
        web_crawl,
        web_search,
    ]
}

__all__ = ["PY_TOOL_REGISTRY"]
