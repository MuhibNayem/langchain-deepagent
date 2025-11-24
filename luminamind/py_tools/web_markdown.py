from __future__ import annotations

import aiohttp
from bs4 import BeautifulSoup
from langchain.tools import tool


@tool("fetch_as_markdown")
async def fetch_as_markdown(url: str) -> str:
    """
    Fetch a URL and convert its content to Markdown.
    
    Args:
        url: The URL to fetch.
    """
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return f"Error fetching {url}: HTTP {response.status}"
                
                html_content = await response.text()
        
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Simple conversion strategy
        # 1. Convert headers
        for i in range(1, 7):
            for tag in soup.find_all(f"h{i}"):
                tag.string = f"{'#' * i} {tag.get_text(strip=True)}\n"
                
        # 2. Convert links
        for tag in soup.find_all("a", href=True):
            text = tag.get_text(strip=True)
            if text:
                tag.string = f"[{text}]({tag['href']})"
                
        # 3. Convert lists (simple)
        for ul in soup.find_all("ul"):
            for li in ul.find_all("li", recursive=False):
                li.string = f"- {li.get_text(strip=True)}\n"
                
        # 4. Convert code blocks
        for pre in soup.find_all("pre"):
            code = pre.get_text()
            pre.string = f"\n```\n{code}\n```\n"

        # Get text with some structure
        text = soup.get_text(separator="\n\n", strip=True)
        return text

    except Exception as e:
        return f"Error fetching {url}: {e}"
