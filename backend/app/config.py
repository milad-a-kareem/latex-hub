from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    firebase_project_id: str = ""
    firebase_storage_bucket: str = ""
    google_application_credentials: str = ""
    cors_allow_origins: str = "http://localhost:5173"
    compile_workdir: str = "/tmp/latex-hub"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
