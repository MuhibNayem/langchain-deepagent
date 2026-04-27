"""Multi-modal vision support for image input and analysis.

Handles base64 encoding, image validation, and vision message construction
for LangChain-compatible models (GPT-4o, Claude, Gemini, etc.).
"""
from __future__ import annotations

import base64
import mimetypes
from io import BytesIO
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage


def encode_image_path(path: str | Path) -> tuple[str, str]:
    """Read an image file and return (base64_string, mime_type)."""
    p = Path(path).expanduser().resolve()
    data = p.read_bytes()
    mime, _ = mimetypes.guess_type(str(p))
    mime = mime or "image/png"
    b64 = base64.b64encode(data).decode("utf-8")
    return b64, mime


def encode_image_bytes(data: bytes, mime_type: str = "image/png") -> str:
    """Encode raw image bytes to base64."""
    return base64.b64encode(data).decode("utf-8")


def build_vision_message(
    text: str,
    image_sources: list[str | Path | bytes],
    mime_hints: list[str] | None = None,
) -> HumanMessage:
    """Build a LangChain HumanMessage with text + images.

    Args:
        text: The text prompt.
        image_sources: List of file paths, URLs, or raw bytes.
        mime_hints: Optional mime types for raw bytes sources.

    Returns:
        A HumanMessage with mixed text and image_url content blocks.
    """
    content: list[dict[str, Any]] = [{"type": "text", "text": text}]
    for idx, src in enumerate(image_sources):
        if isinstance(src, bytes):
            mime = (mime_hints or [])[idx] if mime_hints and idx < len(mime_hints) else "image/png"
            b64 = encode_image_bytes(src, mime)
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
            )
        elif isinstance(src, str) and (src.startswith("http://") or src.startswith("https://")):
            content.append({"type": "image_url", "image_url": {"url": src}})
        else:
            b64, mime = encode_image_path(src)
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
            )
    return HumanMessage(content=content)


def is_vision_capable(model: str) -> bool:
    """Heuristic check if a model supports vision input."""
    vision_keywords = [
        "vision",
        "gpt-4o",
        "claude-3",
        "claude-sonnet",
        "claude-opus",
        "gemini",
        "llava",
        "qwen-vl",
        "pixtral",
    ]
    model_lower = model.lower()
    return any(k in model_lower for k in vision_keywords)
