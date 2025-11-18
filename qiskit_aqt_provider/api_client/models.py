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

import importlib.metadata
import platform
import re
from collections.abc import Collection, Iterator
from re import Pattern
from typing import Final, Literal, Optional, Union
from uuid import UUID

import httpx
from aqt_connector.models.arnica.jobs import BasicJobMetadata
from aqt_connector.models.arnica.response_bodies.jobs import (
    ResultResponse,
    RRCancelled,
    RRError,
    RRFinished,
    RROngoing,
    RRQueued,
)
from aqt_connector.models.arnica.response_bodies.workspaces import Workspace as AQTWorkspace
from aqt_connector.models.operations import GateR, GateRXX, GateRZ, Measure, OperationModel
from pydantic import BaseModel, ConfigDict, NonNegativeInt, RootModel
from qiskit.providers.exceptions import JobError
from typing_extensions import Self, TypeAlias, override


class UnknownJobError(JobError):
    """An unknown job was requested from the AQT cloud portal."""


PACKAGE_VERSION: Final = importlib.metadata.version("qiskit-aqt-provider")
USER_AGENT: Final = " ".join(
    [
        f"aqt-api-client/{PACKAGE_VERSION}",
        f"({platform.system()}; {platform.python_implementation()}/{platform.python_version()})",
    ]
)


def http_client(
    *, base_url: str, token: str, user_agent_extra: Optional[str] = None
) -> httpx.Client:
    """A pre-configured httpx Client.

    Args:
        base_url: base URL of the server
        token: access token for the remote service.
        user_agent_extra: optional extra data to add to the user-agent string.
    """
    user_agent_extra = f" {user_agent_extra}" if user_agent_extra else ""
    headers = {"User-Agent": USER_AGENT + user_agent_extra}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    return httpx.Client(headers=headers, base_url=base_url, timeout=10.0, follow_redirects=True)


AQTBackendType: TypeAlias = Literal["device", "simulator", "offline_simulator"]


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


class Operation:
    """Factories for API payloads of circuit operations."""

    @staticmethod
    def rz(*, phi: float, qubit: int) -> OperationModel:
        """RZ gate."""
        return OperationModel(root=GateRZ(operation="RZ", phi=phi, qubit=qubit))

    @staticmethod
    def r(*, phi: float, theta: float, qubit: int) -> OperationModel:
        """R gate."""
        return OperationModel(root=GateR(operation="R", phi=phi, theta=theta, qubit=qubit))

    @staticmethod
    def rxx(*, theta: float, qubits: list[NonNegativeInt]) -> OperationModel:
        """RXX gate."""
        return OperationModel(
            root=GateRXX(
                operation="RXX",
                theta=theta,
                qubits=list(qubits),
            )
        )

    @staticmethod
    def measure() -> OperationModel:
        """MEASURE operation."""
        return OperationModel(root=Measure(operation="MEASURE"))


JobFinalState: TypeAlias = Union[
    RRFinished,
    RRError,
    RRCancelled,
]


class Response:
    """Factories for API response payloads."""

    @staticmethod
    def queued(*, job_id: UUID, workspace_id: str, resource_id: str) -> ResultResponse:
        """Queued job."""
        return ResultResponse(
            job=BasicJobMetadata(
                job_id=job_id,
                label="qiskit",
                resource_id=resource_id,
                workspace_id=workspace_id,
            ),
            response=RRQueued(),
        )

    @staticmethod
    def ongoing(
        *, job_id: UUID, workspace_id: str, resource_id: str, finished_count: int
    ) -> ResultResponse:
        """Ongoing job."""
        return ResultResponse(
            job=BasicJobMetadata(
                job_id=job_id,
                label="qiskit",
                resource_id=resource_id,
                workspace_id=workspace_id,
            ),
            response=RROngoing(finished_count=finished_count),
        )

    @staticmethod
    def finished(
        *, job_id: UUID, workspace_id: str, resource_id: str, results: dict[str, list[list[int]]]
    ) -> ResultResponse:
        """Completed job with the given results."""
        return ResultResponse(
            job=BasicJobMetadata(
                job_id=job_id,
                label="qiskit",
                resource_id=resource_id,
                workspace_id=workspace_id,
            ),
            response=RRFinished(
                result={
                    int(circuit_index): [list(shot) for shot in samples]
                    for circuit_index, samples in results.items()
                },
            ),
        )

    @staticmethod
    def error(*, job_id: UUID, workspace_id: str, resource_id: str, message: str) -> ResultResponse:
        """Failed job."""
        return ResultResponse(
            job=BasicJobMetadata(
                job_id=job_id,
                label="qiskit",
                resource_id=resource_id,
                workspace_id=workspace_id,
            ),
            response=RRError(message=message),
        )

    @staticmethod
    def cancelled(*, job_id: UUID, workspace_id: str, resource_id: str) -> ResultResponse:
        """Cancelled job."""
        return ResultResponse(
            job=BasicJobMetadata(
                job_id=job_id,
                label="qiskit",
                resource_id=resource_id,
                workspace_id=workspace_id,
            ),
            response=RRCancelled(),
        )
