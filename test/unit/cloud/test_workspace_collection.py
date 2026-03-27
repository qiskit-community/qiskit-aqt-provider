from aqt_connector.models.arnica.response_bodies.workspaces import Workspace
from httpx import Client, MockTransport, Response

from qiskit_aqt_provider._cloud.workspace_collection import WorkspaceCollection


def test_get_by_id_returns_workspace_provider_with_matching_id() -> None:
    """The workspace collection's get_by_id method should return the workspace provider with the specified ID."""
    workspace_collection = WorkspaceCollection(
        workspaces=[
            Workspace(id="w1", accepting_job_submissions=True, jobs_being_processed=False, resources=[]),
            Workspace(id="w2", accepting_job_submissions=True, jobs_being_processed=False, resources=[]),
        ],
        api_client=Client(transport=MockTransport(lambda _: Response(404))),
    )

    workspace = workspace_collection.get_by_id("w1")

    assert workspace is not None
    assert workspace.id == "w1"


def test_get_by_id_returns_none_if_no_matching_id() -> None:
    """The workspace collection's get_by_id method should return None if no workspace provider has the specified ID."""
    workspace_collection = WorkspaceCollection(
        workspaces=[],
        api_client=Client(transport=MockTransport(lambda _: Response(404))),
    )

    workspace = workspace_collection.get_by_id("w1")

    assert workspace is None
