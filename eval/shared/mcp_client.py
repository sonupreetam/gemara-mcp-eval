"""
Shared MCP client for gemara-mcp evaluation harnesses.

Provides an async context manager that connects to the gemara-mcp server
via stdio transport (spawning a Docker container) and exposes typed methods
for calling tools, reading resources, and retrieving prompts.

Environment variables:
    GEMARA_MCP_IMAGE   Docker image (default: ghcr.io/gemaraproj/gemara-mcp:v0.1.0)
    GEMARA_MCP_MODE    Server mode (default: artifact)
    CONTAINER_RUNTIME  Container runtime binary (default: docker)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from mcp import ClientSession, StdioServerParameters, stdio_client

DEFAULT_IMAGE = "ghcr.io/gemaraproj/gemara-mcp:v0.1.0"
DEFAULT_MODE = "artifact"
DEFAULT_RUNTIME = "docker"


@dataclass
class MCPResponse:
    """Wrapper for an MCP tool call result."""

    content: list[dict[str, Any]]
    is_error: bool = False

    @property
    def text(self) -> str:
        """Return concatenated text content."""
        parts = []
        for item in self.content:
            if isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
            elif hasattr(item, "text"):
                parts.append(item.text)
        return "\n".join(parts)

    @property
    def json(self) -> Any:
        """Parse the first text content block as JSON."""
        return json.loads(self.text)


@dataclass
class PromptResponse:
    """Wrapper for an MCP prompt result."""

    description: str | None
    messages: list[dict[str, Any]]

    @property
    def text(self) -> str:
        """Return concatenated message content."""
        parts = []
        for msg in self.messages:
            content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
            if isinstance(content, str):
                parts.append(content)
            elif hasattr(content, "text"):
                parts.append(content.text)
            elif isinstance(content, dict) and "text" in content:
                parts.append(content["text"])
        return "\n".join(parts)


class GemaraMCPClient:
    """
    Async context manager wrapping an MCP stdio session to gemara-mcp.

    Usage::

        async with GemaraMCPClient() as client:
            result = await client.call_tool("validate_gemara_artifact", {
                "artifact_content": yaml_text,
                "definition": "#ControlCatalog",
            })
            print(result.json)
    """

    def __init__(
        self,
        image: str | None = None,
        mode: str | None = None,
        runtime: str | None = None,
    ):
        self._image = image or os.environ.get("GEMARA_MCP_IMAGE", DEFAULT_IMAGE)
        self._mode = mode or os.environ.get("GEMARA_MCP_MODE", DEFAULT_MODE)
        self._runtime = runtime or os.environ.get("CONTAINER_RUNTIME", DEFAULT_RUNTIME)
        self._session: ClientSession | None = None
        self._cm_stack: list[Any] = []

    def _server_params(self) -> StdioServerParameters:
        return StdioServerParameters(
            command=self._runtime,
            args=[
                "run", "--rm", "-i",
                self._image,
                "serve", "--mode", self._mode,
            ],
        )

    async def __aenter__(self) -> GemaraMCPClient:
        params = self._server_params()
        self._stdio_cm = stdio_client(params, errlog=sys.stderr)
        read, write = await self._stdio_cm.__aenter__()
        self._session_cm = ClientSession(read, write)
        self._session = await self._session_cm.__aenter__()
        await self._session.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session_cm:
            await self._session_cm.__aexit__(exc_type, exc_val, exc_tb)
        if self._stdio_cm:
            await self._stdio_cm.__aexit__(exc_type, exc_val, exc_tb)
        self._session = None

    @property
    def session(self) -> ClientSession:
        if self._session is None:
            raise RuntimeError("MCP client not connected; use 'async with GemaraMCPClient() as client:'")
        return self._session

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> MCPResponse:
        result = await self.session.call_tool(name, arguments)
        content = []
        for item in result.content:
            if hasattr(item, "model_dump"):
                content.append(item.model_dump())
            elif isinstance(item, dict):
                content.append(item)
            else:
                content.append({"type": "text", "text": str(item)})
        return MCPResponse(content=content, is_error=bool(result.isError))

    async def read_resource(self, uri: str) -> str:
        result = await self.session.read_resource(uri)
        parts = []
        for item in result.contents:
            if hasattr(item, "text"):
                parts.append(item.text)
            elif isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
        return "\n".join(parts)

    async def get_prompt(self, name: str, arguments: dict[str, str] | None = None) -> PromptResponse:
        result = await self.session.get_prompt(name, arguments)
        messages = []
        for msg in result.messages:
            if hasattr(msg, "model_dump"):
                messages.append(msg.model_dump())
            elif isinstance(msg, dict):
                messages.append(msg)
        return PromptResponse(
            description=getattr(result, "description", None),
            messages=messages,
        )

    async def list_tools(self) -> list[dict[str, Any]]:
        result = await self.session.list_tools()
        return [t.model_dump() if hasattr(t, "model_dump") else t for t in result.tools]


def run_sync(coro):
    """Run an async coroutine synchronously (for non-async harnesses)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)
