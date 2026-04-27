"""Multi-modal tools for the agent harness.

- Image analysis (vision tool)
- Image generation (DALL-E or local)
"""
from __future__ import annotations

import os
from typing import Any, Optional

from langchain.tools import tool

from luminamind.multimodal.vision import build_vision_message, encode_image_path, is_vision_capable
from luminamind.observability.metrics import monitor_tool


@tool("analyze_image")
@monitor_tool
def analyze_image(
    image_path: str,
    prompt: str = "Describe this image in detail.",
    model: str | None = None,
) -> dict[str, Any]:
    """Analyze an image using a vision-capable model.

    Args:
        image_path: Path to the image file.
        prompt: Question or instruction about the image.
        model: Optional vision model override.
    """
    from luminamind.llm import get_llm

    llm = get_llm()
    effective_model = model or os.environ.get("LUMINAMIND_MODEL") or os.environ.get("GLM_MODEL", "")
    if not is_vision_capable(effective_model):
        return {
            "error": True,
            "message": f"Model {effective_model} does not appear to support vision. Use gpt-4o, claude-3, or gemini.",
        }

    try:
        message = build_vision_message(prompt, [image_path])
        response = llm.invoke([message])
        return {
            "error": False,
            "description": response.content,
            "model": effective_model,
            "prompt": prompt,
        }
    except Exception as exc:
        return {"error": True, "message": str(exc)}


@tool("generate_image")
@monitor_tool
def generate_image(
    prompt: str,
    size: str = "1024x1024",
    quality: str = "standard",
    output_path: str | None = None,
) -> dict[str, Any]:
    """Generate an image using DALL-E 3 (requires OpenAI API key).

    Args:
        prompt: Image description.
        size: Image size (1024x1024, 1792x1024, 1024x1792).
        quality: standard or hd.
        output_path: Optional path to save the image.
    """
    try:
        from openai import OpenAI
    except ImportError as exc:
        return {"error": True, "message": "openai package required for image generation"}

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"error": True, "message": "OPENAI_API_KEY required for DALL-E"}

    base_url = os.environ.get("OPENAI_API_BASE")
    client = OpenAI(api_key=api_key, base_url=base_url)

    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality=quality,
            n=1,
        )
        url = response.data[0].url
        result = {"error": False, "url": url, "prompt": prompt}
        if output_path:
            import httpx

            image_data = httpx.get(url).content
            Path(output_path).expanduser().write_bytes(image_data)
            result["saved_to"] = output_path
        return result
    except Exception as exc:
        return {"error": True, "message": str(exc)}


from pathlib import Path
