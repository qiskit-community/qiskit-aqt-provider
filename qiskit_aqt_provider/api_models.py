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

from typing import Any, Dict, List, Union
from uuid import UUID

from qiskit.providers.exceptions import JobError
from typing_extensions import TypeAlias

from qiskit_aqt_provider import api_models_generated as api_models
from qiskit_aqt_provider.api_models_generated import (
    Circuit,
    JobSubmission,
    OperationModel,
    QuantumCircuit,
    QuantumCircuits,
)

__all__ = [
    "Circuit",
    "JobResponse",
    "JobSubmission",
    "Operation",
    "OperationModel",
    "QuantumCircuit",
    "QuantumCircuits",
    "Response",
]


class UnknownJobError(JobError):
    """Requested an unknown job to the AQT API."""


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
