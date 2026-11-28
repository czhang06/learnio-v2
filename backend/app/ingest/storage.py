"""Where uploaded PDFs live, so ingestion can be re-run on the original file.

`LocalStorage` writes under a directory: fine for development and tests, but a
Render instance's disk is wiped on every deploy. `S3Storage` talks to any
S3-compatible store (Backblaze B2 in production, also AWS S3 or Cloudflare R2)
and is what production should use.
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


class S3Storage:
    """S3 API client for one bucket. `client` is injectable for tests."""

    def __init__(self, bucket: str, client=None):
        self.bucket = bucket
        if client is None:
            import boto3
            from botocore.config import Config

            endpoint = settings.s3_endpoint_url
            if endpoint and "://" not in endpoint:
                # Dashboards show the bare host ("s3.us-west-004.backblazeb2.com");
                # boto3 rejects an endpoint without a scheme.
                endpoint = "https://" + endpoint
            client = boto3.client(
                "s3",
                endpoint_url=endpoint,
                region_name=settings.s3_region,
                aws_access_key_id=settings.s3_access_key_id,
                aws_secret_access_key=settings.s3_secret_access_key,
                # Recent boto3 adds CRC checksums to every request by default,
                # which not every S3-compatible store accepts. Only send them
                # when an operation requires one.
                config=Config(
                    request_checksum_calculation="when_required",
                    response_checksum_validation="when_required",
                ),
            )
        self.client = client

    def put(self, key: str, data: bytes) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType="application/pdf")

    def get(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()


@lru_cache
def get_storage() -> Storage:
    if settings.storage_backend == "s3":
        if not settings.s3_bucket:
            raise RuntimeError("STORAGE_BACKEND=s3 needs S3_BUCKET, S3_ENDPOINT_URL, S3_REGION and access keys")
        return S3Storage(settings.s3_bucket)
    return LocalStorage(settings.storage_dir)
