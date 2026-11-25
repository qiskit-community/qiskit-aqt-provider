# This code is part of Qiskit.
#
# (C) Copyright Alpine Quantum Technologies GmbH 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at [http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0).
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

from datetime import datetime

import httpx
import pytest
from aqt_connector import ArnicaApp
from aqt_connector.models.arnica.resources import ResourceStatus, ResourceType
from aqt_connector.models.arnica.response_bodies.resources import ResourceDetails, WorkspaceResource
from aqt_connector.models.arnica.response_bodies.workspaces import Workspace as APIWorkspace
from httpx import Client, MockTransport, Response
from pytest_httpx import HTTPXMock
from qiskit.providers.exceptions import QiskitBackendNotFoundError

from qiskit_aqt_provider._cloud.workspace_provider import WorkspaceProvider


def test_it_gets_backend_by_id(monkeypatch: pytest.MonkeyPatch, httpx_mock: HTTPXMock) -> None:
    """The workspace provider should be able to get a backend by its identifier."""
    resources = [
        WorkspaceResource(id="r1", name="R1", type=ResourceType.DEVICE),
        WorkspaceResource(id="r2", name="R2", type=ResourceType.DEVICE),
    ]
    arnica = ArnicaApp()
    monkeypatch.setattr(arnica.auth_service, "get_or_refresh_access_token", lambda _: "arnica_token")
    httpx_mock.add_callback(_resource_details_request_handler, url="https://arnica.aqt.eu/api/v1/resources/r2")
    workspace_provider = WorkspaceProvider(
        data=APIWorkspace(id="w1", accepting_job_submissions=True, jobs_being_processed=False, resources=resources),
        arnica=arnica,
        api_client=Client(transport=MockTransport(lambda _: Response(404))),
    )

    backend = workspace_provider.get_backend("r2")

    assert backend is not None
    assert backend.id == "r2"
    assert backend.workspace_id == "w1"
    assert backend.num_qubits == 20
    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers["Authorization"] == "Bearer arnica_token"


def test_it_raises_if_backend_id_not_found() -> None:
    """The workspace provider should raise an error if no backend matches the given identifier."""
    resources = [
        WorkspaceResource(id="r1", name="R1", type=ResourceType.DEVICE),
        WorkspaceResource(id="r2", name="R2", type=ResourceType.DEVICE),
    ]
    workspace_provider = WorkspaceProvider(
        data=APIWorkspace(id="w1", accepting_job_submissions=True, jobs_being_processed=False, resources=resources),
        arnica=ArnicaApp(),
        api_client=Client(transport=MockTransport(lambda _: Response(404))),
    )

    with pytest.raises(QiskitBackendNotFoundError, match="Backend with ID 'r3' not found in workspace 'w1'"):
        workspace_provider.get_backend("r3")


def _resource_details_request_handler(request: httpx.Request) -> Response:
    if request.url.path == "/api/v1/resources/r2":
        return Response(
            status_code=200,
            text=ResourceDetails(
                id="r2",
                name="R2",
                type=ResourceType.DEVICE,
                status=ResourceStatus.ONLINE,
                available_qubits=20,
                status_updated_at=datetime(2026, 3, 27, 0, 0, 0),
            ).model_dump_json(),
        )

    return Response(status_code=404)
