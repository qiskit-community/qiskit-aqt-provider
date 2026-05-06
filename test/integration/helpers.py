from datetime import datetime

import httpx
from aqt_connector._arnica_app import ArnicaApp
from aqt_connector.models.arnica.resources import ResourceStatus, ResourceType
from aqt_connector.models.arnica.response_bodies.resources import ResourceDetails

from qiskit_aqt_provider._cloud.resource import CloudResource


def get_dummy_cloud_resource() -> CloudResource:
    """Helper function to create a dummy CloudResource for testing."""
    resource_details = ResourceDetails(
        id="test_resource",
        name="Test Resource",
        type=ResourceType.SIMULATOR,
        status=ResourceStatus.ONLINE,
        available_qubits=12,
        status_updated_at=datetime.now(),
    )
    return CloudResource(
        arnica=ArnicaApp(),
        api_client=httpx.Client(),
        workspace_id="",
        resource_details=resource_details,
    )
