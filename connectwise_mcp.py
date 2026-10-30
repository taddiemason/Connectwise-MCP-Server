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

import asyncio
import base64
import hmac
import json
import logging
import os
from typing import Any

import httpx
from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
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

# Retries. ConnectWise rate-limits, and a 429 mid-conversation currently looks
# to the model like the data does not exist rather than like a speed bump.
CW_MAX_RETRIES = int(os.getenv("CW_MAX_RETRIES", "3"))
CW_RETRY_BASE_DELAY = float(os.getenv("CW_RETRY_BASE_DELAY", "0.5"))
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

# Ceiling on fetchAll, so "every ticket" cannot turn into fifty thousand
# records and a rate-limit ban.
CW_MAX_RECORDS = int(os.getenv("CW_MAX_RECORDS", "1000"))

# Required before the HTTP transport will serve anything. Absent on stdio,
# where the trust boundary is the process rather than the network.
MCP_AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN")

# ---------------------------------------------------------------------------
# Writes
#
# Off unless switched on, per category, by name. Everything else in this file
# is read-only and stays that way for a deployment that does not opt in -- the
# write tools are not even registered, so a model cannot see them to try.
#
#   CW_ENABLE_WRITES=notes        ticket and company notes
#   CW_ENABLE_WRITES=notes,time   ...and time entries
#   CW_ENABLE_WRITES=all          ...and creating and updating tickets
#
# Granular rather than one boolean because the categories carry very different
# risk. A wrong note is embarrassing; a wrong ticket update changes what a
# technician sees as their work queue.
# ---------------------------------------------------------------------------
WRITE_CATEGORIES = frozenset({"notes", "time", "tickets"})
CW_ENABLE_WRITES = os.getenv("CW_ENABLE_WRITES", "")

# Log the request and return it without sending, for proving what a model would
# have done before letting it do it.
CW_WRITE_DRY_RUN = os.getenv("CW_WRITE_DRY_RUN", "").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)


class WritesDisabledError(RuntimeError):
    """A write tool was called while its category is switched off."""


def enabled_writes() -> frozenset[str]:
    """Which write categories are switched on. An empty set means read-only."""
    raw = (CW_ENABLE_WRITES or "").strip().lower()
    if not raw:
        return frozenset()
    if raw == "all":
        return WRITE_CATEGORIES

    asked = {part.strip() for part in raw.split(",") if part.strip()}
    known = asked & WRITE_CATEGORIES
    unknown = asked - WRITE_CATEGORIES
    if unknown:
        # Loudly: the likely cause is CW_ENABLE_WRITES=true, and silently
        # staying read-only would look like the setting had been ignored.
        logger.warning(
            "CW_ENABLE_WRITES: ignoring unrecognised %s. Use a comma-separated "
            "list of %s, or 'all'.",
            ", ".join(sorted(unknown)),
            ", ".join(sorted(WRITE_CATEGORIES)),
        )
    return frozenset(known)


