"""Visual regression detection for UI changes."""
import io
from dataclasses import dataclass
from typing import BinaryIO

from PIL import Image


@dataclass
class DiffResult:
    """Result of visual comparison."""
    has_changed: bool
    diff_percentage: float
    diff_image: bytes | None
    changed_regions: list[dict]


class VisualRegressionDetector:
    """Detects visual regressions by comparing screenshots.

    Uses pixel-by-pixel comparison with configurable threshold
    to determine if UI has changed significantly.
    """

    def __init__(self, threshold: float = 0.01, pixel_threshold: int = 30):
        """Initialize detector.

        Args:
            threshold: Percentage of pixels that must differ (0.0-1.0)
            pixel_threshold: RGB distance to consider pixels "different"
        """
        self.threshold = threshold
        self.pixel_threshold = pixel_threshold

    def compare(self, baseline: bytes | BinaryIO, current: bytes | BinaryIO) -> DiffResult:
        """Compare two screenshots.

        Args:
            baseline: Baseline image bytes or file-like
            current: Current image bytes or file-like

        Returns:
            DiffResult with change detection and diff image
        """
        # Load images
        if isinstance(baseline, bytes):
            baseline_img = Image.open(io.BytesIO(baseline))
        else:
            baseline_img = Image.open(baseline)

        if isinstance(current, bytes):
            current_img = Image.open(io.BytesIO(current))
        else:
            current_img = Image.open(current)

        # Resize to match if needed
        if baseline_img.size != current_img.size:
            current_img = current_img.resize(baseline_img.size, Image.LANCZOS)

        # Convert to RGB
        baseline_rgb = baseline_img.convert("RGB")
        current_rgb = current_img.convert("RGB")

        # Get pixel data
        baseline_pixels = list(baseline_rgb.getdata())
        current_pixels = list(current_rgb.getdata())

        # Compare
        total_pixels = len(baseline_pixels)
        diff_pixels = 0
        changed_regions = []

        width, height = baseline_img.size

        for i, (bp, cp) in enumerate(zip(baseline_pixels, current_pixels)):
            # Calculate RGB distance
            distance = (
                abs(bp[0] - cp[0]) +
                abs(bp[1] - cp[1]) +
                abs(bp[2] - cp[2])
            )

            if distance > self.pixel_threshold:
                diff_pixels += 1
                # Track region (8x8 grid)
                x = i % width
                y = i // width
                grid_x = x * 8 // width
                grid_y = y * 8 // height
                region_key = f"r{grid_y}-{grid_x}"
                if region_key not in [r["region"] for r in changed_regions]:
                    changed_regions.append({
                        "region": region_key,
                        "x": x,
                        "y": y,
                    })

        diff_percentage = diff_pixels / total_pixels
        has_changed = diff_percentage >= self.threshold

        # Generate diff image
        diff_img = self._generate_diff_image(baseline_rgb, current_rgb, width, height)

        return DiffResult(
            has_changed=has_changed,
            diff_percentage=diff_percentage,
            diff_image=diff_img,
            changed_regions=changed_regions,
        )

    def _generate_diff_image(
        self,
        baseline: Image.Image,
        current: Image.Image,
        width: int,
        height: int,
    ) -> bytes:
        """Generate diff image with highlighted changes."""
        diff_img = Image.new("RGB", (width, height))
        baseline_rgb = baseline.convert("RGB")
        current_rgb = current.convert("RGB")

        diff_pixels = []
        for y in range(height):
            row = []
            for x in range(width):
                bp = baseline_rgb.getpixel((x, y))
                cp = current_rgb.getpixel((x, y))

                distance = (
                    abs(bp[0] - cp[0]) +
                    abs(bp[1] - cp[1]) +
                    abs(bp[2] - cp[2])
                )

                if distance > self.pixel_threshold:
                    # Highlight in red
                    row.append((255, 0, 0))
                else:
                    # Dim baseline
                    row.append((
                        int(bp[0] * 0.5),
                        int(bp[1] * 0.5),
                        int(bp[2] * 0.5),
                    ))
            diff_pixels.extend(row)

        diff_img.putdata(diff_pixels)
        output = io.BytesIO()
        diff_img.save(output, format="PNG")
        return output.getvalue()


__all__ = ["VisualRegressionDetector", "DiffResult"]
