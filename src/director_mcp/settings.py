"""Settings for Director MCP."""

from pydantic import AnyHttpUrl, BaseModel, Field, FilePath, SecretStr, ValidationError, model_validator
from pydantic_settings import SettingsConfigDict

from icinga_mcp.transport import TransportSettings


class DirectorActivitySettings(BaseModel):
    ssh_target: str = Field(pattern=r"^[a-z_][a-z0-9_-]*@[a-zA-Z0-9][a-zA-Z0-9.-]*$")
    identity_file: FilePath
    known_hosts: FilePath


class DirectorSettings(TransportSettings):
    model_config = SettingsConfigDict(
        env_prefix="DIRECTOR_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        hide_input_in_errors=True,
        extra="ignore",
    )

    base_url: str
    user: str = Field(min_length=1)
    password: SecretStr = Field(min_length=1)
    verify_ssl: bool = True
    ca_bundle: FilePath | None = None
    mcp_port: int = Field(default=8093, ge=1, le=65535)
    activity: DirectorActivitySettings | None = None

    @model_validator(mode="after")
    def validate_backend(self):
        try:
            url = AnyHttpUrl(self.base_url)
        except ValidationError:
            raise ValueError("The Director URL is invalid") from None
        if url.scheme != "https" or url.username or url.password or url.query or url.fragment:
            raise ValueError("The Director URL must use HTTPS and have no credentials, query or fragment")
        if self.ca_bundle is not None and not self.verify_ssl:
            raise ValueError("A Director CA bundle requires TLS verification")
        return self
