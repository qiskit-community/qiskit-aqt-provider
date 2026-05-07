from collections.abc import Iterator
from datetime import datetime

import httpx
import pytest
from aqt_connector._arnica_app import ArnicaApp
from aqt_connector.models.arnica.resources import ResourceStatus, ResourceType
from aqt_connector.models.arnica.response_bodies.resources import ResourceDetails

from qiskit_aqt_provider._cloud.resource import CloudResource


@pytest.fixture(scope="module")
def dummy_cloud_resource() -> Iterator[CloudResource]:
    """Fixture that creates a dummy CloudResource and cleans up the client."""
    client = httpx.Client()

    resource_details = ResourceDetails(
        id="test_resource",
        name="Test Resource",
        type=ResourceType.SIMULATOR,
        status=ResourceStatus.ONLINE,
        available_qubits=12,
        status_updated_at=datetime.now(),
    )
    resource = CloudResource(
        arnica=ArnicaApp(),
        api_client=client,
        workspace_id="",
        resource_details=resource_details,
    )

    yield resource
    client.close()
