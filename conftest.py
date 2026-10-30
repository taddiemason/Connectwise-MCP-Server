"""
Shared test fixtures.

Everything here runs with no ConnectWise credentials and no network. A
httpx.MockTransport stands in for the API and records what was asked of it, so
the tests can assert on the endpoint and query string each tool produces.
"""
from __future__ import annotations

import httpx
import pytest

import connectwise_mcp as cw


class RecordingApi:
    """A stand-in ConnectWise that records requests and replays canned responses."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.status = 200
        self.payload: object = [{"id": 1, "name": "stub"}]
        self.body: str | None = None

    @property
    def last(self) -> httpx.Request:
        assert self.requests, "no request was made"
        return self.requests[-1]

    @property
    def path(self) -> str:
        """Path after the /vX/apis/3.0 prefix, which is what tools actually pick."""
        return self.last.url.path.split("/apis/3.0/", 1)[-1]

    @property
    def params(self) -> dict[str, str]:
        return dict(self.last.url.params)

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.body is not None:
            return httpx.Response(self.status, text=self.body)
        return httpx.Response(self.status, json=self.payload)


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> RecordingApi:
    """Installs a fake ConnectWise as the module-level client."""
    fake = RecordingApi()

    # Credentials have to look present for the client to build; they are never
    # sent anywhere real because the transport is a mock.
    monkeypatch.setattr(cw, "CW_COMPANY_ID", "testco")
    monkeypatch.setattr(cw, "CW_PUBLIC_KEY", "pub")
    monkeypatch.setattr(cw, "CW_PRIVATE_KEY", "priv")
    monkeypatch.setattr(cw, "CW_API_URL", "https://cw.example")
    monkeypatch.setattr(cw, "CW_API_VERSION", "v2023.2")

    client = cw.ConnectWiseClient(transport=httpx.MockTransport(fake.handler))
    monkeypatch.setattr(cw, "_client", client)
    return fake


@pytest.fixture
def no_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """A clean slate with nothing configured and no cached client."""
    monkeypatch.setattr(cw, "CW_COMPANY_ID", None)
    monkeypatch.setattr(cw, "CW_PUBLIC_KEY", None)
    monkeypatch.setattr(cw, "CW_PRIVATE_KEY", None)
    monkeypatch.setattr(cw, "_client", None)
