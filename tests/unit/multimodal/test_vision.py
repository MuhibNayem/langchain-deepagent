"""Tests for multimodal vision utilities."""
import base64
from pathlib import Path

from luminamind.multimodal.vision import (
    build_vision_message,
    encode_image_bytes,
    encode_image_path,
    is_vision_capable,
)


def test_encode_image_bytes():
    data = b"fake_image_data"
    b64 = encode_image_bytes(data, "image/png")
    assert b64 == base64.b64encode(data).decode("utf-8")


def test_build_vision_message_with_url():
    msg = build_vision_message("Describe this", ["https://example.com/img.png"])
    assert msg.content[0]["type"] == "text"
    assert msg.content[1]["type"] == "image_url"
    assert msg.content[1]["image_url"]["url"] == "https://example.com/img.png"


def test_build_vision_message_with_bytes():
    msg = build_vision_message("Describe this", [b"fake"], mime_hints=["image/jpeg"])
    assert msg.content[1]["type"] == "image_url"
    assert "data:image/jpeg;base64," in msg.content[1]["image_url"]["url"]


def test_is_vision_capable():
    assert is_vision_capable("gpt-4o") is True
    assert is_vision_capable("claude-3-opus") is True
    assert is_vision_capable("text-embedding-3-small") is False
    assert is_vision_capable("glm-4.7-flash") is False  # GLM models don't have vision keyword