def _require_write(category: str) -> None:
    """Second line of defence behind conditional registration."""
    if category not in enabled_writes():
        raise WritesDisabledError(
            f"Writes in the '{category}' category are disabled. Set "
            f"CW_ENABLE_WRITES to include '{category}' to allow this. "
            "This server is read-only by default."
        )


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
        return await self._request("GET", endpoint, params=params)

    async def post(self, endpoint: str, body: Any) -> Any:
        return await self._request("POST", endpoint, json=body)

    async def patch(self, endpoint: str, operations: list[dict]) -> Any:
        """
        ConnectWise PATCH is JSON Patch, not a partial object:

            [{"op": "replace", "path": "status/id", "value": 5}]

        Sending {"status": {"id": 5}} is accepted with a 200 and changes
        nothing, which is the worst possible failure -- it looks like it worked.
        """
        return await self._request("PATCH", endpoint, json=operations)

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        json: Any = None,
    ) -> Any:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        idempotent = method == "GET"

        if idempotent:
            logger.info("GET %s params=%s", url, params or {})
        else:
            # Writes are logged in full at INFO. If something changes a
            # customer's ticket, the transcript should say exactly what.
            logger.info("%s %s body=%s", method, url, json)

        attempt = 0
        while True:
            attempt += 1
            try:
                response = await self.client.request(
                    method, url, params=params, json=json
                )
            except httpx.HTTPError as e:
                # A transport error on a write is NOT safe to retry: the
                # request may well have reached ConnectWise and created the
                # record before the connection dropped, and a duplicate time
                # entry or a second note on a customer ticket is worse than an
                # error the caller can decide about.
                if not idempotent or attempt > CW_MAX_RETRIES:
                    raise ConnectWiseError(
                        f"{method} {endpoint} failed after {attempt} attempt(s): {e}"
                    ) from e
                await self._backoff(attempt, None)
                continue

            # Same reasoning for 5xx on a write -- a 500 does not mean nothing
            # happened. 429 is different: rejected before processing, so
            # retrying it cannot duplicate anything.
            retryable = (
                RETRYABLE_STATUS if idempotent else frozenset({429})
            )

            if response.status_code in retryable and attempt <= CW_MAX_RETRIES:
                logger.warning(
                    "ConnectWise %s on %s, retry %d of %d",
                    response.status_code,
                    endpoint,
                    attempt,
                    CW_MAX_RETRIES,
                )
                await self._backoff(attempt, response.headers.get("Retry-After"))
                continue

            if response.is_error:
                raise self._describe(endpoint, response, attempt)

            # A 204, or a 201 with no body, is a success with nothing to parse.
            if not response.content:
                return {"status": response.status_code, "endpoint": endpoint}

            try:
                return response.json()
            except ValueError as e:
                # A gateway returning an HTML error page with a 200 is not
                # unheard of, and json() blowing up mid-tool is unhelpful.
                raise ConnectWiseError(
                    f"ConnectWise returned non-JSON for {endpoint}: "
                    f"{response.text[:200]!r}"
                ) from e

    @staticmethod
    async def _backoff(attempt: int, retry_after: str | None) -> None:
        """Exponential, unless ConnectWise told us exactly how long to wait."""
        delay = CW_RETRY_BASE_DELAY * (2 ** (attempt - 1))
        if retry_after:
            try:
                delay = max(delay, float(retry_after))
            except ValueError:
                pass  # Retry-After can be an HTTP date; the default stands.
        await asyncio.sleep(delay)

    @staticmethod
    def _describe(
        endpoint: str, response: httpx.Response, attempts: int
    ) -> ConnectWiseError:
        """
        Turn a status code into something that says what to do about it.

        Never includes request headers -- those carry the API key, and a tool
        result goes straight into a model's context and a transcript.
        """
        status = response.status_code
        body = response.text[:300]

        if status in (401, 403):
            detail = (
                "authentication was rejected. Check CW_PUBLIC_KEY and "
                "CW_PRIVATE_KEY, that CW_COMPANY_ID matches the instance, and "
                "that the API member has read rights to this area"
            )
        elif status == 404:
            detail = "not found. The id may be wrong, or the record may be in a different ConnectWise instance"
        elif status == 429:
            detail = f"rate limited, still failing after {attempts} attempts. Reduce pageSize or slow the request rate"
        else:
            detail = "returned an unexpected status"

        # Status stays in the message even when the prose explains it -- it is
        # what anyone reading a transcript or a log will search for.
        return ConnectWiseError(
            f"ConnectWise {endpoint} [{status}]: {detail}. Body: {body}"
        )

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
    fetchAll: bool = False,
) -> Any:
    """
    One page, or every page when fetchAll is set.

    Without fetchAll, a query matching 400 tickets returns 25 of them and says
    nothing about the other 375 -- which reads to a model as "there are 25",
    and that is a wrong answer rather than a partial one.

    The return stays a bare array either way. Wrapping it in {items, total}
    would be more informative and would also silently break every caller of
    /v1/tools/execute, which indexes the array directly.
    """
    client = get_client()
    if not fetchAll:
        return await client.get(
            endpoint, params=_params(conditions, orderBy, page, pageSize)
        )

    size = pageSize or 25
    current = page or 1
    collected: list[Any] = []

    while len(collected) < CW_MAX_RECORDS:
        batch = await client.get(
            endpoint, params=_params(conditions, orderBy, current, size)
        )
        # A detail endpoint handed fetchAll returns an object; nothing to page.
        if not isinstance(batch, list):
            return batch

        collected.extend(batch)
        if len(batch) < size:
            break  # short page means that was the last one
        current += 1

    if len(collected) >= CW_MAX_RECORDS:
        logger.warning(
            "fetchAll on %s hit the %d record cap; results are truncated",
            endpoint,
            CW_MAX_RECORDS,
        )
    return collected[:CW_MAX_RECORDS]


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
    fetchAll: bool = False,
) -> Any:
    return await _search("company/companies", conditions, orderBy, page, pageSize, fetchAll)


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
    fetchAll: bool = False,
) -> Any:
    return await _search(
        f"company/companies/{company_id}/sites", conditions, orderBy, page, pageSize, fetchAll
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
    fetchAll: bool = False,
) -> Any:
    return await _search("company/companies/types", conditions, orderBy, page, pageSize, fetchAll)


