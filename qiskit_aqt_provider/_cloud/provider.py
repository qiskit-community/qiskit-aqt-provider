from typing import Callable, Final

import aqt_connector
import httpx
from aqt_connector import ArnicaApp, ArnicaConfig

from qiskit_aqt_provider._cloud.workspace_collection import WorkspaceCollection
from qiskit_aqt_provider.api_client import models
from qiskit_aqt_provider.api_client.errors import http_response_raise_for_status
from qiskit_aqt_provider.api_client.versions import make_user_agent


def _http_client_factory(config: ArnicaConfig) -> httpx.Client:
    """Creates an HTTP client for the given configuration."""
    return httpx.Client(
        base_url=config.arnica_url,
        headers={"User-Agent": make_user_agent(CloudProvider.USER_AGENT_NAME)},
        timeout=10.0,
        follow_redirects=True,
    )


class CloudProvider:
    """An AQT cloud provider for use in the Qiskit AQT provider."""

    USER_AGENT_NAME: Final = "aqt-cloud-provider"

    def __init__(
        self,
        config: ArnicaConfig,
        *,
        http_client_factory: Callable[[ArnicaConfig], httpx.Client] = _http_client_factory,
    ) -> None:
        """Initializes the cloud provider with the given configuration."""
        self._arnica = ArnicaApp(config)
        self._http_client = http_client_factory(config)

    def close(self) -> None:
        """Closes the cloud provider, releasing any resources it holds."""
        # TODO: close arnica app too, once aqt_connector supports that
        self._http_client.close()

    def log_in(self) -> None:
        """Logs the user into the cloud provider, establishing a session for subsequent API calls."""
        access_token = aqt_connector.log_in(self._arnica)
        self._http_client.headers["Authorization"] = f"Bearer {access_token}"

    def fetch_workspaces(self) -> WorkspaceCollection:
        """Fetches workspaces accessible to the user.

        Returns:
            WorkspaceCollection: A collection of workspaces accessible to the user.
        """
        response = http_response_raise_for_status(self._http_client.get("/v1/workspaces"))
        api_workspaces = models.ApiWorkspaces.model_validate_json(response.text)
        return WorkspaceCollection(api_workspaces.root, self._arnica, self._http_client)
