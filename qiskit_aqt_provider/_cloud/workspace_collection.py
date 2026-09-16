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

import httpx
from aqt_connector import ArnicaApp
from aqt_connector.models.arnica.response_bodies.workspaces import Workspace

from qiskit_aqt_provider._cloud.workspace_provider import WorkspaceProvider


class WorkspaceCollection(list[WorkspaceProvider]):
    """A collection of workspaces accessible to the user in the AQT cloud."""

    def __init__(self, workspaces: list[Workspace], arnica: ArnicaApp, api_client: httpx.Client) -> None:
        """Initializes a workspace collection from the given list of API workspaces and HTTP client."""
        providers = [WorkspaceProvider(workspace, arnica, api_client) for workspace in workspaces]
        super().__init__(providers)

    def get_by_id(self, workspace_id: str) -> WorkspaceProvider | None:
        """Gets a workspace provider from this collection by its identifier.

        Args:
            workspace_id (str): The identifier of the workspace to retrieve.

        Returns:
            Union[WorkspaceProvider, None]: The workspace provider with the specified identifier, or
            None if no such workspace is found.
        """
        for provider in self:
            if provider.id == workspace_id:
                return provider
        return None
