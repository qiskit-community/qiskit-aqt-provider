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

from aqt_connector import ArnicaApp
from aqt_connector.models.arnica.response_bodies.workspaces import Workspace as APIWorkspace
from httpx import Client, MockTransport, Response

from qiskit_aqt_provider._cloud.workspace_provider import WorkspaceProvider


def test_id_property_returns_workspace_id() -> None:
    """The workspace provider's ID property should return the workspace's identifier."""
    workspace_provider = WorkspaceProvider(
        data=APIWorkspace(id="w1", accepting_job_submissions=True, jobs_being_processed=False, resources=[]),
        arnica=ArnicaApp(),
        api_client=Client(transport=MockTransport(lambda _: Response(404))),
    )

    assert workspace_provider.id == "w1"
