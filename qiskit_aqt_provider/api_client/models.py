# This code is part of Qiskit.
#
# (C) Copyright Alpine Quantum Technologies GmbH 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Thin convenience wrappers around aqt-connector models."""

import re
from collections.abc import Collection, Iterator
from re import Pattern
from typing import Literal, Optional, Union

from aqt_connector.models.arnica.resources import ResourceType
from aqt_connector.models.arnica.response_bodies.workspaces import Workspace as AQTWorkspace
from pydantic import BaseModel, ConfigDict, RootModel
from qiskit.providers.exceptions import JobError
from typing_extensions import Self, TypeAlias, override


class UnknownJobError(JobError):
    """An unknown job was requested from the AQT cloud portal."""


AQTBackendType: TypeAlias = Literal[
    ResourceType.DEVICE, ResourceType.SIMULATOR, "offline_simulator"
]


class Resource(BaseModel):
    """Description of a resource.

    This is the element type in :py:attr:`Workspace.resources`.
    """

    model_config = ConfigDict(frozen=True)

    workspace_id: str
    """Identifier of the workspace this resource belongs to."""

    resource_id: str
    """Resource identifier."""

    resource_name: str
    """Resource name."""

    resource_type: AQTBackendType
    """Type of resource."""

    available_qubits: int
    """Number of qubits jobs on this resource can use."""


class Workspace(BaseModel):
    """Description of a workspace and the resources it contains.

    This is the element type in the :py:class:`Workspaces` container.
    """

    model_config = ConfigDict(frozen=True)

    workspace_id: str
    """Workspace identifier."""

    resources: list[Resource]
    """Resources in the workspace."""


class ApiWorkspaces(
    RootModel  # type: ignore[type-arg]
):
    """List of available workspaces and devices, in API format."""

    root: list[AQTWorkspace]


class Workspaces(
    RootModel,  # type: ignore[type-arg]
    Collection[Workspace],
):
    """List of available workspaces and devices.

    ..
        >>> workspaces = Workspaces(
        ...     root=[
        ...         Workspace(
        ...             workspace_id="workspace0",
        ...             resources=[
        ...                 Resource(
        ...                     workspace_id="workspace0",
        ...                     resource_id="resource0",
        ...                     resource_name="resource0",
        ...                     resource_type="device",
        ...                     available_qubits=10,
        ...                 ),
        ...             ],
        ...         ),
        ...        Workspace(
        ...            workspace_id="workspace1",
        ...            resources=[
        ...                Resource(
        ...                    workspace_id="workspace1",
        ...                    resource_id="resource0",
        ...                    resource_name="resource0",
        ...                    resource_type="device",
        ...                    available_qubits=20,
        ...                ),
        ...                Resource(
        ...                    workspace_id="workspace1",
        ...                    resource_id="resource1",
        ...                    resource_name="resource1",
        ...                    resource_type="simulator",
        ...                    available_qubits=12,
        ...                ),
        ...            ],
        ...        ),
        ...    ]
        ... )

    Examples:
        Assume a :py:class:`Workspaces` instance retrieved from the API with
        the following contents:

        .. code-block::

            | Workspace ID | Resource ID | Resource Type | Available Qubits |
            |--------------+-------------+---------------|--------|
            | workspace0   | resource0   | device        |     10 |
            | workspace1   | resource0   | device        |     20 |
            | workspace1   | resource1   | simulator     |     12 |

        Gather basic information:

        >>> # workspaces = PortalClient(...).workspaces()
        >>> len(workspaces)
        2
        >>> [ws.workspace_id for ws in workspaces]
        ['workspace0', 'workspace1']

        Inclusion tests rely only on the identifier:

        >>> Workspace(workspace_id="workspace0", resources=[]) in workspaces
        True

        The :py:meth:`Workspaces.filter` method allows for complex filtering. For example
        by workspace identifier ending in ``0``:

        >>> [ws.workspace_id for ws in workspaces.filter(workspace_pattern=re.compile(".+0$"))]
        ['workspace0']

        or only the non-simulated devices:

        >>> workspaces_devices = workspaces.filter(backend_type="device")
        >>> [(ws.workspace_id, resource.resource_id)
        ...  for ws in workspaces_devices for resource in ws.resources]
        [('workspace0', 'resource0'), ('workspace1', 'resource0')]
    """

    root: list[Workspace]

    @override
    def __len__(self) -> int:
        """Number of available workspaces."""
        return len(self.root)

    @override
    def __iter__(self) -> Iterator[Workspace]:  # type: ignore[override]
        """Iterator over the workspaces."""
        yield from self.root

    @override
    def __contains__(self, obj: object) -> bool:
        """Whether a given workspace is in this workspaces collection."""
        if not isinstance(obj, Workspace):  # pragma: no cover
            return False

        return any(ws.workspace_id == obj.workspace_id for ws in self.root)

    def filter(
        self,
        *,
        workspace_pattern: Optional[Union[str, Pattern[str]]] = None,
        name_pattern: Optional[Union[str, Pattern[str]]] = None,
        backend_type: Optional[AQTBackendType] = None,
    ) -> Self:
        """Filtered copy of the list of available workspaces and devices.

        Omitted criteria match any entry in the respective field.

        Args:
            workspace_pattern: pattern for the workspace ID to match
            name_pattern: pattern for the resource ID to match
            backend_type: backend type to select.

        Returns:
            :py:class:`Workspaces` instance that only contains matching resources.
        """
        filtered_workspaces = []
        for workspace in self.root:
            if workspace_pattern is not None and not re.match(
                workspace_pattern, workspace.workspace_id
            ):
                continue

            filtered_resources = []

            for resource in workspace.resources:
                if backend_type is not None and resource.resource_type != backend_type:
                    continue

                if name_pattern is not None and not re.match(name_pattern, resource.resource_id):
                    continue

                filtered_resources.append(resource)

            filtered_workspaces.append(
                Workspace(workspace_id=workspace.workspace_id, resources=filtered_resources)
            )

        return self.__class__(root=filtered_workspaces)
