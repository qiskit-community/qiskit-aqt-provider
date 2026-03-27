from datetime import datetime

from aqt_connector.models.arnica.resources import ResourceStatus, ResourceType
from aqt_connector.models.arnica.response_bodies.resources import ResourceDetails
from httpx import Client, MockTransport, Response

from qiskit_aqt_provider._cloud.resource import CloudResource


def test_id_property_returns_resource_id() -> None:
    """The workspace provider's ID property should return the workspace's identifier."""
    resource = CloudResource(
        Client(transport=MockTransport(lambda _: Response(404))),
        "workspace_id",
        ResourceDetails(
            id="w1",
            name="W1",
            type=ResourceType.DEVICE,
            status=ResourceStatus.ONLINE,
            available_qubits=20,
            status_updated_at=datetime(2026, 3, 27, 0, 0, 0),
        ),
    )

    assert resource.id == "w1"
