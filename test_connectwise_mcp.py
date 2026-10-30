"""
Tests for the ConnectWise MCP server.

No credentials, no network. The point of most of these is the mapping from a
tool call to a ConnectWise endpoint and query string -- the part that is easy to
get subtly wrong and impossible to notice until a tool quietly returns the wrong
objects.
"""
from __future__ import annotations

import base64

import httpx
import pytest

import connectwise_mcp as cw

# No module-level asyncio mark: pytest.ini sets asyncio_mode = auto, which picks
# up async tests on its own and leaves the sync ones alone.

# 30 from the original read-only set, plus 21 added in Stage 4.
EXPECTED_TOOL_COUNT = 51


# --- the regression that started all of this -------------------------------


def test_module_imports_without_credentials() -> None:
    """
    The original built its ConnectWise client at module scope, so importing it
    without credentials raised and the tool list could not even be inspected.
    Separately, `mcp>=1.0.0` resolved to 2.x where the decorator API this was
    built on no longer exists, so import failed outright with
    AttributeError: 'Server' object has no attribute 'list_tools'.
    """
    import importlib

    importlib.reload(cw)
    assert cw.mcp is not None


async def test_every_tool_is_registered() -> None:
    """
    Hardcoded on purpose: this catches a tool silently dropped by a bad merge
    or a decorator lost in a refactor. Update it deliberately when adding one.
    """
    tools = await cw.mcp.list_tools()
    assert len(tools) == EXPECTED_TOOL_COUNT


async def test_tool_names_are_unchanged() -> None:
    """
    These names are the public contract -- OpenWebUI installs and the REST
    compatibility route call them by name. Renaming one is a breaking change.
    """
    names = {t.name for t in await cw.mcp.list_tools()}
    assert "connectwise_get_companies" in names
    assert "connectwise_get_ticket_schedules" in names
    assert all(n.startswith("connectwise_get_") for n in names)


def test_client_build_names_what_is_missing(no_credentials: None) -> None:
    with pytest.raises(cw.ConnectWiseError) as e:
        cw.get_client()
    message = str(e.value)
    assert "CW_COMPANY_ID" in message
    assert "CW_PUBLIC_KEY" in message


# --- auth ------------------------------------------------------------------


async def test_auth_header_is_company_plus_public_key(api) -> None:
    await cw.get_companies()
    expected = base64.b64encode(b"testco+pub:priv").decode()
    assert api.last.headers["authorization"] == f"Basic {expected}"


async def test_client_id_header_is_sent(api) -> None:
    """ConnectWise rejects requests without clientId, so this is not optional."""
    await cw.get_companies()
    assert api.last.headers["clientid"] == cw.CW_CLIENT_ID


# --- endpoint mapping ------------------------------------------------------


@pytest.mark.parametrize(
    "call, endpoint",
    [
        (lambda: cw.get_companies(), "company/companies"),
        (lambda: cw.get_tickets(), "service/tickets"),
        (lambda: cw.get_contacts(), "company/contacts"),
        (lambda: cw.get_opportunities(), "sales/opportunities"),
        (lambda: cw.get_activities(), "sales/activities"),
        (lambda: cw.get_agreements(), "finance/agreements"),
        (lambda: cw.get_invoices(), "finance/invoices"),
        (lambda: cw.get_billing_cycles(), "finance/billingCycles"),
        (lambda: cw.get_expense_entries(), "expense/entries"),
        (lambda: cw.get_time_entries(), "time/entries"),
        (lambda: cw.get_projects(), "project/projects"),
        (lambda: cw.get_members(), "system/members"),
        (lambda: cw.get_configurations(), "company/configurations"),
        (lambda: cw.get_configuration_types(), "company/configurations/types"),
        (lambda: cw.get_company_types(), "company/companies/types"),
        (lambda: cw.get_company_statuses(), "company/companies/statuses"),
        (lambda: cw.get_contact_types(), "company/contacts/types"),
        (lambda: cw.get_ticket_priorities(), "service/priorities"),
        (lambda: cw.get_ticket_sources(), "service/sources"),
        (lambda: cw.get_service_boards(), "service/boards"),
    ],
)
async def test_collection_endpoints(api, call, endpoint: str) -> None:
    await call()
    assert api.path == endpoint


@pytest.mark.parametrize(
    "call, endpoint",
    [
        (lambda: cw.get_company(42), "company/companies/42"),
        (lambda: cw.get_ticket(42), "service/tickets/42"),
        (lambda: cw.get_contact(42), "company/contacts/42"),
        (lambda: cw.get_configuration(42), "company/configurations/42"),
        (lambda: cw.get_ticket_notes(42), "service/tickets/42/notes"),
        (lambda: cw.get_ticket_tasks(42), "service/tickets/42/tasks"),
        (lambda: cw.get_ticket_schedules(42), "service/tickets/42/scheduleentries"),
        (lambda: cw.get_company_sites(42), "company/companies/42/sites"),
        (lambda: cw.get_board_statuses(42), "service/boards/42/statuses"),
        (lambda: cw.get_agreement_additions(42), "finance/agreements/42/additions"),
    ],
)
async def test_id_scoped_endpoints(api, call, endpoint: str) -> None:
    """The id has to land in the path, not the query string."""
    await call()
    assert api.path == endpoint


