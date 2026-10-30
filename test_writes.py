"""
Stage 5: write operations.

These are the tools that can change a customer's data, so most of what is
tested here is the refusal path rather than the happy path.
"""
from __future__ import annotations

import os
import sys

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

import connectwise_mcp as cw

HERE = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def writes_enabled(monkeypatch):
    def _enable(categories: str):
        monkeypatch.setattr(cw, "CW_ENABLE_WRITES", categories)

    return _enable


# --- the gate --------------------------------------------------------------


def test_read_only_by_default(monkeypatch) -> None:
    monkeypatch.setattr(cw, "CW_ENABLE_WRITES", "")
    assert cw.enabled_writes() == frozenset()


@pytest.mark.parametrize(
    "setting, expected",
    [
        ("notes", {"notes"}),
        ("notes,time", {"notes", "time"}),
        (" NOTES , Time ", {"notes", "time"}),
        ("all", {"notes", "time", "tickets"}),
        ("", set()),
    ],
)
def test_categories_parse(monkeypatch, setting: str, expected: set) -> None:
    monkeypatch.setattr(cw, "CW_ENABLE_WRITES", setting)
    assert cw.enabled_writes() == frozenset(expected)


def test_true_does_not_silently_enable_everything(monkeypatch) -> None:
    """
    CW_ENABLE_WRITES=true is the obvious thing to type and means nothing here.
    Quietly enabling every write because a boolean looked truthy would be the
    worst reading of an ambiguous setting.
    """
    monkeypatch.setattr(cw, "CW_ENABLE_WRITES", "true")
    assert cw.enabled_writes() == frozenset()


async def test_disabled_category_refuses(monkeypatch, api) -> None:
    monkeypatch.setattr(cw, "CW_ENABLE_WRITES", "notes")
    with pytest.raises(cw.WritesDisabledError) as e:
        await cw.create_ticket(summary="x", company_id=1, board_id=1)
    assert "tickets" in str(e.value)
    assert not api.requests, "nothing should have been sent"


async def test_nothing_is_sent_when_writes_are_off(monkeypatch, api) -> None:
    monkeypatch.setattr(cw, "CW_ENABLE_WRITES", "")
    for call in (
        cw.add_ticket_note(1, "hello"),
        cw.create_time_entry(1, 1.0, "worked"),
        cw.update_ticket(1, "summary", "x"),
    ):
        with pytest.raises(cw.WritesDisabledError):
            await call
    assert not api.requests


# --- dry run ---------------------------------------------------------------


async def test_dry_run_sends_nothing(monkeypatch, api, writes_enabled) -> None:
    writes_enabled("all")
    monkeypatch.setattr(cw, "CW_WRITE_DRY_RUN", True)
    result = await cw.add_ticket_note(42, "would be added")
    assert result["dryRun"] is True
    assert result["wouldSend"]["endpoint"] == "service/tickets/42/notes"
    assert not api.requests


# --- request shapes --------------------------------------------------------


async def test_ticket_note_defaults_to_internal(api, writes_enabled) -> None:
    """
    An AI-written note landing in the customer-visible feed unannounced is a
    surprise worth opting into, not out of.
    """
    writes_enabled("notes")
    await cw.add_ticket_note(42, "diagnosis")
    body = cw.json.loads(api.last.content)
    assert body["internalAnalysisFlag"] is True
    assert body["detailDescriptionFlag"] is False
    assert api.last.method == "POST"
    assert api.path == "service/tickets/42/notes"


async def test_ticket_note_can_be_customer_visible(api, writes_enabled) -> None:
    writes_enabled("notes")
    await cw.add_ticket_note(42, "update for you", internal=False)
    body = cw.json.loads(api.last.content)
    assert body["detailDescriptionFlag"] is True
    assert body["internalAnalysisFlag"] is False


async def test_time_entry_shape(api, writes_enabled) -> None:
    writes_enabled("time")
    await cw.create_time_entry(
        ticket_id=7, actual_hours=1.5, notes="patched it", member_identifier="jsmith"
    )
    body = cw.json.loads(api.last.content)
    assert body["chargeToId"] == 7
    assert body["chargeToType"] == "ServiceTicket"
    assert body["actualHours"] == 1.5
    assert body["member"] == {"identifier": "jsmith"}
    assert api.path == "time/entries"


