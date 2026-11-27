"""Where uploaded PDFs live, so ingestion can be re-run on the original file.

`LocalStorage` writes under a directory: fine for development and tests, but a
Render instance's disk is wiped on every deploy. `R2Storage` talks to Cloudflare
R2 (or any S3-compatible store) and is what production should use.
"""

from functools import lru_cache
from pathlib import Path
from typing import Protocol

from ..config import settings


class Storage(Protocol):
    def put(self, key: str, data: bytes) -> None: ...

    def get(self, key: str) -> bytes: ...


class LocalStorage:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError(f"Storage key escapes the storage root: {key!r}")
        return path

    def put(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()


class R2Storage:
    """S3 API client pointed at an R2 bucket. `client` is injectable for tests."""

    def __init__(self, bucket: str, client=None):
        self.bucket = bucket
        if client is None:
            import boto3

            client = boto3.client(
                "s3",
                endpoint_url=settings.r2_endpoint_url,
                aws_access_key_id=settings.r2_access_key_id,
                aws_secret_access_key=settings.r2_secret_access_key,
                region_name="auto",
            )
        self.client = client

    def put(self, key: str, data: bytes) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType="application/pdf")

    def get(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()


@lru_cache
def get_storage() -> Storage:
    if settings.storage_backend == "r2":
        if not settings.r2_bucket:
            raise RuntimeError("STORAGE_BACKEND=r2 needs R2_BUCKET, R2_ENDPOINT_URL and R2 access keys")
        return R2Storage(settings.r2_bucket)
    return LocalStorage(settings.storage_dir)
