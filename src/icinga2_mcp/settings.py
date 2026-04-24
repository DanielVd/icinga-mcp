"""Settings for Icinga2 MCP."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Icinga2Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ICINGA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str
    user: str
    password: str
    verify_ssl: bool = False
