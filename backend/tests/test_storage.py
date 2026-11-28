import io

import pytest

from app.config import settings
from app.ingest import storage
from app.ingest.storage import LocalStorage, S3Storage


def test_local_storage_round_trips_and_creates_folders(tmp_path):
    store = LocalStorage(tmp_path)
    store.put("documents/1.pdf", b"%PDF-1.7 bytes")
    assert store.get("documents/1.pdf") == b"%PDF-1.7 bytes"
    assert (tmp_path / "documents" / "1.pdf").exists()


def test_local_storage_rejects_keys_outside_its_root(tmp_path):
    with pytest.raises(ValueError):
        LocalStorage(tmp_path / "root").put("../escape.pdf", b"x")


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, *, Bucket, Key, Body, ContentType):
        self.objects[(Bucket, Key)] = (Body, ContentType)

    def get_object(self, *, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)][0])}


def test_s3_storage_writes_pdfs_to_the_bucket():
    s3 = FakeS3()
    store = S3Storage("exams", client=s3)
    store.put("documents/7.pdf", b"pdf")
    assert s3.objects[("exams", "documents/7.pdf")] == (b"pdf", "application/pdf")
    assert store.get("documents/7.pdf") == b"pdf"


def test_s3_storage_builds_a_client_for_the_configured_endpoint(monkeypatch):
    monkeypatch.setattr(settings, "s3_endpoint_url", "https://s3.us-west-004.backblazeb2.com")
    monkeypatch.setattr(settings, "s3_region", "us-west-004")
    monkeypatch.setattr(settings, "s3_access_key_id", "id")
    monkeypatch.setattr(settings, "s3_secret_access_key", "secret")
    client = S3Storage("exams").client
    assert client.meta.endpoint_url == "https://s3.us-west-004.backblazeb2.com"
    assert client.meta.region_name == "us-west-004"
    assert client.meta.config.request_checksum_calculation == "when_required"


@pytest.fixture
def fresh_storage():
    storage.get_storage.cache_clear()
    yield
    storage.get_storage.cache_clear()


def test_get_storage_defaults_to_local(fresh_storage):
    assert isinstance(storage.get_storage(), LocalStorage)


def test_get_storage_uses_s3_when_configured(monkeypatch, fresh_storage):
    monkeypatch.setattr(settings, "storage_backend", "s3")
    monkeypatch.setattr(settings, "s3_bucket", "exams")
    monkeypatch.setattr(settings, "s3_endpoint_url", "https://s3.us-west-004.backblazeb2.com")
    assert isinstance(storage.get_storage(), S3Storage)


def test_get_storage_needs_a_bucket_for_s3(monkeypatch, fresh_storage):
    monkeypatch.setattr(settings, "storage_backend", "s3")
    monkeypatch.setattr(settings, "s3_bucket", None)
    with pytest.raises(RuntimeError, match="S3_BUCKET"):
        storage.get_storage()


def test_s3_endpoint_without_a_scheme_gets_https(monkeypatch):
    monkeypatch.setattr(settings, "s3_endpoint_url", "s3.us-west-004.backblazeb2.com")
    monkeypatch.setattr(settings, "s3_region", "us-west-004")
    assert S3Storage("exams").client.meta.endpoint_url == "https://s3.us-west-004.backblazeb2.com"


def test_s3_storage_sets_the_content_type():
    s3 = FakeS3()
    S3Storage("exams", client=s3).put("images/1-0.png", b"png", "image/png")
    assert s3.objects[("exams", "images/1-0.png")] == (b"png", "image/png")
