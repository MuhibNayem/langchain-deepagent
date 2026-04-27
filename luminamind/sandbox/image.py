from typing import Optional
from dataclasses import dataclass

@dataclass
class ContainerImage:
    """Container image specification."""
    name: str
    tag: str
    registry: str = "library"  # docker.io, ghcr.io, etc.
    pull_policy: str = "if-not-present"  # always, if-not-present, never
    
    @property
    def full_name(self) -> str:
        return f"{self.registry}/{self.name}:{self.tag}"
    
    def pull(self) -> bool:
        """Pull image. Returns True if successful."""
        pass
    
    def exists(self) -> bool:
        """Check if image exists locally."""
        pass

class ImageRegistry:
    """Registry for managing container images."""
    
    DEFAULT_IMAGES = {
        'python': ContainerImage(name='python', tag='3.12-slim'),
        'node': ContainerImage(name='node', tag='20-slim'),
        'java': ContainerImage(name='openjdk', tag='17-slim'),
        'go': ContainerImage(name='golang', tag='1.21-alpine'),
    }
    
    def __init__(self):
        self._images: dict[str, ContainerImage] = {}
    
    def register(self, language: str, image: ContainerImage) -> None:
        """Register a container image for a language."""
        self._images[language] = image
    
    def get(self, language: str) -> ContainerImage:
        """Get image for language."""
        return self._images.get(language, self.DEFAULT_IMAGES.get(language))
    
    def list_supported(self) -> list[str]:
        """List all supported language runtimes."""
        return list(self.DEFAULT_IMAGES.keys()) + list(self._images.keys())