@mcp.tool(
    name="connectwise_get_company_statuses",
    description="Get all company statuses for tracking company state",
)
async def get_company_statuses(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search(
        "company/companies/statuses", conditions, orderBy, page, pageSize, fetchAll
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
    fetchAll: bool = False,
) -> Any:
    return await _search("service/tickets", conditions, orderBy, page, pageSize, fetchAll)


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
    fetchAll: bool = False,
) -> Any:
    return await _search(
        f"service/tickets/{ticket_id}/tasks", conditions, orderBy, page, pageSize, fetchAll
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
    fetchAll: bool = False,
) -> Any:
    return await _search(
        f"service/tickets/{ticket_id}/scheduleentries",
        conditions,
        orderBy,
        page,
        pageSize,
        fetchAll,
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
    fetchAll: bool = False,
) -> Any:
    return await _search("service/priorities", conditions, orderBy, page, pageSize, fetchAll)


@mcp.tool(
    name="connectwise_get_ticket_sources",
    description="Get all ticket sources for tracking how tickets are created",
)
async def get_ticket_sources(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search("service/sources", conditions, orderBy, page, pageSize, fetchAll)


@mcp.tool(
    name="connectwise_get_service_boards",
    description="Get all service boards for organizing tickets",
)
async def get_service_boards(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search("service/boards", conditions, orderBy, page, pageSize, fetchAll)


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
    fetchAll: bool = False,
) -> Any:
    return await _search(
        f"service/boards/{board_id}/statuses", conditions, orderBy, page, pageSize, fetchAll
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
    fetchAll: bool = False,
) -> Any:
    return await _search("company/contacts", conditions, orderBy, page, pageSize, fetchAll)


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
    fetchAll: bool = False,
) -> Any:
    return await _search("company/contacts/types", conditions, orderBy, page, pageSize, fetchAll)


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
    fetchAll: bool = False,
) -> Any:
    return await _search("sales/opportunities", conditions, orderBy, page, pageSize, fetchAll)


@mcp.tool(
    name="connectwise_get_activities",
    description="Search and retrieve activities. Supports filtering with conditions.",
)
async def get_activities(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search("sales/activities", conditions, orderBy, page, pageSize, fetchAll)


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
    fetchAll: bool = False,
) -> Any:
    return await _search("finance/agreements", conditions, orderBy, page, pageSize, fetchAll)


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
    fetchAll: bool = False,
) -> Any:
    return await _search(
        f"finance/agreements/{agreement_id}/additions",
        conditions,
        orderBy,
        page,
        pageSize,
        fetchAll,
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
    fetchAll: bool = False,
) -> Any:
    return await _search("finance/invoices", conditions, orderBy, page, pageSize, fetchAll)


