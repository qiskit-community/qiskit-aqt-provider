import httpx
from aqt_connector.models.arnica.response_bodies.resources import ResourceDetails


class CloudResource:
    """A resource in the AQT cloud, associated with a specific workspace."""

    def __init__(self, api_client: httpx.Client, workspace_id: str, resource_details: ResourceDetails) -> None:
        """Initializes a cloud resource with the given workspace and resource details."""
        self._api_client = api_client
        self._workspace_id = workspace_id
        self._resource_id = resource_details.id

    @property
    def id(self) -> str:
        """The resource's identifier."""
        return self._resource_id
