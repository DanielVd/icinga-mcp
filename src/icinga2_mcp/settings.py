"""Settings for Icinga2 MCP."""

from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, DirectoryPath, Field, FilePath, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CoreInstance(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)

    url: AnyHttpUrl
    user: str = Field(min_length=1)
    password: SecretStr
    verify_ssl: bool = True
    ca_bundle: FilePath | None = None
    write_user: str | None = Field(default=None, min_length=1)
    write_password: SecretStr | None = None

    @model_validator(mode="after")
    def validate_connection(self):
        if self.url.scheme != "https" or self.url.username or self.url.password or self.url.query or self.url.fragment:
            raise ValueError("The Core URL must use HTTPS and have no credentials, query or fragment")
        if self.password.get_secret_value() == "":
            raise ValueError("The Core password cannot be empty")
        if (self.write_user is None) != (self.write_password is None):
            raise ValueError("Configure both write_user and write_password")
        if self.write_password is not None and not self.write_password.get_secret_value():
            raise ValueError("The Core write password cannot be empty")
        if self.ca_bundle is not None and not self.verify_ssl:
            raise ValueError("A Core CA bundle requires TLS verification")
        return self


class Icinga2Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ICINGA_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        hide_input_in_errors=True,
        extra="ignore",
    )

    host: str | None = None
    user: str | None = None
    password: SecretStr | None = None
    verify_ssl: bool = False
    instances: dict[str, CoreInstance] = Field(default_factory=dict)
    plugin_catalog_path: DirectoryPath | None = None
    transport: Literal["streamable-http", "stdio"] = "streamable-http"
    mcp_host: str = "0.0.0.0"
    mcp_port: int = Field(default=8092, ge=1, le=65535)

    @model_validator(mode="after")
    def validate_backends(self):
        if self.instances:
            if any(not name or name.strip() != name for name in self.instances):
                raise ValueError("Core instance names must be non-empty and have no surrounding spaces")
        elif any(value is not None for value in (self.host, self.user, self.password)):
            if not self.host or not self.user or self.password is None or not self.password.get_secret_value():
                raise ValueError("Configure ICINGA_HOST, ICINGA_USER and ICINGA_PASSWORD together")
        elif self.plugin_catalog_path is None:
            raise ValueError("Configure a Core instance or ICINGA_PLUGIN_CATALOG_PATH")
        return self