@mcp.tool(
    name="connectwise_get_billing_cycles",
    description="Get all billing cycles for recurring billing",
)
async def get_billing_cycles(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search("finance/billingCycles", conditions, orderBy, page, pageSize, fetchAll)


@mcp.tool(
    name="connectwise_get_expense_entries",
    description="Search and retrieve expense entries. Supports filtering with conditions.",
)
async def get_expense_entries(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search("expense/entries", conditions, orderBy, page, pageSize, fetchAll)


@mcp.tool(
    name="connectwise_get_time_entries",
    description="Search and retrieve time entries. Supports filtering with conditions.",
)
async def get_time_entries(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search("time/entries", conditions, orderBy, page, pageSize, fetchAll)


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
    fetchAll: bool = False,
) -> Any:
    return await _search("project/projects", conditions, orderBy, page, pageSize, fetchAll)


@mcp.tool(
    name="connectwise_get_members",
    description="Search and retrieve team members. Supports filtering with conditions.",
)
async def get_members(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search("system/members", conditions, orderBy, page, pageSize, fetchAll)


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
    fetchAll: bool = False,
) -> Any:
    return await _search("company/configurations", conditions, orderBy, page, pageSize, fetchAll)


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
    fetchAll: bool = False,
) -> Any:
    return await _search(
        "company/configurations/types", conditions, orderBy, page, pageSize, fetchAll
    )


# ---------------------------------------------------------------------------
# Stage 4 additions.
#
# Paths here were taken from the ConnectWiseManageAPI PowerShell module rather
# than guessed, because several are not what you would assume: SLAs is
# capitalised, product types live at /procurement/types rather than
# /procurement/producttypes, note types at /company/noteTypes, and project team
# members at /teamMembers. A wrong path is a tool that 404s on a live instance
# and nowhere else, since none of this can be verified against mocks.
# ---------------------------------------------------------------------------

# --- Documents -------------------------------------------------------------


@mcp.tool(
    name="connectwise_get_documents",
    description=(
        "List documents and attachments linked to a record. recordType is the "
        "kind of record, e.g. Ticket, Company, Contact, Opportunity, Project, "
        "Agreement, Configuration; recordId is its id. Returns metadata only, "
        "not file contents."
    ),
)
async def get_documents(
    recordType: str,
    recordId: int,
    page: int | None = None,
    pageSize: int = 25,
) -> Any:
    # Both are mandatory: /system/documents without them is a 400, not a list
    # of every document in the instance.
    params: dict[str, Any] = {"recordType": recordType, "recordId": recordId}
    if page is not None:
        params["page"] = page
    params["pageSize"] = pageSize
    return await get_client().get("system/documents", params=params)


# --- Scheduling and SLAs ---------------------------------------------------


@mcp.tool(
    name="connectwise_get_schedule_entries",
    description=(
        "Search scheduled work across the business. Filter by member, date or "
        "object with conditions, e.g. member/identifier=\"jsmith\"."
    ),
)
async def get_schedule_entries(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search("schedule/entries", conditions, orderBy, page, pageSize, fetchAll)


@mcp.tool(
    name="connectwise_get_slas",
    description="Get service level agreements and their response/resolution targets",
)
async def get_slas(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    # Capital SLAs -- ConnectWise is case-sensitive here.
    return await _search("service/SLAs", conditions, orderBy, page, pageSize, fetchAll)


# --- Notes -----------------------------------------------------------------


@mcp.tool(
    name="connectwise_get_company_notes",
    description="Get notes recorded against a specific company",
)
async def get_company_notes(
    company_id: int,
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search(
        f"company/companies/{company_id}/notes", conditions, orderBy, page, pageSize, fetchAll
    )


@mcp.tool(
    name="connectwise_get_contact_notes",
    description="Get notes recorded against a specific contact",
)
async def get_contact_notes(
    contact_id: int,
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search(
        f"company/contacts/{contact_id}/notes", conditions, orderBy, page, pageSize, fetchAll
    )


@mcp.tool(
    name="connectwise_get_company_note_types",
    description="Get all company note types",
)
async def get_company_note_types(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search("company/noteTypes", conditions, orderBy, page, pageSize, fetchAll)


@mcp.tool(
    name="connectwise_get_company_teams",
    description="Get the team members assigned to a specific company",
)
async def get_company_teams(
    company_id: int,
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search(
        f"company/companies/{company_id}/teams", conditions, orderBy, page, pageSize, fetchAll
    )


# --- Service desk detail ---------------------------------------------------


@mcp.tool(
    name="connectwise_get_ticket_configurations",
    description=(
        "Get the IT configurations/assets attached to a specific ticket -- "
        "which machines a problem is actually about"
    ),
)
async def get_ticket_configurations(
    ticket_id: int,
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search(
        f"service/tickets/{ticket_id}/configurations", conditions, orderBy, page, pageSize, fetchAll
    )


@mcp.tool(
    name="connectwise_get_board_teams",
    description="Get the teams defined on a specific service board",
)
async def get_board_teams(
    board_id: int,
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search(
        f"service/boards/{board_id}/teams", conditions, orderBy, page, pageSize, fetchAll
    )


@mcp.tool(
    name="connectwise_get_board_types",
    description="Get the ticket types defined on a specific service board",
)
async def get_board_types(
    board_id: int,
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search(
        f"service/boards/{board_id}/types", conditions, orderBy, page, pageSize, fetchAll
    )


@mcp.tool(
    name="connectwise_get_board_subtypes",
    description="Get the ticket subtypes defined on a specific service board",
)
async def get_board_subtypes(
    board_id: int,
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search(
        f"service/boards/{board_id}/subtypes", conditions, orderBy, page, pageSize, fetchAll
    )


# --- Procurement -----------------------------------------------------------


@mcp.tool(
    name="connectwise_get_purchase_orders",
    description="Search purchase orders. Supports filtering with conditions.",
)
async def get_purchase_orders(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search(
        "procurement/purchaseorders", conditions, orderBy, page, pageSize, fetchAll
    )


@mcp.tool(
    name="connectwise_get_purchase_order_line_items",
    description="Get the line items on a specific purchase order",
)
async def get_purchase_order_line_items(
    purchase_order_id: int,
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search(
        f"procurement/purchaseorders/{purchase_order_id}/lineitems",
        conditions,
        orderBy,
        page,
        pageSize,
        fetchAll,
    )


@mcp.tool(
    name="connectwise_get_product_catalog",
    description="Search the product catalog -- what can be sold, not what has been",
)
async def get_product_catalog(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search("procurement/catalog", conditions, orderBy, page, pageSize, fetchAll)


@mcp.tool(
    name="connectwise_get_products",
    description=(
        "Search product items actually sold -- those placed on tickets, "
        "projects, opportunities and agreements"
    ),
)
async def get_products(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search("procurement/products", conditions, orderBy, page, pageSize, fetchAll)


@mcp.tool(
    name="connectwise_get_manufacturers",
    description="Get all manufacturers used in the product catalog",
)
async def get_manufacturers(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search(
        "procurement/manufacturers", conditions, orderBy, page, pageSize, fetchAll
    )


@mcp.tool(
    name="connectwise_get_product_types",
    description="Get all product types for categorising the catalog",
)
async def get_product_types(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    # /procurement/types, not /procurement/producttypes.
    return await _search("procurement/types", conditions, orderBy, page, pageSize, fetchAll)


# --- Projects --------------------------------------------------------------


@mcp.tool(
    name="connectwise_get_project_tickets",
    description="Search project tickets. These are separate from service tickets.",
)
async def get_project_tickets(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search("project/tickets", conditions, orderBy, page, pageSize, fetchAll)


@mcp.tool(
    name="connectwise_get_project_phases",
    description="Get the phases of a specific project",
)
async def get_project_phases(
    project_id: int,
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search(
        f"project/projects/{project_id}/phases", conditions, orderBy, page, pageSize, fetchAll
    )


@mcp.tool(
    name="connectwise_get_project_team_members",
    description="Get the team members assigned to a specific project",
)
async def get_project_team_members(
    project_id: int,
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search(
        f"project/projects/{project_id}/teamMembers",
        conditions,
        orderBy,
        page,
        pageSize,
        fetchAll,
    )


# --- System ----------------------------------------------------------------


@mcp.tool(
    name="connectwise_get_departments",
    description="Get all departments for organising members",
)
async def get_departments(
    conditions: str | None = None,
    orderBy: str | None = None,
    page: int | None = None,
    pageSize: int = 25,
    fetchAll: bool = False,
) -> Any:
    return await _search("system/departments", conditions, orderBy, page, pageSize, fetchAll)


# ---------------------------------------------------------------------------
# Write tools
#
# Defined unconditionally so they are importable and testable, but REGISTERED
# only when their category is enabled -- a read-only deployment does not expose
# them in the tool list at all, so a model cannot see one to try. _require_write
# inside each is the second line of defence for a direct call.
#
# Every one returns what ConnectWise created or changed, so the result in the
# transcript is the record rather than "ok".
# ---------------------------------------------------------------------------


async def _write(category: str, verb: str, endpoint: str, payload: Any) -> Any:
    """Shared gate, dry-run and dispatch for every write."""
    _require_write(category)

    if CW_WRITE_DRY_RUN:
        logger.warning("DRY RUN, not sent: %s %s %s", verb, endpoint, payload)
        return {
            "dryRun": True,
            "wouldSend": {"method": verb, "endpoint": endpoint, "body": payload},
        }

    client = get_client()
    if verb == "POST":
        return await client.post(endpoint, payload)
    return await client.patch(endpoint, payload)


# --- notes -----------------------------------------------------------------


async def add_ticket_note(
    ticket_id: int,
    text: str,
    internal: bool = True,
    resolution: bool = False,
) -> Any:
    """
    Add a note to a service ticket.

    internal defaults to True so a note goes to internal analysis rather than
    the customer-visible description. An AI-written note appearing in a
    client's ticket feed unannounced is the kind of surprise worth opting into
    rather than out of.
    """
    body = {
        "text": text,
        "detailDescriptionFlag": not internal and not resolution,
        "internalAnalysisFlag": internal,
        "resolutionFlag": resolution,
    }
    return await _write("notes", "POST", f"service/tickets/{ticket_id}/notes", body)


async def add_company_note(company_id: int, text: str) -> Any:
    """Add a note to a company record."""
    return await _write(
        "notes", "POST", f"company/companies/{company_id}/notes", {"text": text}
    )


# --- time ------------------------------------------------------------------


async def create_time_entry(
    ticket_id: int,
    actual_hours: float,
    notes: str,
    member_identifier: str | None = None,
    billable_option: str = "Billable",
    time_start: str | None = None,
) -> Any:
    """
    Log time against a service ticket.

    billable_option is one of Billable, DoNotBill, NoCharge, NoDefault.
    member_identifier defaults to the API member if omitted, which is rarely
    what you want -- time should usually be logged against the person who did
    the work, not the integration account.
    """
    body: dict[str, Any] = {
        "chargeToId": ticket_id,
        "chargeToType": "ServiceTicket",
        "actualHours": actual_hours,
        "notes": notes,
        "billableOption": billable_option,
    }
    if member_identifier:
        body["member"] = {"identifier": member_identifier}
    if time_start:
        body["timeStart"] = time_start
    return await _write("time", "POST", "time/entries", body)


# --- tickets ---------------------------------------------------------------


async def create_ticket(
    summary: str,
    company_id: int,
    board_id: int,
    initial_description: str | None = None,
    contact_id: int | None = None,
    priority_id: int | None = None,
) -> Any:
    """
    Create a service ticket.

    summary is the ticket title and is what a technician sees in a queue.
    board_id decides whose queue -- get it from connectwise_get_service_boards.
    """
    body: dict[str, Any] = {
        "summary": summary,
        "company": {"id": company_id},
        "board": {"id": board_id},
    }
    if initial_description:
        body["initialDescription"] = initial_description
    if contact_id:
        body["contact"] = {"id": contact_id}
    if priority_id:
        body["priority"] = {"id": priority_id}
    return await _write("tickets", "POST", "service/tickets", body)


async def update_ticket(
    ticket_id: int,
    path: str,
    value: Any,
    operation: str = "replace",
) -> Any:
    """
    Change one field on a ticket, via JSON Patch.

    path is a ConnectWise field path such as 'status/id', 'summary',
    'priority/id' or 'owner/identifier'. operation is replace, add or remove.

    Worth knowing before using this to close tickets: changing status is how
    work appears and disappears from a technician's queue, and a wrong status
    id is silently accepted.
    """
    if operation not in ("add", "replace", "remove"):
        raise ValueError(
            f"operation must be add, replace or remove, not {operation!r}"
        )
    ops = [{"op": operation, "path": path, "value": value}]
    return await _write("tickets", "PATCH", f"service/tickets/{ticket_id}", ops)


# Registration, by category. Nothing below runs for a read-only deployment.
_WRITE_TOOLS: dict[str, list[tuple[str, Any, str]]] = {
    "notes": [
        ("connectwise_add_ticket_note", add_ticket_note, "Add a note to a service ticket"),
        ("connectwise_add_company_note", add_company_note, "Add a note to a company record"),
    ],
    "time": [
        ("connectwise_create_time_entry", create_time_entry, "Log time against a service ticket"),
    ],
    "tickets": [
        ("connectwise_create_ticket", create_ticket, "Create a service ticket"),
        (
            "connectwise_update_ticket",
            update_ticket,
            "Change one field on a ticket via JSON Patch (path, value, operation)",
        ),
    ],
}


def register_write_tools() -> list[str]:
    """Register the enabled write tools. Returns the names registered."""
    active = enabled_writes()
    registered: list[str] = []
    for category, tools in _WRITE_TOOLS.items():
        if category not in active:
            continue
        for name, fn, description in tools:
            mcp.add_tool(mcp.tool(name=name, description=description)(fn))
            registered.append(name)

    if registered:
        logger.warning(
            "WRITES ENABLED (%s): %s. This server can now change ConnectWise data.",
            ", ".join(sorted(active)),
            ", ".join(registered),
        )
        if CW_WRITE_DRY_RUN:
            logger.warning("CW_WRITE_DRY_RUN is on: writes are logged, not sent.")
    return registered


register_write_tools()


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


class BearerTokenMiddleware(BaseHTTPMiddleware):
    """
    Requires `Authorization: Bearer <MCP_AUTH_TOKEN>` on every route but /health.

    The previous HTTP surface had no authentication at all: anything that could
    reach port 3002 could read every company, ticket, contact and agreement in
    the instance. For an MSP that is every client's data behind an open port on
    a flat network.

    /health stays open because the container healthcheck calls it and it
    reveals nothing -- a fixed status string, no instance detail.
    """

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        if request.url.path == "/health":
            return await call_next(request)

        presented = request.headers.get("authorization", "")
        expected = f"Bearer {MCP_AUTH_TOKEN}" if MCP_AUTH_TOKEN else None

        # compare_digest, not ==, so a wrong token cannot be narrowed down by
        # timing one character at a time.
        if not expected or not hmac.compare_digest(presented, expected):
            logger.warning("Rejected unauthenticated %s %s", request.method, request.url.path)
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        return await call_next(request)


def build_http_app(require_auth: bool = True):
    """The ASGI app as actually served. Auth is on unless a test turns it off."""
    middleware = [Middleware(BearerTokenMiddleware)] if require_auth else []
    return mcp.http_app(middleware=middleware)


def main() -> None:
    """stdio by default; MCP_TRANSPORT=http serves OpenWebUI and the REST routes."""
    transport = os.getenv("MCP_TRANSPORT", "stdio").lower()
    if transport in ("http", "streamable-http"):
        if not MCP_AUTH_TOKEN:
            # Refusing to start beats starting wide open. An HTTP endpoint
            # serving an entire ConnectWise instance should not be reachable
            # because somebody forgot a variable.
            raise SystemExit(
                "MCP_AUTH_TOKEN is required for the http transport. Generate one with\n"
                "    python -c \"import secrets; print(secrets.token_urlsafe(32))\"\n"
                "and set it in .env, then send it as 'Authorization: Bearer <token>'.\n"
                "The stdio transport does not need it."
            )

        import uvicorn

        port = int(os.getenv("MCP_PORT", "3002"))
        logger.info("Serving HTTP on 0.0.0.0:%s (bearer token required)", port)
        uvicorn.run(build_http_app(), host="0.0.0.0", port=port, log_level="info")
    else:
        # On stdio, stdout IS the JSON-RPC stream -- one stray print and the
        # client sees a protocol error instead of a server. Banner off
        # explicitly rather than relying on the framework defaulting it to
        # stderr. Logging already goes to stderr via basicConfig.
        mcp.run(show_banner=False)


if __name__ == "__main__":
    main()
