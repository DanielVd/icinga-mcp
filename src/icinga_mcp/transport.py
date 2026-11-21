"""Streamable HTTP configuration shared by Core and Director."""

import re
from secrets import compare_digest
from typing import Literal

import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field, FilePath, SecretStr, model_validator
from pydantic_settings import BaseSettings
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send


LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")


class TransportSettings(BaseSettings):
    transport: Literal["streamable-http", "stdio"] = "streamable-http"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = Field(ge=1, le=65535)
    mcp_bearer_token: SecretStr | None = None
    mcp_tls_cert: FilePath | None = None
    mcp_tls_key: FilePath | None = None
    mcp_allowed_hosts: list[str] = Field(default_factory=list)
    mcp_allowed_origins: list[str] = Field(default_factory=list)
    allow_writes: bool = False

    @model_validator(mode="after")
    def validate_transport(self):
        if self.transport == "stdio":
            return self
        if self.mcp_bearer_token is not None and not re.fullmatch(
            r"[A-Za-z0-9._~-]{32,}", self.mcp_bearer_token.get_secret_value()
        ):
            raise ValueError("The MCP bearer token requires at least 32 URL-safe ASCII characters")
        if (self.mcp_tls_cert is None) != (self.mcp_tls_key is None):
            raise ValueError("Configure both the MCP TLS certificate and key")
        if self.mcp_host not in LOOPBACK_HOSTS:
            if self.mcp_bearer_token is None or self.mcp_tls_cert is None:
                raise ValueError("A non-loopback MCP listener requires TLS and a bearer token")
            if not self.mcp_allowed_hosts:
                raise ValueError("Set the allowed HTTP Host headers for a non-loopback listener")
        if "*" in self.mcp_allowed_hosts or "*" in self.mcp_allowed_origins:
            raise ValueError("MCP Host and Origin allowlists require explicit entries")
        return self


class RequireBearer:
    def __init__(self, app: ASGIApp, token: SecretStr):
        self.app = app
        self.token = token.get_secret_value().encode("ascii")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            values = [value for name, value in scope["headers"] if name == b"authorization"]
            if len(values) == 1:
                scheme, _, value = values[0].partition(b" ")
                if scheme.lower() == b"bearer" and compare_digest(value, self.token):
                    await self.app(scope, receive, send)
                    return
            response = PlainTextResponse("Unauthorized", status_code=401, headers={"WWW-Authenticate": "Bearer"})
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


def http_app(server: FastMCP, settings: TransportSettings):
    hosts = settings.mcp_allowed_hosts
    if not hosts:
        hosts = ["127.0.0.1", "localhost", "[::1]", "127.0.0.1:*", "localhost:*", "[::1]:*"]
    server.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
        allowed_origins=settings.mcp_allowed_origins,
    )
    app = server.streamable_http_app()
    if settings.mcp_bearer_token is not None:
        app.add_middleware(RequireBearer, token=settings.mcp_bearer_token)
    return app


def run_transport(server: FastMCP, settings: TransportSettings) -> None:
    if settings.transport == "stdio":
        server.run(transport="stdio")
        return
    uvicorn.run(
        http_app(server, settings), host=settings.mcp_host, port=settings.mcp_port,
        ssl_certfile=str(settings.mcp_tls_cert) if settings.mcp_tls_cert else None,
        ssl_keyfile=str(settings.mcp_tls_key) if settings.mcp_tls_key else None,
        proxy_headers=False, access_log=False, log_level=server.settings.log_level.lower(),
    )
