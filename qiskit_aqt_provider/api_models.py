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

import re
from typing import Any, Dict, List, Literal, Optional, Pattern, Union
from uuid import UUID

import httpx
import pydantic as pdt
from qiskit.providers.exceptions import JobError
from typing_extensions import Self, TypeAlias

from qiskit_aqt_provider import api_models_generated as api_models
from qiskit_aqt_provider.api_models_generated import (
    Circuit,
    JobSubmission,
    OperationModel,
    QuantumCircuit,
    QuantumCircuits,
)
from qiskit_aqt_provider.api_models_generated import Type as ResourceType
from qiskit_aqt_provider.versions import USER_AGENT

__all__ = [
    "Circuit",
    "JobResponse",
    "JobSubmission",
    "Operation",
    "OperationModel",
    "QuantumCircuit",
    "QuantumCircuits",
    "Response",
    "ResourceType",
]


class UnknownJobError(JobError):
    """An unknown job was requested from the AQT cloud portal."""


def http_client(*, base_url: str, token: str) -> httpx.Client:
    """A pre-configured httpx Client.

    Args:
        base_url: base URL of the server
        token: access token for the remote service.
    """
    headers = {"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT}
    return httpx.Client(headers=headers, base_url=base_url, timeout=10.0)


class Workspaces(pdt.BaseModel, extra=pdt.Extra.forbid, frozen=True):
    """List of available workspaces and devices."""

    __root__: List[api_models.Workspace]

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
            Workspaces model that only contains matching resources.
        """
        filtered_workspaces = []
        for workspace in self.__root__:
            if workspace_pattern is not None and not re.match(workspace_pattern, workspace.id):
                continue

            filtered_resources = []

            for resource in workspace.resources:
                if backend_type is not None and resource.type is not backend_type:
                    continue

                if name_pattern is not None and not re.match(name_pattern, resource.id):
                    continue

                filtered_resources.append(resource)

            filtered_workspaces.append(
                api_models.Workspace(id=workspace.id, resources=filtered_resources)
            )

        return self.__class__(__root__=filtered_workspaces)


GeneralResourceType: TypeAlias = Literal["device", "simulator", "offline_simulator"]


class ResourceId(pdt.BaseModel, frozen=True):
    """Resource identification and metadata."""

    workspace_id: str
    """Workspace containing the resource."""

    resource_id: str
    """Unique identifier of the resource in the containing workspace."""

    resource_name: str
    """Pretty display name for the resource."""

    resource_type: GeneralResourceType
    """Resource type, also includes offline simulators."""


class Operation:
    """Factories for API payloads of circuit operations."""

    @staticmethod
    def rz(*, phi: float, qubit: int) -> api_models.OperationModel:
        """RZ gate."""
        return api_models.OperationModel(
            __root__=api_models.GateRZ(operation="RZ", phi=phi, qubit=qubit)
        )

    @staticmethod
    def r(*, phi: float, theta: float, qubit: int) -> api_models.OperationModel:
        """R gate."""
        return api_models.OperationModel(
            __root__=api_models.GateR(operation="R", phi=phi, theta=theta, qubit=qubit)
        )

    @staticmethod
    def rxx(*, theta: float, qubits: List[int]) -> api_models.OperationModel:
        """RXX gate."""
        return api_models.OperationModel(
            __root__=api_models.GateRXX(
                operation="RXX",
                theta=theta,
                qubits=[api_models.Qubit(__root__=qubit) for qubit in qubits],
            )
        )

    @staticmethod
    def measure() -> api_models.OperationModel:
        """MEASURE operation."""
        return api_models.OperationModel(__root__=api_models.Measure(operation="MEASURE"))


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
    def parse_obj(data: Any) -> JobResponse:
        """Parse an API response.

        Returns:
            The corresponding JobResponse object.

        Raises:
            UnknownJobError: the server answered with an unknown job error.
        """
        response = api_models.ResultResponse.parse_obj(data).__root__

        if isinstance(response, api_models.UnknownJob):
            raise UnknownJobError(str(response.job_id))

        return response

    @staticmethod
    def queued(*, job_id: UUID, workspace_id: str, resource_id: str) -> JobResponse:
        """Queued job."""
        return api_models.JobResponseRRQueued(
            job=api_models.JobUser(
                job_id=job_id, label="qiskit", resource_id=resource_id, workspace_id=workspace_id
            ),
            response=api_models.RRQueued(),
        )

    @staticmethod
    def ongoing(
        *, job_id: UUID, workspace_id: str, resource_id: str, finished_count: int
    ) -> JobResponse:
        """Ongoing job."""
        return api_models.JobResponseRROngoing(
            job=api_models.JobUser(
                job_id=job_id, label="qiskit", resource_id=resource_id, workspace_id=workspace_id
            ),
            response=api_models.RROngoing(finished_count=finished_count),
        )

    @staticmethod
    def finished(
        *, job_id: UUID, workspace_id: str, resource_id: str, results: Dict[str, List[List[int]]]
    ) -> JobResponse:
        """Completed job with the given results."""
        return api_models.JobResponseRRFinished(
            job=api_models.JobUser(
                job_id=job_id,
                label="qiskit",
                resource_id=resource_id,
                workspace_id=workspace_id,
            ),
            response=api_models.RRFinished(
                result={
                    circuit_index: [
                        [api_models.ResultItem(__root__=state) for state in shot]
                        for shot in samples
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
                job_id=job_id, label="qiskit", resource_id=resource_id, workspace_id=workspace_id
            ),
            response=api_models.RRError(message=message),
        )

    @staticmethod
    def cancelled(*, job_id: UUID, workspace_id: str, resource_id: str) -> JobResponse:
        """Cancelled job."""
        return api_models.JobResponseRRCancelled(
            job=api_models.JobUser(
                job_id=job_id, label="qiskit", resource_id=resource_id, workspace_id=workspace_id
            ),
            response=api_models.RRCancelled(),
        )

    @staticmethod
    def unknown_job(*, job_id: UUID) -> api_models.UnknownJob:
        """Unknown job."""
        return api_models.UnknownJob(job_id=job_id)
