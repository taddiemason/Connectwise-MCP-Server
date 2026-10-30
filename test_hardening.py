"""
Stage 3: retries, pagination and HTTP authentication.

Each of these covers something that was silently wrong rather than loudly
broken -- a rate limit that looked like an empty result, a page-one answer that
looked like the whole answer, and an HTTP port that answered anyone.
"""
from __future__ import annotations

import httpx
import pytest
from starlette.testclient import TestClient

import connectwise_mcp as cw

TOKEN = "test-token-not-a-real-secret"


# --- retries ---------------------------------------------------------------


async def test_retries_a_rate_limit_then_succeeds(api) -> None:
    """
    A 429 used to surface as a failed tool call, which reads to a model as
    "there is no such data" rather than "ask again in a moment".
    """
    api.status_sequence = [429, 429]
    api.payload = [{"id": 7}]
    result = await cw.get_tickets()
    assert result == [{"id": 7}]
    assert len(api.requests) == 3


@pytest.mark.parametrize("status", [500, 502, 503, 504])
async def test_retries_server_errors(api, status: int) -> None:
    api.status_sequence = [status]
    api.payload = [{"id": 1}]
    assert await cw.get_tickets() == [{"id": 1}]
    assert len(api.requests) == 2


async def test_gives_up_after_the_retry_budget(api) -> None:
    api.status = 429
    with pytest.raises(cw.ConnectWiseError) as e:
        await cw.get_tickets()
    # One initial attempt plus CW_MAX_RETRIES retries.
    assert len(api.requests) == cw.CW_MAX_RETRIES + 1
    assert "rate limited" in str(e.value).lower()


@pytest.mark.parametrize("status", [400, 401, 403, 404])
async def test_client_errors_are_not_retried(api, status: int) -> None:
    """Retrying a 404 or a bad key just burns the rate limit."""
    api.status = status
    with pytest.raises(cw.ConnectWiseError):
        await cw.get_tickets()
    assert len(api.requests) == 1


