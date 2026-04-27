"""Unit tests for ScreenshotStore baseline management."""
import pytest


class TestScreenshotStore:
    """Tests for ScreenshotStore."""

    @pytest.fixture
    def store(self, tmp_path):
        """Create store for testing."""
        from luminamind.evaluator.screenshot_store import ScreenshotStore
        return ScreenshotStore(store_root=tmp_path)

    @pytest.mark.asyncio
    async def test_save_and_retrieve(self, store):
        """Test save and retrieve flow."""
        test_url = "https://example.com"
        test_bytes = b"fake-png-data"
        metadata = {"width": 1280, "height": 720, "full_page": False}

        meta = await store.save(test_url, test_bytes, metadata)

        assert meta.version == 1
        assert meta.url == test_url

        retrieved = await store.get_latest(test_url)
        assert retrieved == test_bytes

    @pytest.mark.asyncio
    async def test_versioning(self, store):
        """Test that multiple saves create versions."""
        test_url = "https://example.com"

        await store.save(test_url, b"v1", {"width": 100, "height": 100})
        await store.save(test_url, b"v2", {"width": 100, "height": 100})
        await store.save(test_url, b"v3", {"width": 100, "height": 100})

        v1 = await store.get_version(test_url, 1)
        v3 = await store.get_version(test_url, 3)

        assert v1 == b"v1"
        assert v3 == b"v3"

    @pytest.mark.asyncio
    async def test_get_latest_returns_none_for_unknown_url(self, store):
        """Test that get_latest returns None for unknown URL."""
        result = await store.get_latest("https://unknown.example.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_metadata_stored_correctly(self, store):
        """Test that metadata is stored and retrievable."""
        test_url = "https://example.com"
        metadata = {"width": 1920, "height": 1080, "full_page": True}

        meta = await store.save(test_url, b"test-image", metadata)

        retrieved_meta = await store.get_metadata(test_url)
        assert retrieved_meta is not None
        assert retrieved_meta.url == test_url
        assert retrieved_meta.width == 1920
        assert retrieved_meta.height == 1080
        assert retrieved_meta.full_page is True
