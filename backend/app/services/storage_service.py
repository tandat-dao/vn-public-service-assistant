"""Storage service — MinIO (S3-compatible) object storage wrapper."""


class StorageService:
    """MinIO client wrapper for file upload/download."""

    async def upload(self, local_path: str, object_name: str) -> str:
        """Upload file to MinIO. Returns the object path (not a signed URL)."""
        raise NotImplementedError

    async def download(self, object_name: str, local_path: str) -> None:
        raise NotImplementedError

    async def get_presigned_url(self, object_name: str, expires_seconds: int = 3600) -> str:
        raise NotImplementedError
