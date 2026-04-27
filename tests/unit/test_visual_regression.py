"""Unit tests for visual regression detection."""
import io
import pytest
from PIL import Image


class TestVisualRegressionDetector:
    """Tests for VisualRegressionDetector."""

    @pytest.fixture
    def detector(self):
        """Create detector for testing."""
        from luminamind.evaluator.visual_regression import VisualRegressionDetector
        return VisualRegressionDetector(threshold=0.01, pixel_threshold=30)

    def _create_test_image(self, size=(100, 100), color=(128, 128, 128)) -> bytes:
        """Create a test image."""
        img = Image.new("RGB", size, color)
        output = io.BytesIO()
        img.save(output, format="PNG")
        return output.getvalue()

    def test_identical_images_no_change(self, detector):
        """Test that identical images are detected as unchanged."""
        img_bytes = self._create_test_image()

        result = detector.compare(img_bytes, img_bytes)

        assert result.has_changed is False
        assert result.diff_percentage < 0.001

    def test_different_images_detected(self, detector):
        """Test that different images are detected as changed."""
        img1 = self._create_test_image(color=(100, 100, 100))
        img2 = self._create_test_image(color=(200, 100, 100))

        result = detector.compare(img1, img2)

        assert result.has_changed is True
        assert result.diff_percentage > 0.01

    def test_diff_image_generated(self, detector):
        """Test that diff image is generated."""
        img1 = self._create_test_image(color=(100, 100, 100))
        img2 = self._create_test_image(color=(200, 100, 100))

        result = detector.compare(img1, img2)

        assert result.diff_image is not None
        assert len(result.diff_image) > 0

    def test_threshold_controls_sensitivity(self):
        """Test that threshold affects change detection."""
        from luminamind.evaluator.visual_regression import VisualRegressionDetector

        # Create baseline image (all gray)
        baseline_img = Image.new("RGB", (100, 100), (100, 100, 100))
        output1 = io.BytesIO()
        baseline_img.save(output1, format="PNG")
        baseline_bytes = output1.getvalue()

        # Create changed image (small diff in corner)
        changed_img = Image.new("RGB", (100, 100), (100, 100, 100))
        for x in range(5):
            for y in range(5):
                changed_img.putpixel((x, y), (200, 100, 100))
        output2 = io.BytesIO()
        changed_img.save(output2, format="PNG")
        changed_bytes = output2.getvalue()

        # Very high threshold - should not detect tiny change (25 pixels out of 10000 = 0.25%)
        strict_detector = VisualRegressionDetector(threshold=0.5, pixel_threshold=30)
        # Very low threshold - should detect tiny change
        lenient_detector = VisualRegressionDetector(threshold=0.001, pixel_threshold=30)

        strict_result = strict_detector.compare(baseline_bytes, changed_bytes)
        lenient_result = lenient_detector.compare(baseline_bytes, changed_bytes)

        assert strict_result.has_changed is False
        assert lenient_result.has_changed is True

    def test_changed_regions_identified(self, detector):
        """Test that changed regions are identified in diff result."""
        img1 = self._create_test_image(color=(100, 100, 100))
        img2 = self._create_test_image(color=(200, 200, 200))

        result = detector.compare(img1, img2)

        assert result.changed_regions is not None
        assert len(result.changed_regions) > 0
