from typing import Callable

import httpx

from qiskit_aqt_provider._direct.provider import DirectAccessProvider


def test_get_resource_creates_http_client_with_correct_configuration() -> None:
    """DirectAccessProvider.get_resource should create an HTTP client with the correct configuration."""

    def _client_factory(base_url: str, access_token: str) -> httpx.Client:
        nonlocal given_base_url, given_access_token
        given_base_url = base_url
        given_access_token = access_token
        return _create_client(_device_status_handler)

    given_base_url: str | None = None
    given_access_token: str | None = None
    base_url = "https://example.com:9000"
    access_token = "test-token"  # noqa: S105

    provider = DirectAccessProvider(http_client_factory=_client_factory)
    provider.get_resource(base_url, access_token)

    assert given_base_url == base_url
    assert given_access_token == access_token


def test_get_resource_returns_resource_with_correct_configuration() -> None:
    """DirectAccessProvider.get_resource should return a resource with the correct configuration."""
    provider = DirectAccessProvider(
        http_client_factory=lambda _base_url, _access_token: _create_client(_device_status_handler)
    )
    resource = provider.get_resource("https://example.com:9000", "test-token")

    assert resource.name == "Test Device"
    assert resource.num_qubits == 10


def test_close_closes_http_clients() -> None:
    """DirectAccessProvider.close should close all HTTP clients."""

    def http_client_factory(_base_url: str, _access_token: str) -> httpx.Client:
        client = _create_client(_device_status_handler)
        created_http_clients.append(client)
        return client

    created_http_clients: list[httpx.Client] = []
    provider = DirectAccessProvider(http_client_factory=http_client_factory)
    provider.get_resource("https://example.com:9001", "token1")
    provider.get_resource("https://example.com:9002", "token2")

    provider.close()

    assert len(created_http_clients) == 2
    for client in created_http_clients:
        assert client.is_closed


def _create_client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    """Creates an HTTP client with the given request handler."""
    return httpx.Client(base_url="https://example.com", transport=httpx.MockTransport(handler))


def _device_status_handler(request: httpx.Request) -> httpx.Response:
    """A mock HTTP request handler for device status endpoints."""
    if request.url.path == "/status/ions":
        return httpx.Response(status_code=200, json={"num_ions": 10})
    if request.url.path == "/system/name":
        return httpx.Response(status_code=200, json="Test Device")
    return httpx.Response(status_code=404)
