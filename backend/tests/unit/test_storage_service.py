"""Unit tests for StorageService.

All tests mock the minio.Minio client — no real MinIO connection required.
"""

import asyncio
from unittest.mock import MagicMock, patch, call
import pytest


def _make_service():
    """Return a StorageService with a fully mocked Minio client."""
    from app.services.storage_service import StorageService

    mock_minio = MagicMock()
    mock_minio.bucket_exists.return_value = False
    mock_minio.make_bucket.return_value = None
    mock_minio.set_bucket_policy.return_value = None

    with patch("app.services.storage_service.Minio", return_value=mock_minio):
        with patch("app.services.storage_service.settings") as mock_settings:
            mock_settings.MINIO_ENDPOINT = "localhost:9000"
            mock_settings.MINIO_ACCESS_KEY = "minioadmin"
            mock_settings.MINIO_SECRET_KEY = "minioadmin"
            mock_settings.MINIO_SECURE = False
            mock_settings.MINIO_BUCKET = "test-bucket"
            svc = StorageService()
            svc._client = mock_minio
            return svc, mock_minio


class TestUpload:
    async def test_upload_returns_object_path(self):
        """upload() must return the object path string."""
        svc, mock_minio = _make_service()
        mock_minio.put_object.return_value = None

        result = await svc.upload("images/test.jpg", b"fake-image-data", "image/jpeg")

        assert result == "images/test.jpg"
        mock_minio.put_object.assert_called_once()

    async def test_minio_upload_uses_get_running_loop(self):
        """upload() must use asyncio.get_running_loop(), not the deprecated get_event_loop()."""
        svc, mock_minio = _make_service()
        mock_minio.put_object.return_value = None

        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = MagicMock()

            async def fake_executor(executor, fn):
                return fn()

            mock_loop.run_in_executor = fake_executor
            mock_get_loop.return_value = mock_loop

            await svc.upload("images/test.jpg", b"fake-image-data", "image/jpeg")

        mock_get_loop.assert_called()


class TestEnsureBucket:
    def test_ensure_bucket_creates_if_not_exists(self):
        """When bucket does not exist: make_bucket AND set_bucket_policy must both be called."""
        from app.services.storage_service import StorageService

        mock_minio = MagicMock()
        mock_minio.bucket_exists.return_value = False

        with patch("app.services.storage_service.Minio", return_value=mock_minio):
            with patch("app.services.storage_service.settings") as mock_settings:
                mock_settings.MINIO_ENDPOINT = "localhost:9000"
                mock_settings.MINIO_ACCESS_KEY = "minioadmin"
                mock_settings.MINIO_SECRET_KEY = "minioadmin"
                mock_settings.MINIO_SECURE = False
                mock_settings.MINIO_BUCKET = "test-bucket"
                StorageService()

        mock_minio.make_bucket.assert_called_once_with("test-bucket")
        mock_minio.set_bucket_policy.assert_called_once()

    def test_ensure_bucket_skips_creation_if_exists(self):
        """When bucket already exists: make_bucket must NOT be called, but set_bucket_policy IS called."""
        from app.services.storage_service import StorageService

        mock_minio = MagicMock()
        mock_minio.bucket_exists.return_value = True  # already exists

        with patch("app.services.storage_service.Minio", return_value=mock_minio):
            with patch("app.services.storage_service.settings") as mock_settings:
                mock_settings.MINIO_ENDPOINT = "localhost:9000"
                mock_settings.MINIO_ACCESS_KEY = "minioadmin"
                mock_settings.MINIO_SECRET_KEY = "minioadmin"
                mock_settings.MINIO_SECURE = False
                mock_settings.MINIO_BUCKET = "test-bucket"
                StorageService()

        mock_minio.make_bucket.assert_not_called()
        mock_minio.set_bucket_policy.assert_called_once()  # always enforced


class TestPromoteTmp:
    async def test_promote_tmp_copies_then_deletes(self):
        """promote_tmp must copy the object first, then delete the tmp — in that order."""
        svc, mock_minio = _make_service()

        call_order: list[str] = []

        def _copy(*args, **kwargs):
            call_order.append("copy")

        def _delete(*args, **kwargs):
            call_order.append("delete")

        mock_minio.copy_object.side_effect = _copy
        mock_minio.remove_object.side_effect = _delete

        await svc.promote_tmp("tmp/s1/form.pdf", "final/form_001.pdf")

        assert call_order == ["copy", "delete"]
        mock_minio.copy_object.assert_called_once()
        mock_minio.remove_object.assert_called_once_with("test-bucket", "tmp/s1/form.pdf")

    async def test_promote_tmp_logs_warning_on_delete_failure(self):
        """If delete fails after a successful copy, no exception must be raised."""
        from minio.error import S3Error

        svc, mock_minio = _make_service()
        mock_minio.copy_object.return_value = None
        mock_minio.remove_object.side_effect = S3Error(
            "NoSuchKey", "tmp/s1/form.pdf", "us-east-1", "", "", MagicMock()
        )

        # Must not raise even though delete fails
        await svc.promote_tmp("tmp/s1/form.pdf", "final/form_001.pdf")
