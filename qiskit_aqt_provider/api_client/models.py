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

"""Thin convenience wrappers around generated API models."""

import importlib.metadata
import platform
import re
import typing
from collections.abc import Collection, Iterator
from re import Pattern
from typing import Any, Final, Literal, Optional, Union
from uuid import UUID

import httpx
import pydantic as pdt
from qiskit.providers.exceptions import JobError
from typing_extensions import Self, TypeAlias, override

from . import models_generated as api_models
from .models_generated import (
    Circuit,
    OperationModel,
    QuantumCircuit,
    QuantumCircuits,
    SubmitJobRequest,
)

__all__ = [
    "Circuit",
    "JobResponse",
    "Operation",
    "OperationModel",
    "QuantumCircuit",
    "QuantumCircuits",
    "Response",
    "SubmitJobRequest",
]


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


ResourceType: TypeAlias = Literal["device", "simulator", "offline_simulator"]


class Resource(pdt.BaseModel):
    """Description of a resource.

    This is the element type in :py:attr:`Workspace.resources`.
    """

    model_config = pdt.ConfigDict(frozen=True)

    workspace_id: str
    """Identifier of the workspace this resource belongs to."""

    resource_id: str
    """Resource identifier."""

    resource_name: str
    """Resource name."""

    resource_type: ResourceType
    """Type of resource."""


class Workspace(pdt.BaseModel):
    """Description of a workspace and the resources it contains.

    This is the element type in the :py:class:`Workspaces` container.
    """

    model_config = pdt.ConfigDict(frozen=True)

    workspace_id: str
    """Workspace identifier."""

    resources: list[Resource]
    """Resources in the workspace."""


