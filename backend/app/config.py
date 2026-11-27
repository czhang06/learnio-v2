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

    # Comma-separated browser origins allowed to call the API. "*" is
    # acceptable for a public demo with no auth or cookies; narrow it to the
    # deployed frontend origin the moment either of those changes.
    allowed_origins: str = "*"

    # Where uploaded PDFs are kept: "local" (a directory, for development) or
    # "r2" (Cloudflare R2 through its S3 API, for production).
    storage_backend: str = "local"
    storage_dir: str = "uploads"
    r2_bucket: str | None = None
    r2_endpoint_url: str | None = None  # https://<account id>.r2.cloudflarestorage.com
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None

    @property
    def sqlalchemy_url(self) -> str:
        """The database URL with a driver SQLAlchemy can actually load."""
        return normalize_database_url(self.database_url)

    @property
    def origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


settings = Settings()
