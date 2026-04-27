"""Screenshot storage with versioning for visual regression."""
import asyncio
import dataclasses
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiofiles


@dataclass
class ScreenshotMetadata:
    """Metadata for a stored screenshot."""
    url: str
    captured_at: str
    sha256: str
    width: int
    height: int
    full_page: bool
    version: int


class ScreenshotStore:
    """Manages screenshot storage with versioning.

    Storage structure:
    store/
      {url_hash}/
        metadata.json
        v1.png
        v2.png
        ...
    """

    def __init__(self, store_root: Path | str = ".screenshot_store"):
        self.store_root = Path(store_root)
        self.store_root.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    def _url_to_hash(self, url: str) -> str:
        """Convert URL to safe directory name."""
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    async def save(
        self,
        url: str,
        image_bytes: bytes,
        metadata: dict[str, Any],
    ) -> ScreenshotMetadata:
        """Save screenshot with metadata."""
        async with self._lock:
            url_hash = self._url_to_hash(url)
            dir_path = self.store_root / url_hash
            dir_path.mkdir(parents=True, exist_ok=True)

            # Get existing versions
            versions = await self._get_versions(url_hash)
            new_version = len(versions) + 1

            # Save image
            image_path = dir_path / f"v{new_version}.png"
            async with aiofiles.open(image_path, "wb") as f:
                await f.write(image_bytes)

            # Save metadata
            meta = ScreenshotMetadata(
                url=url,
                captured_at=datetime.now(timezone.utc).isoformat(),
                sha256=hashlib.sha256(image_bytes).hexdigest(),
                width=metadata.get("width", 0),
                height=metadata.get("height", 0),
                full_page=metadata.get("full_page", False),
                version=new_version,
            )

            meta_path = dir_path / "metadata.json"
            async with aiofiles.open(meta_path, "w") as f:
                await f.write(json.dumps(dataclasses.asdict(meta)))

            return meta

    async def _get_versions(self, url_hash: str) -> list[int]:
        """Get list of existing versions."""
        dir_path = self.store_root / url_hash
        if not dir_path.exists():
            return []

        versions = []
        for f in dir_path.iterdir():
            if f.suffix == ".png" and f.stem.startswith("v"):
                try:
                    versions.append(int(f.stem[1:]))
                except ValueError:
                    pass
        return sorted(versions)

    async def get_latest(self, url: str) -> bytes | None:
        """Get latest screenshot for URL."""
        url_hash = self._url_to_hash(url)
        versions = await self._get_versions(url_hash)
        if not versions:
            return None

        image_path = self.store_root / url_hash / f"v{versions[-1]}.png"
        if not image_path.exists():
            return None

        async with aiofiles.open(image_path, "rb") as f:
            return await f.read()

    async def get_version(self, url: str, version: int) -> bytes | None:
        """Get specific version screenshot."""
        url_hash = self._url_to_hash(url)
        image_path = self.store_root / url_hash / f"v{version}.png"
        if not image_path.exists():
            return None

        async with aiofiles.open(image_path, "rb") as f:
            return await f.read()

    async def get_metadata(self, url: str) -> ScreenshotMetadata | None:
        """Get metadata for URL."""
        url_hash = self._url_to_hash(url)
        meta_path = self.store_root / url_hash / "metadata.json"
        if not meta_path.exists():
            return None

        async with aiofiles.open(meta_path, "r") as f:
            data = json.loads(await f.read())
            return ScreenshotMetadata(**data)


__all__ = ["ScreenshotStore", "ScreenshotMetadata"]
