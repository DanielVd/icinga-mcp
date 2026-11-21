"""Settings for Director MCP."""

from pydantic import BaseModel, Field, FilePath
from pydantic_settings import BaseSettings, SettingsConfigDict


class DirectorActivitySettings(BaseModel):
    ssh_target: str = Field(pattern=r"^[a-z_][a-z0-9_-]*@[a-zA-Z0-9][a-zA-Z0-9.-]*$")
    identity_file: FilePath
    known_hosts: FilePath


class DirectorSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DIRECTOR_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    base_url: str
    user: str
    password: str
    verify_ssl: bool = False
    activity: DirectorActivitySettings | None = None
