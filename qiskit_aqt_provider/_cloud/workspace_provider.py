import httpx
from aqt_connector.models.arnica.response_bodies.resources import ResourceDetails, WorkspaceResource
from aqt_connector.models.arnica.response_bodies.workspaces import Workspace as APIWorkspace
from qiskit.providers.exceptions import QiskitBackendNotFoundError

from qiskit_aqt_provider._cloud.resource import CloudResource
from qiskit_aqt_provider.api_client.errors import http_response_raise_for_status


class WorkspaceProvider:
    """A provider for a workspace in the AQT cloud."""

    def __init__(self, data: APIWorkspace, api_client: httpx.Client) -> None:
        """Initializes a workspace provider from the given API workspace data."""
        self._id = data.id
        self._resources = data.resources
        self._api_client = api_client

    @property
    def id(self) -> str:
        """The workspace's identifier."""
        return self._id

    def list_backends(self) -> list[WorkspaceResource]:
        """Lists the backends available in this workspace.

        Returns:
            list[WorkspaceResource]: The list of backends available in this workspace.
        """
        return self._resources

    def get_backend(self, backend_id: str) -> CloudResource:
        """Gets a specific backend available in this workspace by its identifier.

        Args:
            backend_id (str): The identifier of the backend to retrieve.

        Returns:
            CloudResource: The backend with the specified identifier.

        Raises:
            QiskitBackendNotFoundError: If no backend with the specified identifier is found.
        """
        for resource in self._resources:
            if resource.id == backend_id:
                response = http_response_raise_for_status(self._api_client.get(f"/v1/resources/{resource.id}"))
                details = ResourceDetails.model_validate_json(response.text)
                return CloudResource(self._api_client, self._id, details)

        raise QiskitBackendNotFoundError(f"Backend with ID '{backend_id}' not found in workspace '{self._id}'.")
