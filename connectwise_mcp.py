"""
ConnectWise MCP Server - read-only access to ConnectWise Manage.

Serves two transports from one process:

    stdio  -- for MCP clients such as Claude Code and Claude Desktop
    http   -- for OpenWebUI, including a /v1/tools/execute compatibility
              route so tools written against the old Node bridge keep working

There used to be a separate Node bridge that spawned a fresh Python process per
request and sent it a bare tools/call with no MCP initialize handshake. FastMCP
serves HTTP itself, so the bridge, its Dockerfile and that whole class of problem
are gone.
"""
from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any

import httpx
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

CW_COMPANY_ID = os.getenv("CW_COMPANY_ID")
CW_PUBLIC_KEY = os.getenv("CW_PUBLIC_KEY")
CW_PRIVATE_KEY = os.getenv("CW_PRIVATE_KEY")
CW_API_URL = os.getenv("CW_API_URL", "https://api-na.myconnectwise.net")
CW_API_VERSION = os.getenv("CW_API_VERSION", "v2023.2")
CW_CLIENT_ID = os.getenv("CW_CLIENT_ID", "mcp-connectwise-server")


class ConnectWiseError(RuntimeError):
    """A ConnectWise API call failed. Carries the endpoint and status."""


class ConnectWiseClient:
    """Read-only client for the ConnectWise Manage REST API."""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        # transport is for tests: httpx.MockTransport stands in for ConnectWise so
        # the whole tool surface is exercisable with no credentials and no network.
        missing = [
            n
            for n, v in (
                ("CW_COMPANY_ID", CW_COMPANY_ID),
                ("CW_PUBLIC_KEY", CW_PUBLIC_KEY),
                ("CW_PRIVATE_KEY", CW_PRIVATE_KEY),
            )
            if not v
        ]
        if missing:
            raise ConnectWiseError(
                "ConnectWise credentials are not configured: missing "
                + ", ".join(missing)
                + ". Set them in .env or the environment."
            )

        self.base_url = f"{CW_API_URL}/{CW_API_VERSION}/apis/3.0"

        auth = base64.b64encode(
            f"{CW_COMPANY_ID}+{CW_PUBLIC_KEY}:{CW_PRIVATE_KEY}".encode("ascii")
        ).decode("ascii")

        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/json",
                "clientId": CW_CLIENT_ID,
                "Accept": "application/json",
            },
            timeout=30.0,
            transport=transport,
        )
        logger.info("ConnectWise client initialised for company: %s", CW_COMPANY_ID)

    async def get(self, endpoint: str, params: dict | None = None) -> Any:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        logger.info("GET %s params=%s", url, params or {})
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # The endpoint and status, not the request headers -- those carry the
            # API key and have no business in a log or a tool result.
            body = e.response.text[:400]
            raise ConnectWiseError(
                f"ConnectWise returned {e.response.status_code} for {endpoint}: {body}"
            ) from e
        except httpx.HTTPError as e:
            raise ConnectWiseError(f"Request to {endpoint} failed: {e}") from e

    async def aclose(self) -> None:
        await self.client.aclose()


_client: ConnectWiseClient | None = None


def get_client() -> ConnectWiseClient:
    """
    The shared client, built on first use.

    Lazy on purpose. Constructing it at import time meant the module could not be
    imported at all without live credentials -- so the tool list could not be
    inspected, and nothing could be tested without keys.
    """
    global _client
    if _client is None:
        _client = ConnectWiseClient()
    return _client


mcp = FastMCP(
    name="connectwise",
    instructions=(
        "Read-only access to ConnectWise Manage: companies, service tickets, "
        "contacts, agreements, time entries, projects, IT configurations, "
        "invoices and the reference data behind them. Collection tools accept "
        "ConnectWise condition syntax, for example: "
        'status/name="New" and company/identifier="ACME"'
    ),
)


def _params(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int | None = None,
) -> dict:
    """Query string for a collection endpoint, omitting anything unset."""
    params: dict[str, Any] = {}
    if conditions:
        params["conditions"] = conditions
    if orderBy:
        params["orderBy"] = orderBy
    if page is not None:
        params["page"] = page
    if pageSize is not None:
        params["pageSize"] = pageSize
    return params


async def _search(
    endpoint: str,
    conditions: str | None,
    orderBy: str | None,
    page: int | None,
    pageSize: int | None,
) -> Any:
    return await get_client().get(
        endpoint, params=_params(conditions, orderBy, page, pageSize)
    )


# ---------------------------------------------------------------------------
# Tools
#
# Parameter names are camelCase (orderBy, pageSize) rather than Python style
# because FastMCP derives the input schema from the signature, and these names
# are the tool's public contract -- connectwise_tools.py and any existing
# OpenWebUI setup already send them. Renaming them would be a breaking change
# dressed up as a tidy-up.
# ---------------------------------------------------------------------------

# --- Companies -------------------------------------------------------------