class Workspaces(
    pdt.RootModel,  # type: ignore[type-arg]
    Collection[Workspace],
):
    """List of available workspaces and devices.

    ..
        >>> workspaces = Workspaces(
        ...     root=[
        ...         api_models.Workspace(
        ...             id="workspace0",
        ...             resources=[
        ...                 api_models.Resource(
        ...                     id="resource0",
        ...                     name="resource0",
        ...                     type=api_models.Type.device,
        ...                 ),
        ...             ],
        ...         ),
        ...        api_models.Workspace(
        ...            id="workspace1",
        ...            resources=[
        ...                api_models.Resource(
        ...                    id="resource0",
        ...                    name="resource0",
        ...                    type=api_models.Type.device,
        ...                ),
        ...                api_models.Resource(
        ...                    id="resource1",
        ...                    name="resource1",
        ...                    type=api_models.Type.simulator,
        ...                ),
        ...            ],
        ...        ),
        ...    ]
        ... )

    Examples:
        Assume a :py:class:`Workspaces` instance retrieved from the API with
        the following contents:

        .. code-block::

            | Workspace ID | Resource ID | Resource Type |
            |--------------+-------------+---------------|
            | workspace0   | resource0   | device        |
            | workspace1   | resource0   | device        |
            | workspace1   | resource1   | simulator     |

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

    root: list[api_models.Workspace]

    @override
    def __len__(self) -> int:
        """Number of available workspaces."""
        return len(self.root)

    @override
    def __iter__(self) -> Iterator[Workspace]:  # type: ignore[override]
        """Iterator over the workspaces."""
        for ws in self.root:
            yield Workspace(
                workspace_id=ws.id,
                resources=[
                    Resource(
                        workspace_id=ws.id,
                        resource_id=res.id,
                        resource_name=res.name,
                        resource_type=typing.cast(ResourceType, res.type.value),
                    )
                    for res in ws.resources
                ],
            )

    @override
    def __contains__(self, obj: object) -> bool:
        """Whether a given workspace is in this workspaces collection."""
        if not isinstance(obj, Workspace):  # pragma: no cover
            return False

        return any(ws.id == obj.workspace_id for ws in self.root)

    def filter(
        self,
        *,
        workspace_pattern: Optional[Union[str, Pattern[str]]] = None,
        name_pattern: Optional[Union[str, Pattern[str]]] = None,
        backend_type: Optional[ResourceType] = None,
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
            if workspace_pattern is not None and not re.match(workspace_pattern, workspace.id):
                continue

            filtered_resources = []

            for resource in workspace.resources:
                if backend_type is not None and resource.type.value != backend_type:
                    continue

                if name_pattern is not None and not re.match(name_pattern, resource.id):
                    continue

                filtered_resources.append(resource)

            filtered_workspaces.append(
                api_models.Workspace(id=workspace.id, resources=filtered_resources)
            )

        return self.__class__(root=filtered_workspaces)


class Operation:
    """Factories for API payloads of circuit operations."""

    @staticmethod
    def rz(*, phi: float, qubit: int) -> api_models.OperationModel:
        """RZ gate."""
        return api_models.OperationModel(
            root=api_models.GateRZ(operation="RZ", phi=phi, qubit=qubit)
        )

    @staticmethod
    def r(*, phi: float, theta: float, qubit: int) -> api_models.OperationModel:
        """R gate."""
        return api_models.OperationModel(
            root=api_models.GateR(operation="R", phi=phi, theta=theta, qubit=qubit)
        )

    @staticmethod
    def rxx(*, theta: float, qubits: list[int]) -> api_models.OperationModel:
        """RXX gate."""
        return api_models.OperationModel(
            root=api_models.GateRXX(
                operation="RXX",
                theta=theta,
                qubits=[api_models.Qubit(root=qubit) for qubit in qubits],
            )
        )

    @staticmethod
    def measure() -> api_models.OperationModel:
        """MEASURE operation."""
        return api_models.OperationModel(root=api_models.Measure(operation="MEASURE"))


JobResponse: TypeAlias = Union[
    api_models.JobResponseRRQueued,
    api_models.JobResponseRROngoing,
    api_models.JobResponseRRFinished,
    api_models.JobResponseRRError,
    api_models.JobResponseRRCancelled,
]

JobFinalState: TypeAlias = Union[
    api_models.JobResponseRRFinished,
    api_models.JobResponseRRError,
    api_models.JobResponseRRCancelled,
]


class Response:
    """Factories for API response payloads."""

    @staticmethod
    def model_validate(data: Any) -> JobResponse:
        """Parse an API response.

        Returns:
            The corresponding JobResponse object.

        Raises:
            UnknownJobError: the server answered with an unknown job error.
        """
        response = api_models.ResultResponse.model_validate(data).root

        if isinstance(response, api_models.UnknownJob):
            raise UnknownJobError(str(response.job_id))

        return response

    @staticmethod
    def queued(*, job_id: UUID, workspace_id: str, resource_id: str) -> JobResponse:
        """Queued job."""
        return api_models.JobResponseRRQueued(
            job=api_models.JobUser(
                job_type="quantum_circuit",
                job_id=job_id,
                label="qiskit",
                resource_id=resource_id,
                workspace_id=workspace_id,
            ),
            response=api_models.RRQueued(status="queued"),
        )

    @staticmethod
    def ongoing(
        *, job_id: UUID, workspace_id: str, resource_id: str, finished_count: int
    ) -> JobResponse:
        """Ongoing job."""
        return api_models.JobResponseRROngoing(
            job=api_models.JobUser(
                job_type="quantum_circuit",
                job_id=job_id,
                label="qiskit",
                resource_id=resource_id,
                workspace_id=workspace_id,
            ),
            response=api_models.RROngoing(status="ongoing", finished_count=finished_count),
        )

    @staticmethod
    def finished(
        *, job_id: UUID, workspace_id: str, resource_id: str, results: dict[str, list[list[int]]]
    ) -> JobResponse:
        """Completed job with the given results."""
        return api_models.JobResponseRRFinished(
            job=api_models.JobUser(
                job_type="quantum_circuit",
                job_id=job_id,
                label="qiskit",
                resource_id=resource_id,
                workspace_id=workspace_id,
            ),
            response=api_models.RRFinished(
                status="finished",
                result={
                    circuit_index: [
                        [api_models.ResultItem(root=state) for state in shot] for shot in samples
                    ]
                    for circuit_index, samples in results.items()
                },
            ),
        )

    @staticmethod
    def error(*, job_id: UUID, workspace_id: str, resource_id: str, message: str) -> JobResponse:
        """Failed job."""
        return api_models.JobResponseRRError(
            job=api_models.JobUser(
                job_type="quantum_circuit",
                job_id=job_id,
                label="qiskit",
                resource_id=resource_id,
                workspace_id=workspace_id,
            ),
            response=api_models.RRError(status="error", message=message),
        )

    @staticmethod
    def cancelled(*, job_id: UUID, workspace_id: str, resource_id: str) -> JobResponse:
        """Cancelled job."""
        return api_models.JobResponseRRCancelled(
            job=api_models.JobUser(
                job_type="quantum_circuit",
                job_id=job_id,
                label="qiskit",
                resource_id=resource_id,
                workspace_id=workspace_id,
            ),
            response=api_models.RRCancelled(status="cancelled"),
        )

    @staticmethod
    def unknown_job(*, job_id: UUID) -> api_models.UnknownJob:
        """Unknown job."""
        return api_models.UnknownJob(job_id=job_id, message="unknown job_id")
