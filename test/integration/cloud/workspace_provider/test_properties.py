from aqt_connector.models.arnica.response_bodies.workspaces import Workspace as APIWorkspace
from httpx import Client, MockTransport, Response

from qiskit_aqt_provider._cloud.workspace_provider import WorkspaceProvider


def test_id_property_returns_workspace_id() -> None:
    """The workspace provider's ID property should return the workspace's identifier."""
    workspace_provider = WorkspaceProvider(
        data=APIWorkspace(id="w1", accepting_job_submissions=True, jobs_being_processed=False, resources=[]),
        api_client=Client(transport=MockTransport(lambda _: Response(404))),
    )

    assert workspace_provider.id == "w1"
