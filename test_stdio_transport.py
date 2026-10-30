"""
Stdio transport tests, run against a real subprocess.

Separate from the main suite because these spawn `python connectwise_mcp.py`
over real pipes, which is slower -- but it is the only way to catch the failure
that matters on stdio: stdout is the JSON-RPC stream, so anything printed to it
(a logging handler on the wrong stream, a startup banner, a stray print) breaks
the server for Claude Code and Claude Desktop while every in-memory test keeps
passing.
"""
from __future__ import annotations

import os
import sys

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

HERE = os.path.dirname(os.path.abspath(__file__))


def _env_without_credentials() -> dict[str, str]:
    env = dict(os.environ)
    for key in ("CW_COMPANY_ID", "CW_PUBLIC_KEY", "CW_PRIVATE_KEY"):
        env.pop(key, None)
    # Noisiest setting, to give anything mis-routed to stdout its best chance.
    env["LOG_LEVEL"] = "DEBUG"
    env["MCP_TRANSPORT"] = "stdio"
    return env


@pytest.fixture
def stdio_client() -> Client:
    return Client(
        StdioTransport(
            command=sys.executable,
            args=["connectwise_mcp.py"],
            env=_env_without_credentials(),
            cwd=HERE,
        )
    )


async def test_handshake_over_real_pipes(stdio_client: Client) -> None:
    """
    A successful handshake is itself the proof that stdout carries nothing but
    JSON-RPC: the client would fail to parse the stream otherwise.
    """
    async with stdio_client as c:
        tools = await c.list_tools()
    assert len(tools) == 30


async def test_tools_list_without_credentials(stdio_client: Client) -> None:
    """Claude Code lists tools before any are called, so this must not need keys."""
    async with stdio_client as c:
        names = {t.name for t in await c.list_tools()}
    assert "connectwise_get_tickets" in names


async def test_parameter_names_survive_the_wire(stdio_client: Client) -> None:
    """camelCase is the public contract; the schema has to carry it verbatim."""
    async with stdio_client as c:
        tools = await c.list_tools()
    tool = next(t for t in tools if t.name == "connectwise_get_tickets")
    # input_schema, not inputSchema -- the latter is deprecated in MCP SDK v2.
    schema = tool.input_schema
    assert set(schema["properties"]) == {
        "conditions",
        "orderBy",
        "page",
        "pageSize",
        "fetchAll",
    }


async def test_tool_error_does_not_kill_the_session(stdio_client: Client) -> None:
    """
    A missing-credentials error has to come back as a tool error and leave the
    session usable. A server that dies on the first bad call looks to Claude
    Code like the integration is broken rather than unconfigured.
    """
    async with stdio_client as c:
        with pytest.raises(Exception) as e:
            await c.call_tool("connectwise_get_tickets", {"pageSize": 1})
        assert "credentials" in str(e.value).lower()

        # Still alive and answering.
        assert len(await c.list_tools()) == 30
