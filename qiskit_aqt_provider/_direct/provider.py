from typing import Callable, Final

import httpx

from qiskit_aqt_provider._direct.api_client import DirectAccessAPIClient
from qiskit_aqt_provider._direct.resource import DirectAccessResource, DirectAccessResourceConfig
from qiskit_aqt_provider.api_client.versions import make_user_agent


def _http_client_factory(base_url: str, access_token: str) -> httpx.Client:
    """Creates an HTTP client for the given configuration."""
    return httpx.Client(
        base_url=base_url,
        headers={
            "User-Agent": make_user_agent(DirectAccessProvider.USER_AGENT_NAME),
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        timeout=10.0,
        follow_redirects=True,
    )


class DirectAccessProvider:
    """A provider for direct access resources."""

    USER_AGENT_NAME: Final = "aqt-direct-access-provider"

    def __init__(self, *, http_client_factory: Callable[[str, str], httpx.Client] = _http_client_factory) -> None:
        """Initializes the direct access provider."""
        self._http_client_factory = http_client_factory
        self._api_clients: dict[str, DirectAccessAPIClient] = {}

    def get_resource(self, base_url: str, access_token: str) -> DirectAccessResource:
        """Gets a direct access resource at the given base URL.

        Args:
            base_url (str): The base URL of the resource's API.
            access_token (str): The access token to use for authentication when accessing the resource.

        Returns:
            DirectAccessResource: A direct access resource for the given base URL.
        """
        client = DirectAccessAPIClient(self._http_client_factory(base_url, access_token))
        self._api_clients[base_url] = client

        available_qubits = client.fetch_available_qubits()
        name = client.fetch_name()

        config = DirectAccessResourceConfig(
            name=name,
            number_of_ions=available_qubits,
            client=client,
        )
        return DirectAccessResource(config)

    def close(self) -> None:
        """Closes the provider, releasing any resources it holds."""
        for client in self._api_clients.values():
            client.close()
        self._api_clients.clear()
