"""Tests for optional dependencies lazy import system."""

import sys
from unittest.mock import patch

import pytest


class TestOptionalDependencies:
    """Test lazy loading of optional dependencies."""

    def test_pillow_lazy_import_success(self):
        """Test that PIL lazy import works when pillow is installed."""
        # Import the module fresh
        import importlib

        from pinterest_dl.storage import media

        # Force re-evaluation by resetting cache
        media._PIL = None
        media._PIL_available = None

        # Should work if pillow is installed
        try:
            pil_module = media._get_PIL()
            assert pil_module is not None
            assert media._PIL_available is True
            assert media._PIL is not None
        except ImportError:
            pytest.skip("Pillow not installed, skipping test")

    def test_pillow_lazy_import_cached(self):
        """Test that PIL lazy import is cached and only checked once."""
        from pinterest_dl.storage import media

        # Reset cache
        media._PIL = None
        media._PIL_available = None

        try:
            # First call
            result1 = media._get_PIL()
            # Second call should return cached result
            result2 = media._get_PIL()
            assert result1 is result2
        except ImportError:
            pytest.skip("Pillow not installed, skipping test")

    def test_pillow_lazy_import_failure(self):
        """Test that PIL lazy import raises clear error when not installed."""
        from pinterest_dl.storage import media

        # Reset cache
        media._PIL = None
        media._PIL_available = None

        # Mock the import to fail
        with patch.dict("sys.modules", {"PIL": None}):
            with patch(
                "builtins.__import__", side_effect=ImportError("No module named 'PIL'")
            ):
                media._PIL = None
                media._PIL_available = None

                with pytest.raises(
                    ImportError, match="Pillow is required for image operations"
                ):
                    media._get_PIL()

    def test_pyexiv2_lazy_import_success(self):
        """Test that pyexiv2 lazy import works when installed."""
        import importlib

        from pinterest_dl.storage import media

        # Force re-evaluation by resetting cache
        media._pyexiv2 = None
        media._pyexiv2_available = None

        # Should work if pyexiv2 is installed
        try:
            pyexiv2_module = media._get_pyexiv2()
            assert pyexiv2_module is not None
            assert media._pyexiv2_available is True
            assert media._pyexiv2 is not None
        except ImportError:
            pytest.skip("pyexiv2 not installed, skipping test")

    def test_pyexiv2_lazy_import_cached(self):
        """Test that pyexiv2 lazy import is cached and only checked once."""
        from pinterest_dl.storage import media

        # Reset cache
        media._pyexiv2 = None
        media._pyexiv2_available = None

        try:
            # First call
            result1 = media._get_pyexiv2()
            # Second call should return cached result
            result2 = media._get_pyexiv2()
            assert result1 is result2
        except ImportError:
            pytest.skip("pyexiv2 not installed, skipping test")

    def test_pyexiv2_lazy_import_failure(self):
        """Test that pyexiv2 lazy import raises clear error when not installed."""
        from pinterest_dl.storage import media

        # Reset cache
        media._pyexiv2 = None
        media._pyexiv2_available = None

        # Mock the import to fail
        with patch.dict("sys.modules", {"pyexiv2": None}):
            with patch(
                "builtins.__import__",
                side_effect=ImportError("No module named 'pyexiv2'"),
            ):
                media._pyexiv2 = None
                media._pyexiv2_available = None

                with pytest.raises(
                    ImportError, match="pyexiv2 is required for EXIF operations"
                ):
                    media._get_pyexiv2()

    def test_write_exif_without_pyexiv2(self):
        """Test that write_exif functions fail gracefully without pyexiv2."""
        from pathlib import Path

        from pinterest_dl.domain.media import PinterestMedia
        from pinterest_dl.storage import media

        # Reset cache
        media._pyexiv2 = None
        media._pyexiv2_available = None

        # Create a mock media object
        test_media = PinterestMedia(
            id=123,
            src="https://example.com/image.jpg",
            alt="Test image",
            origin="https://pinterest.com/pin/123",
            resolution=(512, 512),
        )
        test_media.local_path = Path("test.jpg")

        # Mock the import to fail
        with patch.dict("sys.modules", {"pyexiv2": None}):
            with patch(
                "builtins.__import__",
                side_effect=ImportError("No module named 'pyexiv2'"),
            ):
                media._pyexiv2 = None
                media._pyexiv2_available = None

                with pytest.raises(ImportError, match="pyexiv2 is required"):
                    media.write_exif_comment(test_media, "test comment")

                with pytest.raises(ImportError, match="pyexiv2 is required"):
                    media.write_exif_subject(test_media, "test subject")

    def test_set_local_resolution_without_pillow(self):
        """Test that set_local_resolution fails gracefully without Pillow."""
        from pathlib import Path

        from pinterest_dl.domain.media import PinterestMedia
        from pinterest_dl.storage import media

        # Reset cache
        media._PIL = None
        media._PIL_available = None

        # Create a mock media object
        test_media = PinterestMedia(
            id=123,
            src="https://example.com/image.jpg",
            alt="Test image",
            origin="https://pinterest.com/pin/123",
            resolution=(512, 512),
        )

        # Mock file existence check
        mock_path = Path("test.jpg")

        # Mock the import to fail
        with patch.dict("sys.modules", {"PIL": None}):
            with patch(
                "builtins.__import__", side_effect=ImportError("No module named 'PIL'")
            ):
                with patch.object(Path, "exists", return_value=True):
                    media._PIL = None
                    media._PIL_available = None

                    with pytest.raises(
                        ImportError, match="Pillow is required for image operations"
                    ):
                        media.set_local_resolution(test_media, mock_path)

    def test_lazy_import_not_triggered_for_videos(self):
        """Test that PIL is not imported for video files."""
        from pathlib import Path

        from pinterest_dl.domain.media import PinterestMedia
        from pinterest_dl.storage import media

        # Reset cache
        media._PIL = None
        media._PIL_available = None

        # Create a mock media object with video path
        test_media = PinterestMedia(
            id=456,
            src="https://example.com/video.mp4",
            alt="Test video",
            origin="https://pinterest.com/pin/456",
            resolution=(1920, 1080),
        )

        # Should not trigger PIL import for video files
        media.set_local_resolution(test_media, Path("test.mp4"))

        # Cache should still be uninitialized
        assert media._PIL_available is None

    def test_lazy_import_error_messages(self):
        """Test that error messages are helpful and include install instructions."""
        from pinterest_dl.storage import media

        # Reset cache
        media._PIL = None
        media._PIL_available = None

        with patch.dict("sys.modules", {"PIL": None}):
            with patch("builtins.__import__", side_effect=ImportError("No module")):
                media._PIL = None
                media._PIL_available = None

                try:
                    media._get_PIL()
                    pytest.fail("Should have raised ImportError")
                except ImportError as e:
                    assert "Pillow is required" in str(e)
                    assert "pip install" in str(e).lower()

        # Reset cache for pyexiv2
        media._pyexiv2 = None
        media._pyexiv2_available = None

        with patch.dict("sys.modules", {"pyexiv2": None}):
            with patch("builtins.__import__", side_effect=ImportError("No module")):
                media._pyexiv2 = None
                media._pyexiv2_available = None

                try:
                    media._get_pyexiv2()
                    pytest.fail("Should have raised ImportError")
                except ImportError as e:
                    assert "pyexiv2 is required" in str(e)
                    assert "pip install" in str(e).lower()