async def test_create_ticket_shape(api, writes_enabled) -> None:
    writes_enabled("tickets")
    await cw.create_ticket(summary="Printer down", company_id=3, board_id=9)
    body = cw.json.loads(api.last.content)
    assert body == {
        "summary": "Printer down",
        "company": {"id": 3},
        "board": {"id": 9},
    }


async def test_update_ticket_sends_json_patch(api, writes_enabled) -> None:
    """
    ConnectWise PATCH is JSON Patch. Sending {"status": {"id": 5}} is accepted
    with a 200 and changes nothing, which is the worst kind of failure -- it
    looks like it worked.
    """
    writes_enabled("tickets")
    await cw.update_ticket(42, "status/id", 5)
    body = cw.json.loads(api.last.content)
    assert body == [{"op": "replace", "path": "status/id", "value": 5}]
    assert api.last.method == "PATCH"


async def test_update_ticket_rejects_a_bad_operation(api, writes_enabled) -> None:
    writes_enabled("tickets")
    with pytest.raises(ValueError):
        await cw.update_ticket(42, "summary", "x", operation="destroy")
    assert not api.requests


# --- retries must not duplicate --------------------------------------------


async def test_writes_are_not_retried_on_5xx(api, writes_enabled) -> None:
    """
    The important one. A 500 on a POST does not mean nothing happened -- the
    note may well have been created before the error. Retrying produces a
    duplicate on a customer's ticket, which is worse than surfacing the error.
    """
    writes_enabled("notes")
    api.status = 500
    with pytest.raises(cw.ConnectWiseError):
        await cw.add_ticket_note(1, "hello")
    assert len(api.requests) == 1


async def test_writes_are_retried_on_429(api, writes_enabled) -> None:
    """A 429 is rejected before processing, so a retry cannot duplicate."""
    writes_enabled("notes")
    api.status_sequence = [429]
    api.payload = {"id": 99}
    result = await cw.add_ticket_note(1, "hello")
    assert len(api.requests) == 2
    assert result["id"] == 99


async def test_reads_are_still_retried_on_5xx(api) -> None:
    """The write change must not have made GETs give up early."""
    api.status_sequence = [500]
    api.payload = [{"id": 1}]
    await cw.get_tickets()
    assert len(api.requests) == 2


async def test_write_returns_the_created_record(api, writes_enabled) -> None:
    writes_enabled("notes")
    api.payload = {"id": 500, "text": "diagnosis"}
    assert (await cw.add_ticket_note(1, "diagnosis"))["id"] == 500


async def test_empty_body_response_is_not_a_crash(api, writes_enabled) -> None:
    """A 201 with no body is a success, not a JSON parse error."""
    writes_enabled("notes")
    api.status = 201
    api.body = ""
    result = await cw.add_ticket_note(1, "x")
    assert result["status"] == 201


# --- registration, end to end ----------------------------------------------


def _stdio(env_extra: dict[str, str]) -> Client:
    env = dict(os.environ)
    for key in ("CW_COMPANY_ID", "CW_PUBLIC_KEY", "CW_PRIVATE_KEY"):
        env.pop(key, None)
    env.pop("CW_ENABLE_WRITES", None)
    env.update(env_extra)
    return Client(
        StdioTransport(
            command=sys.executable, args=["connectwise_mcp.py"], env=env, cwd=HERE
        )
    )


async def test_write_tools_are_absent_by_default() -> None:
    """
    Not merely refused -- absent. A model cannot be talked into calling a tool
    it cannot see.
    """
    async with _stdio({}) as c:
        names = {t.name for t in await c.list_tools()}
    assert not [n for n in names if "add_" in n or "create_" in n or "update_" in n]


async def test_only_the_enabled_category_appears() -> None:
    async with _stdio({"CW_ENABLE_WRITES": "notes"}) as c:
        names = {t.name for t in await c.list_tools()}
    assert "connectwise_add_ticket_note" in names
    assert "connectwise_create_ticket" not in names
    assert "connectwise_create_time_entry" not in names
