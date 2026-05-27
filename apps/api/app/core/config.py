from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    storage_root: Path = Path("storage")
    max_source_video_mb: int = 200
    ffmpeg_binary: str | None = None
    auth_source_api_base_url: str | None = None
    auth_source_api_token: str | None = None
    auth_source_timeout_seconds: float = 30
    allow_private_source_urls: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


settings = Settings()
