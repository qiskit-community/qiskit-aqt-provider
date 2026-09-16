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

from collections.abc import Callable

import pytest
from aqt_connector import ArnicaConfig
from aqt_connector.models.arnica.response_bodies.workspaces import Workspace
from httpx import Client, MockTransport, Request, Response

from qiskit_aqt_provider._cloud.provider import CloudProvider
from qiskit_aqt_provider.api_client.models import ApiWorkspaces


@pytest.mark.parametrize(
    "workspaces",
    [
        ApiWorkspaces(root=[]),
        ApiWorkspaces(
            root=[
                Workspace(id="w1", accepting_job_submissions=True, jobs_being_processed=False, resources=[]),
            ]
        ),
        ApiWorkspaces(
            root=[
                Workspace(id="w1", accepting_job_submissions=True, jobs_being_processed=False, resources=[]),
                Workspace(id="w2", accepting_job_submissions=True, jobs_being_processed=False, resources=[]),
            ]
        ),
    ],
)
def test_it_lists_accessible_workspaces(workspaces: ApiWorkspaces) -> None:
    """It should list workspaces the user has access to."""

    def client_factory(_: ArnicaConfig) -> Client:
        return Client(
            base_url="https://arnica.aqt.eu/api", transport=MockTransport(_create_request_handler(workspaces))
        )

    provider = CloudProvider(ArnicaConfig(), http_client_factory=client_factory)

    workspace_providers = provider.fetch_workspaces()

    assert {provider.id for provider in workspace_providers} == {workspace.id for workspace in workspaces.root}


def _create_request_handler(workspaces: ApiWorkspaces) -> Callable[[Request], Response]:
    def _workspaces_request_handler(request: Request) -> Response:
        if request.url.path == "/api/v1/workspaces":
            return Response(
                status_code=200,
                text=workspaces.model_dump_json(),
            )

        return Response(status_code=404)

    return _workspaces_request_handler
