from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://learnio:learnio@localhost:5432/learnio"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    max_upload_mb: int = 20


settings = Settings()