async def test_retry_after_header_is_honoured(api, monkeypatch) -> None:
    """ConnectWise saying 'wait 5s' should beat our own backoff curve."""
    slept: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(cw.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(cw, "CW_RETRY_BASE_DELAY", 0.5)

    api.status_sequence = [429]
    api.headers = {"Retry-After": "5"}
    await cw.get_tickets()
    assert slept == [5.0]


async def test_a_nonsense_retry_after_falls_back_to_backoff(api, monkeypatch) -> None:
    """Retry-After may be an HTTP date; it must not crash the retry path."""
    slept: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(cw.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(cw, "CW_RETRY_BASE_DELAY", 0.5)

    api.status_sequence = [429]
    api.headers = {"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}
    await cw.get_tickets()
    assert slept == [0.5]


# --- error messages --------------------------------------------------------


async def test_auth_failure_says_what_to_check(api) -> None:
    api.status = 401
    with pytest.raises(cw.ConnectWiseError) as e:
        await cw.get_tickets()
    message = str(e.value)
    assert "CW_PUBLIC_KEY" in message
    assert "401" in message


async def test_not_found_is_distinguishable_from_empty(api) -> None:
    api.status = 404
    with pytest.raises(cw.ConnectWiseError) as e:
        await cw.get_ticket(999999)
    assert "not found" in str(e.value).lower()


async def test_non_json_body_is_reported_clearly(api) -> None:
    """A gateway can return HTML with a 200; json() blowing up is unhelpful."""
    api.body = "<html>502 Bad Gateway</html>"
    with pytest.raises(cw.ConnectWiseError) as e:
        await cw.get_tickets()
    assert "non-JSON" in str(e.value)


# --- pagination ------------------------------------------------------------


async def test_fetch_all_walks_every_page(api) -> None:
    """
    Without this, a query matching 7 records with pageSize 3 returns 3 -- and
    "3" is a wrong answer, not a partial one.
    """
    api.pages = {
        "1": [{"id": 1}, {"id": 2}, {"id": 3}],
        "2": [{"id": 4}, {"id": 5}, {"id": 6}],
        "3": [{"id": 7}],
    }
    result = await cw.get_tickets(pageSize=3, fetchAll=True)
    assert [r["id"] for r in result] == [1, 2, 3, 4, 5, 6, 7]
    assert len(api.requests) == 3


async def test_fetch_all_stops_on_a_short_page(api) -> None:
    api.pages = {"1": [{"id": 1}]}
    await cw.get_tickets(pageSize=25, fetchAll=True)
    assert len(api.requests) == 1


async def test_fetch_all_respects_the_record_cap(api, monkeypatch) -> None:
    """'Every ticket' must not become fifty thousand records and a ban."""
    monkeypatch.setattr(cw, "CW_MAX_RECORDS", 5)
    api.pages = {str(p): [{"id": p}] * 3 for p in range(1, 20)}
    result = await cw.get_tickets(pageSize=3, fetchAll=True)
    assert len(result) == 5


async def test_fetch_all_is_off_by_default(api) -> None:
    api.pages = {"1": [{"id": i} for i in range(25)], "2": [{"id": 99}]}
    result = await cw.get_tickets(pageSize=25)
    assert len(result) == 25
    assert len(api.requests) == 1


async def test_result_is_still_a_bare_array(api) -> None:
    """
    Shape is the compatibility contract. Wrapping paged results in
    {items, total} would be more useful and would break every existing caller.
    """
    api.pages = {"1": [{"id": 1}, {"id": 2}], "2": [{"id": 3}]}
    assert isinstance(await cw.get_tickets(pageSize=2, fetchAll=True), list)


# --- HTTP authentication ---------------------------------------------------


@pytest.fixture
def authed_app(api, monkeypatch):
    monkeypatch.setattr(cw, "MCP_AUTH_TOKEN", TOKEN)
    return cw.build_http_app()


def test_health_needs_no_token(authed_app) -> None:
    """The container healthcheck calls it, and it reveals nothing."""
    with TestClient(authed_app) as http:
        r = http.get("/health")
    assert r.status_code == 200


def test_requests_without_a_token_are_rejected(authed_app) -> None:
    with TestClient(authed_app) as http:
        r = http.post(
            "/v1/tools/execute", json={"tool_name": "connectwise_get_companies"}
        )
    assert r.status_code == 401


def test_a_wrong_token_is_rejected(authed_app) -> None:
    with TestClient(authed_app) as http:
        r = http.post(
            "/v1/tools/execute",
            json={"tool_name": "connectwise_get_companies"},
            headers={"Authorization": "Bearer wrong"},
        )
    assert r.status_code == 401


def test_the_right_token_gets_through(authed_app, api) -> None:
    api.payload = [{"id": 1, "identifier": "ACME"}]
    with TestClient(authed_app) as http:
        r = http.post(
            "/v1/tools/execute",
            json={"tool_name": "connectwise_get_companies"},
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
    assert r.status_code == 200
    assert r.json()[0]["identifier"] == "ACME"


def test_no_token_configured_rejects_everything(api, monkeypatch) -> None:
    """
    Belt and braces behind main()'s refusal to start. If the app is ever built
    without a token, it must deny rather than wave everything through.
    """
    monkeypatch.setattr(cw, "MCP_AUTH_TOKEN", None)
    with TestClient(cw.build_http_app()) as http:
        r = http.post("/v1/tools/execute", json={"tool_name": "x"})
    assert r.status_code == 401


def test_http_transport_refuses_to_start_without_a_token(monkeypatch) -> None:
    """Starting wide open is worse than not starting."""
    monkeypatch.setattr(cw, "MCP_AUTH_TOKEN", None)
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    with pytest.raises(SystemExit) as e:
        cw.main()
    assert "MCP_AUTH_TOKEN" in str(e.value)