@mcp.tool(
    name="connectwise_get_companies",
    description="Search and retrieve companies. Supports filtering with conditions.",
)
async def get_companies(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    return await _search("company/companies", conditions, orderBy, page, pageSize)


@mcp.tool(
    name="connectwise_get_company",
    description="Get a specific company by ID",
)
async def get_company(company_id: int) -> Any:
    return await get_client().get(f"company/companies/{company_id}")


@mcp.tool(
    name="connectwise_get_company_sites",
    description="Get sites/locations for a specific company",
)
async def get_company_sites(
    company_id: int,
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    return await _search(
        f"company/companies/{company_id}/sites", conditions, orderBy, page, pageSize
    )


@mcp.tool(
    name="connectwise_get_company_types",
    description="Get all company types for categorizing companies",
)
async def get_company_types(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    return await _search("company/companies/types", conditions, orderBy, page, pageSize)


@mcp.tool(
    name="connectwise_get_company_statuses",
    description="Get all company statuses for tracking company state",
)
async def get_company_statuses(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    return await _search(
        "company/companies/statuses", conditions, orderBy, page, pageSize
    )


# --- Service tickets -------------------------------------------------------


@mcp.tool(
    name="connectwise_get_tickets",
    description="Search and retrieve service tickets. Supports filtering with conditions.",
)
async def get_tickets(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    return await _search("service/tickets", conditions, orderBy, page, pageSize)


@mcp.tool(
    name="connectwise_get_ticket",
    description="Get a specific ticket by ID with full details",
)
async def get_ticket(ticket_id: int) -> Any:
    return await get_client().get(f"service/tickets/{ticket_id}")


@mcp.tool(
    name="connectwise_get_ticket_notes",
    description="Get notes for a specific ticket",
)
async def get_ticket_notes(ticket_id: int, pageSize: int = 25) -> Any:
    return await get_client().get(
        f"service/tickets/{ticket_id}/notes", params={"pageSize": pageSize}
    )


@mcp.tool(
    name="connectwise_get_ticket_tasks",
    description="Get tasks/checklist items for a specific ticket",
)
async def get_ticket_tasks(
    ticket_id: int,
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    return await _search(
        f"service/tickets/{ticket_id}/tasks", conditions, orderBy, page, pageSize
    )


@mcp.tool(
    name="connectwise_get_ticket_schedules",
    description="Get schedule entries for a specific ticket",
)
async def get_ticket_schedules(
    ticket_id: int,
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    return await _search(
        f"service/tickets/{ticket_id}/scheduleentries",
        conditions,
        orderBy,
        page,
        pageSize,
    )


@mcp.tool(
    name="connectwise_get_ticket_priorities",
    description="Get all ticket priorities for categorizing urgency",
)
async def get_ticket_priorities(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    return await _search("service/priorities", conditions, orderBy, page, pageSize)


@mcp.tool(
    name="connectwise_get_ticket_sources",
    description="Get all ticket sources for tracking how tickets are created",
)
async def get_ticket_sources(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    return await _search("service/sources", conditions, orderBy, page, pageSize)


@mcp.tool(
    name="connectwise_get_service_boards",
    description="Get all service boards for organizing tickets",
)
async def get_service_boards(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    return await _search("service/boards", conditions, orderBy, page, pageSize)


@mcp.tool(
    name="connectwise_get_board_statuses",
    description="Get all statuses for a specific service board",
)
async def get_board_statuses(
    board_id: int,
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    return await _search(
        f"service/boards/{board_id}/statuses", conditions, orderBy, page, pageSize
    )


# --- Contacts --------------------------------------------------------------


@mcp.tool(
    name="connectwise_get_contacts",
    description="Search and retrieve contacts. Supports filtering with conditions.",
)
async def get_contacts(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    return await _search("company/contacts", conditions, orderBy, page, pageSize)


@mcp.tool(
    name="connectwise_get_contact",
    description="Get a specific contact by ID",
)
async def get_contact(contact_id: int) -> Any:
    return await get_client().get(f"company/contacts/{contact_id}")


@mcp.tool(
    name="connectwise_get_contact_types",
    description="Get all contact types for categorizing contacts",
)
async def get_contact_types(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    return await _search("company/contacts/types", conditions, orderBy, page, pageSize)


# --- Sales -----------------------------------------------------------------


@mcp.tool(
    name="connectwise_get_opportunities",
    description="Search and retrieve sales opportunities. Supports filtering with conditions.",
)
async def get_opportunities(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    return await _search("sales/opportunities", conditions, orderBy, page, pageSize)


@mcp.tool(
    name="connectwise_get_activities",
    description="Search and retrieve activities. Supports filtering with conditions.",
)
async def get_activities(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    return await _search("sales/activities", conditions, orderBy, page, pageSize)


# --- Agreements, finance and time ------------------------------------------


@mcp.tool(
    name="connectwise_get_agreements",
    description="Search and retrieve agreements/contracts. Supports filtering with conditions.",
)
async def get_agreements(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    return await _search("finance/agreements", conditions, orderBy, page, pageSize)


@mcp.tool(
    name="connectwise_get_agreement_additions",
    description="Get additions/add-ons for a specific agreement",
)
async def get_agreement_additions(
    agreement_id: int,
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    return await _search(
        f"finance/agreements/{agreement_id}/additions",
        conditions,
        orderBy,
        page,
        pageSize,
    )


@mcp.tool(
    name="connectwise_get_invoices",
    description="Search and retrieve invoices. Supports filtering with conditions.",
)
async def get_invoices(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    return await _search("finance/invoices", conditions, orderBy, page, pageSize)


@mcp.tool(
    name="connectwise_get_billing_cycles",
    description="Get all billing cycles for recurring billing",
)
async def get_billing_cycles(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    return await _search("finance/billingCycles", conditions, orderBy, page, pageSize)


@mcp.tool(
    name="connectwise_get_expense_entries",
    description="Search and retrieve expense entries. Supports filtering with conditions.",
)
async def get_expense_entries(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    return await _search("expense/entries", conditions, orderBy, page, pageSize)


@mcp.tool(
    name="connectwise_get_time_entries",
    description="Search and retrieve time entries. Supports filtering with conditions.",
)
async def get_time_entries(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    return await _search("time/entries", conditions, orderBy, page, pageSize)


# --- Projects and people ---------------------------------------------------


@mcp.tool(
    name="connectwise_get_projects",
    description="Search and retrieve projects. Supports filtering with conditions.",
)
async def get_projects(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    return await _search("project/projects", conditions, orderBy, page, pageSize)


@mcp.tool(
    name="connectwise_get_members",
    description="Search and retrieve team members. Supports filtering with conditions.",
)
async def get_members(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    return await _search("system/members", conditions, orderBy, page, pageSize)


# --- IT asset management ---------------------------------------------------


@mcp.tool(
    name="connectwise_get_configurations",
    description="Search and retrieve IT configurations/assets. Supports filtering with conditions.",
)
async def get_configurations(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    return await _search("company/configurations", conditions, orderBy, page, pageSize)


@mcp.tool(
    name="connectwise_get_configuration",
    description="Get a specific configuration/asset by ID",
)
async def get_configuration(configuration_id: int) -> Any:
    return await get_client().get(f"company/configurations/{configuration_id}")


@mcp.tool(
    name="connectwise_get_configuration_types",
    description="Get all configuration types for categorizing IT assets",
)
async def get_configuration_types(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    return await _search(
        "company/configurations/types", conditions, orderBy, page, pageSize
    )


# ---------------------------------------------------------------------------
# HTTP compatibility routes
#
# The Node bridge is gone, but connectwise_tools.py and any OpenWebUI install
# already point at these two paths. Serving them from the same process keeps
# those working without a second container, a second language, or a Python
# process spawned per request.
# ---------------------------------------------------------------------------


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "connectwise-mcp"})


@mcp.custom_route("/v1/tools/execute", methods=["POST"])
async def execute_tool(request: Request) -> JSONResponse:
    """Flat REST shape the old bridge exposed: {tool_name, arguments} -> result."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Body must be JSON"}, status_code=400)

    tool_name = body.get("tool_name")
    if not tool_name:
        return JSONResponse({"error": "tool_name is required"}, status_code=400)

    try:
        result = await mcp.call_tool(tool_name, body.get("arguments") or {})
    except Exception as e:
        logger.error("Tool %s failed: %s", tool_name, e)
        return JSONResponse({"error": str(e)}, status_code=500)

    # Shape matters: the old bridge JSON.parse'd the text block and returned the
    # result directly, so a collection came back as a bare array. Anything built
    # against it -- connectwise_tools.py included -- indexes that array. Wrapping
    # it in {"data": ...} would be a silent breaking change, so parse first and
    # only wrap when the payload genuinely is not JSON.
    blocks = getattr(result, "content", None) or []
    text = next((b.text for b in blocks if getattr(b, "type", None) == "text"), None)
    if text is not None:
        try:
            return JSONResponse(json.loads(text))
        except (TypeError, ValueError):
            return JSONResponse({"data": text})

    structured = getattr(result, "structured_content", None)
    return JSONResponse(structured if structured is not None else {})


def main() -> None:
    """stdio by default; MCP_TRANSPORT=http serves OpenWebUI and the REST routes."""
    transport = os.getenv("MCP_TRANSPORT", "stdio").lower()
    if transport in ("http", "streamable-http"):
        port = int(os.getenv("MCP_PORT", "3002"))
        logger.info("Serving HTTP on 0.0.0.0:%s", port)
        mcp.run(transport="http", host="0.0.0.0", port=port)
    else:
        # On stdio, stdout IS the JSON-RPC stream -- one stray print and the
        # client sees a protocol error instead of a server. Banner off
        # explicitly rather than relying on the framework defaulting it to
        # stderr. Logging already goes to stderr via basicConfig.
        mcp.run(show_banner=False)


if __name__ == "__main__":
    main()
