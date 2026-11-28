import re

from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Force the psycopg (v3) driver onto a provider-supplied URL.

    Hosted Postgres hands out URLs like ``postgres://...`` (Heroku-style, still
    common on Render and Railway) or ``postgresql://...`` (Neon, Supabase).
    SQLAlchemy 2 rejects the first outright, and resolves the second to
    psycopg2 -- which this project does not install, since it uses psycopg 3.

    Rewriting the scheme here means DATABASE_URL can be pasted from any
    provider's dashboard unchanged. Without it, the first deploy fails with
    "Can't load plugin: sqlalchemy.dialects:postgres" or a missing psycopg2.
    """
    return re.sub(r"^postgres(ql)?://", "postgresql+psycopg://", url, count=1)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://learnio:learnio@localhost:5432/learnio"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    max_upload_mb: int = 20

    # When set, adding courses and uploading PDFs require this value in the
    # X-Admin-Key header, so a public demo stays read-only for visitors.
    # Unset (local development, tests) leaves both open.
    admin_key: str | None = None

    # Accounts. The frontend signs users in (Google, through NextAuth) and
    # sends the API a short-lived HS256 token signed with this shared secret.
    # Unset: no accounts, every visitor is a guest.
    auth_api_secret: str | None = None
    # Comma-separated emails whose accounts get the admin role (uploads,
    # adding courses), alongside the admin key.
    admin_emails: str = ""

    # Comma-separated browser origins allowed to call the API. "*" is
    # acceptable for a public demo with no auth or cookies; narrow it to the
    # deployed frontend origin the moment either of those changes.
    allowed_origins: str = "*"

    # Where uploaded PDFs are kept: "local" (a directory, for development) or
    # "s3" (any S3-compatible store, for production). The deployed demo uses
    # Backblaze B2: endpoint https://s3.<region>.backblazeb2.com, region e.g.
    # us-west-004, and a B2 application key's keyID / applicationKey as the keys.
    storage_backend: str = "local"
    storage_dir: str = "uploads"
    s3_bucket: str | None = None
    s3_endpoint_url: str | None = None  # unset means AWS S3 itself
    s3_region: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None

    # Background ingestion. The worker loop runs inside the API process.
    run_worker: bool = True
    worker_poll_seconds: float = 2.0
    job_timeout_seconds: int = 600  # a job processing longer than this is claimed again
    max_attempts: int = 3
    # Publish straight after ingestion instead of waiting in needs_review.
    # On until the admin review screen exists.
    auto_publish: bool = True
    # Process uploads inside the request, before responding (tests only).
    ingest_inline: bool = False

    @property
    def sqlalchemy_url(self) -> str:
        """The database URL with a driver SQLAlchemy can actually load."""
        return normalize_database_url(self.database_url)

    @property
    def admin_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}

    @property
    def origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


settings = Settings()