@pytest.mark.parametrize(
    "call, endpoint",
    [
        # Several of these are not what you would guess, which is why they were
        # taken from the ConnectWiseManageAPI module rather than invented. A
        # wrong path only shows up as a 404 against a live instance, and these
        # tests are the nearest thing to catching it before then.
        (lambda: cw.get_slas(), "service/SLAs"),  # capitalised
        (lambda: cw.get_product_types(), "procurement/types"),  # not producttypes
        (lambda: cw.get_company_note_types(), "company/noteTypes"),  # camelCase
        (lambda: cw.get_project_team_members(7), "project/projects/7/teamMembers"),
        (lambda: cw.get_schedule_entries(), "schedule/entries"),
        (lambda: cw.get_purchase_orders(), "procurement/purchaseorders"),
        (lambda: cw.get_purchase_order_line_items(3), "procurement/purchaseorders/3/lineitems"),
        (lambda: cw.get_product_catalog(), "procurement/catalog"),
        (lambda: cw.get_products(), "procurement/products"),
        (lambda: cw.get_manufacturers(), "procurement/manufacturers"),
        (lambda: cw.get_company_notes(5), "company/companies/5/notes"),
        (lambda: cw.get_contact_notes(5), "company/contacts/5/notes"),
        (lambda: cw.get_company_teams(5), "company/companies/5/teams"),
        (lambda: cw.get_ticket_configurations(9), "service/tickets/9/configurations"),
        (lambda: cw.get_board_teams(2), "service/boards/2/teams"),
        (lambda: cw.get_board_types(2), "service/boards/2/types"),
        (lambda: cw.get_board_subtypes(2), "service/boards/2/subtypes"),
        (lambda: cw.get_project_tickets(), "project/tickets"),
        (lambda: cw.get_project_phases(4), "project/projects/4/phases"),
        (lambda: cw.get_departments(), "system/departments"),
    ],
)
async def test_stage_four_endpoints(api, call, endpoint: str) -> None:
    await call()
    assert api.path == endpoint


async def test_documents_require_record_type_and_id(api) -> None:
    """
    /system/documents is entity-scoped: without both parameters ConnectWise
    returns 400 rather than a list, so they are required rather than optional.
    """
    await cw.get_documents(recordType="Ticket", recordId=1234)
    assert api.path == "system/documents"
    assert api.params["recordType"] == "Ticket"
    assert api.params["recordId"] == "1234"


# --- query parameters ------------------------------------------------------


async def test_conditions_and_ordering_pass_through(api) -> None:
    await cw.get_tickets(
        conditions='status/name="New"', orderBy="id desc", page=2, pageSize=5
    )
    assert api.params == {
        "conditions": 'status/name="New"',
        "orderBy": "id desc",
        "page": "2",
        "pageSize": "5",
    }


async def test_unset_parameters_are_omitted(api) -> None:
    """
    An empty conditions string must not be sent. ConnectWise treats an empty
    conditions parameter as a malformed filter rather than as 'no filter'.
    """
    await cw.get_tickets()
    assert set(api.params) == {"pageSize"}


async def test_page_zero_is_sent_not_dropped(api) -> None:
    """`if page:` would swallow 0; the check has to be against None."""
    await cw.get_tickets(page=0)
    assert api.params["page"] == "0"


# --- error paths -----------------------------------------------------------


@pytest.mark.parametrize("status", [400, 401, 404, 429, 500])
async def test_http_errors_name_the_endpoint_and_status(api, status: int) -> None:
    api.status = status
    with pytest.raises(cw.ConnectWiseError) as e:
        await cw.get_companies()
    assert str(status) in str(e.value)
    assert "company/companies" in str(e.value)


async def test_errors_never_leak_the_api_key(api) -> None:
    api.status = 401
    with pytest.raises(cw.ConnectWiseError) as e:
        await cw.get_companies()
    assert "priv" not in str(e.value)
    assert "Basic " not in str(e.value)


async def test_malformed_json_is_an_error_not_a_crash(api) -> None:
    api.body = "<html>gateway timeout</html>"
    with pytest.raises(Exception):
        await cw.get_companies()


# --- read-only guarantee ---------------------------------------------------


def test_health_route(api) -> None:
    from starlette.testclient import TestClient

    with TestClient(cw.mcp.http_app()) as http:
        r = http.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_rest_route_returns_a_bare_array_like_the_old_bridge(api) -> None:
    """
    The Node bridge JSON.parse'd the text block and returned it directly, so a
    collection arrived as a bare array and callers index it. Wrapping that in
    {"data": ...} would break every existing OpenWebUI install silently -- the
    requests would still succeed, they would just stop finding anything.
    """
    from starlette.testclient import TestClient

    api.payload = [{"id": 1, "identifier": "ACME"}]
    with TestClient(cw.mcp.http_app()) as http:
        r = http.post(
            "/v1/tools/execute",
            json={"tool_name": "connectwise_get_companies", "arguments": {"pageSize": 1}},
        )
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert body[0]["identifier"] == "ACME"


def test_rest_route_rejects_a_missing_tool_name(api) -> None:
    from starlette.testclient import TestClient

    with TestClient(cw.mcp.http_app()) as http:
        r = http.post("/v1/tools/execute", json={})
    assert r.status_code == 400
    assert "tool_name" in r.json()["error"]


def test_rest_route_reports_an_unknown_tool(api) -> None:
    from starlette.testclient import TestClient

    with TestClient(cw.mcp.http_app()) as http:
        r = http.post("/v1/tools/execute", json={"tool_name": "connectwise_nope"})
    assert r.status_code == 500
    assert "error" in r.json()


async def test_no_tool_issues_a_write(api) -> None:
    """
    Stage 1 is read-only. Writes arrive later behind an explicit opt-in, and
    until then nothing should be capable of changing a customer's data.
    """
    for call in (
        cw.get_companies(),
        cw.get_tickets(),
        cw.get_ticket(1),
        cw.get_time_entries(),
    ):
        await call
    assert {r.method for r in api.requests} == {"GET"}
