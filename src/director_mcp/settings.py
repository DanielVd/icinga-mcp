"""Settings for Director MCP."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class DirectorSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DIRECTOR_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    base_url: str
    user: str
    password: str
    verify_ssl: bool = False
