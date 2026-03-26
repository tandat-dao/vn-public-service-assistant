"""Storage service — MinIO (S3-compatible) object storage wrapper.

Bucket policy is PRIVATE: anonymous get_object returns 403.
All blocking MinIO SDK calls are wrapped in asyncio.get_event_loop().run_in_executor()
so they do not block the async event loop.

Partial form-fill PDFs are written to a ``tmp/{session_id}/`` prefix and
promoted to the final path via ``promote_tmp()`` only when all required
fields are confirmed filled.
"""

import asyncio
import io
import json
import logging

import structlog
from minio import Minio
from minio.error import S3Error

from app.config import settings

logger = structlog.get_logger(__name__)

_PRIVATE_POLICY = json.dumps({"Version": "2012-10-17", "Statement": []})


class StorageError(Exception):
    """Raised when a MinIO operation fails."""


class StorageService:
    """MinIO client wrapper for file upload/download."""

    def __init__(self) -> None:
        self._client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self._bucket = settings.MINIO_BUCKET
        self._loop = asyncio.get_event_loop
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Create the bucket if it does not exist, then always enforce PRIVATE policy."""
        try:
            if not self._client.bucket_exists(self._bucket):
                self._client.make_bucket(self._bucket)
                logger.info("Created MinIO bucket", bucket=self._bucket)
            # Always enforce PRIVATE policy on startup, even if bucket already existed
            self._client.set_bucket_policy(self._bucket, _PRIVATE_POLICY)
            logger.info("MinIO bucket ready with PRIVATE policy", bucket=self._bucket)
        except S3Error as exc:
            logger.warning("MinIO bucket init failed", error=str(exc))

    def _executor(self):
        return asyncio.get_event_loop()

    async def upload(
        self,
        object_path: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload bytes to MinIO. Returns the object path."""
        def _put():
            self._client.put_object(
                self._bucket,
                object_path,
                io.BytesIO(data),
                length=len(data),
                content_type=content_type,
            )

        try:
            await self._executor().run_in_executor(None, _put)
            logger.info("Uploaded object to MinIO", path=object_path, size=len(data))
            return object_path
        except S3Error as exc:
            raise StorageError(f"Upload failed for {object_path}: {exc}") from exc

    async def download(self, object_path: str) -> bytes:
        """Download an object from MinIO and return its content as bytes."""
        def _get():
            response = self._client.get_object(self._bucket, object_path)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()

        try:
            return await self._executor().run_in_executor(None, _get)
        except S3Error as exc:
            raise StorageError(f"Download failed for {object_path}: {exc}") from exc

    async def get_presigned_url(self, object_path: str, expires_seconds: int = 3600) -> str:
        """Return a presigned GET URL valid for ``expires_seconds``."""
        from datetime import timedelta

        def _presign():
            return self._client.presigned_get_object(
                self._bucket,
                object_path,
                expires=timedelta(seconds=expires_seconds),
            )

        try:
            return await self._executor().run_in_executor(None, _presign)
        except S3Error as exc:
            raise StorageError(f"Presign failed for {object_path}: {exc}") from exc

    async def promote_tmp(self, tmp_path: str, final_path: str) -> None:
        """Copy a tmp object to its final path, then delete the tmp object.

        Called by form_filler_fn only when unfilled_required_fields is empty.
        Never call this on a partially filled form.

        If the delete fails after a successful copy, logs a warning but does NOT raise —
        the file is safely promoted and the tmp copy will expire or be cleaned up later.
        """
        from minio.commonconfig import CopySource

        def _copy():
            self._client.copy_object(
                self._bucket,
                final_path,
                CopySource(self._bucket, tmp_path),
            )

        def _delete():
            self._client.remove_object(self._bucket, tmp_path)

        try:
            await self._executor().run_in_executor(None, _copy)
        except S3Error as exc:
            raise StorageError(f"Copy failed {tmp_path} -> {final_path}: {exc}") from exc

        try:
            await self._executor().run_in_executor(None, _delete)
            logger.info("Promoted tmp PDF", tmp=tmp_path, final=final_path)
        except S3Error as exc:
            logger.warning(
                "Copy succeeded but delete of tmp failed — manual cleanup may be needed",
                tmp=tmp_path,
                final=final_path,
                error=str(exc),
            )
